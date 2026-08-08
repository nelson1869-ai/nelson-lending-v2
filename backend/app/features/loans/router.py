"""HTTP router for Owner and Borrower loan lifecycle endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.borrowers.auth_dependencies import get_current_borrower_account
from app.features.borrowers.auth_service import BorrowerAuthContext
from app.features.loans.calculator import calculate_quote
from app.features.loans.schemas import (
    BorrowerLoanDetailResponse,
    BorrowerLoanResponse,
    BorrowerSummarySchema,
    LoanQuoteRequest,
    LoanQuoteResponse,
    OwnerLoanDetailResponse,
    OwnerLoanResponse,
)
from app.features.loans.service import (
    InvalidLoanStatusTransitionError,
    LoanAlreadyCreatedError,
    LoanNotFoundError,
    LoanRequestNotApprovedError,
    LoanRequestNotFoundError,
    cancel_loan,
    create_loan_from_request,
    disburse_loan,
    get_borrower_loan_detail,
    get_borrower_loans,
    get_owner_loan_detail,
    get_owner_loans,
)
from app.features.owner_identity.dependencies import get_current_owner
from app.features.owner_identity.models import OwnerUser

owner_loans_router = APIRouter(prefix="/owner", tags=["owner-loans"])
borrower_loans_router = APIRouter(prefix="/borrower/loans", tags=["borrower-loans"])

# Backward compatibility alias
router = owner_loans_router


@owner_loans_router.post(
    "/loans/quote",
    response_model=LoanQuoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate loan repayment quote and schedule",
)
async def get_loan_quote(
    request: LoanQuoteRequest,
    _owner: Annotated[OwnerUser, Depends(get_current_owner)],
) -> LoanQuoteResponse:
    """Stateless calculation endpoint for Flexible Reducing-Balance loan quote."""
    try:
        quote = calculate_quote(
            principal=request.principal,
            monthly_rate=request.monthly_rate,
            term_months=request.term_months,
            payment_frequency=request.payment_frequency,
            first_due_date=request.first_due_date,
        )
        return LoanQuoteResponse.from_domain(quote)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@owner_loans_router.post(
    "/loan-requests/{request_id}/create-loan",
    response_model=OwnerLoanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Convert approved loan request into a loan contract",
)
async def create_loan_from_approved_request(
    request_id: UUID,
    owner: Annotated[OwnerUser, Depends(get_current_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OwnerLoanResponse:
    """Owner endpoint to convert an approved loan request into a durable loan."""
    try:
        loan = await create_loan_from_request(
            db,
            request_id=request_id,
            owner_id=owner.id,
        )
        return OwnerLoanResponse.model_validate(loan)
    except LoanRequestNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except LoanRequestNotApprovedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except LoanAlreadyCreatedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@owner_loans_router.post(
    "/loans/{loan_id}/disburse",
    response_model=OwnerLoanResponse,
    status_code=status.HTTP_200_OK,
    summary="Disburse pending loan contract",
)
async def disburse_loan_endpoint(
    loan_id: UUID,
    owner: Annotated[OwnerUser, Depends(get_current_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OwnerLoanResponse:
    """Owner endpoint to confirm disbursement and transition loan status to active."""
    try:
        loan = await disburse_loan(
            db,
            loan_id=loan_id,
            owner_id=owner.id,
        )
        return OwnerLoanResponse.model_validate(loan)
    except LoanNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except InvalidLoanStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@owner_loans_router.post(
    "/loans/{loan_id}/cancel",
    response_model=OwnerLoanResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel pending loan contract prior to disbursement",
)
async def cancel_loan_endpoint(
    loan_id: UUID,
    owner: Annotated[OwnerUser, Depends(get_current_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OwnerLoanResponse:
    """Owner endpoint to cancel a pending-disbursement loan."""
    try:
        loan = await cancel_loan(
            db,
            loan_id=loan_id,
            owner_id=owner.id,
        )
        return OwnerLoanResponse.model_validate(loan)
    except LoanNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except InvalidLoanStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@owner_loans_router.get(
    "/loans",
    response_model=list[OwnerLoanResponse],
    status_code=status.HTTP_200_OK,
    summary="List all loan contracts for owner review",
)
async def list_owner_loans(
    _owner: Annotated[OwnerUser, Depends(get_current_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
    loan_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[OwnerLoanResponse]:
    """Retrieve all loan contracts for owner review."""
    loans = await get_owner_loans(
        db,
        status=loan_status,
        limit=limit,
        offset=offset,
    )
    res: list[OwnerLoanResponse] = []
    for loan_obj in loans:
        resp = OwnerLoanResponse.model_validate(loan_obj)
        if loan_obj.borrower:
            resp.borrower = BorrowerSummarySchema.model_validate(loan_obj.borrower)
        res.append(resp)
    return res


@owner_loans_router.get(
    "/loans/{loan_id}",
    response_model=OwnerLoanDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single loan contract detail for owner",
)
async def get_owner_loan(
    loan_id: UUID,
    _owner: Annotated[OwnerUser, Depends(get_current_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OwnerLoanDetailResponse:
    """Retrieve detail view of a single loan contract for owner."""
    try:
        loan = await get_owner_loan_detail(db, loan_id)
        quote = calculate_quote(
            principal=loan.original_principal,
            monthly_rate=loan.monthly_rate,
            term_months=loan.term_months,
            payment_frequency=loan.payment_frequency,
            first_due_date=loan.first_due_date,
        )
        resp = OwnerLoanDetailResponse.model_validate(loan)
        if loan.borrower:
            resp.borrower = BorrowerSummarySchema.model_validate(loan.borrower)
        resp.quote_preview = LoanQuoteResponse.from_domain(quote)
        return resp
    except LoanNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@borrower_loans_router.get(
    "",
    response_model=list[BorrowerLoanResponse],
    status_code=status.HTTP_200_OK,
    summary="List borrower's own loan contracts",
)
async def list_borrower_loans(
    auth_ctx: Annotated[BorrowerAuthContext, Depends(get_current_borrower_account)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[BorrowerLoanResponse]:
    """Retrieve loans belonging to the authenticated borrower."""
    loans = await get_borrower_loans(
        db,
        borrower_id=auth_ctx.borrower.id,
        limit=limit,
        offset=offset,
    )
    return [BorrowerLoanResponse.model_validate(loan_obj) for loan_obj in loans]


@borrower_loans_router.get(
    "/{loan_id}",
    response_model=BorrowerLoanDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single loan contract detail for borrower",
)
async def get_borrower_loan(
    loan_id: UUID,
    auth_ctx: Annotated[BorrowerAuthContext, Depends(get_current_borrower_account)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BorrowerLoanDetailResponse:
    """Retrieve detail view of a borrower's own loan contract."""
    try:
        loan = await get_borrower_loan_detail(
            db,
            loan_id=loan_id,
            borrower_id=auth_ctx.borrower.id,
        )
        quote = calculate_quote(
            principal=loan.original_principal,
            monthly_rate=loan.monthly_rate,
            term_months=loan.term_months,
            payment_frequency=loan.payment_frequency,
            first_due_date=loan.first_due_date,
        )
        resp = BorrowerLoanDetailResponse.model_validate(loan)
        resp.quote_preview = LoanQuoteResponse.from_domain(quote)
        return resp
    except LoanNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
