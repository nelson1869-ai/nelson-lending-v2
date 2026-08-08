"""Thin HTTP routes for Owner authentication."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.owner_identity.dependencies import get_current_owner
from app.features.owner_identity.exceptions import AuthenticationFailed
from app.features.owner_identity.models import OwnerUser
from app.features.owner_identity.schemas import (
    LoginRequest,
    OwnerMeResponse,
    RefreshRequest,
    TokenPairResponse,
)
from app.features.owner_identity.service import (
    TokenPair,
    login_owner,
    logout_owner,
    refresh_owner_session,
)

router = APIRouter(prefix="/owner/auth", tags=["owner-auth"])


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _token_response(pair: TokenPair) -> TokenPairResponse:
    return TokenPairResponse(
        access_token=pair.access_token.value,
        refresh_token=pair.refresh_token,
        access_token_expires_at=pair.access_token.expires_at,
    )


@router.post("/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPairResponse:
    """Authenticate the single active Owner using a generic failure contract."""

    try:
        pair = await login_owner(
            session,
            username=payload.username,
            password=payload.password,
        )
    except AuthenticationFailed:
        raise _unauthorized() from None
    return _token_response(pair)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPairResponse:
    """Rotate a single-use opaque refresh token."""

    try:
        pair = await refresh_owner_session(session, refresh_token=payload.refresh_token)
    except AuthenticationFailed:
        raise _unauthorized() from None
    return _token_response(pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Revoke the submitted refresh session; access JWTs expire naturally."""

    try:
        await logout_owner(session, refresh_token=payload.refresh_token)
    except AuthenticationFailed:
        raise _unauthorized() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=OwnerMeResponse)
async def me(owner: Annotated[OwnerUser, Depends(get_current_owner)]) -> OwnerUser:
    """Return the safe profile of the authenticated active Owner."""

    return owner
