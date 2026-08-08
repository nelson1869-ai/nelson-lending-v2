"""Domain service functions for loan lifecycle management."""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.features.loan_requests.models import LoanRequest
from app.features.loans.calculator import calculate_quote
from app.features.loans.models import Loan


class LoanNotFoundError(Exception):
    """Raised when a requested loan contract is not found."""


class LoanRequestNotFoundError(Exception):
    """Raised when a loan request is not found for conversion."""


class LoanRequestNotApprovedError(Exception):
    """Raised when trying to convert a non-approved loan request into a loan."""


class LoanAlreadyCreatedError(Exception):
    """Raised when a loan has already been created from the given loan request."""


class InvalidLoanStatusTransitionError(Exception):
    """Raised when attempting an invalid loan status transition."""


async def create_loan_from_request(
    db: AsyncSession,
    *,
    request_id: UUID,
    owner_id: UUID,
) -> Loan:
    """Convert an approved LoanRequest into a durable Loan contract."""

    stmt = select(LoanRequest).where(LoanRequest.id == request_id).with_for_update()
    result = await db.execute(stmt)
    loan_request = result.scalar_one_or_none()

    if loan_request is None:
        raise LoanRequestNotFoundError(f"Loan request {request_id} not found")

    if loan_request.status != "approved":
        raise LoanRequestNotApprovedError(
            f"Loan request {request_id} has status '{loan_request.status}', expected 'approved'"
        )

    existing_loan_stmt = select(Loan).where(Loan.loan_request_id == request_id)
    existing_result = await db.execute(existing_loan_stmt)
    if existing_result.scalar_one_or_none() is not None:
        raise LoanAlreadyCreatedError(
            f"A loan has already been created for loan request {request_id}"
        )

    quote = calculate_quote(
        principal=loan_request.requested_principal,
        monthly_rate=loan_request.requested_monthly_rate,
        term_months=loan_request.requested_term_months,
        payment_frequency=loan_request.requested_payment_frequency,
        first_due_date=loan_request.requested_first_due_date,
    )

    loan = Loan(
        loan_request_id=loan_request.id,
        borrower_id=loan_request.borrower_id,
        original_principal=loan_request.requested_principal,
        outstanding_principal=loan_request.requested_principal,
        accrued_interest=Decimal("0.00"),
        monthly_rate=loan_request.requested_monthly_rate,
        term_months=loan_request.requested_term_months,
        payment_frequency=loan_request.requested_payment_frequency,
        number_of_payments=quote.number_of_payments,
        first_due_date=loan_request.requested_first_due_date,
        final_due_date=quote.final_due_date,
        next_interest_due_date=loan_request.requested_first_due_date,
        status="pending_disbursement",
    )

    db.add(loan)
    await db.flush()

    stmt_created = select(Loan).options(joinedload(Loan.borrower)).where(Loan.id == loan.id)
    created_result = await db.execute(stmt_created)
    return created_result.scalar_one()


async def disburse_loan(
    db: AsyncSession,
    *,
    loan_id: UUID,
    owner_id: UUID,
) -> Loan:
    """Disburse a pending loan, setting its status to active."""

    stmt = (
        select(Loan)
        .options(joinedload(Loan.borrower))
        .where(Loan.id == loan_id)
        .with_for_update(of=Loan)
    )
    result = await db.execute(stmt)
    loan = result.scalar_one_or_none()

    if loan is None:
        raise LoanNotFoundError(f"Loan {loan_id} not found")

    if loan.status != "pending_disbursement":
        raise InvalidLoanStatusTransitionError(
            f"Cannot disburse loan {loan_id} in status '{loan.status}'"
        )

    loan.status = "active"
    loan.disbursed_at = datetime.now(UTC)
    loan.accrued_interest = Decimal("0.00")
    if loan.next_interest_due_date is None:
        loan.next_interest_due_date = loan.first_due_date
    await db.flush()

    stmt_updated = select(Loan).options(joinedload(Loan.borrower)).where(Loan.id == loan.id)
    res_updated = await db.execute(stmt_updated)
    return res_updated.scalar_one()


async def cancel_loan(
    db: AsyncSession,
    *,
    loan_id: UUID,
    owner_id: UUID,
) -> Loan:
    """Cancel a pending loan prior to disbursement."""

    stmt = (
        select(Loan)
        .options(joinedload(Loan.borrower))
        .where(Loan.id == loan_id)
        .with_for_update(of=Loan)
    )
    result = await db.execute(stmt)
    loan = result.scalar_one_or_none()

    if loan is None:
        raise LoanNotFoundError(f"Loan {loan_id} not found")

    if loan.status != "pending_disbursement":
        raise InvalidLoanStatusTransitionError(
            f"Cannot cancel loan {loan_id} in status '{loan.status}'"
        )

    loan.status = "cancelled"
    loan.cancelled_at = datetime.now(UTC)
    await db.flush()

    stmt_updated = select(Loan).options(joinedload(Loan.borrower)).where(Loan.id == loan.id)
    res_updated = await db.execute(stmt_updated)
    return res_updated.scalar_one()


async def get_owner_loans(
    db: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Loan]:
    """Retrieve all loan contracts for owner review."""

    stmt = (
        select(Loan)
        .options(joinedload(Loan.borrower))
        .order_by(Loan.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status is not None:
        stmt = stmt.where(Loan.status == status)

    result = await db.execute(stmt)
    return result.scalars().all()


async def get_owner_loan_detail(
    db: AsyncSession,
    loan_id: UUID,
) -> Loan:
    """Retrieve detailed view of a single loan contract for owner."""

    stmt = select(Loan).options(joinedload(Loan.borrower)).where(Loan.id == loan_id)
    result = await db.execute(stmt)
    loan = result.scalar_one_or_none()
    if loan is None:
        raise LoanNotFoundError(f"Loan {loan_id} not found")
    return loan


async def get_borrower_loans(
    db: AsyncSession,
    borrower_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Loan]:
    """Retrieve loans belonging to an authenticated borrower."""

    stmt = (
        select(Loan)
        .where(Loan.borrower_id == borrower_id)
        .order_by(Loan.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_borrower_loan_detail(
    db: AsyncSession,
    *,
    loan_id: UUID,
    borrower_id: UUID,
) -> Loan:
    """Retrieve detailed view of a borrower's own loan contract."""

    stmt = select(Loan).where(Loan.id == loan_id, Loan.borrower_id == borrower_id)
    result = await db.execute(stmt)
    loan = result.scalar_one_or_none()
    if loan is None:
        raise LoanNotFoundError(f"Loan {loan_id} not found for borrower {borrower_id}")
    return loan
