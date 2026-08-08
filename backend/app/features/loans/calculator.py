"""Canonical Flexible Reducing-Balance financial calculator."""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


def quantize_money(amount: Decimal) -> Decimal:
    """Quantize monetary amount to PHP 0.01 precision using ROUND_HALF_UP."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def quantize_rate(rate: Decimal) -> Decimal:
    """Quantize rate to 10 decimal places."""
    return rate.quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ScheduleItem:
    """Stateless representation of a scheduled loan installment."""

    installment_number: int
    due_date: date
    opening_principal: Decimal
    interest_due: Decimal
    scheduled_principal: Decimal
    scheduled_payment: Decimal
    closing_principal: Decimal


@dataclass(frozen=True)
class LoanQuote:
    """Stateless summary of a calculated loan quote."""

    principal: Decimal
    monthly_rate: Decimal
    term_months: int
    payment_frequency: str
    number_of_payments: int
    period_rate: Decimal
    scheduled_payment: Decimal
    total_scheduled_interest: Decimal
    total_scheduled_repayment: Decimal
    first_due_date: date
    final_due_date: date
    schedule: list[ScheduleItem]


def build_due_dates(
    first_due_date: date,
    payment_frequency: str,
    number_of_payments: int,
) -> list[date]:
    """Generate calendar-safe due dates based on payment frequency.

    Monthly:
      Calendar-anchored (e.g. Jan 31 -> Feb 28/29 -> Mar 31).

    Twice a Month:
      15th and last calendar day of each month.
    """
    if number_of_payments <= 0:
        raise ValueError("number_of_payments must be greater than zero")

    due_dates: list[date] = []

    if payment_frequency == "monthly":
        anchor_day = first_due_date.day
        start_year = first_due_date.year
        start_month = first_due_date.month

        for i in range(number_of_payments):
            year_offset = (start_month - 1 + i) // 12
            target_month = (start_month - 1 + i) % 12 + 1
            target_year = start_year + year_offset
            max_days = calendar.monthrange(target_year, target_month)[1]
            due_day = min(anchor_day, max_days)
            due_dates.append(date(target_year, target_month, due_day))

    elif payment_frequency == "twice_monthly":
        year = first_due_date.year
        month = first_due_date.month

        # Determine starting occurrence: 15th vs last day
        last_day = calendar.monthrange(year, month)[1]
        if first_due_date.day <= 15:
            current_is_fifteenth = True
        else:
            current_is_fifteenth = False

        while len(due_dates) < number_of_payments:
            last_day = calendar.monthrange(year, month)[1]
            if current_is_fifteenth:
                due_dates.append(date(year, month, 15))
                current_is_fifteenth = False
            else:
                due_dates.append(date(year, month, last_day))
                current_is_fifteenth = True
                month += 1
                if month > 12:
                    month = 1
                    year += 1

    else:
        raise ValueError(f"Unsupported payment frequency '{payment_frequency}'")

    return due_dates


def calculate_period_rate(monthly_rate: Decimal, payment_frequency: str) -> Decimal:
    """Derive periodic interest rate from canonical monthly rate."""
    if monthly_rate < Decimal("0"):
        raise ValueError("monthly_rate cannot be negative")

    if payment_frequency == "monthly":
        return monthly_rate
    elif payment_frequency == "twice_monthly":
        return monthly_rate / Decimal("2")
    else:
        raise ValueError(f"Unsupported payment frequency '{payment_frequency}'")


def calculate_quote(
    principal: Decimal,
    monthly_rate: Decimal,
    term_months: int,
    payment_frequency: str,
    first_due_date: date,
) -> LoanQuote:
    """Calculate stateless Reducing-Balance loan quote and schedule."""
    if principal <= Decimal("0"):
        raise ValueError("principal must be greater than zero")
    if monthly_rate < Decimal("0"):
        raise ValueError("monthly_rate cannot be negative")
    if term_months <= 0:
        raise ValueError("term_months must be greater than zero")
    if payment_frequency not in ("monthly", "twice_monthly"):
        raise ValueError(f"Unsupported payment frequency '{payment_frequency}'")

    payments_per_month = 1 if payment_frequency == "monthly" else 2
    number_of_payments = term_months * payments_per_month

    period_rate = calculate_period_rate(monthly_rate, payment_frequency)
    due_dates = build_due_dates(first_due_date, payment_frequency, number_of_payments)

    principal_q = quantize_money(principal)
    monthly_rate_q = quantize_rate(monthly_rate)

    if period_rate == Decimal("0"):
        raw_payment = principal_q / Decimal(number_of_payments)
        scheduled_payment = quantize_money(raw_payment)
    else:
        one_plus_r = Decimal("1") + period_rate
        discount_factor = one_plus_r ** (-number_of_payments)
        raw_payment = (principal_q * period_rate) / (Decimal("1") - discount_factor)
        scheduled_payment = quantize_money(raw_payment)

    schedule: list[ScheduleItem] = []
    current_principal = principal_q
    total_interest = Decimal("0.00")
    total_repayment = Decimal("0.00")

    for i in range(number_of_payments):
        due_date = due_dates[i]
        opening_principal = current_principal
        interest_due = quantize_money(opening_principal * period_rate)

        is_last_installment = i == (number_of_payments - 1)

        if is_last_installment:
            scheduled_principal = opening_principal
            installment_payment = opening_principal + interest_due
            closing_principal = Decimal("0.00")
        else:
            scheduled_principal = scheduled_payment - interest_due
            installment_payment = scheduled_payment
            closing_principal = quantize_money(opening_principal - scheduled_principal)

        schedule.append(
            ScheduleItem(
                installment_number=i + 1,
                due_date=due_date,
                opening_principal=opening_principal,
                interest_due=interest_due,
                scheduled_principal=scheduled_principal,
                scheduled_payment=installment_payment,
                closing_principal=closing_principal,
            )
        )

        current_principal = closing_principal
        total_interest = quantize_money(total_interest + interest_due)
        total_repayment = quantize_money(total_repayment + installment_payment)

    return LoanQuote(
        principal=principal_q,
        monthly_rate=monthly_rate_q,
        term_months=term_months,
        payment_frequency=payment_frequency,
        number_of_payments=number_of_payments,
        period_rate=quantize_rate(period_rate),
        scheduled_payment=scheduled_payment,
        total_scheduled_interest=total_interest,
        total_scheduled_repayment=total_repayment,
        first_due_date=due_dates[0],
        final_due_date=due_dates[-1],
        schedule=schedule,
    )
