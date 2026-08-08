"""Outbox dispatcher delivery, retry, dead-letter, and deduplication tests."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.features.notifications.dispatcher import dispatch_pending_notifications
from app.features.notifications.models import Notification, NotificationOutbox
from app.features.notifications.service import enqueue_notification

pytestmark = pytest.mark.integration
FIXED_NOW = datetime(2026, 8, 9, 12, tzinfo=UTC)


class FailingProvider:
    def __init__(self, message: str = "secret-token=must-not-persist") -> None:
        self.calls = 0
        self.message = message

    async def deliver(self, db: AsyncSession, outbox: NotificationOutbox) -> bool:
        self.calls += 1
        raise RuntimeError(self.message)


async def _pending(db: AsyncSession, *, max_attempts: int = 5) -> NotificationOutbox:
    outbox = await enqueue_notification(
        db,
        event_type="payment_received",
        aggregate_type="payment",
        aggregate_id=uuid4(),
        recipient_type="borrower",
        recipient_id=uuid4(),
        template_key="payment_received",
        payload={"amount": "700.00", "payment_date": "2026-08-09"},
        max_attempts=max_attempts,
    )
    await db.execute(
        update(NotificationOutbox)
        .where(NotificationOutbox.id != outbox.id)
        .values(next_attempt_at=datetime(2100, 1, 1, tzinfo=UTC))
    )
    return outbox


async def test_dispatch_success_creates_one_visible_notification(
    db_session: AsyncSession,
) -> None:
    outbox = await _pending(db_session)
    outbox.next_attempt_at = FIXED_NOW

    processed = await dispatch_pending_notifications(db_session, clock=lambda: FIXED_NOW)

    assert processed == 1
    assert outbox.status == "delivered"
    assert outbox.attempt_count == 1
    assert outbox.delivered_at == FIXED_NOW
    notification = (
        await db_session.execute(
            select(Notification).where(Notification.source_outbox_id == outbox.id)
        )
    ).scalar_one()
    assert notification.body == "We recorded your payment of ₱700.00. Thank you!"


async def test_dispatch_failure_is_retryable_and_sanitized(
    db_session: AsyncSession,
) -> None:
    outbox = await _pending(db_session)
    outbox.next_attempt_at = FIXED_NOW
    provider = FailingProvider()

    await dispatch_pending_notifications(db_session, provider=provider, clock=lambda: FIXED_NOW)

    assert provider.calls == 1
    assert outbox.status == "failed"
    assert outbox.attempt_count == 1
    assert outbox.next_attempt_at is not None
    assert outbox.next_attempt_at > FIXED_NOW
    assert outbox.last_error == "Notification provider delivery failed"
    assert "secret" not in outbox.last_error


async def test_dispatch_exhaustion_dead_letters_and_stops_retry(
    db_session: AsyncSession,
) -> None:
    outbox = await _pending(db_session, max_attempts=1)
    outbox.next_attempt_at = FIXED_NOW
    provider = FailingProvider()

    await dispatch_pending_notifications(db_session, provider=provider, clock=lambda: FIXED_NOW)
    second = await dispatch_pending_notifications(
        db_session, provider=provider, clock=lambda: FIXED_NOW
    )

    assert second == 0
    assert provider.calls == 1
    assert outbox.status == "dead_letter"
    assert outbox.next_attempt_at is None


async def test_delivery_retry_cannot_duplicate_visible_notification(
    db_session: AsyncSession,
) -> None:
    outbox = await _pending(db_session)
    outbox.next_attempt_at = FIXED_NOW
    await dispatch_pending_notifications(db_session, clock=lambda: FIXED_NOW)
    outbox.status = "pending"
    outbox.next_attempt_at = FIXED_NOW
    await dispatch_pending_notifications(db_session, clock=lambda: FIXED_NOW)

    count = await db_session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.source_outbox_id == outbox.id)
    )
    assert count == 1


async def test_two_workers_do_not_deliver_same_outbox_attempt(
    integration_engine: AsyncEngine,
) -> None:
    """Committed rows are claimed at most once across real concurrent sessions."""
    factory = async_sessionmaker(integration_engine, expire_on_commit=False)
    aggregate_ids = [uuid4() for _ in range(4)]
    outbox_ids = []
    async with factory() as setup:
        for aggregate_id in aggregate_ids:
            row = await enqueue_notification(
                setup,
                event_type="payment_received",
                aggregate_type="payment",
                aggregate_id=aggregate_id,
                recipient_type="borrower",
                recipient_id=uuid4(),
                template_key="payment_received",
                payload={"amount": "100.00"},
            )
            row.created_at = datetime(2000, 1, 1, tzinfo=UTC)
            outbox_ids.append(row.id)
        await setup.commit()

    async def run_worker() -> int:
        async with factory() as worker:
            processed = await dispatch_pending_notifications(worker, batch_size=4)
            await worker.commit()
            return processed

    try:
        processed = await asyncio.gather(run_worker(), run_worker())
        async with factory() as verification:
            delivered_count = await verification.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.source_outbox_id.in_(outbox_ids))
            )
            attempts = (
                await verification.execute(
                    select(NotificationOutbox.attempt_count).where(
                        NotificationOutbox.id.in_(outbox_ids)
                    )
                )
            ).scalars()
            assert sum(processed) >= 4
            assert delivered_count == 4
            assert list(attempts) == [1, 1, 1, 1]
    finally:
        async with factory() as cleanup:
            await cleanup.execute(
                delete(Notification).where(Notification.source_outbox_id.in_(outbox_ids))
            )
            await cleanup.execute(
                delete(NotificationOutbox).where(NotificationOutbox.id.in_(outbox_ids))
            )
            await cleanup.commit()
