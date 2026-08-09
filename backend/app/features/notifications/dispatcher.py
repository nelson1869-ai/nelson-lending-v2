"""Asynchronous outbox dispatcher executing retry backoff and provider delivery."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.constants import (
    OUTBOX_STATUS_DEAD_LETTER,
    OUTBOX_STATUS_DELIVERED,
    OUTBOX_STATUS_FAILED,
    OUTBOX_STATUS_PENDING,
)
from app.features.notifications.models import NotificationOutbox
from app.features.notifications.providers import InAppNotificationProvider, NotificationProvider

logger = logging.getLogger(__name__)


Clock = Callable[[], datetime]


def calculate_next_attempt(
    attempt_count: int,
    *,
    now: datetime | None = None,
    base_seconds: int = 60,
    max_seconds: int = 3600,
) -> datetime:
    """Calculate exponential backoff next attempt time."""
    delay = min(base_seconds * (2 ** max(0, attempt_count - 1)), max_seconds)
    return (now or datetime.now(UTC)) + timedelta(seconds=delay)


async def dispatch_pending_notifications(
    db: AsyncSession,
    provider: NotificationProvider | None = None,
    batch_size: int = 50,
    clock: Clock = lambda: datetime.now(UTC),
) -> int:
    """Lock and process a bounded batch without involving business requests."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    active_provider = provider or InAppNotificationProvider()
    now = clock()

    stmt = (
        select(NotificationOutbox)
        .where(
            NotificationOutbox.status.in_([OUTBOX_STATUS_PENDING, OUTBOX_STATUS_FAILED]),
            (NotificationOutbox.next_attempt_at.is_(None))
            | (NotificationOutbox.next_attempt_at <= now),
        )
        .order_by(NotificationOutbox.created_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )

    res = await db.execute(stmt)
    pending_records = list(res.scalars().all())

    processed_count = 0
    for outbox in pending_records:
        processed_count += 1
        outbox.attempt_count += 1
        outbox.last_attempt_at = now

        try:
            success = await active_provider.deliver(db, outbox)
            if success:
                outbox.status = OUTBOX_STATUS_DELIVERED
                outbox.delivered_at = now
                outbox.last_error = None
            else:
                _handle_dispatch_failure(outbox, now=now)
        except Exception as err:
            logger.warning(
                "Notification delivery attempt %d failed for outbox %s: %s",
                outbox.attempt_count,
                outbox.id,
                type(err).__name__,
            )
            _handle_dispatch_failure(outbox, now=now)

    if processed_count > 0:
        await db.flush()

    return processed_count


def _handle_dispatch_failure(outbox: NotificationOutbox, *, now: datetime) -> None:
    """Apply failure/retry metadata or dead-letter state to an outbox entry."""
    outbox.last_error = "Notification provider delivery failed"
    if outbox.attempt_count >= outbox.max_attempts:
        outbox.status = OUTBOX_STATUS_DEAD_LETTER
        outbox.next_attempt_at = None
    else:
        outbox.status = OUTBOX_STATUS_FAILED
        outbox.next_attempt_at = calculate_next_attempt(outbox.attempt_count, now=now)
