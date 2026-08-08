"""Contract tests for Owner authentication security primitives."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    AccessTokenError,
    create_owner_access_token,
    decode_owner_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

TEST_SETTINGS = Settings(
    jwt_secret_key="unit-test-secret-key-that-is-long-enough",
    owner_access_token_minutes=15,
)


def test_password_hashing_and_verification() -> None:
    password = "correct horse battery staple"
    password_hash = hash_password(password)

    assert password_hash.startswith("$argon2id$")
    assert password not in password_hash
    assert verify_password(password, password_hash)
    assert not verify_password("wrong password", password_hash)


def test_password_policy_rejects_short_password() -> None:
    with pytest.raises(ValueError, match="at least 12"):
        hash_password("too-short")


def test_owner_access_token_contract() -> None:
    owner_id = uuid4()
    token = create_owner_access_token(owner_id, settings=TEST_SETTINGS)
    payload = decode_owner_access_token(token.value, settings=TEST_SETTINGS)

    assert payload["sub"] == str(owner_id)
    assert payload["token_type"] == "owner_access"
    assert {"iat", "exp", "jti"} <= payload.keys()


def test_expired_owner_access_token_is_rejected() -> None:
    token = create_owner_access_token(
        uuid4(),
        settings=TEST_SETTINGS,
        now=datetime.now(UTC) - timedelta(hours=1),
    )

    with pytest.raises(AccessTokenError):
        decode_owner_access_token(token.value, settings=TEST_SETTINGS)


def test_wrong_token_type_is_rejected() -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "token_type": "borrower_access",
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "jti": str(uuid4()),
        },
        TEST_SETTINGS.jwt_secret_key,
        algorithm=TEST_SETTINGS.jwt_algorithm,
    )

    with pytest.raises(AccessTokenError):
        decode_owner_access_token(token, settings=TEST_SETTINGS)


def test_refresh_tokens_are_opaque_and_hash_deterministically() -> None:
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert first != second
    assert len(first) >= 64
    assert hash_refresh_token(first) == hash_refresh_token(first)
    assert hash_refresh_token(first) != hash_refresh_token(second)
    assert first not in hash_refresh_token(first)
