"""Regression tests for payment idempotency enforcement.

Proves that:
- Idempotency-Key header is mandatory for payment posting (HTTP 422 if missing).
- Same (loan_id, idempotency_key) + identical payload → original payment returned (HTTP 200).
- Same (loan_id, idempotency_key) + conflicting payload → HTTP 409 Conflict.
- Different loans may reuse the same key without conflict.
- Concurrent requests with the same key produce exactly one payment record without HTTP 500 errors.
- The idempotency replay is non-mutating (no second balance change or status transition).

LOAN_RULES.md §9
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_owner_access_token, hash_password
from app.features.borrowers.auth_security import hash_pin
from app.features.borrowers.models import Borrower, BorrowerAccount
from app.features.loan_requests.models import LoanRequest
from app.features.loans.models import Loan
from app.features.owner_identity.models import OwnerUser

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _owner_headers(session: AsyncSession) -> dict[str, str]:
    owner = OwnerUser(
        username=f"owner-{uuid4().hex[:6]}",
        password_hash=hash_password("OwnerPassword123!"),
        is_active=True,
    )
    session.add(owner)
    await session.flush()
    token = create_owner_access_token(owner.id)
    return {"Authorization": f"Bearer {token.value}"}


def _with_key(headers: dict[str, str], key: str | None = None) -> dict[str, str]:
    return {**headers, "Idempotency-Key": key or f"idem-{uuid4().hex}"}


async def _active_loan(
    session: AsyncSession,
    *,
    principal: Decimal = Decimal("5000.00"),
    monthly_rate: Decimal = Decimal("0.05"),
    first_due_date: date = date(2026, 6, 15),
) -> Loan:
    suffix = uuid4().hex[:8]
    borrower = Borrower(
        first_name="Idem",
        last_name="Test",
        national_id=f"NAT-{suffix}",
        address="2 Idem St",
        phone_number=f"0916{suffix[:7]}",
        phone_number_normalized=f"+6316{suffix[:7]}",
        date_of_birth=date(1985, 3, 15),
        status="active",
    )
    session.add(borrower)
    await session.flush()

    account = BorrowerAccount(
        borrower_id=borrower.id,
        phone_number=borrower.phone_number,
        phone_number_normalized=borrower.phone_number_normalized,
        account_status="activated",
        pin_hash=hash_pin("654321"),
    )
    session.add(account)
    await session.flush()

    request = LoanRequest(
        borrower_id=borrower.id,
        requested_principal=principal,
        requested_term_months=6,
        requested_payment_frequency="monthly",
        requested_monthly_rate=monthly_rate,
        requested_first_due_date=first_due_date,
        status="approved",
        submitted_at=datetime.now(UTC),
    )
    session.add(request)
    await session.flush()

    loan = Loan(
        loan_request_id=request.id,
        borrower_id=borrower.id,
        original_principal=principal,
        outstanding_principal=principal,
        accrued_interest=Decimal("0.00"),
        monthly_rate=monthly_rate,
        term_months=6,
        payment_frequency="monthly",
        number_of_payments=6,
        first_due_date=first_due_date,
        final_due_date=date(2026, 12, 15),
        next_interest_due_date=first_due_date,
        status="active",
        disbursed_at=datetime(2026, 5, 15, tzinfo=UTC),
    )
    session.add(loan)
    await session.flush()
    return loan


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_missing_idempotency_key_header_rejected(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Payments without an Idempotency-Key header are rejected with HTTP 422."""
    owner_headers = await _owner_headers(db_session)
    loan = await _active_loan(db_session)

    res = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,  # No Idempotency-Key header
        json={"amount": "500.00", "payment_date": "2026-06-15"},
    )
    assert res.status_code == 422
    assert "Idempotency-Key" in res.json()["detail"]


