"""Unit tests for pure financial calculator and schedule generation."""

from datetime import date
from decimal import Decimal

import pytest

from app.features.loans.calculator import (
    build_due_dates,
    calculate_period_rate,
    calculate_quote,
    quantize_money,
    quantize_rate,
)


def test_quantize_money_rounding() -> None:
    assert quantize_money(Decimal("10.004")) == Decimal("10.00")
    assert quantize_money(Decimal("10.005")) == Decimal("10.01")
    assert quantize_money(Decimal("200.000")) == Decimal("200.00")


def test_one_month_monthly_loan_canonical_example() -> None:
    quote = calculate_quote(
        principal=Decimal("2000.00"),
        monthly_rate=Decimal("0.10"),
        term_months=1,
        payment_frequency="monthly",
        first_due_date=date(2026, 9, 7),
    )

    assert quote.principal == Decimal("2000.00")
    assert quote.monthly_rate == Decimal("0.1000000000")
    assert quote.term_months == 1
    assert quote.payment_frequency == "monthly"
    assert quote.number_of_payments == 1
    assert quote.period_rate == Decimal("0.1000000000")
    assert quote.scheduled_payment == Decimal("2200.00")
    assert quote.total_scheduled_interest == Decimal("200.00")
    assert quote.total_scheduled_repayment == Decimal("2200.00")
    assert quote.first_due_date == date(2026, 9, 7)
    assert quote.final_due_date == date(2026, 9, 7)

    assert len(quote.schedule) == 1
    item = quote.schedule[0]
    assert item.installment_number == 1
    assert item.due_date == date(2026, 9, 7)
    assert item.opening_principal == Decimal("2000.00")
    assert item.interest_due == Decimal("200.00")
    assert item.scheduled_principal == Decimal("2000.00")
    assert item.scheduled_payment == Decimal("2200.00")
    assert item.closing_principal == Decimal("0.00")


def test_multi_month_monthly_loan() -> None:
    quote = calculate_quote(
        principal=Decimal("10000.00"),
        monthly_rate=Decimal("0.05"),
        term_months=3,
        payment_frequency="monthly",
        first_due_date=date(2026, 1, 15),
    )

    assert quote.number_of_payments == 3
    assert len(quote.schedule) == 3

    # Total principal portions must equal original principal exactly
    total_principal_portions = sum(item.scheduled_principal for item in quote.schedule)
    assert total_principal_portions == Decimal("10000.00")

    # Closing principal of final installment must be 0.00
    assert quote.schedule[-1].closing_principal == Decimal("0.00")

    # Due dates check
    assert quote.schedule[0].due_date == date(2026, 1, 15)
    assert quote.schedule[1].due_date == date(2026, 2, 15)
    assert quote.schedule[2].due_date == date(2026, 3, 15)


def test_twice_monthly_loan() -> None:
    quote = calculate_quote(
        principal=Decimal("5000.00"),
        monthly_rate=Decimal("0.06"),
        term_months=2,
        payment_frequency="twice_monthly",
        first_due_date=date(2026, 1, 15),
    )

    assert quote.number_of_payments == 4
    assert quote.period_rate == Decimal("0.0300000000")
    assert len(quote.schedule) == 4

    # Due dates check: 15th and last day of Jan, Feb
    assert quote.schedule[0].due_date == date(2026, 1, 15)
    assert quote.schedule[1].due_date == date(2026, 1, 31)
    assert quote.schedule[2].due_date == date(2026, 2, 15)
    assert quote.schedule[3].due_date == date(2026, 2, 28)

    assert quote.schedule[-1].closing_principal == Decimal("0.00")


def test_zero_interest_loan() -> None:
    quote = calculate_quote(
        principal=Decimal("1200.00"),
        monthly_rate=Decimal("0.00"),
        term_months=3,
        payment_frequency="monthly",
        first_due_date=date(2026, 5, 1),
    )

    assert quote.period_rate == Decimal("0.0000000000")
    assert quote.total_scheduled_interest == Decimal("0.00")
    assert quote.total_scheduled_repayment == Decimal("1200.00")
    assert quote.scheduled_payment == Decimal("400.00")

    for item in quote.schedule:
        assert item.interest_due == Decimal("0.00")
    assert quote.schedule[-1].closing_principal == Decimal("0.00")


def test_month_end_re_expansion_schedule() -> None:
    # Jan 31 start -> Feb 28 (non-leap) -> Mar 31 -> Apr 30
    due_dates = build_due_dates(date(2026, 1, 31), "monthly", 4)
    assert due_dates == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
    ]


def test_leap_year_february_due_date() -> None:
    # 2028 is a leap year -> Feb 29
    due_dates = build_due_dates(date(2028, 1, 31), "monthly", 3)
    assert due_dates == [
        date(2028, 1, 31),
        date(2028, 2, 29),
        date(2028, 3, 31),
    ]


def test_invalid_calculator_inputs() -> None:
    with pytest.raises(ValueError, match="principal must be greater than zero"):
        calculate_quote(Decimal("0.00"), Decimal("0.10"), 1, "monthly", date(2026, 1, 1))

    with pytest.raises(ValueError, match="monthly_rate cannot be negative"):
        calculate_quote(Decimal("100.00"), Decimal("-0.01"), 1, "monthly", date(2026, 1, 1))

    with pytest.raises(ValueError, match="term_months must be greater than zero"):
        calculate_quote(Decimal("100.00"), Decimal("0.10"), 0, "monthly", date(2026, 1, 1))

    with pytest.raises(ValueError, match="Unsupported payment frequency"):
        calculate_quote(Decimal("100.00"), Decimal("0.10"), 1, "weekly", date(2026, 1, 1))
