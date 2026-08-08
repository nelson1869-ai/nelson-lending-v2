"""Financial calculator regression test suite enforcing canonical lending rules."""

from datetime import date
from decimal import Decimal

import pytest

from app.features.loans.calculator import (
    build_due_dates,
    calculate_period_rate,
    calculate_quote,
)


def test_regression_canonical_2000_at_10_percent() -> None:
    """Explicit regression for ₱2000 @ 10% monthly rate for 1 month."""
    quote = calculate_quote(
        principal=Decimal("2000.00"),
        monthly_rate=Decimal("0.10"),
        term_months=1,
        payment_frequency="monthly",
        first_due_date=date(2026, 9, 7),
    )

    assert quote.principal == Decimal("2000.00")
    assert quote.total_scheduled_interest == Decimal("200.00")
    assert quote.scheduled_payment == Decimal("2200.00")
    assert quote.total_scheduled_repayment == Decimal("2200.00")
    assert len(quote.schedule) == 1

    item = quote.schedule[0]
    assert item.opening_principal == Decimal("2000.00")
    assert item.interest_due == Decimal("200.00")
    assert item.scheduled_principal == Decimal("2000.00")
    assert item.scheduled_payment == Decimal("2200.00")
    assert item.closing_principal == Decimal("0.00")


def test_regression_schedule_closing_and_principal_sum() -> None:
    """Verify that schedule principal sum equals original principal and closing principal is 0.00."""
    quote = calculate_quote(
        principal=Decimal("15000.00"),
        monthly_rate=Decimal("0.075"),
        term_months=6,
        payment_frequency="twice_monthly",
        first_due_date=date(2026, 3, 15),
    )

    assert quote.number_of_payments == 12
    sum_principal = sum(item.scheduled_principal for item in quote.schedule)
    assert sum_principal == Decimal("15000.00")

    sum_repayment = sum(item.scheduled_payment for item in quote.schedule)
    assert sum_repayment == quote.total_scheduled_repayment

    assert quote.schedule[-1].closing_principal == Decimal("0.00")

    for item in quote.schedule:
        assert item.scheduled_principal > Decimal("0.00")
        assert item.closing_principal >= Decimal("0.00")


def test_regression_twice_monthly_february_dates() -> None:
    """Twice-monthly February dates in leap and non-leap years."""
    # Non-leap year 2026
    dates_2026 = build_due_dates(date(2026, 2, 15), "twice_monthly", 2)
    assert dates_2026 == [date(2026, 2, 15), date(2026, 2, 28)]

    # Leap year 2028
    dates_2028 = build_due_dates(date(2028, 2, 15), "twice_monthly", 2)
    assert dates_2028 == [date(2028, 2, 15), date(2028, 2, 29)]


def test_regression_period_rate_derivation() -> None:
    """Verify period rate derivation for monthly and twice-monthly frequencies."""
    monthly_r = Decimal("0.12")
    assert calculate_period_rate(monthly_r, "monthly") == Decimal("0.12")
    assert calculate_period_rate(monthly_r, "twice_monthly") == Decimal("0.06")


def test_regression_invalid_input_validations() -> None:
    """Comprehensive validation rejection tests."""
    with pytest.raises(ValueError, match="principal must be greater than zero"):
        calculate_quote(Decimal("-100.00"), Decimal("0.05"), 3, "monthly", date(2026, 1, 1))

    with pytest.raises(ValueError, match="monthly_rate cannot be negative"):
        calculate_quote(Decimal("1000.00"), Decimal("-0.05"), 3, "monthly", date(2026, 1, 1))

    with pytest.raises(ValueError, match="term_months must be greater than zero"):
        calculate_quote(Decimal("1000.00"), Decimal("0.05"), 0, "monthly", date(2026, 1, 1))

    with pytest.raises(ValueError, match="Unsupported payment frequency"):
        calculate_quote(Decimal("1000.00"), Decimal("0.05"), 3, "daily", date(2026, 1, 1))
