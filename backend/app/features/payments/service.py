"""Payment domain service enforcing atomic allocation and loan status updates."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.loans.calculator import (
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
) -> tuple[Payment, bool]:
    """Atomically record a payment against an active loan and update balances.

    Returns ``(payment, was_replayed)`` where ``was_replayed`` is ``True`` when an
    existing payment was returned due to a matching idempotency key.

    Sequence:
    1. Lock Loan row using SELECT ... FOR UPDATE.
    2. Verify loan status (must be active or defaulted).
    3. If idempotency_key supplied, check for a prior identical or conflicting payment.
    4. Accumulate new-period interest onto loan.accrued_interest so partial prior
       payments carry forward — do NOT recompute fresh full interest from scratch.
    5. Allocate payment interest-first, then principal, then unapplied credit.
    6. Persist Payment record (storing idempotency_key for replay detection).
    7. Update Loan.outstanding_principal and Loan.accrued_interest.
    8. If loan obligations are fully satisfied, transition Loan status to paid.
    """
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
    if payload.idempotency_key is not None:
        existing = await _find_idempotent_payment(session, loan_id, payload.idempotency_key)
        if existing is not None:
            # Verify the prior request matches; conflict → 409.
            _assert_idempotency_match(existing, payload)
            return existing, True

    if loan.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loan is already paid in full.",
        )

    # --- Accrued interest accumulation ---
    # New period interest is based on the CURRENT outstanding principal (post prior reductions).
    # It is added to whatever interest was left unpaid from previous partial payments.
    period_rate = calculate_period_rate(loan.monthly_rate, loan.payment_frequency)
    new_period_interest = quantize_money(loan.outstanding_principal * period_rate)
    total_interest_due = quantize_money(loan.accrued_interest + new_period_interest)

    allocation = allocate_payment(
        amount=payload.amount,
        interest_due=total_interest_due,
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
        idempotency_key=payload.idempotency_key,
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

    await session.flush()
    return payment, False


async def list_loan_payments(
    session: AsyncSession,
    loan_id: UUID,
) -> list[Payment]:
    """Retrieve ordered payment history for a loan."""
    result = await session.execute(
        select(Payment)
        .where(Payment.loan_id == loan_id)
        .order_by(Payment.posted_at.asc(), Payment.created_at.asc())
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
    """Raise HTTP 409 if the retry payload conflicts with the original payment.

    Two fields are compared because they are the financially material inputs that
    the idempotency guarantee protects:
    - amount: the money posted
    - payment_date: the effective date recorded on the payment

    reference, note, and idempotency_key itself are deliberately excluded.
    """
    conflicts: list[str] = []
    if quantize_money(payload.amount) != existing.amount:
        conflicts.append(
            f"amount: existing={existing.amount}, requested={quantize_money(payload.amount)}"
        )
    if payload.payment_date != existing.payment_date:
        conflicts.append(
            f"payment_date: existing={existing.payment_date}, requested={payload.payment_date}"
        )
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Idempotency key conflict: a payment with the same key already exists "
                f"but the request differs. Conflicts: {'; '.join(conflicts)}"
            ),
        )
