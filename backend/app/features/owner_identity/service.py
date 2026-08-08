"""Transactional Owner bootstrap and authentication services."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import (
    AccessToken,
    create_owner_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    normalize_username,
    verify_password,
)
from app.features.owner_identity.exceptions import (
    AuthenticationFailed,
    OwnerAlreadyBootstrapped,
)
from app.features.owner_identity.models import OwnerRefreshToken, OwnerUser

_BOOTSTRAP_ADVISORY_LOCK = 4_004_001


@dataclass(frozen=True)
class TokenPair:
    access_token: AccessToken
    refresh_token: str


def _authentication_failed() -> AuthenticationFailed:
    return AuthenticationFailed("Invalid credentials")


def _new_refresh_session(
    owner_id: UUID,
    *,
    settings: Settings,
    now: datetime,
) -> tuple[str, OwnerRefreshToken]:
    raw_token = generate_refresh_token()
    record = OwnerRefreshToken(
        owner_user_id=owner_id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=now + timedelta(days=settings.owner_refresh_token_days),
    )
    return raw_token, record


async def bootstrap_owner(session: AsyncSession, *, username: str, password: str) -> OwnerUser:
    """Create the one Owner exactly once inside a race-safe transaction."""

    normalized_username = normalize_username(username)
    if not normalized_username:
        raise ValueError("Username must not be blank")
    password_hash = hash_password(password)

    async with session.begin():
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": _BOOTSTRAP_ADVISORY_LOCK},
        )
        owner_count = await session.scalar(select(func.count()).select_from(OwnerUser))
        if owner_count:
            raise OwnerAlreadyBootstrapped("Owner bootstrap has already been completed")

        owner = OwnerUser(
            username=normalized_username,
            password_hash=password_hash,
            is_active=True,
        )
        session.add(owner)
        await session.flush()
    return owner


async def login_owner(
    session: AsyncSession,
    *,
    username: str,
    password: str,
    settings: Settings | None = None,
) -> TokenPair:
    """Authenticate Owner credentials and create one refresh session atomically."""

    config = settings or get_settings()
    normalized_username = normalize_username(username)
    now = datetime.now(UTC)

    async with session.begin():
        owner = await session.scalar(
            select(OwnerUser).where(OwnerUser.username == normalized_username)
        )
        if owner is None:
            # Perform an Argon2 verification-equivalent path without exposing which check failed.
            verify_password(password, hash_password("nonexistent owner timing password"))
            raise _authentication_failed()
        if not owner.is_active or not verify_password(password, owner.password_hash):
            raise _authentication_failed()

        owner.last_login_at = now
        raw_refresh_token, refresh_session = _new_refresh_session(
            owner.id,
            settings=config,
            now=now,
        )
        session.add(refresh_session)
        access_token = create_owner_access_token(owner.id, settings=config, now=now)

    return TokenPair(access_token=access_token, refresh_token=raw_refresh_token)


async def refresh_owner_session(
    session: AsyncSession,
    *,
    refresh_token: str,
    settings: Settings | None = None,
) -> TokenPair:
    """Rotate one valid refresh token under a row lock and issue a new pair."""

    config = settings or get_settings()
    token_hash = hash_refresh_token(refresh_token)
    now = datetime.now(UTC)

    async with session.begin():
        current = await session.scalar(
            select(OwnerRefreshToken)
            .where(OwnerRefreshToken.token_hash == token_hash)
            .with_for_update()
        )
        if current is None or current.revoked_at is not None or current.expires_at <= now:
            raise _authentication_failed()

        owner = await session.get(OwnerUser, current.owner_user_id)
        if owner is None or not owner.is_active:
            raise _authentication_failed()

        raw_replacement, replacement = _new_refresh_session(
            owner.id,
            settings=config,
            now=now,
        )
        session.add(replacement)
        await session.flush()
        current.revoked_at = now
        current.rotated_to_token_id = replacement.id
        access_token = create_owner_access_token(owner.id, settings=config, now=now)

    return TokenPair(access_token=access_token, refresh_token=raw_replacement)


async def logout_owner(session: AsyncSession, *, refresh_token: str) -> None:
    """Revoke exactly one submitted refresh session atomically."""

    token_hash = hash_refresh_token(refresh_token)
    now = datetime.now(UTC)
    async with session.begin():
        current = await session.scalar(
            select(OwnerRefreshToken)
            .where(OwnerRefreshToken.token_hash == token_hash)
            .with_for_update()
        )
        if current is None or current.revoked_at is not None or current.expires_at <= now:
            raise _authentication_failed()
        current.revoked_at = now
