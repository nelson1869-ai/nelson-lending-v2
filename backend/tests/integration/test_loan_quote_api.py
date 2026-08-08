"""Integration tests for Owner Loan Quote API."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.loans.models import Loan
from app.features.owner_identity.service import bootstrap_owner, login_owner
from app.main import app

pytestmark = pytest.mark.integration

QUOTE_URL = "/api/v1/owner/loans/quote"
PASSWORD = "owner quote test pass 123"


@pytest.fixture
async def api_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


async def get_owner_headers(db_session: AsyncSession) -> dict[str, str]:
    await bootstrap_owner(db_session, username="ownerquote", password=PASSWORD)
    pair = await login_owner(db_session, username="ownerquote", password=PASSWORD)
    return {"Authorization": f"Bearer {pair.access_token.value}"}


async def test_quote_api_unauthorized_without_token(api_client: AsyncClient) -> None:
    res = await api_client.post(
        QUOTE_URL,
        json={
            "principal": "2000.00",
            "monthlyRate": "0.10",
            "termMonths": 1,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-09-07",
        },
    )
    assert res.status_code == 401


async def test_quote_api_success(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await get_owner_headers(db_session)
    res = await api_client.post(
        QUOTE_URL,
        headers=headers,
        json={
            "principal": "2000.00",
            "monthlyRate": "0.10",
            "termMonths": 1,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-09-07",
        },
    )
    assert res.status_code == 200
    data = res.json()

    assert data["principal"] == "2000.00"
    assert data["monthlyRate"] == "0.1000000000"
    assert data["termMonths"] == 1
    assert data["paymentFrequency"] == "monthly"
    assert data["numberOfPayments"] == 1
    assert data["scheduledPayment"] == "2200.00"
    assert data["totalScheduledInterest"] == "200.00"
    assert data["totalScheduledRepayment"] == "2200.00"
    assert data["firstDueDate"] == "2026-09-07"
    assert data["finalDueDate"] == "2026-09-07"

    assert len(data["schedule"]) == 1
    item = data["schedule"][0]
    assert item["installmentNumber"] == 1
    assert item["dueDate"] == "2026-09-07"
    assert item["openingPrincipal"] == "2000.00"
    assert item["interestDue"] == "200.00"
    assert item["scheduledPrincipal"] == "2000.00"
    assert item["scheduledPayment"] == "2200.00"
    assert item["closingPrincipal"] == "0.00"


async def test_quote_api_stateless_does_not_insert_loan(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await get_owner_headers(db_session)
    count_before = (await db_session.execute(select(func.count()).select_from(Loan))).scalar()

    res = await api_client.post(
        QUOTE_URL,
        headers=headers,
        json={
            "principal": "5000.00",
            "monthlyRate": "0.05",
            "termMonths": 3,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-09-07",
        },
    )
    assert res.status_code == 200

    count_after = (await db_session.execute(select(func.count()).select_from(Loan))).scalar()
    assert count_before == count_after


async def test_quote_api_invalid_frequency(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await get_owner_headers(db_session)
    res = await api_client.post(
        QUOTE_URL,
        headers=headers,
        json={
            "principal": "2000.00",
            "monthlyRate": "0.10",
            "termMonths": 1,
            "paymentFrequency": "weekly",
            "firstDueDate": "2026-09-07",
        },
    )
    assert res.status_code == 422


async def test_quote_api_invalid_twice_monthly_first_due_date(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await get_owner_headers(db_session)
    res = await api_client.post(
        QUOTE_URL,
        headers=headers,
        json={
            "principal": "2000.00",
            "monthlyRate": "0.10",
            "termMonths": 1,
            "paymentFrequency": "twice_monthly",
            "firstDueDate": "2026-09-07",  # 7th is invalid for twice_monthly
        },
    )
    assert res.status_code == 422


async def test_quote_api_valid_twice_monthly_quote(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await get_owner_headers(db_session)
    res = await api_client.post(
        QUOTE_URL,
        headers=headers,
        json={
            "principal": "3000.00",
            "monthlyRate": "0.06",
            "termMonths": 1,
            "paymentFrequency": "twice_monthly",
            "firstDueDate": "2026-09-15",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["numberOfPayments"] == 2
    assert data["firstDueDate"] == "2026-09-15"
    assert data["finalDueDate"] == "2026-09-30"

