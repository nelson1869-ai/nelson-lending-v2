"""Thin Owner issuance and Borrower authentication routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.borrowers.auth_dependencies import get_current_borrower_account
from app.features.borrowers.auth_exceptions import (
    ActivationUnavailable,
    BorrowerAuthFailed,
    BorrowerNotFound,
)
from app.features.borrowers.auth_schemas import (
    ActivateRequest,
    ActivationCodeResponse,
    ActivationResponse,
    BorrowerLoginRequest,
    BorrowerLogoutRequest,
    BorrowerMeResponse,
    BorrowerRefreshRequest,
    BorrowerTokenPairResponse,
)
from app.features.borrowers.auth_service import (
    BorrowerAuthContext,
    BorrowerTokenPair,
    activate_borrower,
    issue_activation_code,
    login_borrower,
    logout_borrower,
    refresh_borrower_session,
)
from app.features.owner_identity.dependencies import get_current_owner
from app.features.owner_identity.models import OwnerUser

owner_router = APIRouter(prefix="/owner/borrowers", tags=["owner-borrower-activation"])
borrower_router = APIRouter(prefix="/borrower/auth", tags=["borrower-auth"])


def _unauthorized(detail: str = "Invalid credentials") -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def _token_response(pair: BorrowerTokenPair) -> BorrowerTokenPairResponse:
    return BorrowerTokenPairResponse(
        access_token=pair.access_token.value,
        refresh_token=pair.refresh_token,
        access_token_expires_at=pair.access_token.expires_at,
    )


@owner_router.post("/{borrower_id}/activation-code", response_model=ActivationCodeResponse)
async def create_activation_code(
    borrower_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[OwnerUser, Depends(get_current_owner)],
) -> ActivationCodeResponse:
    del owner
    try:
        grant = await issue_activation_code(session, borrower_id=borrower_id)
    except BorrowerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ActivationUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return ActivationCodeResponse(
        borrower_id=grant.borrower_id, expires_at=grant.expires_at, activation_code=grant.code
    )


@borrower_router.post("/activate", response_model=ActivationResponse)
async def activate(
    payload: ActivateRequest, session: Annotated[AsyncSession, Depends(get_db)]
) -> ActivationResponse:
    try:
        await activate_borrower(
            session,
            normalized_phone=payload.phone_number,
            activation_code=payload.activation_code,
            pin=payload.pin,
        )
    except BorrowerAuthFailed as exc:
        raise _unauthorized(str(exc)) from None
    return ActivationResponse()


@borrower_router.post("/login", response_model=BorrowerTokenPairResponse)
async def login(
    payload: BorrowerLoginRequest, session: Annotated[AsyncSession, Depends(get_db)]
) -> BorrowerTokenPairResponse:
    try:
        pair = await login_borrower(
            session,
            normalized_phone=payload.phone_number,
            pin=payload.pin,
            device_identifier=payload.device_identifier,
            platform=payload.platform,
        )
    except BorrowerAuthFailed:
        raise _unauthorized() from None
    return _token_response(pair)


@borrower_router.post("/refresh", response_model=BorrowerTokenPairResponse)
async def refresh(
    payload: BorrowerRefreshRequest, session: Annotated[AsyncSession, Depends(get_db)]
) -> BorrowerTokenPairResponse:
    try:
        pair = await refresh_borrower_session(
            session,
            refresh_token=payload.refresh_token,
            device_identifier=payload.device_identifier,
        )
    except BorrowerAuthFailed:
        raise _unauthorized() from None
    return _token_response(pair)


@borrower_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: BorrowerLogoutRequest, session: Annotated[AsyncSession, Depends(get_db)]
) -> Response:
    try:
        await logout_borrower(session, refresh_token=payload.refresh_token)
    except BorrowerAuthFailed:
        raise _unauthorized() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@borrower_router.get("/me", response_model=BorrowerMeResponse)
async def me(
    context: Annotated[BorrowerAuthContext, Depends(get_current_borrower_account)],
) -> BorrowerMeResponse:
    return BorrowerMeResponse(
        borrower_id=context.borrower.id,
        account_id=context.account.id,
        first_name=context.borrower.first_name,
        last_name=context.borrower.last_name,
        phone_number=context.account.phone_number,
        account_status=context.account.account_status,
    )
