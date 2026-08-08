"""HTTP router for Owner loan operations and calculation quote endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.features.loans.calculator import calculate_quote
from app.features.loans.schemas import LoanQuoteRequest, LoanQuoteResponse
from app.features.owner_identity.dependencies import get_current_owner
from app.features.owner_identity.models import OwnerUser

router = APIRouter(prefix="/owner/loans", tags=["owner-loans"])


@router.post(
    "/quote",
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
