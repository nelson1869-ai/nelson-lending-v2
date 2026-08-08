"""PostgreSQL integration coverage for transactional notification intent."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models import NotificationOutbox
from app.features.notifications.service import enqueue_notification

pytestmark = pytest.mark.integration


async def test_enqueue_creates_pending_safe_intent(db_session: AsyncSession) -> None:
    aggregate_id = uuid4()
    recipient_id = uuid4()

    outbox = await enqueue_notification(
        db_session,
        event_type="payment_received",
        aggregate_type="payment",
        aggregate_id=aggregate_id,
        recipient_type="borrower",
        recipient_id=recipient_id,
        template_key="payment_received",
        payload={"amount": "700.00", "payment_date": "2026-08-09"},
    )

    assert outbox.status == "pending"
    assert outbox.attempt_count == 0
    assert outbox.payload == {"amount": "700.00", "payment_date": "2026-08-09"}
    assert outbox.delivered_at is None


async def test_enqueue_same_business_event_is_idempotent(db_session: AsyncSession) -> None:
    aggregate_id = uuid4()
    recipient_id = uuid4()
    values = {
        "event_type": "loan_disbursed",
        "aggregate_type": "loan",
        "aggregate_id": aggregate_id,
        "recipient_type": "borrower",
        "recipient_id": recipient_id,
        "template_key": "loan_disbursed",
        "payload": {"original_principal": "10000.00"},
    }

    first = await enqueue_notification(db_session, **values)
    second = await enqueue_notification(db_session, **values)

    assert second.id == first.id
    rows = (
        (
            await db_session.execute(
                select(NotificationOutbox).where(
                    NotificationOutbox.aggregate_id == aggregate_id,
                    NotificationOutbox.recipient_id == recipient_id,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


async def test_database_uniqueness_blocks_duplicate_idempotency_key(
    db_session: AsyncSession,
) -> None:
    common = {
        "event_type": "loan_disbursed",
        "aggregate_type": "loan",
        "recipient_type": "borrower",
        "channel": "in_app",
        "template_key": "loan_disbursed",
        "payload": {},
        "status": "pending",
        "attempt_count": 0,
        "max_attempts": 5,
        "next_attempt_at": datetime.now(UTC),
        "idempotency_key": f"duplicate-{uuid4()}",
    }
    db_session.add_all(
        [
            NotificationOutbox(aggregate_id=uuid4(), recipient_id=uuid4(), **common),
            NotificationOutbox(aggregate_id=uuid4(), recipient_id=uuid4(), **common),
        ]
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_database_rejects_unsupported_channel(db_session: AsyncSession) -> None:
    db_session.add(
        NotificationOutbox(
            event_type="loan_disbursed",
            aggregate_type="loan",
            aggregate_id=uuid4(),
            recipient_type="borrower",
            recipient_id=uuid4(),
            channel="sms",
            template_key="loan_disbursed",
            payload={},
            status="pending",
            attempt_count=0,
            max_attempts=5,
            next_attempt_at=datetime.now(UTC),
            idempotency_key=f"unsupported-{uuid4()}",
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()
