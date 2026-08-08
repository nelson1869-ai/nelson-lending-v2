"""Borrower activation and device-bound session lifecycle on real PostgreSQL."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.security import hash_refresh_token
from app.db.session import get_db
from app.features.borrowers.activation_models import BorrowerActivationCode
from app.features.borrowers.auth_exceptions import BorrowerAuthFailed
from app.features.borrowers.auth_security import (
    hash_activation_code,
    hash_device_identifier,
    verify_pin,
)
from app.features.borrowers.auth_service import (
    activate_borrower,
    issue_activation_code,
    login_borrower,
    refresh_borrower_session,
)
from app.features.borrowers.models import (
    Borrower,
    BorrowerAccount,
    BorrowerDevice,
    BorrowerRefreshToken,
)
from app.features.owner_identity.service import bootstrap_owner, login_owner
from app.main import app

pytestmark = pytest.mark.integration

PIN = "482915"
DEVICE = "synthetic-device-identifier-00000001"
PHONE = "+639171234567"
AUTH = "/api/v1/borrower/auth"


@pytest.fixture
async def borrower_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


async def seed_account(
    session: AsyncSession, *, account_status: str = "approved", borrower_status: str = "active"
) -> tuple[Borrower, BorrowerAccount]:
    borrower = Borrower(
        first_name="Synthetic",
        last_name="Borrower",
        national_id="SYNTH-M06-ID",
        address="Synthetic test address",
        phone_number="09171234567",
        phone_number_normalized=PHONE,
        date_of_birth=date(1995, 5, 10),
        status=borrower_status,
    )
    session.add(borrower)
    await session.flush()
    account = BorrowerAccount(
        borrower_id=borrower.id,
        phone_number="09171234567",
        phone_number_normalized=PHONE,
        account_status=account_status,
    )
    session.add(account)
    await session.commit()
    return borrower, account


async def owner_headers(session: AsyncSession) -> dict[str, str]:
    owner = await bootstrap_owner(session, username="m06-owner", password="m06 owner password")
    pair = await login_owner(session, username=owner.username, password="m06 owner password")
    return {"Authorization": f"Bearer {pair.access_token.value}"}


async def activate_account(session: AsyncSession) -> tuple[Borrower, BorrowerAccount]:
    borrower, account = await seed_account(session)
    grant = await issue_activation_code(session, borrower_id=borrower.id)
    await activate_borrower(session, normalized_phone=PHONE, activation_code=grant.code, pin=PIN)
    await session.refresh(account)
    return borrower, account


async def api_login(client: AsyncClient, **overrides: str):
    body = {
        "phoneNumber": "09171234567",
        "pin": PIN,
        "deviceIdentifier": DEVICE,
        "platform": "android",
    }
    body.update(overrides)
    return await client.post(f"{AUTH}/login", json=body)


async def test_owner_issues_hashed_code_and_reissue_revokes_previous(
    db_session: AsyncSession, borrower_client: AsyncClient
) -> None:
    borrower, account = await seed_account(db_session)
    headers = await owner_headers(db_session)
    first = await borrower_client.post(
        f"/api/v1/owner/borrowers/{borrower.id}/activation-code", headers=headers
    )
    first_record = await db_session.scalar(select(BorrowerActivationCode))
    second = await borrower_client.post(
        f"/api/v1/owner/borrowers/{borrower.id}/activation-code", headers=headers
    )
    await db_session.refresh(first_record)
    records = list(await db_session.scalars(select(BorrowerActivationCode)))

    assert first.status_code == second.status_code == 200
    assert first.json()["activationCode"] != second.json()["activationCode"]
    assert first_record.code_hash == hash_activation_code(
        account.id, first.json()["activationCode"]
    )
    assert first.json()["activationCode"] not in first_record.code_hash
    assert first_record.revoked_at is not None
    assert len(records) == 2


@pytest.mark.parametrize("authorization", [None, "Bearer malformed-token"])
async def test_activation_code_issue_requires_owner_access(
    db_session: AsyncSession, borrower_client: AsyncClient, authorization: str | None
) -> None:
    borrower, _ = await seed_account(db_session)
    headers = {"Authorization": authorization} if authorization else {}
    response = await borrower_client.post(
        f"/api/v1/owner/borrowers/{borrower.id}/activation-code", headers=headers
    )
    assert response.status_code == 401


async def test_wrong_code_increments_and_exhausts_attempts(db_session: AsyncSession) -> None:
    borrower, account = await seed_account(db_session)
    grant = await issue_activation_code(db_session, borrower_id=borrower.id)
    record = await db_session.scalar(select(BorrowerActivationCode))
    wrong = "000000" if grant.code != "000000" else "000001"
    for _ in range(5):
        with pytest.raises(Exception, match="Activation could not"):
            await activate_borrower(
                db_session, normalized_phone=PHONE, activation_code=wrong, pin=PIN
            )
    await db_session.refresh(record)
    await db_session.refresh(account)
    assert record.failed_attempts == 5
    assert record.revoked_at is not None
    assert account.account_status == "approved"
    assert account.pin_hash is None


async def test_expired_code_is_rejected(db_session: AsyncSession) -> None:
    borrower, account = await seed_account(db_session)
    grant = await issue_activation_code(db_session, borrower_id=borrower.id)
    record = await db_session.scalar(select(BorrowerActivationCode))
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()
    with pytest.raises(Exception, match="Activation could not"):
        await activate_borrower(
            db_session, normalized_phone=PHONE, activation_code=grant.code, pin=PIN
        )


async def test_activation_sets_argon2_pin_verified_time_and_single_use(
    db_session: AsyncSession,
) -> None:
    borrower, account = await seed_account(db_session)
    grant = await issue_activation_code(db_session, borrower_id=borrower.id)
    await activate_borrower(db_session, normalized_phone=PHONE, activation_code=grant.code, pin=PIN)
    code = await db_session.scalar(select(BorrowerActivationCode))
    await db_session.refresh(account)
    assert account.account_status == "activated"
    assert account.pin_hash.startswith("$argon2id$") and verify_pin(PIN, account.pin_hash)
    assert PIN not in account.pin_hash
    assert account.phone_verified_at is not None
    assert code.used_at is not None
    with pytest.raises(Exception, match="Activation could not"):
        await activate_borrower(
            db_session, normalized_phone=PHONE, activation_code=grant.code, pin=PIN
        )


async def test_pending_account_cannot_activate(db_session: AsyncSession) -> None:
    _, account = await seed_account(db_session, account_status="pending")
    code = BorrowerActivationCode(
        borrower_account_id=account.id,
        code_hash=hash_activation_code(account.id, "123456"),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
        max_attempts=5,
    )
    db_session.add(code)
    await db_session.commit()
    with pytest.raises(Exception, match="Activation could not"):
        await activate_borrower(
            db_session, normalized_phone=PHONE, activation_code="123456", pin=PIN
        )


async def test_login_persists_only_hashed_device_and_refresh(
    db_session: AsyncSession, borrower_client: AsyncClient
) -> None:
    borrower, account = await activate_account(db_session)
    response = await api_login(borrower_client)
    device = await db_session.scalar(select(BorrowerDevice))
    refresh = await db_session.scalar(select(BorrowerRefreshToken))
    assert response.status_code == 200
    assert device.device_identifier_hash == hash_device_identifier(DEVICE)
    assert DEVICE not in device.device_identifier_hash
    assert not device.is_trusted and device.is_active
    assert refresh.token_hash == hash_refresh_token(response.json()["refreshToken"])
    assert response.json()["refreshToken"] not in refresh.token_hash
    assert refresh.borrower_account_id == account.id and refresh.device_id == device.id
    assert borrower.id == account.borrower_id


@pytest.mark.parametrize(
    "kind", ["wrong-pin", "unknown-phone", "approved", "suspended", "disabled", "inactive"]
)
async def test_login_failures_are_generic(
    db_session: AsyncSession, borrower_client: AsyncClient, kind: str
) -> None:
    borrower, account = await activate_account(db_session)
    body: dict[str, str] = {}
    if kind == "wrong-pin":
        body["pin"] = "111111"
    elif kind == "unknown-phone":
        body["phoneNumber"] = "09179999999"
    elif kind == "approved":
        account.account_status = "approved"
    elif kind in {"suspended", "disabled"}:
        account.account_status = kind
    elif kind == "inactive":
        borrower.status = "inactive"
    await db_session.commit()
    response = await api_login(borrower_client, **body)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


async def test_me_enforces_owner_borrower_token_domain_isolation(
    db_session: AsyncSession, borrower_client: AsyncClient
) -> None:
    await activate_account(db_session)
    login = await api_login(borrower_client)
    borrower_access = login.json()["accessToken"]
    borrower_refresh = login.json()["refreshToken"]
    owner = await bootstrap_owner(
        db_session, username="domain-owner", password="domain owner password"
    )
    owner_pair = await login_owner(
        db_session, username=owner.username, password="domain owner password"
    )
    good = await borrower_client.get(
        f"{AUTH}/me", headers={"Authorization": f"Bearer {borrower_access}"}
    )
    owner_to_borrower = await borrower_client.get(
        f"{AUTH}/me", headers={"Authorization": f"Bearer {owner_pair.access_token.value}"}
    )
    owner_refresh_to_borrower = await borrower_client.get(
        f"{AUTH}/me", headers={"Authorization": f"Bearer {owner_pair.refresh_token}"}
    )
    refresh_to_me = await borrower_client.get(
        f"{AUTH}/me", headers={"Authorization": f"Bearer {borrower_refresh}"}
    )
    borrower_to_owner = await borrower_client.get(
        "/api/v1/owner/auth/me", headers={"Authorization": f"Bearer {borrower_access}"}
    )
    borrower_to_owner_issue = await borrower_client.post(
        f"/api/v1/owner/borrowers/{good.json()['borrowerId']}/activation-code",
        headers={"Authorization": f"Bearer {borrower_access}"},
    )
    assert good.status_code == 200
    assert set(good.json()) == {
        "borrowerId",
        "accountId",
        "firstName",
        "lastName",
        "phoneNumber",
        "accountStatus",
    }
    assert owner_to_borrower.status_code == owner_refresh_to_borrower.status_code == 401
    assert refresh_to_me.status_code == borrower_to_owner.status_code == 401
    assert borrower_to_owner_issue.status_code == 401


async def test_refresh_rotation_links_replacement(
    db_session: AsyncSession, borrower_client: AsyncClient
) -> None:
    await activate_account(db_session)
    login = await api_login(borrower_client)
    old = login.json()["refreshToken"]
    rotated = await borrower_client.post(
        f"{AUTH}/refresh", json={"refreshToken": old, "deviceIdentifier": DEVICE}
    )
    new = rotated.json()["refreshToken"]
    old_record = await db_session.scalar(
        select(BorrowerRefreshToken).where(
            BorrowerRefreshToken.token_hash == hash_refresh_token(old)
        )
    )
    assert rotated.status_code == 200 and new != old
    assert old_record.revoked_at is not None and old_record.rotated_to_token_id is not None


@pytest.mark.parametrize("failure", ["wrong-device", "old-reuse"])
async def test_refresh_rejects_wrong_device_or_old_reuse(
    db_session: AsyncSession, borrower_client: AsyncClient, failure: str
) -> None:
    await activate_account(db_session)
    login = await api_login(borrower_client)
    old = login.json()["refreshToken"]
    if failure == "old-reuse":
        assert (
            await borrower_client.post(
                f"{AUTH}/refresh", json={"refreshToken": old, "deviceIdentifier": DEVICE}
            )
        ).status_code == 200
        device_identifier = DEVICE
    else:
        device_identifier = "different-device-identifier-00002"
    response = await borrower_client.post(
        f"{AUTH}/refresh", json={"refreshToken": old, "deviceIdentifier": device_identifier}
    )
    assert response.status_code == 401


async def test_logout_revokes_refresh(
    db_session: AsyncSession, borrower_client: AsyncClient
) -> None:
    await activate_account(db_session)
    login = await api_login(borrower_client)
    raw = login.json()["refreshToken"]
    response = await borrower_client.post(f"{AUTH}/logout", json={"refreshToken": raw})
    record = await db_session.scalar(
        select(BorrowerRefreshToken).where(
            BorrowerRefreshToken.token_hash == hash_refresh_token(raw)
        )
    )
    assert response.status_code == 204
    assert record.revoked_at is not None


@pytest.mark.parametrize("failure", ["inactive-device", "expired-token"])
async def test_inactive_device_or_expired_refresh_is_rejected(
    db_session: AsyncSession, borrower_client: AsyncClient, failure: str
) -> None:
    await activate_account(db_session)
    first = await api_login(borrower_client)
    if failure == "inactive-device":
        device = await db_session.scalar(select(BorrowerDevice))
        device.is_active = False
    else:
        token = await db_session.scalar(
            select(BorrowerRefreshToken).where(
                BorrowerRefreshToken.token_hash == hash_refresh_token(first.json()["refreshToken"])
            )
        )
        token.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()
    response = await borrower_client.post(
        f"{AUTH}/refresh",
        json={"refreshToken": first.json()["refreshToken"], "deviceIdentifier": DEVICE},
    )
    assert response.status_code == 401


async def test_one_account_and_one_identity_remain_authoritative(db_session: AsyncSession) -> None:
    borrower, account = await activate_account(db_session)
    assert await db_session.scalar(select(func.count()).select_from(Borrower)) == 1
    assert await db_session.scalar(select(func.count()).select_from(BorrowerAccount)) == 1
    assert account.borrower_id == borrower.id


async def _committed_account(engine: AsyncEngine, suffix: str) -> tuple[Borrower, BorrowerAccount]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        borrower = Borrower(
            first_name="Concurrent",
            last_name="Borrower",
            national_id=f"SYNTH-M06-{suffix}",
            address="Synthetic concurrency address",
            phone_number=f"0918{suffix:0>7}",
            phone_number_normalized=f"+63918{suffix:0>7}",
            date_of_birth=date(1990, 1, 1),
            status="active",
        )
        session.add(borrower)
        await session.flush()
        account = BorrowerAccount(
            borrower_id=borrower.id,
            phone_number=borrower.phone_number,
            phone_number_normalized=borrower.phone_number_normalized,
            account_status="approved",
        )
        session.add(account)
        await session.commit()
        return borrower, account


async def _cleanup_committed_account(engine: AsyncEngine, borrower_id, account_id) -> None:
    async with AsyncSession(engine) as session, session.begin():
        await session.execute(
            delete(BorrowerActivationCode).where(
                BorrowerActivationCode.borrower_account_id == account_id
            )
        )
        await session.execute(
            delete(BorrowerRefreshToken).where(
                BorrowerRefreshToken.borrower_account_id == account_id
            )
        )
        await session.execute(
            delete(BorrowerDevice).where(BorrowerDevice.borrower_account_id == account_id)
        )
        await session.execute(delete(BorrowerAccount).where(BorrowerAccount.id == account_id))
        await session.execute(delete(Borrower).where(Borrower.id == borrower_id))


async def test_concurrent_activation_allows_one_success(integration_engine: AsyncEngine) -> None:
    borrower, account = await _committed_account(integration_engine, "601")
    async with AsyncSession(integration_engine) as session:
        grant = await issue_activation_code(session, borrower_id=borrower.id)

    async def attempt() -> str:
        async with AsyncSession(integration_engine) as session:
            try:
                await activate_borrower(
                    session,
                    normalized_phone=account.phone_number_normalized,
                    activation_code=grant.code,
                    pin=PIN,
                )
                return "activated"
            except BorrowerAuthFailed:
                return "rejected"

    try:
        assert sorted(await asyncio.gather(attempt(), attempt())) == ["activated", "rejected"]
        async with AsyncSession(integration_engine) as verify:
            persisted = await verify.get(BorrowerAccount, account.id)
            assert persisted.account_status == "activated"
            assert (
                await verify.scalar(
                    select(func.count())
                    .select_from(BorrowerActivationCode)
                    .where(
                        BorrowerActivationCode.borrower_account_id == account.id,
                        BorrowerActivationCode.used_at.is_not(None),
                    )
                )
                == 1
            )
    finally:
        await _cleanup_committed_account(integration_engine, borrower.id, account.id)


async def test_concurrent_refresh_allows_one_rotation(integration_engine: AsyncEngine) -> None:
    borrower, account = await _committed_account(integration_engine, "602")
    async with AsyncSession(integration_engine) as session:
        grant = await issue_activation_code(session, borrower_id=borrower.id)
        await activate_borrower(
            session,
            normalized_phone=account.phone_number_normalized,
            activation_code=grant.code,
            pin=PIN,
        )
        pair = await login_borrower(
            session,
            normalized_phone=account.phone_number_normalized,
            pin=PIN,
            device_identifier=DEVICE,
            platform="android",
        )

    async def attempt() -> str:
        async with AsyncSession(integration_engine) as session:
            try:
                await refresh_borrower_session(
                    session, refresh_token=pair.refresh_token, device_identifier=DEVICE
                )
                return "refreshed"
            except BorrowerAuthFailed:
                return "rejected"

    try:
        assert sorted(await asyncio.gather(attempt(), attempt())) == ["refreshed", "rejected"]
        async with AsyncSession(integration_engine) as verify:
            old = await verify.scalar(
                select(BorrowerRefreshToken).where(
                    BorrowerRefreshToken.token_hash == hash_refresh_token(pair.refresh_token)
                )
            )
            assert old.revoked_at is not None and old.rotated_to_token_id is not None
    finally:
        await _cleanup_committed_account(integration_engine, borrower.id, account.id)
