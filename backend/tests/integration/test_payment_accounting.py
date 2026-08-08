"""Integration tests for payment double-entry accounting."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.features.accounting.constants import (
    ACCOUNT_CASH_CODE,
    ACCOUNT_CUSTOMER_CREDIT_CODE,
    ACCOUNT_INTEREST_INCOME_CODE,
    ACCOUNT_LOANS_RECEIVABLE_CODE,
)
from app.features.accounting.models import JournalEntry, JournalTransaction
from app.features.borrowers.models import Borrower
from app.features.loan_requests.models import LoanRequest
from app.features.loans.models import Loan
from app.features.payments.schemas import PaymentPostRequest
from app.features.payments.service import post_payment


async def _create_active_loan(
    db: AsyncSession,
    principal: str = "2000.00",
    monthly_rate: str = "0.10",
) -> Loan:
    borrower = Borrower(
        first_name="Payment",
        last_name="Accounted",
        national_id=f"NAT-PAY-{uuid4().hex[:6]}",
        address="123 Payment St",
        phone_number=f"0918{uuid4().hex[:7]}",
        phone_number_normalized=f"+63918{uuid4().hex[:7]}",
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
        requested_monthly_rate=Decimal(monthly_rate),
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
        monthly_rate=Decimal(monthly_rate),
        term_months=1,
        payment_frequency="monthly",
        number_of_payments=1,
        first_due_date=date(2026, 6, 15),
        final_due_date=date(2026, 6, 15),
        next_interest_due_date=date(2026, 6, 15),
        status="active",
        disbursed_at=datetime(2026, 5, 15, tzinfo=UTC),
        accrued_interest=Decimal("0.00"),
    )
    db.add(loan)
    await db.flush()
    return loan


async def test_payment_case_b_interest_only(db_session: AsyncSession) -> None:
    """Case B: ₱200 payment satisfying ₱200 interest -> DR Cash 200, CR Interest Income 200."""
    loan = await _create_active_loan(db_session, principal="2000.00")
    key = f"pay-case-b-{uuid4().hex[:6]}"

    payment, replayed = await post_payment(
        db_session,
        loan.id,
        PaymentPostRequest(amount=Decimal("200.00"), payment_date=date(2026, 6, 15)),
        idempotency_key=key,
    )
    assert not replayed

    stmt = (
        select(JournalTransaction)
        .options(joinedload(JournalTransaction.entries).joinedload(JournalEntry.account))
        .where(
            JournalTransaction.event_type == "payment",
            JournalTransaction.source_id == payment.id,
        )
    )
    res = await db_session.execute(stmt)
    tx = res.unique().scalar_one_or_none()
    assert tx is not None
    assert len(tx.entries) == 2

    by_code = {e.account.code: e for e in tx.entries}
    assert by_code[ACCOUNT_CASH_CODE].debit == Decimal("200.00")
    assert by_code[ACCOUNT_INTEREST_INCOME_CODE].credit == Decimal("200.00")
    assert ACCOUNT_LOANS_RECEIVABLE_CODE not in by_code


async def test_payment_case_c_interest_and_principal(db_session: AsyncSession) -> None:
    """Case C: ₱700 payment (₱200 interest + ₱500 principal)."""
    loan = await _create_active_loan(db_session, principal="2000.00")
    key = f"pay-case-c-{uuid4().hex[:6]}"

    payment, _ = await post_payment(
        db_session,
        loan.id,
        PaymentPostRequest(amount=Decimal("700.00"), payment_date=date(2026, 6, 15)),
        idempotency_key=key,
    )

    stmt = (
        select(JournalTransaction)
        .options(joinedload(JournalTransaction.entries).joinedload(JournalEntry.account))
        .where(
            JournalTransaction.event_type == "payment",
            JournalTransaction.source_id == payment.id,
        )
    )
    res = await db_session.execute(stmt)
    tx = res.unique().scalar_one_or_none()
    assert tx is not None
    assert len(tx.entries) == 3

    by_code = {e.account.code: e for e in tx.entries}
    assert by_code[ACCOUNT_CASH_CODE].debit == Decimal("700.00")
    assert by_code[ACCOUNT_INTEREST_INCOME_CODE].credit == Decimal("200.00")
    assert by_code[ACCOUNT_LOANS_RECEIVABLE_CODE].credit == Decimal("500.00")


async def test_payment_case_d_principal_only_same_period(db_session: AsyncSession) -> None:
    """Case D: ₱500 payment in same period after interest satisfied."""
    loan = await _create_active_loan(db_session, principal="2000.00")
    # Payment 1 satisfies ₱200 interest
    await post_payment(
        db_session,
        loan.id,
        PaymentPostRequest(amount=Decimal("200.00"), payment_date=date(2026, 6, 15)),
        idempotency_key=f"pay-case-d1-{uuid4().hex[:6]}",
    )

    # Payment 2 in same period satisfies ₱500 principal
    payment2, _ = await post_payment(
        db_session,
        loan.id,
        PaymentPostRequest(amount=Decimal("500.00"), payment_date=date(2026, 6, 15)),
        idempotency_key=f"pay-case-d2-{uuid4().hex[:6]}",
    )

    stmt = (
        select(JournalTransaction)
        .options(joinedload(JournalTransaction.entries).joinedload(JournalEntry.account))
        .where(
            JournalTransaction.event_type == "payment",
            JournalTransaction.source_id == payment2.id,
        )
    )
    res = await db_session.execute(stmt)
    tx = res.unique().scalar_one_or_none()
    assert tx is not None
    assert len(tx.entries) == 2

    by_code = {e.account.code: e for e in tx.entries}
    assert by_code[ACCOUNT_CASH_CODE].debit == Decimal("500.00")
    assert by_code[ACCOUNT_LOANS_RECEIVABLE_CODE].credit == Decimal("500.00")
    assert ACCOUNT_INTEREST_INCOME_CODE not in by_code


async def test_payment_case_e_overpayment(db_session: AsyncSession) -> None:
    """Case E: ₱2,500 overpayment (₱200 interest + ₱2,000 principal + ₱300 credit)."""
    loan = await _create_active_loan(db_session, principal="2000.00")
    key = f"pay-case-e-{uuid4().hex[:6]}"

    payment, _ = await post_payment(
        db_session,
        loan.id,
        PaymentPostRequest(amount=Decimal("2500.00"), payment_date=date(2026, 6, 15)),
        idempotency_key=key,
    )

    stmt = (
        select(JournalTransaction)
        .options(joinedload(JournalTransaction.entries).joinedload(JournalEntry.account))
        .where(
            JournalTransaction.event_type == "payment",
            JournalTransaction.source_id == payment.id,
        )
    )
    res = await db_session.execute(stmt)
    tx = res.unique().scalar_one_or_none()
    assert tx is not None
    assert len(tx.entries) == 4

    by_code = {e.account.code: e for e in tx.entries}
    assert by_code[ACCOUNT_CASH_CODE].debit == Decimal("2500.00")
    assert by_code[ACCOUNT_INTEREST_INCOME_CODE].credit == Decimal("200.00")
    assert by_code[ACCOUNT_LOANS_RECEIVABLE_CODE].credit == Decimal("2000.00")
    assert by_code[ACCOUNT_CUSTOMER_CREDIT_CODE].credit == Decimal("300.00")

    # Verify journal is balanced
    tot_debit = sum(e.debit for e in tx.entries)
    tot_credit = sum(e.credit for e in tx.entries)
    assert tot_debit == Decimal("2500.00")
    assert tot_credit == Decimal("2500.00")


async def test_idempotent_payment_replay_produces_zero_new_journals(
    db_session: AsyncSession,
) -> None:
    """Verify replaying payment with same key produces NO new journals."""
    loan = await _create_active_loan(db_session, principal="1000.00")
    key = f"pay-idem-{uuid4().hex[:6]}"

    pay1, replayed1 = await post_payment(
        db_session,
        loan.id,
        PaymentPostRequest(amount=Decimal("300.00"), payment_date=date(2026, 6, 15)),
        idempotency_key=key,
    )
    assert not replayed1

    pay2, replayed2 = await post_payment(
        db_session,
        loan.id,
        PaymentPostRequest(amount=Decimal("300.00"), payment_date=date(2026, 6, 15)),
        idempotency_key=key,
    )
    assert replayed2
    assert pay1.id == pay2.id

    # Count journal transactions for this payment
    stmt = select(JournalTransaction).where(
        JournalTransaction.event_type == "payment",
        JournalTransaction.source_id == pay1.id,
    )
    res = await db_session.execute(stmt)
    journals = res.scalars().all()
    assert len(journals) == 1
