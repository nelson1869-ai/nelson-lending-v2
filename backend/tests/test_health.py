"""Unit tests for liveness and mocked database readiness."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import health


async def test_liveness_does_not_require_database(client: AsyncClient) -> None:
    response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_reports_available_database(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def available_probe(session: AsyncSession) -> None:
        del session

    monkeypatch.setattr(health, "probe_database", available_probe)

    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "available"}


async def test_readiness_hides_database_failure(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sensitive_detail = "connection failed for password=do-not-return"

    async def unavailable_probe(session: AsyncSession) -> None:
        del session
        raise RuntimeError(sensitive_detail)

    monkeypatch.setattr(health, "probe_database", unavailable_probe)

    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unready", "database": "unavailable"}
    assert sensitive_detail not in response.text
