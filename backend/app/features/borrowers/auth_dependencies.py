"""Canonical authenticated Borrower account context dependency."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AccessTokenError
from app.db.session import get_db
from app.features.borrowers.auth_security import decode_borrower_access_token
from app.features.borrowers.auth_service import BorrowerAuthContext
from app.features.borrowers.models import Borrower, BorrowerAccount
from app.features.owner_identity.dependencies import bearer_scheme


async def get_current_borrower_account(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BorrowerAuthContext:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        payload = decode_borrower_access_token(credentials.credentials)
        account_id = UUID(str(payload["sub"]))
        borrower_id = UUID(str(payload["borrower_id"]))
    except (AccessTokenError, KeyError, TypeError, ValueError):
        raise unauthorized from None

    account = await session.get(BorrowerAccount, account_id)
    borrower = await session.get(Borrower, borrower_id)
    if (
        account is None
        or account.account_status != "activated"
        or account.borrower_id != borrower_id
        or borrower is None
        or borrower.status != "active"
    ):
        raise unauthorized
    return BorrowerAuthContext(account=account, borrower=borrower)
