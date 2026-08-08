"""Payment endpoints for Owner posting and Borrower history visibility."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.borrowers.auth_dependencies import get_current_borrower_account
from app.features.borrowers.auth_service import BorrowerAuthContext
from app.features.loans.models import Loan
from app.features.owner_identity.dependencies import get_current_owner
from app.features.owner_identity.models import OwnerUser
from app.features.payments.schemas import (
    BorrowerPaymentResponse,
    PaymentPostRequest,
    PaymentResponse,
)
from app.features.payments.service import list_loan_payments, post_payment

owner_router = APIRouter(prefix="/owner", tags=["Owner Payments"])
borrower_router = APIRouter(prefix="/borrower", tags=["Borrower Payments"])

CurrentBorrowerAuth = Annotated[BorrowerAuthContext, Depends(get_current_borrower_account)]
CurrentOwner = Annotated[OwnerUser, Depends(get_current_owner)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


@owner_router.post(
    "/loans/{loan_id}/payments",
    response_model=PaymentResponse,
    # FastAPI default for the decorator; actual status code is set dynamically below.
    status_code=status.HTTP_201_CREATED,
    summary="Post payment against active loan (Owner only)",
)
async def owner_post_payment(
    loan_id: UUID,
    payload: PaymentPostRequest,
    _current_owner: CurrentOwner,
    db: DatabaseSession,
    response: Response,
) -> PaymentResponse:
    """Record a received payment and atomically allocate interest and principal.

    Returns HTTP 201 for a newly created payment, or HTTP 200 when the request is
    an idempotent replay of an existing payment (same idempotency key + same payload).
    """
    payment, was_replayed = await post_payment(db, loan_id, payload)
    if was_replayed:
        response.status_code = status.HTTP_200_OK
    return PaymentResponse.model_validate(payment)


@owner_router.get(
    "/loans/{loan_id}/payments",
    response_model=list[PaymentResponse],
    summary="List payment history for a loan (Owner only)",
)
async def owner_list_loan_payments(
    loan_id: UUID,
    _current_owner: CurrentOwner,
    db: DatabaseSession,
) -> list[PaymentResponse]:
    """Retrieve complete payment history for a loan."""
    loan = await db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan '{loan_id}' not found.",
        )
    payments = await list_loan_payments(db, loan_id)
    return [PaymentResponse.model_validate(p) for p in payments]


@borrower_router.get(
    "/loans/{loan_id}/payments",
    response_model=list[BorrowerPaymentResponse],
    summary="List payment history for owned loan (Borrower only)",
)
async def borrower_list_loan_payments(
    loan_id: UUID,
    auth: CurrentBorrowerAuth,
    db: DatabaseSession,
) -> list[BorrowerPaymentResponse]:
    """Retrieve payment history for a loan owned by the authenticated borrower."""
    loan = await db.get(Loan, loan_id)
    if loan is None or loan.borrower_id != auth.borrower.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan '{loan_id}' not found.",
        )
    payments = await list_loan_payments(db, loan_id)
    return [BorrowerPaymentResponse.model_validate(p) for p in payments]
