"""Business logic and database transactions for loan requests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.borrowers.models import Borrower
from app.features.business_settings.models import BusinessSetting
from app.features.loan_requests.models import LoanRequest
from app.features.loans.calculator import calculate_quote, quantize_money, quantize_rate
from app.features.notifications.constants import (
    TEMPLATE_LOAN_REQUEST_APPROVED,
    TEMPLATE_LOAN_REQUEST_REJECTED,
    TEMPLATE_LOAN_REQUEST_SUBMITTED,
)
from app.features.notifications.service import enqueue_notification


class LoanRequestNotFoundError(Exception):
    """Raised when a requested loan request record does not exist."""


class LoanRequestConflictError(Exception):
    """Raised when a borrower attempts to submit multiple pending requests."""


class LoanRequestStateError(Exception):
    """Raised when an invalid state transition is attempted on a loan request."""


class BusinessEstimateRateUnconfiguredError(Exception):
    """Raised when business estimate rate has not been configured by the owner."""


async def get_business_estimate_rate(db_session: AsyncSession) -> Decimal:
    """Load default monthly estimate rate from BusinessSetting singleton."""
    stmt = select(BusinessSetting.default_monthly_estimate_rate).where(
        BusinessSetting.id == "default"
    )
    res = await db_session.execute(stmt)
    rate = res.scalar_one_or_none()
    if rate is None:
        raise BusinessEstimateRateUnconfiguredError(
            "Loan estimate/request cannot currently be calculated because the lending rate "
            "has not yet been configured by the owner."
        )
    return rate


async def submit_loan_request(
    db_session: AsyncSession,
    *,
    borrower_id: UUID,
    principal: Decimal,
    term_months: int,
    payment_frequency: str,
    first_due_date: date,
) -> LoanRequest:
    """Submit a new loan request for an authenticated borrower."""
    monthly_rate = await get_business_estimate_rate(db_session)

    # Check for existing pending request to provide clean error
    stmt = select(LoanRequest).where(
        LoanRequest.borrower_id == borrower_id,
        LoanRequest.status == "pending",
    )
    res = await db_session.execute(stmt)
    if res.scalar_one_or_none() is not None:
        raise LoanRequestConflictError("Borrower already has a pending loan request")

    # Validate calculations via domain calculator
    calculate_quote(
        principal=principal,
        monthly_rate=monthly_rate,
        term_months=term_months,
        payment_frequency=payment_frequency,
        first_due_date=first_due_date,
    )

    request = LoanRequest(
        borrower_id=borrower_id,
        requested_principal=quantize_money(principal),
        requested_monthly_rate=quantize_rate(monthly_rate),
        requested_term_months=term_months,
        requested_payment_frequency=payment_frequency,
        requested_first_due_date=first_due_date,
        status="pending",
        submitted_at=datetime.now(UTC),
    )
    db_session.add(request)
    try:
        await db_session.flush()
        await enqueue_notification(
            db_session,
            event_type="loan_request_submitted",
            aggregate_type="loan_request",
            aggregate_id=request.id,
            recipient_type="borrower",
            recipient_id=borrower_id,
            template_key=TEMPLATE_LOAN_REQUEST_SUBMITTED,
            payload={
                "loan_request_id": str(request.id),
                "requested_principal": str(request.requested_principal),
            },
        )
    except IntegrityError as exc:
        await db_session.rollback()
        raise LoanRequestConflictError("Borrower already has a pending loan request") from exc

    return request


async def list_borrower_loan_requests(
    db_session: AsyncSession,
    borrower_id: UUID,
) -> list[LoanRequest]:
    """Fetch all loan requests belonging to the authenticated borrower."""
    stmt = (
        select(LoanRequest)
        .where(LoanRequest.borrower_id == borrower_id)
        .order_by(LoanRequest.created_at.desc())
    )
    res = await db_session.execute(stmt)
    return list(res.scalars().all())


async def get_borrower_loan_request_detail(
    db_session: AsyncSession,
    borrower_id: UUID,
    request_id: UUID,
) -> LoanRequest:
    """Fetch detail of a specific loan request owned by the authenticated borrower."""
    stmt = select(LoanRequest).where(
        LoanRequest.id == request_id,
        LoanRequest.borrower_id == borrower_id,
    )
    res = await db_session.execute(stmt)
    req = res.scalar_one_or_none()
    if req is None:
        raise LoanRequestNotFoundError("Loan request not found")
    return req


async def cancel_borrower_loan_request(
    db_session: AsyncSession,
    borrower_id: UUID,
    request_id: UUID,
) -> LoanRequest:
    """Cancel a pending loan request owned by the authenticated borrower."""
    stmt = (
        select(LoanRequest)
        .where(
            LoanRequest.id == request_id,
            LoanRequest.borrower_id == borrower_id,
        )
        .with_for_update()
    )
    res = await db_session.execute(stmt)
    req = res.scalar_one_or_none()
    if req is None:
        raise LoanRequestNotFoundError("Loan request not found")

    if req.status != "pending":
        raise LoanRequestStateError("Only pending loan requests can be cancelled")

    req.status = "cancelled"
    await db_session.flush()
    return req


async def list_owner_loan_requests(
    db_session: AsyncSession,
    status_filter: str | None = None,
) -> list[tuple[LoanRequest, Borrower]]:
    """Fetch loan requests with borrower information for owner review."""
    stmt = (
        select(LoanRequest, Borrower)
        .join(Borrower, LoanRequest.borrower_id == Borrower.id)
        .order_by(LoanRequest.created_at.desc())
    )
    if status_filter is not None:
        stmt = stmt.where(LoanRequest.status == status_filter)

    res = await db_session.execute(stmt)
    return [(row[0], row[1]) for row in res.all()]


async def get_owner_loan_request_detail(
    db_session: AsyncSession,
    request_id: UUID,
) -> tuple[LoanRequest, Borrower]:
    """Fetch specific loan request with borrower information for owner review."""
    stmt = (
        select(LoanRequest, Borrower)
        .join(Borrower, LoanRequest.borrower_id == Borrower.id)
        .where(LoanRequest.id == request_id)
    )
    res = await db_session.execute(stmt)
    row = res.one_or_none()
    if row is None:
        raise LoanRequestNotFoundError("Loan request not found")
    return row[0], row[1]


async def approve_loan_request(
    db_session: AsyncSession,
    *,
    owner_id: UUID,
    request_id: UUID,
    owner_note: str | None = None,
) -> LoanRequest:
    """Approve a pending loan request (does NOT create Loan ORM instance in M10)."""
    stmt = select(LoanRequest).where(LoanRequest.id == request_id).with_for_update()
    res = await db_session.execute(stmt)
    req = res.scalar_one_or_none()
    if req is None:
        raise LoanRequestNotFoundError("Loan request not found")

    if req.status != "pending":
        raise LoanRequestStateError("Only pending loan requests can be approved")

    req.status = "approved"
    req.reviewed_at = datetime.now(UTC)
    req.reviewed_by_owner_id = owner_id
    req.owner_note = owner_note
    await enqueue_notification(
        db_session,
        event_type="loan_request_approved",
        aggregate_type="loan_request",
        aggregate_id=req.id,
        recipient_type="borrower",
        recipient_id=req.borrower_id,
        template_key=TEMPLATE_LOAN_REQUEST_APPROVED,
        payload={
            "loan_request_id": str(req.id),
            "requested_principal": str(req.requested_principal),
        },
    )
    await db_session.flush()
    return req


async def reject_loan_request(
    db_session: AsyncSession,
    *,
    owner_id: UUID,
    request_id: UUID,
    owner_note: str | None = None,
) -> LoanRequest:
    """Reject a pending loan request."""
    stmt = select(LoanRequest).where(LoanRequest.id == request_id).with_for_update()
    res = await db_session.execute(stmt)
    req = res.scalar_one_or_none()
    if req is None:
        raise LoanRequestNotFoundError("Loan request not found")

    if req.status != "pending":
        raise LoanRequestStateError("Only pending loan requests can be rejected")

    req.status = "rejected"
    req.reviewed_at = datetime.now(UTC)
    req.reviewed_by_owner_id = owner_id
    req.owner_note = owner_note
    await enqueue_notification(
        db_session,
        event_type="loan_request_rejected",
        aggregate_type="loan_request",
        aggregate_id=req.id,
        recipient_type="borrower",
        recipient_id=req.borrower_id,
        template_key=TEMPLATE_LOAN_REQUEST_REJECTED,
        payload={
            "loan_request_id": str(req.id),
            "requested_principal": str(req.requested_principal),
            "rejection_reason": req.owner_note or "Not specified",
        },
    )
    await db_session.flush()
    return req
