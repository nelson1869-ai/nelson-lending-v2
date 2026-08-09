"""Authenticated Owner reporting API."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.owner_identity.dependencies import get_current_owner
from app.features.owner_identity.models import OwnerUser
from app.features.reports.schemas import OwnerDashboardResponse
from app.features.reports.service import InvalidCollectionDateRangeError, get_owner_dashboard

CurrentOwner = Annotated[OwnerUser, Depends(get_current_owner)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]

owner_router = APIRouter(prefix="/owner/reports", tags=["Owner Reports"])


@owner_router.get(
    "/dashboard",
    response_model=OwnerDashboardResponse,
    summary="Get Owner Dashboard Metrics",
)
async def owner_dashboard(
    session: DatabaseSession,
    _: CurrentOwner,
    from_date: Annotated[date, Query(description="Inclusive Philippine collection date")],
    to_date: Annotated[date, Query(description="Inclusive Philippine collection date")],
) -> OwnerDashboardResponse:
    """Return portfolio, collections, accounting, and request summaries."""
    try:
        return await get_owner_dashboard(session, from_date=from_date, to_date=to_date)
    except InvalidCollectionDateRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
