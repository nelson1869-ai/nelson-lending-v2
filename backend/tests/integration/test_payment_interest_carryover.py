"""Regression tests for contractual interest accrual periods and payment allocation.

Proves that:
- Interest accrues ONCE per contractual period when payment_date >= next_interest_due_date.
- Subsequent payments within the SAME contractual period do NOT trigger duplicate interest.
- Unpaid interest from a partial payment carries forward before any new period interest.
- Future interest is calculated on reduced principal only when the next contractual period arrives.
- Early payoff excludes future unaccrued interest.
- Payments dated in the future or backdated before the latest payment date are rejected.

LOAN_RULES.md §3, §4, §7
"""

from datetime import UTC, date, datetime, timedelta
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
    return {
        "Authorization": f"Bearer {token.value}",
        "Idempotency-Key": f"idem-{uuid4().hex}",
    }


def _with_key(headers: dict[str, str], key: str | None = None) -> dict[str, str]:
    return {**headers, "Idempotency-Key": key or f"idem-{uuid4().hex}"}


async def _active_loan(
    session: AsyncSession,
    *,
    principal: Decimal,
    monthly_rate: Decimal,
    first_due_date: date = date(2026, 6, 30),
    payment_frequency: str = "monthly",
    accrued_interest: Decimal = Decimal("0.00"),
    next_interest_due_date: date | None = None,
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
        requested_payment_frequency=payment_frequency,
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
        accrued_interest=accrued_interest,
        monthly_rate=monthly_rate,
        term_months=3,
        payment_frequency=payment_frequency,
        number_of_payments=3,
        first_due_date=first_due_date,
        final_due_date=first_due_date + timedelta(days=90),
        next_interest_due_date=next_interest_due_date or first_due_date,
        status="active",
        disbursed_at=datetime.combine(first_due_date - timedelta(days=15), datetime.min.time(), tzinfo=UTC),
    )
    session.add(loan)
    await session.flush()
    return loan


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_same_period_two_partial_payments(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Proves two partial payments in SAME contractual period do NOT double-accrue interest.

    Setup: ₱2,000 principal @ 10%/month. Due date: 2026-06-30.
    Payment 1 (2026-06-30): ₱100.
      Interest due for 2026-06-30 period: ₱200.
      Allocation: ₱100 interest paid, ₱100 accrued interest remaining, ₱0 principal paid.
    Payment 2 (2026-06-30, SAME period): ₱100.
      No new period interest accrued (next_interest_due_date is now 2026-07-30).
      Allocation: ₱100 interest paid against remaining accrued interest, ₱0 principal paid.
    Total: ₱200 interest paid, ₱0 remaining accrued interest, ₱2,000 outstanding principal.
    """
    headers = await _owner_headers(db_session)
    loan = await _active_loan(
        db_session, principal=Decimal("2000.00"), monthly_rate=Decimal("0.10")
    )

    # Payment 1
    res1 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "100.00", "payment_date": "2026-06-30"},
    )
    assert res1.status_code == 201, res1.text
    d1 = res1.json()
    assert d1["interest_paid"] == "100.00"
    assert d1["principal_paid"] == "0.00"
    assert d1["remaining_interest"] == "100.00"
    assert d1["remaining_principal"] == "2000.00"

    await db_session.refresh(loan)
    assert loan.accrued_interest == Decimal("100.00")
    assert loan.next_interest_due_date == date(2026, 7, 30)

    # Payment 2 in SAME contractual period
    res2 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "100.00", "payment_date": "2026-06-30"},
    )
    assert res2.status_code == 201, res2.text
    d2 = res2.json()
    assert d2["interest_paid"] == "100.00"
    assert d2["principal_paid"] == "0.00"
    assert d2["remaining_interest"] == "0.00"
    assert d2["remaining_principal"] == "2000.00"

    await db_session.refresh(loan)
    assert loan.accrued_interest == Decimal("0.00")
    assert loan.outstanding_principal == Decimal("2000.00")


async def test_same_period_principal_reduction_and_second_payment(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Proves second payment in SAME period after principal reduction charges no interest.

    Setup: ₱2,000 @ 10% monthly. Due date: 2026-06-30.
    Payment 1 (2026-06-30): ₱700.
      Interest = ₱200, Principal = ₱500 -> remaining principal = ₱1,500.
    Payment 2 (2026-06-30, SAME period): ₱200.
      Interest due = ₱0 (no new period due).
      Principal paid = ₱200 -> remaining principal = ₱1,300.
    """
    headers = await _owner_headers(db_session)
    loan = await _active_loan(
        db_session, principal=Decimal("2000.00"), monthly_rate=Decimal("0.10")
    )

    # Payment 1
    res1 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "700.00", "payment_date": "2026-06-30"},
    )
    assert res1.status_code == 201
    d1 = res1.json()
    assert d1["interest_paid"] == "200.00"
    assert d1["principal_paid"] == "500.00"
    assert d1["remaining_principal"] == "1500.00"

    # Payment 2 in SAME period
    res2 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "200.00", "payment_date": "2026-06-30"},
    )
    assert res2.status_code == 201
    d2 = res2.json()
    assert d2["interest_paid"] == "0.00"
    assert d2["principal_paid"] == "200.00"
    assert d2["remaining_principal"] == "1300.00"

    await db_session.refresh(loan)
    assert loan.outstanding_principal == Decimal("1300.00")
    assert loan.accrued_interest == Decimal("0.00")


