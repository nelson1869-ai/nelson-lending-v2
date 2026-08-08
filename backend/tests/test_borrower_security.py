"""Contract tests for Borrower activation and authentication primitives."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.security import AccessTokenError, create_owner_access_token
from app.features.borrowers.auth_security import (
    create_borrower_access_token,
    decode_borrower_access_token,
    generate_activation_code,
    hash_activation_code,
    hash_device_identifier,
    hash_pin,
    validate_pin,
    verify_activation_code,
    verify_pin,
)

SETTINGS = Settings(
    jwt_secret_key="borrower-unit-jwt-secret-long-enough",
    borrower_activation_code_secret="borrower-unit-activation-secret-long-enough",
    device_identifier_secret="borrower-unit-device-secret-long-enough",
)


@pytest.mark.parametrize("pin", ["12345", "1234567", "12345a", " 123456", "１２３４５６"])
def test_pin_policy_rejects_non_six_ascii_digits(pin: str) -> None:
    with pytest.raises(ValueError, match="6 numeric digits"):
        validate_pin(pin)


def test_pin_uses_argon2id() -> None:
    pin_hash = hash_pin("482915")
    assert pin_hash.startswith("$argon2id$")
    assert "482915" not in pin_hash
    assert verify_pin("482915", pin_hash)
    assert not verify_pin("482916", pin_hash)


def test_activation_code_format_and_keyed_hash() -> None:
    account_id = uuid4()
    code = generate_activation_code()
    digest = hash_activation_code(account_id, code, settings=SETTINGS)
    assert len(code) == 6 and code.isdigit()
    assert code not in digest
    assert verify_activation_code(account_id, code, digest, settings=SETTINGS)
    assert not verify_activation_code(account_id, "000001", digest, settings=SETTINGS)
    assert hash_activation_code(uuid4(), code, settings=SETTINGS) != digest


def test_device_identifier_is_keyed_and_deterministic() -> None:
    raw = "synthetic-device-identifier-0001"
    first = hash_device_identifier(raw, settings=SETTINGS)
    assert first == hash_device_identifier(raw, settings=SETTINGS)
    assert raw not in first


def test_borrower_access_token_contract_and_owner_separation() -> None:
    account_id, borrower_id = uuid4(), uuid4()
    token = create_borrower_access_token(account_id, borrower_id, settings=SETTINGS)
    payload = decode_borrower_access_token(token.value, settings=SETTINGS)
    assert payload["sub"] == str(account_id)
    assert payload["borrower_id"] == str(borrower_id)
    assert payload["token_type"] == "borrower_access"
    assert {"iat", "exp", "jti"} <= payload.keys()
    owner_token = create_owner_access_token(uuid4(), settings=SETTINGS)
    with pytest.raises(AccessTokenError):
        decode_borrower_access_token(owner_token.value, settings=SETTINGS)


def test_expired_borrower_access_token_is_rejected() -> None:
    token = create_borrower_access_token(
        uuid4(), uuid4(), settings=SETTINGS, now=datetime.now(UTC) - timedelta(hours=1)
    )
    with pytest.raises(AccessTokenError):
        decode_borrower_access_token(token.value, settings=SETTINGS)
