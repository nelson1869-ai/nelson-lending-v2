"""HTTP API routers for borrower loan requests and owner review workflows."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.borrowers.auth_dependencies import get_current_borrower_account
from app.features.borrowers.auth_service import BorrowerAuthContext
from app.features.loan_requests.schemas import (
    LoanRequestCreate,
    LoanRequestResponse,
    LoanRequestReviewRequest,
    OwnerLoanRequestDetailResponse,
)
from app.features.loan_requests.service import (
    LoanRequestConflictError,
    LoanRequestNotFoundError,
    LoanRequestStateError,
    approve_loan_request,
    cancel_borrower_loan_request,
    get_borrower_loan_request_detail,
    get_owner_loan_request_detail,
    list_borrower_loan_requests,
    list_owner_loan_requests,
    reject_loan_request,
    submit_loan_request,
)
from app.features.loans.calculator import calculate_quote
from app.features.loans.schemas import LoanQuoteRequest, LoanQuoteResponse
from app.features.owner_identity.dependencies import get_current_owner
from app.features.owner_identity.models import OwnerUser

borrower_loan_requests_router = APIRouter(
    prefix="/borrower/loan-requests",
    tags=["Borrower Loan Requests"],
)

owner_loan_requests_router = APIRouter(
    prefix="/owner/loan-requests",
    tags=["Owner Loan Requests"],
)

CurrentBorrowerAuth = Annotated[BorrowerAuthContext, Depends(get_current_borrower_account)]
CurrentOwner = Annotated[OwnerUser, Depends(get_current_owner)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


@borrower_loan_requests_router.post(
    "/quote",
    response_model=LoanQuoteResponse,
    status_code=status.HTTP_200_OK,
)
async def borrower_loan_quote(
    payload: LoanQuoteRequest,
    auth: CurrentBorrowerAuth,
) -> LoanQuoteResponse:
    """Stateless loan quote preview for authenticated borrowers."""
    quote = calculate_quote(
        principal=payload.principal,
        monthly_rate=payload.monthly_rate,
        term_months=payload.term_months,
        payment_frequency=payload.payment_frequency,
        first_due_date=payload.first_due_date,
    )
    return LoanQuoteResponse.model_validate(quote)


@borrower_loan_requests_router.post(
    "",
    response_model=LoanRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def borrower_submit_loan_request(
    payload: LoanRequestCreate,
    auth: CurrentBorrowerAuth,
    db_session: DatabaseSession,
) -> LoanRequestResponse:
    """Submit a new loan request for the authenticated borrower."""
    try:
        req = await submit_loan_request(
            db_session,
            borrower_id=auth.borrower.id,
            principal=payload.principal,
            monthly_rate=payload.monthly_rate,
            term_months=payload.term_months,
            payment_frequency=payload.payment_frequency,
            first_due_date=payload.first_due_date,
        )
        await db_session.commit()
        await db_session.refresh(req)
        return LoanRequestResponse.model_validate(req)
    except LoanRequestConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@borrower_loan_requests_router.get(
    "",
    response_model=list[LoanRequestResponse],
    status_code=status.HTTP_200_OK,
)
async def borrower_list_loan_requests(
    auth: CurrentBorrowerAuth,
    db_session: DatabaseSession,
) -> list[LoanRequestResponse]:
    """List all loan requests created by the authenticated borrower."""
    requests = await list_borrower_loan_requests(db_session, auth.borrower.id)
    return [LoanRequestResponse.model_validate(r) for r in requests]


@borrower_loan_requests_router.get(
    "/{request_id}",
    response_model=LoanRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def borrower_get_loan_request_detail(
    request_id: UUID,
    auth: CurrentBorrowerAuth,
    db_session: DatabaseSession,
) -> LoanRequestResponse:
    """Fetch detail of a specific loan request owned by the authenticated borrower."""
    try:
        req = await get_borrower_loan_request_detail(
            db_session,
            borrower_id=auth.borrower.id,
            request_id=request_id,
        )
        return LoanRequestResponse.model_validate(req)
    except LoanRequestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@borrower_loan_requests_router.post(
    "/{request_id}/cancel",
    response_model=LoanRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def borrower_cancel_loan_request(
    request_id: UUID,
    auth: CurrentBorrowerAuth,
    db_session: DatabaseSession,
) -> LoanRequestResponse:
    """Cancel a pending loan request owned by the authenticated borrower."""
    try:
        req = await cancel_borrower_loan_request(
            db_session,
            borrower_id=auth.borrower.id,
            request_id=request_id,
        )
        await db_session.commit()
        await db_session.refresh(req)
        return LoanRequestResponse.model_validate(req)
    except LoanRequestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LoanRequestStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@owner_loan_requests_router.get(
    "",
    response_model=list[OwnerLoanRequestDetailResponse],
    status_code=status.HTTP_200_OK,
)
async def owner_list_loan_requests(
    owner: CurrentOwner,
    db_session: DatabaseSession,
    status_filter: str | None = None,
) -> list[OwnerLoanRequestDetailResponse]:
    """List loan requests for owner review with borrower details and calculated quotes."""
    rows = await list_owner_loan_requests(db_session, status_filter=status_filter)
    results: list[OwnerLoanRequestDetailResponse] = []
    for req, b in rows:
        quote = calculate_quote(
            principal=req.requested_principal,
            monthly_rate=req.requested_monthly_rate,
            term_months=req.requested_term_months,
            payment_frequency=req.requested_payment_frequency,
            first_due_date=req.requested_first_due_date,
        )
        results.append(
            OwnerLoanRequestDetailResponse(
                id=req.id,
                borrower_id=req.borrower_id,
                requested_principal=req.requested_principal,
                requested_monthly_rate=req.requested_monthly_rate,
                requested_term_months=req.requested_term_months,
                requested_payment_frequency=req.requested_payment_frequency,
                requested_first_due_date=req.requested_first_due_date,
                status=req.status,
                submitted_at=req.submitted_at,
                reviewed_at=req.reviewed_at,
                reviewed_by_owner_id=req.reviewed_by_owner_id,
                owner_note=req.owner_note,
                created_at=req.created_at,
                updated_at=req.updated_at,
                borrower_first_name=b.first_name,
                borrower_last_name=b.last_name,
                borrower_national_id=b.national_id,
                borrower_phone_number=b.phone_number,
                quote_preview=LoanQuoteResponse.model_validate(quote),
            )
        )
    return results


@owner_loan_requests_router.get(
    "/{request_id}",
    response_model=OwnerLoanRequestDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def owner_get_loan_request_detail(
    request_id: UUID,
    owner: CurrentOwner,
    db_session: DatabaseSession,
) -> OwnerLoanRequestDetailResponse:
    """Fetch loan request detail for owner review."""
    try:
        req, b = await get_owner_loan_request_detail(db_session, request_id)
        quote = calculate_quote(
            principal=req.requested_principal,
            monthly_rate=req.requested_monthly_rate,
            term_months=req.requested_term_months,
            payment_frequency=req.requested_payment_frequency,
            first_due_date=req.requested_first_due_date,
        )
        return OwnerLoanRequestDetailResponse(
            id=req.id,
            borrower_id=req.borrower_id,
            requested_principal=req.requested_principal,
            requested_monthly_rate=req.requested_monthly_rate,
            requested_term_months=req.requested_term_months,
            requested_payment_frequency=req.requested_payment_frequency,
            requested_first_due_date=req.requested_first_due_date,
            status=req.status,
            submitted_at=req.submitted_at,
            reviewed_at=req.reviewed_at,
            reviewed_by_owner_id=req.reviewed_by_owner_id,
            owner_note=req.owner_note,
            created_at=req.created_at,
            updated_at=req.updated_at,
            borrower_first_name=b.first_name,
            borrower_last_name=b.last_name,
            borrower_national_id=b.national_id,
            borrower_phone_number=b.phone_number,
            quote_preview=LoanQuoteResponse.model_validate(quote),
        )
    except LoanRequestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@owner_loan_requests_router.post(
    "/{request_id}/approve",
    response_model=LoanRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def owner_approve_loan_request(
    request_id: UUID,
    owner: CurrentOwner,
    db_session: DatabaseSession,
    payload: LoanRequestReviewRequest | None = None,
) -> LoanRequestResponse:
    """Approve a pending loan request (does NOT create Loan instance)."""
    try:
        note = payload.owner_note if payload else None
        req = await approve_loan_request(
            db_session,
            owner_id=owner.id,
            request_id=request_id,
            owner_note=note,
        )
        await db_session.commit()
        await db_session.refresh(req)
        return LoanRequestResponse.model_validate(req)
    except LoanRequestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LoanRequestStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@owner_loan_requests_router.post(
    "/{request_id}/reject",
    response_model=LoanRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def owner_reject_loan_request(
    request_id: UUID,
    owner: CurrentOwner,
    db_session: DatabaseSession,
    payload: LoanRequestReviewRequest | None = None,
) -> LoanRequestResponse:
    """Reject a pending loan request."""
    try:
        note = payload.owner_note if payload else None
        req = await reject_loan_request(
            db_session,
            owner_id=owner.id,
            request_id=request_id,
            owner_note=note,
        )
        await db_session.commit()
        await db_session.refresh(req)
        return LoanRequestResponse.model_validate(req)
    except LoanRequestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LoanRequestStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
