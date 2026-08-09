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
    outstanding_principal: Decimal
    accrued_interest: Decimal
    active_loan_count: int
    paid_loan_count: int


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
