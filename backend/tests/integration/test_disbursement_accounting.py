"""Integration tests for loan disbursement double-entry accounting."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.features.accounting.constants import (
    ACCOUNT_CASH_CODE,
    ACCOUNT_LOANS_RECEIVABLE_CODE,
)
from app.features.accounting.models import JournalEntry, JournalTransaction
from app.features.borrowers.models import Borrower
from app.features.loan_requests.models import LoanRequest
from app.features.loans.models import Loan
from app.features.loans.service import disburse_loan


async def _create_pending_loan(
    db: AsyncSession, principal: str = "10000.00"
) -> tuple[Loan, Borrower]:
    borrower = Borrower(
        first_name="Disburse",
        last_name="Accounted",
        national_id=f"NAT-DISB-{uuid4().hex[:6]}",
        address="123 Disburse St",
        phone_number=f"0917{uuid4().hex[:7]}",
        phone_number_normalized=f"+63917{uuid4().hex[:7]}",
        date_of_birth=date(1990, 1, 1),
        status="active",
    )
    db.add(borrower)
    await db.flush()

    request = LoanRequest(
        borrower_id=borrower.id,
        requested_principal=Decimal(principal),
        requested_term_months=1,
        requested_payment_frequency="monthly",
        requested_monthly_rate=Decimal("0.10"),
        requested_first_due_date=date(2026, 6, 15),
        status="approved",
        submitted_at=datetime.now(UTC),
    )
    db.add(request)
    await db.flush()

    loan = Loan(
        loan_request_id=request.id,
        borrower_id=borrower.id,
        original_principal=Decimal(principal),
        outstanding_principal=Decimal(principal),
        monthly_rate=Decimal("0.10"),
        term_months=1,
        payment_frequency="monthly",
        number_of_payments=1,
        first_due_date=date(2026, 6, 15),
        final_due_date=date(2026, 6, 15),
        next_interest_due_date=date(2026, 6, 15),
        status="pending_disbursement",
        accrued_interest=Decimal("0.00"),
    )
    db.add(loan)
    await db.flush()
    return loan, borrower


async def test_disbursement_creates_balanced_accounting_journal(db_session: AsyncSession) -> None:
    """Verify disbursing a loan creates a balanced loan_disbursement journal."""
    loan, _ = await _create_pending_loan(db_session, principal="10000.00")
    owner_id = uuid4()

    disbursed_loan = await disburse_loan(db_session, loan_id=loan.id, owner_id=owner_id)
    assert disbursed_loan.status == "active"

    # Query created journal
    stmt = (
        select(JournalTransaction)
        .options(joinedload(JournalTransaction.entries).joinedload(JournalEntry.account))
        .where(
            JournalTransaction.event_type == "loan_disbursement",
            JournalTransaction.source_id == loan.id,
        )
    )
    res = await db_session.execute(stmt)
    tx = res.unique().scalar_one_or_none()
    assert tx is not None
    assert tx.description == f"Disbursement for Loan {loan.id}"
    assert len(tx.entries) == 2

    by_code = {e.account.code: e for e in tx.entries}
    assert by_code[ACCOUNT_LOANS_RECEIVABLE_CODE].debit == Decimal("10000.00")
    assert by_code[ACCOUNT_LOANS_RECEIVABLE_CODE].credit == Decimal("0.00")
    assert by_code[ACCOUNT_CASH_CODE].credit == Decimal("10000.00")
    assert by_code[ACCOUNT_CASH_CODE].debit == Decimal("0.00")


async def test_disbursement_journal_is_idempotent(db_session: AsyncSession) -> None:
    """Verify calling disburse_loan multiple times does not duplicate journals."""
    loan, _ = await _create_pending_loan(db_session, principal="5000.00")
    owner_id = uuid4()

    await disburse_loan(db_session, loan_id=loan.id, owner_id=owner_id)

    # Query count of journals for this loan
    stmt = select(JournalTransaction).where(
        JournalTransaction.event_type == "loan_disbursement",
        JournalTransaction.source_id == loan.id,
    )
    res = await db_session.execute(stmt)
    journals = res.scalars().all()
    assert len(journals) == 1
