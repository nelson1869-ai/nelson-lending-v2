"""Typed API schemas for Owner reporting summaries."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class StatusCount(BaseModel):
    """Deterministically ordered count for one canonical status."""

    status: str
    count: int


class PortfolioSnapshot(BaseModel):
    """Current loan portfolio balances and status counts."""

    status_counts: list[StatusCount]
    total_original_principal: Decimal
    total_scheduled_interest: Decimal
    total_scheduled_repayment: Decimal
    next_interest_due: Decimal
    outstanding_principal: Decimal
    accrued_interest: Decimal
    active_loan_count: int
    paid_loan_count: int
    borrower_count: int = 0
    due_today_count: int = 0
    overdue_loan_count: int = 0
    overdue_outstanding_principal: Decimal = Decimal("0.00")
    due_next_7_days_count: int = 0
    due_next_7_days_outstanding_principal: Decimal = Decimal("0.00")
    overdue_1_7_days_count: int = 0
    overdue_8_30_days_count: int = 0
    overdue_30_plus_days_count: int = 0


class CollectionsSummary(BaseModel):
    """Posted payment allocations for an inclusive Philippine date range."""

    from_date: date
    to_date: date
    total_payment_amount: Decimal
    principal_allocation: Decimal
    interest_allocation: Decimal
    unapplied_credit_allocation: Decimal


class AccountBalance(BaseModel):
    """Current normal-balance amount derived from immutable journal entries."""

    code: str
    name: str
    normal_balance: str
    balance: Decimal


class LoanRequestSnapshot(BaseModel):
    """Current loan-request counts for every canonical request status."""

    status_counts: list[StatusCount]


class OwnerDashboardResponse(BaseModel):
    """Complete Owner dashboard response."""

    portfolio: PortfolioSnapshot
    collections: CollectionsSummary
    accounting_balances: list[AccountBalance]
    loan_requests: LoanRequestSnapshot
