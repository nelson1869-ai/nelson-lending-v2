"""Notification delivery provider interfaces and implementations."""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.constants import CHANNEL_IN_APP
from app.features.notifications.models import Notification, NotificationOutbox
from app.features.notifications.service import render_notification


class NotificationProvider(Protocol):
    """Protocol defining external or internal notification delivery channels."""

    async def deliver(self, db: AsyncSession, outbox: NotificationOutbox) -> bool:
        """Deliver a notification outbox record. Returns True on success, raises or returns False on failure."""
        ...


class InAppNotificationProvider:
    """Delivers outbox notification intents into user-visible in-app Notification records."""

    async def deliver(self, db: AsyncSession, outbox: NotificationOutbox) -> bool:
        """Deliver an outbox entry to the notifications table with source_outbox_id uniqueness."""
        if outbox.channel != CHANNEL_IN_APP:
            return False

        # Deduplication check: if notification for this outbox entry already exists, consider delivered
        stmt = select(Notification).where(Notification.source_outbox_id == outbox.id)
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing is not None:
            return True

        title, body = render_notification(outbox.template_key, outbox.payload)
        notification = Notification(
            source_outbox_id=outbox.id,
            recipient_type=outbox.recipient_type,
            recipient_id=outbox.recipient_id,
            title=title,
            body=body,
            event_type=outbox.event_type,
            source_id=outbox.aggregate_id,
        )
        db.add(notification)
        await db.flush()
        return True
