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
) -> Payment:
    """Atomically record a payment against an active loan and update balances.

    Sequence:
    1. Lock Loan row using SELECT ... FOR UPDATE.
    2. Verify loan status (must be active or defaulted).
    3. Calculate interest due using period rate on current outstanding principal.
    4. Allocate payment interest-first, then principal, then unapplied credit.
    5. Persist Payment record.
    6. Update Loan.outstanding_principal.
    7. If loan obligations are fully satisfied, transition Loan status to paid.
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

    if loan.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loan is already paid in full.",
        )

    period_rate = calculate_period_rate(loan.monthly_rate, loan.payment_frequency)
    interest_due = quantize_money(loan.outstanding_principal * period_rate)

    allocation = allocate_payment(
        amount=payload.amount,
        interest_due=interest_due,
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
    )

    session.add(payment)

    loan.outstanding_principal = allocation.remaining_principal

    if allocation.remaining_principal == Decimal(
        "0.00"
    ) and allocation.remaining_interest == Decimal("0.00"):
        loan.status = "paid"
        loan.paid_at = now

    await session.flush()
    return payment


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
