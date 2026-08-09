"""Transactional contractual-interest accrual for due active loans."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.loans.calculator import (
    advance_due_date,
    calculate_period_rate,
    quantize_money,
)
from app.features.loans.models import Loan


async def accrue_due_interest(
    session: AsyncSession,
    *,
    as_of: date | None = None,
) -> int:
    """Accrue each due contractual period once and return loans changed."""
    accrual_date = as_of or date.today()
    result = await session.execute(
        select(Loan)
        .where(
            Loan.status == "active",
            Loan.next_interest_due_date.is_not(None),
            Loan.next_interest_due_date <= accrual_date,
        )
        .with_for_update()
    )
    changed = 0
    for loan in result.scalars():
        period_rate = calculate_period_rate(loan.monthly_rate, loan.payment_frequency)
        while loan.next_interest_due_date is not None and loan.next_interest_due_date <= accrual_date:
            interest = quantize_money(loan.outstanding_principal * period_rate)
            loan.accrued_interest = quantize_money(loan.accrued_interest + interest)
            loan.next_interest_due_date = advance_due_date(
                loan.next_interest_due_date,
                loan.payment_frequency,
                loan.first_due_date,
            )
        changed += 1
    await session.flush()
    return changed
