"""Public and Owner-facing routes for Borrower registration review."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.borrowers.registration_exceptions import (
    RegistrationConflict,
    RegistrationNotFound,
    RegistrationStateConflict,
)
from app.features.borrowers.registration_schemas import (
    BorrowerRegistrationCreate,
    BorrowerRegistrationListResponse,
    BorrowerRegistrationOwnerResponse,
    BorrowerRegistrationRejectRequest,
    BorrowerRegistrationResponse,
)
from app.features.borrowers.registration_service import (
    approve_registration,
    create_registration,
    get_registration,
    list_registrations,
    reject_registration,
)
from app.features.owner_identity.dependencies import get_current_owner
from app.features.owner_identity.models import OwnerUser

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


def _review_error(exc: Exception) -> HTTPException:
    if isinstance(exc, RegistrationNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@owner_router.get("", response_model=BorrowerRegistrationListResponse)
async def pending_registrations(
    session: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[OwnerUser, Depends(get_current_owner)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BorrowerRegistrationListResponse:
    """List pending registrations oldest-first for the authenticated Owner."""

    del owner
    items, total = await list_registrations(session, limit=limit, offset=offset)
    return BorrowerRegistrationListResponse(
        items=[BorrowerRegistrationOwnerResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@owner_router.get("/{registration_id}", response_model=BorrowerRegistrationOwnerResponse)
async def registration_detail(
    registration_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[OwnerUser, Depends(get_current_owner)],
) -> BorrowerRegistrationOwnerResponse:
    """Return the PII required for one Owner review."""

    del owner
    try:
        registration = await get_registration(session, registration_id)
    except RegistrationNotFound as exc:
        raise _review_error(exc) from None
    return BorrowerRegistrationOwnerResponse.model_validate(registration)


@owner_router.post("/{registration_id}/approve", response_model=BorrowerRegistrationOwnerResponse)
async def approve(
    registration_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[OwnerUser, Depends(get_current_owner)],
) -> BorrowerRegistrationOwnerResponse:
    """Approve one pending registration and create its pre-activation identities."""

    try:
        registration = await approve_registration(
            session, registration_id=registration_id, owner_id=owner.id
        )
    except (RegistrationConflict, RegistrationNotFound, RegistrationStateConflict) as exc:
        raise _review_error(exc) from None
    return BorrowerRegistrationOwnerResponse.model_validate(registration)


@owner_router.post("/{registration_id}/reject", response_model=BorrowerRegistrationOwnerResponse)
async def reject(
    registration_id: UUID,
    payload: BorrowerRegistrationRejectRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[OwnerUser, Depends(get_current_owner)],
) -> BorrowerRegistrationOwnerResponse:
    """Reject one pending registration with a durable bounded reason."""

    try:
        registration = await reject_registration(
            session,
            registration_id=registration_id,
            owner_id=owner.id,
            reason=payload.reason,
        )
    except (RegistrationNotFound, RegistrationStateConflict) as exc:
        raise _review_error(exc) from None
    return BorrowerRegistrationOwnerResponse.model_validate(registration)
