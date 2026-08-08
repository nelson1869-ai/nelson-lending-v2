"""Fail-closed fixtures for the dedicated local PostgreSQL test database."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.db.session import get_db
from app.main import app

EXPECTED_TEST_DATABASE = "lending_nelson_v2_test"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


@pytest.fixture(scope="session")
def safe_test_database_url() -> str:
    """Return only the explicitly configured, exact local test database URL."""

    configured_url = Settings().test_database_url
    if configured_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")

    database_url = str(configured_url)
    parsed_url = make_url(database_url)
    if (
        parsed_url.drivername != "postgresql+asyncpg"
        or parsed_url.host not in LOCAL_HOSTS
        or parsed_url.port != 5432
        or parsed_url.database != EXPECTED_TEST_DATABASE
    ):
        raise RuntimeError(
            "Integration tests require postgresql+asyncpg on loopback port 5432 "
            f"with database {EXPECTED_TEST_DATABASE}"
        )

    return database_url


@pytest_asyncio.fixture(scope="session")
async def integration_engine(safe_test_database_url: str) -> AsyncIterator[AsyncEngine]:
    """Connect to the protected test database without altering its schema."""

    engine = create_async_engine(safe_test_database_url, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(integration_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Isolate each test in a transaction that is always rolled back."""

    async with integration_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            if transaction.is_active:
                await transaction.rollback()


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Provide an AsyncClient wired directly to the test db_session."""

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
