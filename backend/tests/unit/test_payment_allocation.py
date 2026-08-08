"""Unit tests for Flexible Reducing-Balance payment allocation rules."""

from decimal import Decimal

import pytest

from app.features.loans.calculator import allocate_payment, quantize_money


def test_canonical_allocation_exact_interest_payment() -> None:
    # ₱2000 principal, ₱200 interest due, payment ₱200
    res = allocate_payment(
        amount=Decimal("200.00"),
        interest_due=Decimal("200.00"),
        outstanding_principal=Decimal("2000.00"),
    )

    assert res.interest_paid == Decimal("200.00")
    assert res.principal_paid == Decimal("0.00")
    assert res.unapplied_credit == Decimal("0.00")
    assert res.remaining_interest == Decimal("0.00")
    assert res.remaining_principal == Decimal("2000.00")


def test_canonical_allocation_substantial_principal_reduction() -> None:
    # ₱2000 principal, ₱200 interest due, payment ₱700
    res = allocate_payment(
        amount=Decimal("700.00"),
        interest_due=Decimal("200.00"),
        outstanding_principal=Decimal("2000.00"),
    )

    assert res.interest_paid == Decimal("200.00")
    assert res.principal_paid == Decimal("500.00")
    assert res.unapplied_credit == Decimal("0.00")
    assert res.remaining_interest == Decimal("0.00")
    assert res.remaining_principal == Decimal("1500.00")


def test_subsequent_interest_on_reduced_principal() -> None:
    # Initial ₱2000 @ 10% -> ₱200 interest
    # Borrower pays ₱700 -> ₱200 interest + ₱500 principal -> remaining principal ₱1500
    res1 = allocate_payment(
        amount=Decimal("700.00"),
        interest_due=Decimal("200.00"),
        outstanding_principal=Decimal("2000.00"),
    )
    assert res1.remaining_principal == Decimal("1500.00")

    # Next period interest is calculated on remaining ₱1500 @ 10%
    monthly_rate = Decimal("0.10")
    next_interest_due = quantize_money(res1.remaining_principal * monthly_rate)
    assert next_interest_due == Decimal("150.00")

    # Second period payment of ₱700
    res2 = allocate_payment(
        amount=Decimal("700.00"),
        interest_due=next_interest_due,
        outstanding_principal=res1.remaining_principal,
    )
    assert res2.interest_paid == Decimal("150.00")
    assert res2.principal_paid == Decimal("550.00")
    assert res2.remaining_principal == Decimal("950.00")


def test_overpayment_unapplied_credit() -> None:
    # ₱2000 principal, ₱200 interest due, payment ₱2500
    res = allocate_payment(
        amount=Decimal("2500.00"),
        interest_due=Decimal("200.00"),
        outstanding_principal=Decimal("2000.00"),
    )

    assert res.interest_paid == Decimal("200.00")
    assert res.principal_paid == Decimal("2000.00")
    assert res.unapplied_credit == Decimal("300.00")
    assert res.remaining_interest == Decimal("0.00")
    assert res.remaining_principal == Decimal("0.00")


def test_partial_interest_payment() -> None:
    # ₱2000 principal, ₱200 interest due, payment ₱100
    res = allocate_payment(
        amount=Decimal("100.00"),
        interest_due=Decimal("200.00"),
        outstanding_principal=Decimal("2000.00"),
    )

    assert res.interest_paid == Decimal("100.00")
    assert res.principal_paid == Decimal("0.00")
    assert res.unapplied_credit == Decimal("0.00")
    assert res.remaining_interest == Decimal("100.00")
    assert res.remaining_principal == Decimal("2000.00")


def test_invalid_allocation_inputs() -> None:
    with pytest.raises(ValueError, match="payment amount must be greater than zero"):
        allocate_payment(Decimal("0.00"), Decimal("10.00"), Decimal("100.00"))

    with pytest.raises(ValueError, match="interest_due cannot be negative"):
        allocate_payment(Decimal("50.00"), Decimal("-1.00"), Decimal("100.00"))

    with pytest.raises(ValueError, match="outstanding_principal cannot be negative"):
        allocate_payment(Decimal("50.00"), Decimal("10.00"), Decimal("-5.00"))