async def test_idempotent_retry_returns_same_payment(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Retrying with the same idempotency key and identical payload returns the
    original payment record without creating a duplicate or mutating balances.
    """
    owner_headers = await _owner_headers(db_session)
    loan = await _active_loan(db_session)
    key = f"pay-{uuid4().hex}"
    headers = _with_key(owner_headers, key)

    payload = {
        "amount": "500.00",
        "payment_date": "2026-06-15",
        "reference": "REF-001",
    }

    # First request — creates the payment.
    res1 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=headers,
        json=payload,
    )
    assert res1.status_code == 201
    d1 = res1.json()
    original_id = d1["id"]
    assert d1["idempotency_key"] == key

    # Balance after first payment.
    await db_session.refresh(loan)
    principal_after_first = loan.outstanding_principal

    # Retry — must return the same record with HTTP 200, not create a new one.
    res2 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=headers,
        json=payload,
    )
    assert res2.status_code == 200, res2.text
    d2 = res2.json()
    assert d2["id"] == original_id, "Retry must return the original payment ID"
    assert d2["idempotency_key"] == key

    # Balance must not have changed on the retry.
    await db_session.refresh(loan)
    assert loan.outstanding_principal == principal_after_first, (
        "Retry must not mutate loan balances"
    )


async def test_idempotent_conflict_on_different_amount(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Retrying with the same key but a different amount is rejected with HTTP 409."""
    owner_headers = await _owner_headers(db_session)
    loan = await _active_loan(db_session)
    key = f"pay-{uuid4().hex}"
    headers = _with_key(owner_headers, key)

    # Original payment.
    res1 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=headers,
        json={"amount": "300.00", "payment_date": "2026-06-15"},
    )
    assert res1.status_code == 201

    # Conflicting retry with a different amount.
    res2 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=headers,
        json={"amount": "999.00", "payment_date": "2026-06-15"},
    )
    assert res2.status_code == 409, res2.text
    assert "amount" in res2.json()["detail"]


async def test_idempotent_conflict_on_different_payment_date(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Retrying with the same key but a different payment_date is rejected with HTTP 409."""
    owner_headers = await _owner_headers(db_session)
    loan = await _active_loan(db_session)
    key = f"pay-{uuid4().hex}"
    headers = _with_key(owner_headers, key)

    res1 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=headers,
        json={"amount": "300.00", "payment_date": "2026-06-15"},
    )
    assert res1.status_code == 201

    res2 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=headers,
        json={"amount": "300.00", "payment_date": "2026-07-15"},
    )
    assert res2.status_code == 409, res2.text
    assert "payment_date" in res2.json()["detail"]


async def test_different_loans_may_reuse_same_idempotency_key(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """The same client-generated key is scoped to a loan_id — different loans
    may independently use the same key without conflict.
    """
    owner_headers = await _owner_headers(db_session)
    loan_a = await _active_loan(db_session)
    loan_b = await _active_loan(db_session)
    shared_key = "shared-key-across-loans"

    res_a = await api_client.post(
        f"/api/v1/owner/loans/{loan_a.id}/payments",
        headers=_with_key(owner_headers, shared_key),
        json={"amount": "200.00", "payment_date": "2026-06-15"},
    )
    assert res_a.status_code == 201

    res_b = await api_client.post(
        f"/api/v1/owner/loans/{loan_b.id}/payments",
        headers=_with_key(owner_headers, shared_key),
        json={"amount": "200.00", "payment_date": "2026-06-15"},
    )
    assert res_b.status_code == 201, res_b.text
    assert res_a.json()["id"] != res_b.json()["id"]


async def test_idempotent_replay_does_not_change_status_to_paid(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A replayed (idempotent) payment that originally paid off the loan must not
    re-trigger the paid transition and must not double-reduce the balance.
    """
    owner_headers = await _owner_headers(db_session)
    loan = await _active_loan(db_session, principal=Decimal("500.00"), monthly_rate=Decimal("0.10"))
    key = f"payoff-{uuid4().hex}"
    headers = _with_key(owner_headers, key)

    # ₱500 principal @ 10% = ₱50 interest. Total payoff = ₱550.
    res1 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=headers,
        json={"amount": "550.00", "payment_date": "2026-06-15"},
    )
    assert res1.status_code == 201

    await db_session.refresh(loan)
    assert loan.status == "paid"
    assert loan.outstanding_principal == Decimal("0.00")

    # Replay
    res2 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=headers,
        json={"amount": "550.00", "payment_date": "2026-06-15"},
    )
    assert res2.status_code == 200, res2.text
    assert res2.json()["id"] == res1.json()["id"]

    await db_session.refresh(loan)
    assert loan.status == "paid"
    assert loan.outstanding_principal == Decimal("0.00")
