"""Payment domain service enforcing atomic allocation and contractual accrual."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.loans.calculator import (
    advance_due_date,
    allocate_payment,
    calculate_period_rate,
    quantize_money,
)
from app.features.loans.models import Loan
from app.features.payments.models import Payment
from app.features.payments.schemas import PaymentPostRequest


async def post_payment(
    session: AsyncSession,
    loan_id: UUID,
    payload: PaymentPostRequest,
    idempotency_key: str,
) -> tuple[Payment, bool]:
    """Atomically record a payment against an active loan and update balances."""
    key = idempotency_key.strip()
    result = await session.execute(select(Loan).where(Loan.id == loan_id).with_for_update())
    loan = result.scalar_one_or_none()

    if loan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan '{loan_id}' not found.",
        )

    if loan.status in ("pending_disbursement", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot post payment against loan in '{loan.status}' status.",
        )

    # --- Idempotency check (before any mutation or status check for paid) ---
    existing = await _find_idempotent_payment(session, loan_id, key)
    if existing is not None:
        # Verify the prior request matches; conflict → 409.
        _assert_idempotency_match(existing, payload)
        return existing, True

    if loan.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loan is already paid in full.",
        )

    # --- Payment Date Validation ---
    today = date.today()
    if payload.payment_date > today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment date '{payload.payment_date}' cannot be in the future.",
        )

    if loan.disbursed_at is not None and payload.payment_date < loan.disbursed_at.date():
        disbursed_date = loan.disbursed_at.date()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Payment date '{payload.payment_date}' cannot predate loan "
                f"disbursement date '{disbursed_date}'."
            ),
        )

    latest_payment_res = await session.execute(
        select(Payment)
        .where(Payment.loan_id == loan_id)
        .order_by(Payment.payment_date.desc(), Payment.posted_at.desc())
        .limit(1)
    )
    latest_payment = latest_payment_res.scalar_one_or_none()
    if latest_payment is not None and payload.payment_date < latest_payment.payment_date:
        last_date = latest_payment.payment_date
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Payment date '{payload.payment_date}' cannot be earlier than "
                f"latest posted payment date '{last_date}'."
            ),
        )

    # --- Contractual Accrual ---
    if loan.next_interest_due_date is None:
        loan.next_interest_due_date = loan.first_due_date

    period_rate = calculate_period_rate(loan.monthly_rate, loan.payment_frequency)

    # Accrue interest only for due contractual periods that have arrived relative to payment_date
    while payload.payment_date >= loan.next_interest_due_date:
        period_interest = quantize_money(loan.outstanding_principal * period_rate)
        loan.accrued_interest = quantize_money(loan.accrued_interest + period_interest)
        loan.next_interest_due_date = advance_due_date(
            loan.next_interest_due_date,
            loan.payment_frequency,
            loan.first_due_date,
        )

    allocation = allocate_payment(
        amount=payload.amount,
        interest_due=loan.accrued_interest,
        outstanding_principal=loan.outstanding_principal,
    )

    now = datetime.now(UTC)
    payment = Payment(
        loan_id=loan.id,
        amount=quantize_money(payload.amount),
        interest_paid=allocation.interest_paid,
        principal_paid=allocation.principal_paid,
        unapplied_credit=allocation.unapplied_credit,
        remaining_interest=allocation.remaining_interest,
        remaining_principal=allocation.remaining_principal,
        payment_date=payload.payment_date,
        posted_at=now,
        created_at=now,
        updated_at=now,
        reference=payload.reference,
        note=payload.note,
        idempotency_key=key,
    )

    session.add(payment)

    # Update loan balances atomically.
    loan.outstanding_principal = allocation.remaining_principal
    loan.accrued_interest = allocation.remaining_interest

    if allocation.remaining_principal == Decimal(
        "0.00"
    ) and allocation.remaining_interest == Decimal("0.00"):
        loan.status = "paid"
        loan.paid_at = now

    try:
        await session.flush()
    except IntegrityError as err:
        # Handle concurrent requests with the exact same idempotency_key safely
        await session.rollback()
        existing = await _find_idempotent_payment(session, loan_id, key)
        if existing is not None:
            _assert_idempotency_match(existing, payload)
            return existing, True
        raise err

    return payment, False


async def list_loan_payments(
    session: AsyncSession,
    loan_id: UUID,
) -> list[Payment]:
    """Retrieve ordered payment history for a loan."""
    result = await session.execute(
        select(Payment)
        .where(Payment.loan_id == loan_id)
        .order_by(Payment.payment_date.asc(), Payment.posted_at.asc(), Payment.id.asc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _find_idempotent_payment(
    session: AsyncSession,
    loan_id: UUID,
    idempotency_key: str,
) -> Payment | None:
    """Return an existing payment for this (loan_id, idempotency_key) pair, or None."""
    result = await session.execute(
        select(Payment).where(
            Payment.loan_id == loan_id,
            Payment.idempotency_key == idempotency_key,
        )
    )
    return result.scalar_one_or_none()


def _assert_idempotency_match(existing: Payment, payload: PaymentPostRequest) -> None:
    """Raise HTTP 409 if the retry payload conflicts with the original payment."""
    conflicts: list[str] = []
    if quantize_money(payload.amount) != existing.amount:
        conflicts.append(
            f"amount: existing={existing.amount}, requested={quantize_money(payload.amount)}"
        )
    if payload.payment_date != existing.payment_date:
        conflicts.append(
            f"payment_date: existing={existing.payment_date}, requested={payload.payment_date}"
        )
    if payload.reference != existing.reference:
        conflicts.append(f"reference: existing={existing.reference}, requested={payload.reference}")
    if payload.note != existing.note:
        conflicts.append(f"note: existing={existing.note}, requested={payload.note}")
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Idempotency key conflict: a payment with the same key already exists "
                f"but the request differs. Conflicts: {'; '.join(conflicts)}"
            ),
        )
