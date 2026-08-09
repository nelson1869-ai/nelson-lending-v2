"""Read-only canonical aggregate queries for Owner reports."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.accounting.constants import SYSTEM_ACCOUNTS
from app.features.accounting.models import Account, JournalEntry
from app.features.loan_requests.models import LOAN_REQUEST_STATUSES, LoanRequest
from app.features.loans.calculator import quantize_money
from app.features.loans.models import LOAN_STATUSES, Loan
from app.features.payments.models import Payment
from app.features.reports.schemas import (
    AccountBalance,
    CollectionsSummary,
    LoanRequestSnapshot,
    OwnerDashboardResponse,
    PortfolioSnapshot,
    StatusCount,
)

ZERO = Decimal("0.00")


async def get_owner_dashboard(
    db: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> OwnerDashboardResponse:
    """Return all current dashboard summaries without mutating financial records."""
    return OwnerDashboardResponse(
        portfolio=await get_portfolio_snapshot(db),
        collections=await get_collections_summary(db, from_date=from_date, to_date=to_date),
        accounting_balances=await get_accounting_balances(db),
        loan_requests=await get_loan_request_snapshot(db),
    )


async def get_portfolio_snapshot(db: AsyncSession) -> PortfolioSnapshot:
    """Aggregate canonical loan state without recomputing balances."""
    count_rows = (
        await db.execute(select(Loan.status, func.count(Loan.id)).group_by(Loan.status))
    ).all()
    counts = {status: int(count) for status, count in count_rows}

    monetary = (
        await db.execute(
            select(
                func.coalesce(
                    func.sum(Loan.original_principal).filter(Loan.status.in_(("active", "paid"))),
                    ZERO,
                ),
                func.coalesce(
                    func.sum(Loan.outstanding_principal).filter(Loan.status == "active"), ZERO
                ),
                func.coalesce(
                    func.sum(Loan.accrued_interest).filter(Loan.status == "active"), ZERO
                ),
            )
        )
    ).one()

    return PortfolioSnapshot(
        status_counts=[
            StatusCount(status=status, count=counts.get(status, 0)) for status in LOAN_STATUSES
        ],
        total_original_principal=quantize_money(monetary[0]),
        outstanding_principal=quantize_money(monetary[1]),
        accrued_interest=quantize_money(monetary[2]),
        active_loan_count=counts.get("active", 0),
        paid_loan_count=counts.get("paid", 0),
    )


async def get_collections_summary(
    db: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> CollectionsSummary:
    """Aggregate posted Payments using the effective payment_date half-open interval."""
    exclusive_end = to_date + timedelta(days=1)
    totals = (
        await db.execute(
            select(
                func.coalesce(func.sum(Payment.amount), ZERO),
                func.coalesce(func.sum(Payment.principal_paid), ZERO),
                func.coalesce(func.sum(Payment.interest_paid), ZERO),
                func.coalesce(func.sum(Payment.unapplied_credit), ZERO),
            ).where(Payment.payment_date >= from_date, Payment.payment_date < exclusive_end)
        )
    ).one()
    return CollectionsSummary(
        from_date=from_date,
        to_date=to_date,
        total_payment_amount=quantize_money(totals[0]),
        principal_allocation=quantize_money(totals[1]),
        interest_allocation=quantize_money(totals[2]),
        unapplied_credit_allocation=quantize_money(totals[3]),
    )


async def get_accounting_balances(db: AsyncSession) -> list[AccountBalance]:
    """Calculate system account balances using each account's normal balance."""
    codes = [definition["code"] for definition in SYSTEM_ACCOUNTS]
    rows = (
        await db.execute(
            select(
                Account.code,
                Account.name,
                Account.normal_balance,
                func.coalesce(func.sum(JournalEntry.debit), ZERO),
                func.coalesce(func.sum(JournalEntry.credit), ZERO),
            )
            .outerjoin(JournalEntry, JournalEntry.account_id == Account.id)
            .where(Account.code.in_(codes))
            .group_by(Account.id, Account.code, Account.name, Account.normal_balance)
        )
    ).all()
    by_code = {row.code: row for row in rows}
    balances: list[AccountBalance] = []
    for definition in SYSTEM_ACCOUNTS:
        row = by_code.get(definition["code"])
        debit = row[3] if row is not None else ZERO
        credit = row[4] if row is not None else ZERO
        normal_balance = definition["normal_balance"] if row is None else row.normal_balance
        balance = debit - credit if normal_balance == "debit" else credit - debit
        balances.append(
            AccountBalance(
                code=definition["code"],
                name=definition["name"] if row is None else row.name,
                normal_balance=normal_balance,
                balance=quantize_money(balance),
            )
        )
    return balances


async def get_loan_request_snapshot(db: AsyncSession) -> LoanRequestSnapshot:
    """Count every canonical loan-request status, including empty statuses."""
    rows = (
        await db.execute(
            select(LoanRequest.status, func.count(LoanRequest.id)).group_by(LoanRequest.status)
        )
    ).all()
    counts = {status: int(count) for status, count in rows}
    return LoanRequestSnapshot(
        status_counts=[
            StatusCount(status=status, count=counts.get(status, 0))
            for status in LOAN_REQUEST_STATUSES
        ]
    )
