"""Domain service for notification enqueuing, rendering, and database queries."""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.constants import (
    ALL_CHANNELS,
    ALL_RECIPIENT_TYPES,
    ALL_TEMPLATE_KEYS,
    CHANNEL_IN_APP,
    OUTBOX_STATUS_DEAD_LETTER,
    OUTBOX_STATUS_PENDING,
    RECIPIENT_TYPE_BORROWER,
    TEMPLATE_BORROWER_REGISTRATION_APPROVED,
    TEMPLATE_LOAN_DISBURSED,
    TEMPLATE_LOAN_REQUEST_APPROVED,
    TEMPLATE_LOAN_REQUEST_REJECTED,
    TEMPLATE_LOAN_REQUEST_SUBMITTED,
    TEMPLATE_PAYMENT_RECEIVED,
)
from app.features.notifications.models import Notification, NotificationOutbox


class NotificationError(Exception):
    """Base exception for notification domain errors."""


class InvalidNotificationTemplateError(NotificationError):
    """Raised when an unrecognized notification template key is supplied."""


class InvalidNotificationChannelError(NotificationError):
    """Raised when an unsupported notification channel is supplied."""


class InvalidRecipientTypeError(NotificationError):
    """Raised when an invalid recipient type is supplied."""


class NotificationNotFoundError(NotificationError):
    """Raised when a requested notification entity is missing."""


class CannotRetryOutboxError(NotificationError):
    """Raised when attempting to retry an outbox record that is not dead-lettered."""


def render_notification(template_key: str, payload: dict[str, Any]) -> tuple[str, str]:
    """Render plain-text title and body for a notification template."""
    if template_key == TEMPLATE_BORROWER_REGISTRATION_APPROVED:
        return (
            "Registration Approved",
            "Your borrower registration was approved. Activate your account before logging in.",
        )
    if template_key == TEMPLATE_LOAN_REQUEST_SUBMITTED:
        principal = payload.get("requested_principal", "0.00")
        return (
            "Loan Request Submitted",
            f"Your loan request for ₱{principal} has been submitted for review.",
        )
    if template_key == TEMPLATE_LOAN_REQUEST_APPROVED:
        principal = payload.get("requested_principal", "0.00")
        return (
            "Loan Request Approved",
            f"Your loan request for ₱{principal} has been approved.",
        )
    if template_key == TEMPLATE_LOAN_REQUEST_REJECTED:
        principal = payload.get("requested_principal", "0.00")
        reason = payload.get("rejection_reason", "Not specified")
        return (
            "Loan Request Rejected",
            f"Your loan request for ₱{principal} was rejected. Reason: {reason}",
        )
    if template_key == TEMPLATE_LOAN_DISBURSED:
        principal = payload.get("original_principal", "0.00")
        return (
            "Loan Disbursed",
            f"Your loan of ₱{principal} has been disbursed and is now active.",
        )
    if template_key == TEMPLATE_PAYMENT_RECEIVED:
        amount = payload.get("amount", "0.00")
        return (
            "Payment Received",
            f"We recorded your payment of ₱{amount}. Thank you!",
        )
    raise InvalidNotificationTemplateError(f"Unknown template key: '{template_key}'")


async def enqueue_notification(
    db: AsyncSession,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    recipient_type: str,
    recipient_id: UUID,
    template_key: str,
    payload: dict[str, Any],
    channel: str = CHANNEL_IN_APP,
    max_attempts: int = 5,
) -> NotificationOutbox:
    """Enqueue a notification intent durably into notification_outbox within current DB session.

    CRITICAL INVARIANT: Never calls db.commit(). The outer business transaction owns commit.
    """
    if template_key not in ALL_TEMPLATE_KEYS:
        raise InvalidNotificationTemplateError(f"Invalid template key: '{template_key}'")
    if channel not in ALL_CHANNELS:
        raise InvalidNotificationChannelError(f"Invalid channel: '{channel}'")
    if recipient_type not in ALL_RECIPIENT_TYPES:
        raise InvalidRecipientTypeError(f"Invalid recipient type: '{recipient_type}'")

    identity = f"{event_type}:{aggregate_id}:{recipient_id}:{template_key}:{channel}"
    idempotency_key = f"notification:{sha256(identity.encode()).hexdigest()}"

    # Deduplication check: return existing outbox entry if already enqueued
    stmt = select(NotificationOutbox).where(NotificationOutbox.idempotency_key == idempotency_key)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing is not None:
        return existing

    outbox = NotificationOutbox(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        channel=channel,
        template_key=template_key,
        payload=payload,
        status=OUTBOX_STATUS_PENDING,
        attempt_count=0,
        max_attempts=max_attempts,
        next_attempt_at=datetime.now(UTC),
        idempotency_key=idempotency_key,
    )
    db.add(outbox)
    await db.flush()
    return outbox


async def list_borrower_notifications(
    db: AsyncSession,
    borrower_id: UUID,
    limit: int = 50,
) -> list[Notification]:
    """Retrieve delivered notifications for a Borrower, ordered newest first."""
    stmt = (
        select(Notification)
        .where(
            Notification.recipient_type == RECIPIENT_TYPE_BORROWER,
            Notification.recipient_id == borrower_id,
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_borrower_unread_count(db: AsyncSession, borrower_id: UUID) -> int:
    """Return count of unread notifications for a Borrower."""
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.recipient_type == RECIPIENT_TYPE_BORROWER,
            Notification.recipient_id == borrower_id,
            Notification.read_at.is_(None),
        )
    )
    res = await db.execute(stmt)
    return res.scalar_one() or 0


async def mark_notification_read(
    db: AsyncSession,
    notification_id: UUID,
    borrower_id: UUID,
) -> Notification:
    """Mark a delivered notification as read for a Borrower."""
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.recipient_type == RECIPIENT_TYPE_BORROWER,
        Notification.recipient_id == borrower_id,
    )
    res = await db.execute(stmt)
    notification = res.scalar_one_or_none()
    if notification is None:
        raise NotificationNotFoundError(f"Notification '{notification_id}' not found.")

    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        await db.flush()
    return notification


async def list_outbox_items(
    db: AsyncSession,
    status: str | None = None,
    limit: int = 50,
) -> tuple[list[NotificationOutbox], int]:
    """Retrieve operational outbox entries for Owner monitoring."""
    stmt = select(NotificationOutbox)
    if status is not None:
        stmt = stmt.where(NotificationOutbox.status == status)

    count_stmt = select(func.count()).select_from(NotificationOutbox)
    if status is not None:
        count_stmt = count_stmt.where(NotificationOutbox.status == status)

    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar_one() or 0

    stmt = stmt.order_by(NotificationOutbox.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all()), total_count


async def retry_dead_letter_outbox(
    db: AsyncSession,
    outbox_id: UUID,
) -> NotificationOutbox:
    """Reset a dead-letter outbox entry back to pending status for manual retry."""
    stmt = select(NotificationOutbox).where(NotificationOutbox.id == outbox_id)
    res = await db.execute(stmt)
    outbox = res.scalar_one_or_none()
    if outbox is None:
        raise NotificationNotFoundError(f"Outbox entry '{outbox_id}' not found.")

    if outbox.status != OUTBOX_STATUS_DEAD_LETTER:
        raise CannotRetryOutboxError(
            f"Outbox entry '{outbox_id}' has status '{outbox.status}' and cannot be retried."
        )

    outbox.status = OUTBOX_STATUS_PENDING
    outbox.attempt_count = 0
    outbox.next_attempt_at = datetime.now(UTC)
    outbox.last_error = None
    await db.flush()
    return outbox
