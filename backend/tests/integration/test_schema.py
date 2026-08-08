"""Constraint and type behavior against real local PostgreSQL."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.features.borrowers.models import (
    Borrower,
    BorrowerAccount,
    BorrowerDevice,
    BorrowerRefreshToken,
)
from app.features.business_settings.models import BusinessSetting
from app.features.owner_identity.models import OwnerUser

pytestmark = pytest.mark.integration

EXPECTED_TABLES = {
    "alembic_version",
    "borrower_accounts",
    "borrower_activation_codes",
    "borrower_devices",
    "borrower_refresh_tokens",
    "borrower_registrations",
    "borrowers",
    "business_settings",
    "loan_requests",
    "loans",
    "owner_refresh_tokens",
    "owner_users",
    "payments",
}


def borrower(suffix: str, *, status: str = "active") -> Borrower:
    return Borrower(
        first_name="Test",
        last_name=f"Borrower {suffix}",
        national_id=f"NATIONAL-{suffix}",
        address="Local integration test address",
        phone_number=f"0917{suffix:0>7}",
        phone_number_normalized=f"+63917{suffix:0>7}",
        date_of_birth=date(1990, 1, 1),
        status=status,
    )


def account(borrower_id: UUID, suffix: str, *, status: str = "pending") -> BorrowerAccount:
    return BorrowerAccount(
        borrower_id=borrower_id,
        phone_number=f"0920{suffix:0>7}",
        phone_number_normalized=f"+63920{suffix:0>7}",
        account_status=status,
    )


async def flushed_borrower(session: AsyncSession, suffix: str) -> Borrower:
    record = borrower(suffix)
    session.add(record)
    await session.flush()
    return record


async def flushed_account(session: AsyncSession, suffix: str) -> BorrowerAccount:
    borrower_record = await flushed_borrower(session, suffix)
    record = account(borrower_record.id, suffix)
    session.add(record)
    await session.flush()
    return record


async def test_expected_schema_and_migration_exist(integration_engine: AsyncEngine) -> None:
    async with integration_engine.connect() as connection:
        tables = await connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
        )
        revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))

    assert set(tables.scalars()) == EXPECTED_TABLES
    assert revision == "0009_m12_review_fixes"


async def test_single_active_owner_invariant(db_session: AsyncSession) -> None:
    db_session.add(OwnerUser(username="owner-a", password_hash="hash-a", is_active=True))
    await db_session.flush()
    db_session.add(OwnerUser(username="owner-b", password_hash="hash-b", is_active=True))

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_owner_username_is_unique(db_session: AsyncSession) -> None:
    db_session.add_all(
        [
            OwnerUser(username="same-owner", password_hash="hash-a", is_active=False),
            OwnerUser(username="same-owner", password_hash="hash-b", is_active=False),
        ]
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_borrower_national_id_is_unique(db_session: AsyncSession) -> None:
    first = borrower("1000001")
    second = borrower("1000002")
    second.national_id = first.national_id
    db_session.add_all([first, second])

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_borrower_has_only_one_account(db_session: AsyncSession) -> None:
    borrower_record = await flushed_borrower(db_session, "1000003")
    db_session.add_all(
        [account(borrower_record.id, "1000003"), account(borrower_record.id, "1000004")]
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_login_phone_is_unique(db_session: AsyncSession) -> None:
    first_borrower = await flushed_borrower(db_session, "1000005")
    second_borrower = await flushed_borrower(db_session, "1000006")
    first = account(first_borrower.id, "1000005")
    second = account(second_borrower.id, "1000006")
    second.phone_number_normalized = first.phone_number_normalized
    db_session.add_all([first, second])

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_borrower_status_check(db_session: AsyncSession) -> None:
    db_session.add(borrower("1000007", status="unknown"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_borrower_account_status_check(db_session: AsyncSession) -> None:
    borrower_record = await flushed_borrower(db_session, "1000008")
    db_session.add(account(borrower_record.id, "1000008", status="unknown"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_device_hash_is_unique_per_account(db_session: AsyncSession) -> None:
    borrower_account = await flushed_account(db_session, "1000009")
    devices = [
        BorrowerDevice(
            borrower_account_id=borrower_account.id,
            device_identifier_hash="same-device-hash",
            platform="android",
        )
        for _ in range(2)
    ]
    db_session.add_all(devices)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_refresh_token_hash_is_unique(db_session: AsyncSession) -> None:
    borrower_account = await flushed_account(db_session, "1000010")
    device = BorrowerDevice(
        borrower_account_id=borrower_account.id,
        device_identifier_hash="device-hash-10",
        platform="android",
    )
    db_session.add(device)
    await db_session.flush()
    expires_at = datetime.now(UTC) + timedelta(days=30)
    db_session.add_all(
        [
            BorrowerRefreshToken(
                borrower_account_id=borrower_account.id,
                device_id=device.id,
                token_hash="same-token-hash",
                expires_at=expires_at,
            ),
            BorrowerRefreshToken(
                borrower_account_id=borrower_account.id,
                device_id=device.id,
                token_hash="same-token-hash",
                expires_at=expires_at,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_foreign_key_integrity(db_session: AsyncSession) -> None:
    db_session.add(
        BorrowerDevice(
            borrower_account_id=uuid4(),
            device_identifier_hash="orphan-device-hash",
            platform="android",
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_token_device_must_belong_to_account(db_session: AsyncSession) -> None:
    first_account = await flushed_account(db_session, "1000011")
    second_account = await flushed_account(db_session, "1000012")
    device = BorrowerDevice(
        borrower_account_id=first_account.id,
        device_identifier_hash="device-hash-11",
        platform="ios",
    )
    db_session.add(device)
    await db_session.flush()
    db_session.add(
        BorrowerRefreshToken(
            borrower_account_id=second_account.id,
            device_id=device.id,
            token_hash="cross-account-token-hash",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_business_setting_singleton_check(db_session: AsyncSession) -> None:
    db_session.add(BusinessSetting(id="another"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_estimate_rate_must_be_nonnegative(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        await db_session.execute(
            update(BusinessSetting)
            .where(BusinessSetting.id == "default")
            .values(default_monthly_estimate_rate=Decimal("-0.0000000001"))
        )


async def test_rate_decimal_round_trip(db_session: AsyncSession) -> None:
    expected = Decimal("0.1234567890")
    await db_session.execute(
        update(BusinessSetting)
        .where(BusinessSetting.id == "default")
        .values(default_monthly_estimate_rate=expected)
    )
    actual = await db_session.scalar(
        select(BusinessSetting.default_monthly_estimate_rate).where(BusinessSetting.id == "default")
    )

    assert actual == expected
    assert isinstance(actual, Decimal)


async def test_timestamps_are_timezone_aware(db_session: AsyncSession) -> None:
    record = await flushed_borrower(db_session, "1000013")
    await db_session.refresh(record)

    assert record.created_at.tzinfo is not None
    assert record.updated_at.tzinfo is not None
