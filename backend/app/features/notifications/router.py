"""FastAPI routers for Borrower notifications and Owner outbox operations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.session import DatabaseSession
from app.features.borrowers.auth_dependencies import CurrentBorrowerAccount
from app.features.borrowers.models import BorrowerAccount
from app.features.notifications.schemas import (
    BorrowerNotificationResponse,
    OutboxItemResponse,
    OutboxListResponse,
    UnreadCountResponse,
)
from app.features.notifications.service import (
    CannotRetryOutboxError,
    NotificationNotFoundError,
    get_borrower_unread_count,
    list_borrower_notifications,
    list_outbox_items,
    mark_notification_read,
    retry_dead_letter_outbox,
)
from app.features.owner_identity.dependencies import get_current_owner
from app.features.owner_identity.models import OwnerUser

borrower_router = APIRouter(prefix="/borrower/notifications", tags=["Borrower Notifications"])
owner_router = APIRouter(prefix="/owner/notifications", tags=["Owner Outbox Operations"])

CurrentBorrower = Annotated[BorrowerAccount, Depends(CurrentBorrowerAccount)]
CurrentOwner = Annotated[OwnerUser, Depends(get_current_owner)]


@borrower_router.get(
    "",
    response_model=list[BorrowerNotificationResponse],
    summary="List Borrower Notifications",
)
async def borrower_list_notifications(
    session: DatabaseSession,
    borrower_acc: CurrentBorrower,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[BorrowerNotificationResponse]:
    """Retrieve delivered in-app notifications for the authenticated Borrower."""
    notifications = await list_borrower_notifications(
        session, borrower_acc.borrower_id, limit=limit
    )
    return [BorrowerNotificationResponse.model_validate(n) for n in notifications]


@borrower_router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get Unread Notification Count",
)
async def borrower_unread_count(
    session: DatabaseSession,
    borrower_acc: CurrentBorrower,
) -> UnreadCountResponse:
    """Get the unread notification count for the authenticated Borrower."""
    count = await get_borrower_unread_count(session, borrower_acc.borrower_id)
    return UnreadCountResponse(unread_count=count)


@borrower_router.post(
    "/{notification_id}/read",
    response_model=BorrowerNotificationResponse,
    summary="Mark Notification as Read",
)
async def borrower_mark_read(
    notification_id: UUID,
    session: DatabaseSession,
    borrower_acc: CurrentBorrower,
) -> BorrowerNotificationResponse:
    """Mark a delivered notification as read for the authenticated Borrower."""
    try:
        notification = await mark_notification_read(
            session, notification_id, borrower_acc.borrower_id
        )
        await session.commit()
        return BorrowerNotificationResponse.model_validate(notification)
    except NotificationNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@owner_router.get(
    "/outbox",
    response_model=OutboxListResponse,
    summary="List Notification Outbox Items",
)
async def owner_list_outbox(
    session: DatabaseSession,
    _: CurrentOwner,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
) -> OutboxListResponse:
    """Retrieve operational outbox entries for Owner monitoring."""
    items, total = await list_outbox_items(session, status=status_filter, limit=limit)
    return OutboxListResponse(
        items=[OutboxItemResponse.model_validate(i) for i in items],
        total_count=total,
    )


@owner_router.post(
    "/outbox/{outbox_id}/retry",
    response_model=OutboxItemResponse,
    summary="Retry Dead-Letter Outbox Entry",
)
async def owner_retry_outbox(
    outbox_id: UUID,
    session: DatabaseSession,
    _: CurrentOwner,
) -> OutboxItemResponse:
    """Manually reset a dead-letter outbox entry back to pending status for retry."""
    try:
        outbox = await retry_dead_letter_outbox(session, outbox_id)
        await session.commit()
        return OutboxItemResponse.model_validate(outbox)
    except NotificationNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except CannotRetryOutboxError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
