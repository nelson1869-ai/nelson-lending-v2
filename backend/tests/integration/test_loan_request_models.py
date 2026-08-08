"""Database persistence and constraint integration tests for LoanRequest model."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.borrowers.models import Borrower
from app.features.loan_requests.models import LoanRequest

pytestmark = pytest.mark.integration


def make_borrower(suffix: str = "101") -> Borrower:
    return Borrower(
        first_name="Request",
        last_name=f"Borrower {suffix}",
        national_id=f"REQ-ID-{suffix}",
        address="123 Request St",
        phone_number=f"0918{suffix:0>7}",
        phone_number_normalized=f"+63918{suffix:0>7}",
        date_of_birth=date(1991, 6, 20),
        status="active",
    )


async def test_loan_request_persistence_success(db_session: AsyncSession) -> None:
    b = make_borrower("101")
    db_session.add(b)
    await db_session.flush()

    req = LoanRequest(
        borrower_id=b.id,
        requested_principal=Decimal("5000.00"),
        requested_monthly_rate=Decimal("0.0500000000"),
        requested_term_months=3,
        requested_payment_frequency="monthly",
        requested_first_due_date=date(2026, 10, 1),
        status="pending",
        submitted_at=datetime.now(UTC),
    )
    db_session.add(req)
    await db_session.flush()

    assert req.id is not None
    assert req.requested_principal == Decimal("5000.00")
    assert req.status == "pending"


async def test_loan_request_one_pending_per_borrower_constraint(
    db_session: AsyncSession,
) -> None:
    b = make_borrower("102")
    db_session.add(b)
    await db_session.flush()

    req1 = LoanRequest(
        borrower_id=b.id,
        requested_principal=Decimal("2000.00"),
        requested_monthly_rate=Decimal("0.10"),
        requested_term_months=1,
        requested_payment_frequency="monthly",
        requested_first_due_date=date(2026, 10, 1),
        status="pending",
        submitted_at=datetime.now(UTC),
    )
    db_session.add(req1)
    await db_session.flush()

    # Second pending request for same borrower should fail partial unique constraint
    req2 = LoanRequest(
        borrower_id=b.id,
        requested_principal=Decimal("3000.00"),
        requested_monthly_rate=Decimal("0.08"),
        requested_term_months=2,
        requested_payment_frequency="monthly",
        requested_first_due_date=date(2026, 10, 1),
        status="pending",
        submitted_at=datetime.now(UTC),
    )
    db_session.add(req2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_loan_request_invalid_status_constraint(db_session: AsyncSession) -> None:
    b = make_borrower("103")
    db_session.add(b)
    await db_session.flush()

    req = LoanRequest(
        borrower_id=b.id,
        requested_principal=Decimal("2000.00"),
        requested_monthly_rate=Decimal("0.10"),
        requested_term_months=1,
        requested_payment_frequency="monthly",
        requested_first_due_date=date(2026, 10, 1),
        status="active",  # active is not a valid LoanRequest status
        submitted_at=datetime.now(UTC),
    )
    db_session.add(req)
    with pytest.raises(IntegrityError, match="loan_request_status_valid"):
        await db_session.flush()
