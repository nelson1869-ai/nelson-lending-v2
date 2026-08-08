"""Canonical FastAPI dependency for the Owner authentication domain."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AccessTokenError, decode_owner_access_token
from app.db.session import get_db
from app.features.owner_identity.models import OwnerUser

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_owner(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OwnerUser:
    """Resolve one active Owner from a valid Owner access token."""

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        payload = decode_owner_access_token(credentials.credentials)
        owner_id = UUID(str(payload["sub"]))
    except (AccessTokenError, KeyError, TypeError, ValueError):
        raise unauthorized from None

    owner = await session.get(OwnerUser, owner_id)
    if owner is None or not owner.is_active:
        raise unauthorized
    return owner
