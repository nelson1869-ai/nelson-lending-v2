"""Atomic rollback proofs for business mutations that require outbox intent."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.features.loan_requests.service as request_service
import app.features.loans.service as loan_service
import app.features.payments.service as payment_service
from app.features.accounting.models import JournalTransaction
from app.features.borrowers.models import Borrower
from app.features.loan_requests.models import LoanRequest
from app.features.loans.models import Loan
from app.features.notifications.models import NotificationOutbox
from app.features.payments.models import Payment
from app.features.payments.schemas import PaymentPostRequest

pytestmark = pytest.mark.integration


async def _borrower(db: AsyncSession) -> Borrower:
    suffix = uuid4().hex[:8]
    borrower = Borrower(
        first_name="Atomic",
        last_name="Outbox",
        national_id=f"NAT-NOTIFY-{suffix}",
        address="1 Transaction Street",
        phone_number=f"0917{suffix[:7]}",
        phone_number_normalized=f"+63917{suffix[:7]}",
        date_of_birth=date(1990, 1, 1),
        status="active",
    )
    db.add(borrower)
    await db.flush()
    return borrower


async def _request(db: AsyncSession, borrower: Borrower, status: str) -> LoanRequest:
    request = LoanRequest(
        borrower_id=borrower.id,
        requested_principal=Decimal("10000.00"),
        requested_term_months=1,
        requested_payment_frequency="monthly",
        requested_monthly_rate=Decimal("0.10"),
        requested_first_due_date=date(2026, 6, 15),
        status=status,
        submitted_at=datetime.now(UTC),
    )
    db.add(request)
    await db.flush()
    return request


async def _loan(db: AsyncSession, *, active: bool) -> Loan:
    borrower = await _borrower(db)
    request = await _request(db, borrower, "approved")
    loan = Loan(
        loan_request_id=request.id,
        borrower_id=borrower.id,
        original_principal=Decimal("10000.00"),
        outstanding_principal=Decimal("10000.00"),
        accrued_interest=Decimal("0.00"),
        monthly_rate=Decimal("0.10"),
        term_months=1,
        payment_frequency="monthly",
        number_of_payments=1,
        first_due_date=date(2026, 6, 15),
        final_due_date=date(2026, 6, 15),
        next_interest_due_date=date(2026, 6, 15),
        status="active" if active else "pending_disbursement",
        disbursed_at=datetime(2026, 6, 1, tzinfo=UTC) if active else None,
    )
    db.add(loan)
    await db.flush()
    return loan


async def _fail_enqueue(*args: object, **kwargs: object) -> None:
    raise RuntimeError("forced outbox failure")


async def test_approval_rolls_back_when_outbox_enqueue_fails(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    borrower = await _borrower(db_session)
    request = await _request(db_session, borrower, "pending")
    outbox_count_before = await db_session.scalar(
        select(func.count()).select_from(NotificationOutbox)
    )
    nested = await db_session.begin_nested()
    monkeypatch.setattr(request_service, "enqueue_notification", _fail_enqueue)

    with pytest.raises(RuntimeError, match="forced outbox failure"):
        await request_service.approve_loan_request(
            db_session, owner_id=uuid4(), request_id=request.id
        )
    await nested.rollback()
    await db_session.refresh(request)

    assert request.status == "pending"
    assert request.reviewed_at is None
    assert (
        await db_session.scalar(select(func.count()).select_from(NotificationOutbox))
        == outbox_count_before
    )


async def test_disbursement_and_journal_roll_back_when_enqueue_fails(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    loan = await _loan(db_session, active=False)
    journal_count_before = await db_session.scalar(
        select(func.count()).select_from(JournalTransaction)
    )
    outbox_count_before = await db_session.scalar(
        select(func.count()).select_from(NotificationOutbox)
    )
    nested = await db_session.begin_nested()
    monkeypatch.setattr(loan_service, "enqueue_notification", _fail_enqueue)

    with pytest.raises(RuntimeError, match="forced outbox failure"):
        await loan_service.disburse_loan(db_session, loan_id=loan.id, owner_id=uuid4())
    await nested.rollback()
    await db_session.refresh(loan)

    assert loan.status == "pending_disbursement"
    assert loan.disbursed_at is None
    assert (
        await db_session.scalar(select(func.count()).select_from(JournalTransaction))
        == journal_count_before
    )
    assert (
        await db_session.scalar(select(func.count()).select_from(NotificationOutbox))
        == outbox_count_before
    )


async def test_payment_and_journal_roll_back_when_enqueue_fails(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    loan = await _loan(db_session, active=True)
    journal_count_before = await db_session.scalar(
        select(func.count()).select_from(JournalTransaction)
    )
    outbox_count_before = await db_session.scalar(
        select(func.count()).select_from(NotificationOutbox)
    )
    nested = await db_session.begin_nested()
    monkeypatch.setattr(payment_service, "enqueue_notification", _fail_enqueue)
    payload = PaymentPostRequest(amount=Decimal("700.00"), payment_date=date(2026, 6, 1))

    with pytest.raises(RuntimeError, match="forced outbox failure"):
        await payment_service.post_payment(db_session, loan.id, payload, "atomic-payment")
    await nested.rollback()
    await db_session.refresh(loan)

    assert loan.outstanding_principal == Decimal("10000.00")
    assert loan.accrued_interest == Decimal("0.00")
    assert loan.next_interest_due_date == date(2026, 6, 15)
    assert await db_session.scalar(select(func.count()).select_from(Payment)) == 0
    assert (
        await db_session.scalar(select(func.count()).select_from(JournalTransaction))
        == journal_count_before
    )
    assert (
        await db_session.scalar(select(func.count()).select_from(NotificationOutbox))
        == outbox_count_before
    )


async def test_payment_replay_keeps_one_payment_journal_and_outbox(
    db_session: AsyncSession,
) -> None:
    loan = await _loan(db_session, active=True)
    payload = PaymentPostRequest(amount=Decimal("700.00"), payment_date=date(2026, 6, 1))

    first, first_replay = await payment_service.post_payment(
        db_session, loan.id, payload, "notification-replay"
    )
    second, second_replay = await payment_service.post_payment(
        db_session, loan.id, payload, "notification-replay"
    )

    assert first.id == second.id
    assert first_replay is False
    assert second_replay is True
    assert await db_session.scalar(select(func.count()).select_from(Payment)) == 1
    journal_count = await db_session.scalar(
        select(func.count())
        .select_from(JournalTransaction)
        .where(
            JournalTransaction.event_type == "payment",
            JournalTransaction.source_id == first.id,
        )
    )
    outbox_count = await db_session.scalar(
        select(func.count())
        .select_from(NotificationOutbox)
        .where(
            NotificationOutbox.event_type == "payment_received",
            NotificationOutbox.aggregate_id == first.id,
        )
    )
    assert journal_count == 1
    assert outbox_count == 1
