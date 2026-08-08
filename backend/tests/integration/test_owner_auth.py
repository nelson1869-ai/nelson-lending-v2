"""Owner authentication lifecycle against the dedicated local PostgreSQL database."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_refresh_token
from app.db.session import get_db
from app.features.owner_identity.exceptions import (
    AuthenticationFailed,
    OwnerAlreadyBootstrapped,
)
from app.features.owner_identity.models import OwnerRefreshToken, OwnerUser
from app.features.owner_identity.service import (
    bootstrap_owner,
    login_owner,
    refresh_owner_session,
)
from app.main import app

pytestmark = pytest.mark.integration

PASSWORD = "owner test password 123"
AUTH_PREFIX = "/api/v1/owner/auth"


@pytest.fixture
async def auth_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


async def create_owner(db_session: AsyncSession, username: str = "nelson") -> OwnerUser:
    return await bootstrap_owner(db_session, username=username, password=PASSWORD)


async def api_login(client: AsyncClient, username: str = "nelson", password: str = PASSWORD):
    return await client.post(
        f"{AUTH_PREFIX}/login",
        json={"username": username, "password": password},
    )


async def test_bootstrap_creates_first_owner_with_argon2_hash(db_session: AsyncSession) -> None:
    owner = await create_owner(db_session, "  Nelson  ")

    assert owner.username == "nelson"
    assert owner.is_active
    assert owner.password_hash.startswith("$argon2id$")
    assert PASSWORD not in owner.password_hash


async def test_second_bootstrap_is_rejected(db_session: AsyncSession) -> None:
    await create_owner(db_session)

    with pytest.raises(OwnerAlreadyBootstrapped):
        await bootstrap_owner(db_session, username="another", password=PASSWORD)


async def test_login_succeeds_and_updates_last_login(
    db_session: AsyncSession, auth_client: AsyncClient
) -> None:
    owner = await create_owner(db_session)
    response = await api_login(auth_client, username=" NELSON ")
    await db_session.refresh(owner)

    assert response.status_code == 200
    assert response.json()["tokenType"] == "bearer"
    assert owner.last_login_at is not None


@pytest.mark.parametrize(
    ("username", "password"),
    [("nelson", "wrong password value"), ("unknown", PASSWORD)],
)
async def test_login_failures_are_generic(
    db_session: AsyncSession,
    auth_client: AsyncClient,
    username: str,
    password: str,
) -> None:
    await create_owner(db_session)

    response = await api_login(auth_client, username=username, password=password)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


async def test_inactive_owner_login_is_rejected(
    db_session: AsyncSession, auth_client: AsyncClient
) -> None:
    owner = await create_owner(db_session)
    owner.is_active = False
    await db_session.commit()

    response = await api_login(auth_client)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


async def test_login_stores_only_refresh_token_hash(
    db_session: AsyncSession, auth_client: AsyncClient
) -> None:
    await create_owner(db_session)
    response = await api_login(auth_client)
    raw_token = response.json()["refreshToken"]
    stored = await db_session.scalar(select(OwnerRefreshToken))

    assert stored is not None
    assert stored.token_hash == hash_refresh_token(raw_token)
    assert stored.token_hash != raw_token


async def test_me_returns_safe_owner_profile(
    db_session: AsyncSession, auth_client: AsyncClient
) -> None:
    await create_owner(db_session)
    login = await api_login(auth_client)

    response = await auth_client.get(
        f"{AUTH_PREFIX}/me",
        headers={"Authorization": f"Bearer {login.json()['accessToken']}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "nelson"
    assert "passwordHash" not in response.text
    assert "tokenHash" not in response.text


@pytest.mark.parametrize("token", ["not-a-token", ""])
async def test_me_rejects_malformed_or_missing_token(auth_client: AsyncClient, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = await auth_client.get(f"{AUTH_PREFIX}/me", headers=headers)

    assert response.status_code == 401


async def test_me_rejects_refresh_token(db_session: AsyncSession, auth_client: AsyncClient) -> None:
    await create_owner(db_session)
    login = await api_login(auth_client)

    response = await auth_client.get(
        f"{AUTH_PREFIX}/me",
        headers={"Authorization": f"Bearer {login.json()['refreshToken']}"},
    )

    assert response.status_code == 401


async def test_refresh_rotates_and_links_session(
    db_session: AsyncSession, auth_client: AsyncClient
) -> None:
    await create_owner(db_session)
    login = await api_login(auth_client)
    old_refresh = login.json()["refreshToken"]

    response = await auth_client.post(f"{AUTH_PREFIX}/refresh", json={"refreshToken": old_refresh})
    old_record = await db_session.scalar(
        select(OwnerRefreshToken).where(
            OwnerRefreshToken.token_hash == hash_refresh_token(old_refresh)
        )
    )

    assert response.status_code == 200
    assert response.json()["refreshToken"] != old_refresh
    assert old_record is not None
    assert old_record.revoked_at is not None
    assert old_record.rotated_to_token_id is not None


async def test_old_refresh_token_cannot_be_reused(
    db_session: AsyncSession, auth_client: AsyncClient
) -> None:
    await create_owner(db_session)
    login = await api_login(auth_client)
    old_refresh = login.json()["refreshToken"]
    first = await auth_client.post(f"{AUTH_PREFIX}/refresh", json={"refreshToken": old_refresh})
    second = await auth_client.post(f"{AUTH_PREFIX}/refresh", json={"refreshToken": old_refresh})

    assert first.status_code == 200
    assert second.status_code == 401


async def test_expired_refresh_token_is_rejected(db_session: AsyncSession) -> None:
    owner = await create_owner(db_session)
    pair = await login_owner(db_session, username=owner.username, password=PASSWORD)
    record = await db_session.scalar(
        select(OwnerRefreshToken).where(
            OwnerRefreshToken.token_hash == hash_refresh_token(pair.refresh_token)
        )
    )
    assert record is not None
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()

    with pytest.raises(AuthenticationFailed):
        await refresh_owner_session(db_session, refresh_token=pair.refresh_token)


async def test_logout_revokes_refresh_and_prevents_reuse(
    db_session: AsyncSession, auth_client: AsyncClient
) -> None:
    await create_owner(db_session)
    login = await api_login(auth_client)
    refresh_token = login.json()["refreshToken"]

    logout = await auth_client.post(f"{AUTH_PREFIX}/logout", json={"refreshToken": refresh_token})
    reuse = await auth_client.post(f"{AUTH_PREFIX}/refresh", json={"refreshToken": refresh_token})

    assert logout.status_code == 204
    assert reuse.status_code == 401


async def test_database_remains_single_owner(db_session: AsyncSession) -> None:
    await create_owner(db_session)
    owner_count = await db_session.scalar(select(func.count()).select_from(OwnerUser))

    assert owner_count == 1
