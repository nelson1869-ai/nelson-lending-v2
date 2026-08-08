"""Process liveness and database readiness endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


async def probe_database(session: AsyncSession) -> None:
    """Run the smallest useful database availability query."""

    await session.execute(text("SELECT 1"))


@router.get("/live")
async def liveness() -> dict[str, str]:
    """Report process availability without depending on external services."""

    return {"status": "ok"}


@router.get("/ready")
async def readiness(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """Report whether PostgreSQL can accept a minimal query."""

    try:
        await probe_database(session)
    except Exception:
        logger.warning("Database readiness probe failed")
        return JSONResponse(
            status_code=503,
            content={"status": "unready", "database": "unavailable"},
        )

    return JSONResponse(content={"status": "ready", "database": "available"})
