"""Owner password, access-token, and opaque refresh-token primitives."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings, get_settings

OWNER_ACCESS_TOKEN_TYPE = "owner_access"
PASSWORD_MIN_LENGTH = 12
_password_hasher = PasswordHasher()


class AccessTokenError(ValueError):
    """Raised when an access token fails the Owner token contract."""


@dataclass(frozen=True)
class AccessToken:
    """An encoded access token and its exact expiration instant."""

    value: str
    expires_at: datetime


def normalize_username(username: str) -> str:
    """Normalize case-insensitive Owner usernames at the system boundary."""

    return username.strip().lower()


def validate_password(password: str) -> None:
    """Apply the deliberately simple Owner bootstrap password policy."""

    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must contain at least {PASSWORD_MIN_LENGTH} characters")
    if not password.strip():
        raise ValueError("Password must not be blank")


def hash_password(password: str) -> str:
    """Hash a valid password using Argon2id with a library-managed random salt."""

    validate_password(password)
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether a password matches without leaking malformed-hash errors."""

    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return False


def create_owner_access_token(
    owner_id: UUID,
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> AccessToken:
    """Issue a short-lived JWT restricted to the Owner authentication domain."""

    config = settings or get_settings()
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=config.owner_access_token_minutes)
    payload = {
        "sub": str(owner_id),
        "token_type": OWNER_ACCESS_TOKEN_TYPE,
        "iat": issued_at,
        "exp": expires_at,
        "jti": str(uuid4()),
    }
    encoded = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)
    return AccessToken(value=encoded, expires_at=expires_at)


def decode_owner_access_token(
    token: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Decode and enforce the Owner access-token type and subject contract."""

    config = settings or get_settings()
    try:
        payload = jwt.decode(token, config.jwt_secret_key, algorithms=[config.jwt_algorithm])
        if payload.get("token_type") != OWNER_ACCESS_TOKEN_TYPE:
            raise AccessTokenError("Invalid access token")
        UUID(str(payload["sub"]))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise AccessTokenError("Invalid access token") from exc
    return payload


def generate_refresh_token() -> str:
    """Generate a high-entropy opaque refresh token suitable for bearer use."""

    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Hash a random refresh token for deterministic database lookup."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