async def test_next_period_interest_uses_reduced_principal(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Proves interest is calculated on reduced principal when NEXT period arrives.

    Setup: principal reduced to ₱1,300.
    Next period (2026-07-31): 10% on ₱1,300 = ₱130.00.
    """
    headers = await _owner_headers(db_session)
    loan = await _active_loan(
        db_session, principal=Decimal("2000.00"), monthly_rate=Decimal("0.10")
    )

    # Jun 30 payment: ₱700 (reduces principal to ₱1,500) + ₱200 (reduces principal to ₱1,300)
    await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "700.00", "payment_date": "2026-06-30"},
    )
    await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "200.00", "payment_date": "2026-06-30"},
    )

    # Next period payment on 2026-07-31
    res3 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "130.00", "payment_date": "2026-07-31"},
    )
    assert res3.status_code == 201
    d3 = res3.json()
    assert d3["interest_paid"] == "130.00"
    assert d3["principal_paid"] == "0.00"
    assert d3["remaining_principal"] == "1300.00"


async def test_early_payoff_excludes_unaccrued_future_interest(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Proves that paying off the remaining principal in full before the next period arrives
    does NOT collect unaccrued future scheduled interest.
    """
    headers = await _owner_headers(db_session)
    loan = await _active_loan(
        db_session, principal=Decimal("2000.00"), monthly_rate=Decimal("0.10")
    )

    # Jun 30 payment: ₱200 interest + ₱2000 payoff = ₱2200 total on first due date
    res = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "2200.00", "payment_date": "2026-06-30"},
    )
    assert res.status_code == 201
    d = res.json()
    assert d["interest_paid"] == "200.00"
    assert d["principal_paid"] == "2000.00"
    assert d["remaining_principal"] == "0.00"
    assert d["remaining_interest"] == "0.00"

    await db_session.refresh(loan)
    assert loan.status == "paid"
    assert loan.outstanding_principal == Decimal("0.00")
    assert loan.accrued_interest == Decimal("0.00")


async def test_twice_monthly_accrual_rules(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Tests twice_monthly payment frequency accrual on 15th and month-end, including leap year.

    Loan: ₱4,000 @ 10% monthly (period rate = 5% per half month).
    First due date: 2024-02-15 (Leap year).
    Payment 1 (2024-02-15): 5% of ₱4,000 = ₱200.
    Payment 2 (2024-02-29, Feb end in leap year): 5% of ₱4,000 = ₱200.
    """
    headers = await _owner_headers(db_session)
    loan = await _active_loan(
        db_session,
        principal=Decimal("4000.00"),
        monthly_rate=Decimal("0.10"),
        payment_frequency="twice_monthly",
        first_due_date=date(2024, 2, 15),
    )

    # Feb 15 payment
    res1 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "200.00", "payment_date": "2024-02-15"},
    )
    assert res1.status_code == 201
    assert res1.json()["interest_paid"] == "200.00"

    # Feb 29 (Leap year end of month) payment
    res2 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "200.00", "payment_date": "2024-02-29"},
    )
    assert res2.status_code == 201
    assert res2.json()["interest_paid"] == "200.00"


async def test_future_dated_payment_rejected(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Payments with a payment_date in the future relative to today are rejected."""
    headers = await _owner_headers(db_session)
    loan = await _active_loan(
        db_session, principal=Decimal("2000.00"), monthly_rate=Decimal("0.10")
    )
    future_date = (date.today() + timedelta(days=5)).isoformat()

    res = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "100.00", "payment_date": future_date},
    )
    assert res.status_code == 400
    assert "cannot be in the future" in res.json()["detail"]


async def test_backdated_payment_rejected(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Payments with a payment_date earlier than the latest posted payment date are rejected."""
    headers = await _owner_headers(db_session)
    loan = await _active_loan(
        db_session, principal=Decimal("2000.00"), monthly_rate=Decimal("0.10")
    )

    # Payment 1 on Jun 30
    res1 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "100.00", "payment_date": "2026-06-30"},
    )
    assert res1.status_code == 201

    # Attempted Payment 2 on Jun 15 (earlier than Jun 30)
    res2 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=_with_key(headers),
        json={"amount": "100.00", "payment_date": "2026-06-15"},
    )
    assert res2.status_code == 400
    assert "cannot be earlier than latest posted payment date" in res2.json()["detail"]
