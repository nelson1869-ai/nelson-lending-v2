"""Regression tests for partial-interest carryover across sequential payments.

Proves that when a payment only partially covers accrued interest, the unpaid
remainder is carried forward and satisfied by the next payment BEFORE any
new period's interest is added — not silently discarded or recalculated fresh.

LOAN_RULES.md §3, §7:
  "A payment first satisfies accrued or due interest, then reduces principal."
  "Partial payments are allowed and follow the canonical allocation order."
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
# Helpers (duplicated locally so this module is fully self-contained)
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


async def _active_loan(
    session: AsyncSession,
    *,
    principal: Decimal,
    monthly_rate: Decimal,
    accrued_interest: Decimal = Decimal("0.00"),
) -> Loan:
    """Create a minimal active loan with specified financial terms."""
    suffix = uuid4().hex[:8]
    borrower = Borrower(
        first_name="Test",
        last_name="Borrower",
        national_id=f"NAT-{suffix}",
        address="1 Test St",
        phone_number=f"0917{suffix[:7]}",
        phone_number_normalized=f"+6317{suffix[:7]}",
        date_of_birth=date(1990, 1, 1),
        status="active",
    )
    session.add(borrower)
    await session.flush()

    account = BorrowerAccount(
        borrower_id=borrower.id,
        phone_number=borrower.phone_number,
        phone_number_normalized=borrower.phone_number_normalized,
        account_status="activated",
        pin_hash=hash_pin("123456"),
    )
    session.add(account)
    await session.flush()

    request = LoanRequest(
        borrower_id=borrower.id,
        requested_principal=principal,
        requested_term_months=3,
        requested_payment_frequency="monthly",
        requested_monthly_rate=monthly_rate,
        requested_first_due_date=date(2026, 9, 15),
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
        accrued_interest=accrued_interest,
        monthly_rate=monthly_rate,
        term_months=3,
        payment_frequency="monthly",
        number_of_payments=3,
        first_due_date=date(2026, 9, 15),
        final_due_date=date(2026, 11, 15),
        status="active",
        disbursed_at=datetime.now(UTC),
    )
    session.add(loan)
    await session.flush()
    return loan


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_partial_interest_payment_carries_forward(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Partial interest payment leaves remaining_interest > 0 on the payment record.

    Setup: ₱2,000 principal @ 10%/month → ₱200 interest this period.
    Payment 1: ₱100 (only covers half the interest).

    Expected:
      interest_paid     = ₱100
      principal_paid    = ₱0
      remaining_interest= ₱100
      remaining_principal=₱2,000
      loan.accrued_interest = ₱100   (carried forward)
      loan.outstanding_principal = ₱2,000  (unchanged)
    """
    owner_headers = await _owner_headers(db_session)
    loan = await _active_loan(
        db_session, principal=Decimal("2000.00"), monthly_rate=Decimal("0.10")
    )

    res = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={"amount": "100.00", "payment_date": "2026-09-15"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["interest_paid"] == "100.00"
    assert data["principal_paid"] == "0.00"
    assert data["remaining_interest"] == "100.00"
    assert data["remaining_principal"] == "2000.00"
    assert data["unapplied_credit"] == "0.00"

    await db_session.refresh(loan)
    assert loan.accrued_interest == Decimal("100.00")
    assert loan.outstanding_principal == Decimal("2000.00")
    assert loan.status == "active"


async def test_second_payment_resolves_prior_partial_interest_before_new_period(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """After a partial interest payment the next payment:
    1. First covers the carried-forward ₱100 unpaid interest.
    2. Then adds new period interest on the (still unchanged) ₱2,000 principal: ₱200.
    3. Total interest owed at payment 2 = ₱100 (carried) + ₱200 (new) = ₱300.
    4. Payment 2 = ₱300 → exactly zeroes interest, zero principal reduction.

    This proves the service accumulates, rather than discards, unpaid interest.
    """
    owner_headers = await _owner_headers(db_session)
    # Start with ₱100 already accrued (simulates the state after payment 1 above).
    loan = await _active_loan(
        db_session,
        principal=Decimal("2000.00"),
        monthly_rate=Decimal("0.10"),
        accrued_interest=Decimal("100.00"),
    )

    # Payment 2: must cover ₱100 carried + ₱200 new-period = ₱300 total to clear interest.
    res = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={"amount": "300.00", "payment_date": "2026-10-15"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["interest_paid"] == "300.00"
    assert data["principal_paid"] == "0.00"
    assert data["remaining_interest"] == "0.00"
    assert data["remaining_principal"] == "2000.00"

    await db_session.refresh(loan)
    assert loan.accrued_interest == Decimal("0.00")
    assert loan.outstanding_principal == Decimal("2000.00")


async def test_payment_in_excess_of_accrued_interest_reduces_principal(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Payment exceeding total accrued interest reduces principal correctly.

    Accrued ₱100 + new period ₱200 = ₱300 total due.
    Payment ₱500 → ₱300 interest, ₱200 principal, zero remaining.
    """
    owner_headers = await _owner_headers(db_session)
    loan = await _active_loan(
        db_session,
        principal=Decimal("2000.00"),
        monthly_rate=Decimal("0.10"),
        accrued_interest=Decimal("100.00"),
    )

    res = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={"amount": "500.00", "payment_date": "2026-10-15"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["interest_paid"] == "300.00"
    assert data["principal_paid"] == "200.00"
    assert data["remaining_interest"] == "0.00"
    assert data["remaining_principal"] == "1800.00"

    await db_session.refresh(loan)
    assert loan.accrued_interest == Decimal("0.00")
    assert loan.outstanding_principal == Decimal("1800.00")


async def test_future_interest_uses_reduced_principal(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Canonical LOAN_RULES §3.1 sequence via HTTP endpoints.

    Payment 1 (₱700): clears ₱200 interest + ₱500 principal → outstanding = ₱1,500.
    Payment 2 (₱700): new-period interest on ₱1,500 @ 10% = ₱150.
      interest_paid = ₱150, principal_paid = ₱550, remaining_principal = ₱950.
    """
    owner_headers = await _owner_headers(db_session)
    loan = await _active_loan(
        db_session, principal=Decimal("2000.00"), monthly_rate=Decimal("0.10")
    )

    # Payment 1
    res1 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={"amount": "700.00", "payment_date": "2026-09-15"},
    )
    assert res1.status_code == 201
    d1 = res1.json()
    assert d1["interest_paid"] == "200.00"
    assert d1["principal_paid"] == "500.00"
    assert d1["remaining_principal"] == "1500.00"

    await db_session.refresh(loan)
    assert loan.outstanding_principal == Decimal("1500.00")
    assert loan.accrued_interest == Decimal("0.00")

    # Payment 2 — interest must be based on ₱1,500, not ₱2,000
    res2 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={"amount": "700.00", "payment_date": "2026-10-15"},
    )
    assert res2.status_code == 201
    d2 = res2.json()
    assert d2["interest_paid"] == "150.00"
    assert d2["principal_paid"] == "550.00"
    assert d2["remaining_principal"] == "950.00"

    await db_session.refresh(loan)
    assert loan.outstanding_principal == Decimal("950.00")
    assert loan.accrued_interest == Decimal("0.00")
