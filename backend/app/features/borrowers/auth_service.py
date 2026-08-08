"""Transactional Borrower activation and authentication services."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import AccessToken, generate_refresh_token, hash_refresh_token
from app.features.borrowers.activation_models import BorrowerActivationCode
from app.features.borrowers.auth_exceptions import (
    ActivationUnavailable,
    BorrowerAuthFailed,
    BorrowerNotFound,
)
from app.features.borrowers.auth_security import (
    create_borrower_access_token,
    generate_activation_code,
    hash_activation_code,
    hash_device_identifier,
    hash_pin,
    verify_activation_code,
    verify_pin,
)
from app.features.borrowers.models import (
    Borrower,
    BorrowerAccount,
    BorrowerDevice,
    BorrowerRefreshToken,
)

_DUMMY_PIN_HASH = hash_pin("000000")
GENERIC_AUTH_MESSAGE = "Invalid credentials"
GENERIC_ACTIVATION_MESSAGE = "Activation could not be completed"


@dataclass(frozen=True)
class ActivationCodeGrant:
    borrower_id: UUID
    code: str
    expires_at: datetime


@dataclass(frozen=True)
class BorrowerTokenPair:
    access_token: AccessToken
    refresh_token: str


@dataclass(frozen=True)
class BorrowerAuthContext:
    account: BorrowerAccount
    borrower: Borrower


def _auth_failed() -> BorrowerAuthFailed:
    return BorrowerAuthFailed(GENERIC_AUTH_MESSAGE)


def _activation_failed() -> BorrowerAuthFailed:
    return BorrowerAuthFailed(GENERIC_ACTIVATION_MESSAGE)


async def issue_activation_code(
    session: AsyncSession,
    *,
    borrower_id: UUID,
    settings: Settings | None = None,
) -> ActivationCodeGrant:
    """Revoke prior usable codes and return one new plaintext code exactly once."""

    config = settings or get_settings()
    now = datetime.now(UTC)
    try:
        account = await session.scalar(
            select(BorrowerAccount)
            .where(BorrowerAccount.borrower_id == borrower_id)
            .with_for_update()
        )
        if account is None:
            borrower = await session.get(Borrower, borrower_id)
            if borrower is None:
                raise BorrowerNotFound("Borrower not found")
            raise ActivationUnavailable("Borrower account is not available for activation")
        if account.account_status != "approved":
            raise ActivationUnavailable("Borrower account is not available for activation")

        existing_codes = await session.scalars(
            select(BorrowerActivationCode)
            .where(
                BorrowerActivationCode.borrower_account_id == account.id,
                BorrowerActivationCode.used_at.is_(None),
                BorrowerActivationCode.revoked_at.is_(None),
            )
            .with_for_update()
        )
        for existing in existing_codes:
            existing.revoked_at = now

        raw_code = generate_activation_code()
        expires_at = now + timedelta(minutes=config.borrower_activation_code_minutes)
        record = BorrowerActivationCode(
            borrower_account_id=account.id,
            code_hash=hash_activation_code(account.id, raw_code, settings=config),
            expires_at=expires_at,
            max_attempts=config.borrower_activation_code_max_attempts,
        )
        session.add(record)
        await session.commit()
        return ActivationCodeGrant(borrower_id=borrower_id, code=raw_code, expires_at=expires_at)
    except Exception:
        await session.rollback()
        raise


async def activate_borrower(
    session: AsyncSession,
    *,
    normalized_phone: str,
    activation_code: str,
    pin: str,
    settings: Settings | None = None,
) -> None:
    """Consume one valid code and set an Argon2id PIN atomically."""

    config = settings or get_settings()
    now = datetime.now(UTC)
    failure: BorrowerAuthFailed | None = None
    try:
        account = await session.scalar(
            select(BorrowerAccount)
            .where(BorrowerAccount.phone_number_normalized == normalized_phone)
            .with_for_update()
        )
        if account is None or account.account_status != "approved":
            raise _activation_failed()

        code = await session.scalar(
            select(BorrowerActivationCode)
            .where(
                BorrowerActivationCode.borrower_account_id == account.id,
                BorrowerActivationCode.used_at.is_(None),
                BorrowerActivationCode.revoked_at.is_(None),
            )
            .order_by(BorrowerActivationCode.created_at.desc())
            .with_for_update()
        )
        if code is None or code.expires_at <= now or code.failed_attempts >= code.max_attempts:
            raise _activation_failed()

        code.last_attempt_at = now
        if not verify_activation_code(account.id, activation_code, code.code_hash, settings=config):
            code.failed_attempts += 1
            if code.failed_attempts >= code.max_attempts:
                code.revoked_at = now
            failure = _activation_failed()
        else:
            account.pin_hash = hash_pin(pin)
            account.account_status = "activated"
            account.phone_verified_at = now
            code.used_at = now
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    if failure is not None:
        raise failure


def _new_refresh_session(
    account_id: UUID,
    device_id: UUID,
    *,
    settings: Settings,
    now: datetime,
) -> tuple[str, BorrowerRefreshToken]:
    raw = generate_refresh_token()
    return raw, BorrowerRefreshToken(
        borrower_account_id=account_id,
        device_id=device_id,
        token_hash=hash_refresh_token(raw),
        expires_at=now + timedelta(days=settings.borrower_refresh_token_days),
    )


async def login_borrower(
    session: AsyncSession,
    *,
    normalized_phone: str,
    pin: str,
    device_identifier: str,
    platform: str,
    settings: Settings | None = None,
) -> BorrowerTokenPair:
    config = settings or get_settings()
    now = datetime.now(UTC)
    try:
        account = await session.scalar(
            select(BorrowerAccount).where(
                BorrowerAccount.phone_number_normalized == normalized_phone
            )
        )
        if account is None:
            verify_pin(pin, _DUMMY_PIN_HASH)
            raise _auth_failed()
        borrower = await session.get(Borrower, account.borrower_id)
        if (
            account.account_status != "activated"
            or account.pin_hash is None
            or borrower is None
            or borrower.status != "active"
            or not verify_pin(pin, account.pin_hash)
        ):
            raise _auth_failed()

        device_hash = hash_device_identifier(device_identifier, settings=config)
        device = await session.scalar(
            select(BorrowerDevice).where(
                BorrowerDevice.borrower_account_id == account.id,
                BorrowerDevice.device_identifier_hash == device_hash,
            )
        )
        if device is None:
            device = BorrowerDevice(
                borrower_account_id=account.id,
                device_identifier_hash=device_hash,
                platform=platform,
                is_active=True,
                is_trusted=False,
                first_seen_at=now,
                last_seen_at=now,
            )
            session.add(device)
            await session.flush()
        else:
            device.platform = platform
            device.last_seen_at = now
            device.is_active = True
            device.revoked_at = None

        raw_refresh, refresh_record = _new_refresh_session(
            account.id, device.id, settings=config, now=now
        )
        session.add(refresh_record)
        access = create_borrower_access_token(account.id, borrower.id, settings=config, now=now)
        await session.commit()
        return BorrowerTokenPair(access_token=access, refresh_token=raw_refresh)
    except Exception:
        await session.rollback()
        raise


async def refresh_borrower_session(
    session: AsyncSession,
    *,
    refresh_token: str,
    device_identifier: str,
    settings: Settings | None = None,
) -> BorrowerTokenPair:
    config = settings or get_settings()
    now = datetime.now(UTC)
    try:
        current = await session.scalar(
            select(BorrowerRefreshToken)
            .where(BorrowerRefreshToken.token_hash == hash_refresh_token(refresh_token))
            .with_for_update()
        )
        if current is None or current.revoked_at is not None or current.expires_at <= now:
            raise _auth_failed()
        account = await session.get(BorrowerAccount, current.borrower_account_id)
        borrower = await session.get(Borrower, account.borrower_id) if account else None
        device = await session.get(BorrowerDevice, current.device_id)
        submitted_hash = hash_device_identifier(device_identifier, settings=config)
        if (
            account is None
            or account.account_status != "activated"
            or borrower is None
            or borrower.status != "active"
            or device is None
            or not device.is_active
            or device.revoked_at is not None
            or not hmac_compare(submitted_hash, device.device_identifier_hash)
        ):
            raise _auth_failed()

        raw_replacement, replacement = _new_refresh_session(
            account.id, device.id, settings=config, now=now
        )
        session.add(replacement)
        await session.flush()
        current.revoked_at = now
        current.rotated_to_token_id = replacement.id
        device.last_seen_at = now
        access = create_borrower_access_token(account.id, borrower.id, settings=config, now=now)
        await session.commit()
        return BorrowerTokenPair(access_token=access, refresh_token=raw_replacement)
    except Exception:
        await session.rollback()
        raise


def hmac_compare(left: str, right: str) -> bool:
    """Keep deterministic identifier comparison explicit and constant-time."""

    import hmac

    return hmac.compare_digest(left, right)


async def logout_borrower(session: AsyncSession, *, refresh_token: str) -> None:
    now = datetime.now(UTC)
    try:
        current = await session.scalar(
            select(BorrowerRefreshToken)
            .where(BorrowerRefreshToken.token_hash == hash_refresh_token(refresh_token))
            .with_for_update()
        )
        if current is None or current.revoked_at is not None or current.expires_at <= now:
            raise _auth_failed()
        current.revoked_at = now
        await session.commit()
    except Exception:
        await session.rollback()
        raise
