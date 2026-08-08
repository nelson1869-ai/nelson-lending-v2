"""Borrower activation, PIN, device, JWT, and token security primitives."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings, get_settings
from app.core.security import AccessToken, AccessTokenError

BORROWER_ACCESS_TOKEN_TYPE = "borrower_access"
PIN_LENGTH = 6
_pin_hasher = PasswordHasher()


def validate_pin(pin: str) -> None:
    """Require exactly six numeric digits without boundary trimming."""

    if len(pin) != PIN_LENGTH or not pin.isascii() or not pin.isdigit():
        raise ValueError("PIN must contain exactly 6 numeric digits")


def hash_pin(pin: str) -> str:
    validate_pin(pin)
    return _pin_hasher.hash(pin)


def verify_pin(pin: str, pin_hash: str) -> bool:
    try:
        return _pin_hasher.verify(pin_hash, pin)
    except (InvalidHashError, VerificationError):
        return False


def generate_activation_code() -> str:
    """Return a cryptographically random six-digit code, preserving leading zeros."""

    return f"{secrets.randbelow(1_000_000):06d}"


def hash_activation_code(account_id: UUID, code: str, *, settings: Settings | None = None) -> str:
    config = settings or get_settings()
    message = f"{account_id}:{code}".encode()
    return hmac.new(
        config.borrower_activation_code_secret.encode(), message, hashlib.sha256
    ).hexdigest()


def verify_activation_code(
    account_id: UUID, code: str, code_hash: str, *, settings: Settings | None = None
) -> bool:
    candidate = hash_activation_code(account_id, code, settings=settings)
    return hmac.compare_digest(candidate, code_hash)


def hash_device_identifier(identifier: str, *, settings: Settings | None = None) -> str:
    config = settings or get_settings()
    return hmac.new(
        config.device_identifier_secret.encode(), identifier.encode(), hashlib.sha256
    ).hexdigest()


def create_borrower_access_token(
    account_id: UUID,
    borrower_id: UUID,
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> AccessToken:
    config = settings or get_settings()
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=config.borrower_access_token_minutes)
    payload = {
        "sub": str(account_id),
        "borrower_id": str(borrower_id),
        "token_type": BORROWER_ACCESS_TOKEN_TYPE,
        "iat": issued_at,
        "exp": expires_at,
        "jti": str(uuid4()),
    }
    encoded = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)
    return AccessToken(value=encoded, expires_at=expires_at)


def decode_borrower_access_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    config = settings or get_settings()
    try:
        payload = jwt.decode(token, config.jwt_secret_key, algorithms=[config.jwt_algorithm])
        if payload.get("token_type") != BORROWER_ACCESS_TOKEN_TYPE:
            raise AccessTokenError("Invalid access token")
        UUID(str(payload["sub"]))
        UUID(str(payload["borrower_id"]))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise AccessTokenError("Invalid access token") from exc
    return payload
