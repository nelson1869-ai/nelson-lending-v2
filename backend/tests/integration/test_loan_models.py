"""Loan model database persistence and constraint integration tests."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.borrowers.models import Borrower
from app.features.loan_requests.models import LoanRequest
from app.features.loans.models import Loan

pytestmark = pytest.mark.integration


def make_borrower(suffix: str = "001") -> Borrower:
    return Borrower(
        first_name="Loan",
        last_name=f"Borrower {suffix}",
        national_id=f"LOAN-ID-{suffix}",
        address="123 Loan St",
        phone_number=f"0917{suffix:0>7}",
        phone_number_normalized=f"+63917{suffix:0>7}",
        date_of_birth=date(1990, 5, 15),
        status="active",
    )


def make_loan_request(borrower_id: str | None = None) -> LoanRequest:
    return LoanRequest(
        requested_principal=Decimal("2000.00"),
        requested_monthly_rate=Decimal("0.1000000000"),
        requested_term_months=1,
        requested_payment_frequency="monthly",
        requested_first_due_date=date(2026, 9, 7),
        status="approved",
        submitted_at=datetime.now(UTC),
    )


async def test_loan_persistence_success(db_session: AsyncSession) -> None:
    b = make_borrower("001")
    db_session.add(b)
    await db_session.flush()

    req = make_loan_request()
    req.borrower_id = b.id
    db_session.add(req)
    await db_session.flush()

    loan = Loan(
        borrower_id=b.id,
        loan_request_id=req.id,
        original_principal=Decimal("2000.00"),
        outstanding_principal=Decimal("2000.00"),
        monthly_rate=Decimal("0.1000000000"),
        term_months=1,
        payment_frequency="monthly",
        number_of_payments=1,
        first_due_date=date(2026, 9, 7),
        final_due_date=date(2026, 9, 7),
        status="pending_disbursement",
    )
    db_session.add(loan)
    await db_session.flush()

    assert loan.id is not None
    assert loan.loan_request_id == req.id
    assert loan.original_principal == Decimal("2000.00")
    assert loan.monthly_rate == Decimal("0.1000000000")


async def test_loan_missing_loan_request_id_fails(db_session: AsyncSession) -> None:
    b = make_borrower("002")
    db_session.add(b)
    await db_session.flush()

    loan = Loan(
        borrower_id=b.id,
        loan_request_id=None,
        original_principal=Decimal("2000.00"),
        outstanding_principal=Decimal("2000.00"),
        monthly_rate=Decimal("0.10"),
        term_months=1,
        payment_frequency="monthly",
        number_of_payments=1,
        first_due_date=date(2026, 9, 7),
        final_due_date=date(2026, 9, 7),
        status="pending_disbursement",
    )
    db_session.add(loan)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_loan_duplicate_loan_request_id_fails(db_session: AsyncSession) -> None:
    b = make_borrower("003")
    db_session.add(b)
    await db_session.flush()

    req = make_loan_request()
    req.borrower_id = b.id
    db_session.add(req)
    await db_session.flush()

    loan1 = Loan(
        borrower_id=b.id,
        loan_request_id=req.id,
        original_principal=Decimal("2000.00"),
        outstanding_principal=Decimal("2000.00"),
        monthly_rate=Decimal("0.10"),
        term_months=1,
        payment_frequency="monthly",
        number_of_payments=1,
        first_due_date=date(2026, 9, 7),
        final_due_date=date(2026, 9, 7),
        status="pending_disbursement",
    )
    db_session.add(loan1)
    await db_session.flush()

    loan2 = Loan(
        borrower_id=b.id,
        loan_request_id=req.id,
        original_principal=Decimal("2000.00"),
        outstanding_principal=Decimal("2000.00"),
        monthly_rate=Decimal("0.10"),
        term_months=1,
        payment_frequency="monthly",
        number_of_payments=1,
        first_due_date=date(2026, 9, 7),
        final_due_date=date(2026, 9, 7),
        status="pending_disbursement",
    )
    db_session.add(loan2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_loan_invalid_principal_constraint(db_session: AsyncSession) -> None:
    b = make_borrower("004")
    db_session.add(b)
    await db_session.flush()

    req = make_loan_request()
    req.borrower_id = b.id
    db_session.add(req)
    await db_session.flush()

    loan = Loan(
        borrower_id=b.id,
        loan_request_id=req.id,
        original_principal=Decimal("0.00"),
        outstanding_principal=Decimal("0.00"),
        monthly_rate=Decimal("0.10"),
        term_months=1,
        payment_frequency="monthly",
        number_of_payments=1,
        first_due_date=date(2026, 9, 7),
        final_due_date=date(2026, 9, 7),
    )
    db_session.add(loan)
    with pytest.raises(IntegrityError, match="original_principal_positive"):
        await db_session.flush()


async def test_loan_invalid_frequency_constraint(db_session: AsyncSession) -> None:
    b = make_borrower("005")
    db_session.add(b)
    await db_session.flush()

    req = make_loan_request()
    req.borrower_id = b.id
    db_session.add(req)
    await db_session.flush()

    loan = Loan(
        borrower_id=b.id,
        loan_request_id=req.id,
        original_principal=Decimal("1000.00"),
        outstanding_principal=Decimal("1000.00"),
        monthly_rate=Decimal("0.05"),
        term_months=2,
        payment_frequency="weekly",
        number_of_payments=8,
        first_due_date=date(2026, 9, 7),
        final_due_date=date(2026, 11, 7),
    )
    db_session.add(loan)
    with pytest.raises(IntegrityError, match="payment_frequency_valid"):
        await db_session.flush()
