"""Integration tests for Payment model database constraints against real PostgreSQL."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.borrowers.models import Borrower
from app.features.loan_requests.models import LoanRequest
from app.features.loans.models import Loan
from app.features.payments.models import Payment

pytestmark = pytest.mark.integration


async def create_active_loan(session: AsyncSession) -> Loan:
    """Helper to create a flushed active Borrower, LoanRequest, and Loan."""
    borrower = Borrower(
        first_name="Payment",
        last_name="Test",
        national_id=f"NAT-{uuid4().hex[:8]}",
        address="Integration address",
        phone_number=f"0917{uuid4().hex[:7]}",
        phone_number_normalized=f"+63917{uuid4().hex[:7]}",
        date_of_birth=date(1990, 1, 1),
        status="active",
    )
    session.add(borrower)
    await session.flush()

    request = LoanRequest(
        borrower_id=borrower.id,
        requested_principal=Decimal("2000.00"),
        requested_term_months=1,
        requested_payment_frequency="monthly",
        requested_monthly_rate=Decimal("0.10"),
        requested_first_due_date=date(2026, 9, 15),
        status="approved",
        submitted_at=datetime.now(UTC),
    )
    session.add(request)
    await session.flush()

    loan = Loan(
        loan_request_id=request.id,
        borrower_id=borrower.id,
        original_principal=Decimal("2000.00"),
        outstanding_principal=Decimal("2000.00"),
        monthly_rate=Decimal("0.10"),
        term_months=1,
        payment_frequency="monthly",
        number_of_payments=1,
        first_due_date=date(2026, 9, 15),
        final_due_date=date(2026, 9, 15),
        next_interest_due_date=date(2026, 9, 15),
        accrued_interest=Decimal("0.00"),
        status="active",
        disbursed_at=datetime.now(UTC),
    )
    session.add(loan)
    await session.flush()
    return loan


async def test_payment_persistence_success(db_session: AsyncSession) -> None:
    loan = await create_active_loan(db_session)
    payment = Payment(
        loan_id=loan.id,
        amount=Decimal("700.00"),
        interest_paid=Decimal("200.00"),
        principal_paid=Decimal("500.00"),
        unapplied_credit=Decimal("0.00"),
        remaining_interest=Decimal("0.00"),
        remaining_principal=Decimal("1500.00"),
        payment_date=date(2026, 9, 15),
        posted_at=datetime.now(UTC),
        reference="REF-12345",
        note="Test payment note",
    )
    db_session.add(payment)
    await db_session.flush()
    assert payment.id is not None
    assert payment.amount == Decimal("700.00")


async def test_payment_zero_amount_fails_constraint(db_session: AsyncSession) -> None:
    loan = await create_active_loan(db_session)
    payment = Payment(
        loan_id=loan.id,
        amount=Decimal("0.00"),
        interest_paid=Decimal("0.00"),
        principal_paid=Decimal("0.00"),
        unapplied_credit=Decimal("0.00"),
        remaining_interest=Decimal("0.00"),
        remaining_principal=Decimal("2000.00"),
        payment_date=date(2026, 9, 15),
        posted_at=datetime.now(UTC),
    )
    db_session.add(payment)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_payment_negative_interest_paid_fails_constraint(db_session: AsyncSession) -> None:
    loan = await create_active_loan(db_session)
    payment = Payment(
        loan_id=loan.id,
        amount=Decimal("100.00"),
        interest_paid=Decimal("-0.01"),
        principal_paid=Decimal("100.00"),
        unapplied_credit=Decimal("0.00"),
        remaining_interest=Decimal("0.00"),
        remaining_principal=Decimal("1900.00"),
        payment_date=date(2026, 9, 15),
        posted_at=datetime.now(UTC),
    )
    db_session.add(payment)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_payment_foreign_key_constraint(db_session: AsyncSession) -> None:
    payment = Payment(
        loan_id=uuid4(),
        amount=Decimal("100.00"),
        interest_paid=Decimal("10.00"),
        principal_paid=Decimal("90.00"),
        unapplied_credit=Decimal("0.00"),
        remaining_interest=Decimal("0.00"),
        remaining_principal=Decimal("1910.00"),
        payment_date=date(2026, 9, 15),
        posted_at=datetime.now(UTC),
    )
    db_session.add(payment)
    with pytest.raises(IntegrityError):
        await db_session.flush()
