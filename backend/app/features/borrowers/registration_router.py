"""Public and Owner-facing routes for Borrower registration review."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.borrowers.registration_exceptions import RegistrationConflict
from app.features.borrowers.registration_schemas import (
    BorrowerRegistrationCreate,
    BorrowerRegistrationResponse,
)
from app.features.borrowers.registration_service import create_registration

public_router = APIRouter(prefix="/borrower/registrations", tags=["borrower-registration"])
owner_router = APIRouter(
    prefix="/owner/borrower-registrations", tags=["owner-borrower-registration"]
)


@public_router.post(
    "", response_model=BorrowerRegistrationResponse, status_code=status.HTTP_201_CREATED
)
async def register_borrower(
    payload: BorrowerRegistrationCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BorrowerRegistrationResponse:
    """Accept one privacy-preserving public registration request."""

    try:
        registration = await create_registration(session, payload)
    except RegistrationConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    return BorrowerRegistrationResponse(
        registration_id=registration.id,
        status=registration.status,
        submitted_at=registration.submitted_at,
        message="Registration submitted for Owner review.",
    )
