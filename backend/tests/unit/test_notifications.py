"""Fast tests for notification validation, rendering, retry, and error hygiene."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.notifications.dispatcher import calculate_next_attempt
from app.features.notifications.service import (
    InvalidNotificationChannelError,
    InvalidNotificationTemplateError,
    InvalidRecipientTypeError,
    enqueue_notification,
    render_notification,
)


def test_render_payment_received_uses_event_snapshot() -> None:
    title, body = render_notification("payment_received", {"amount": "700.00"})

    assert title == "Payment Received"
    assert body == "We recorded your payment of ₱700.00. Thank you!"
    assert "journal" not in body.lower()


def test_render_unknown_template_is_rejected() -> None:
    with pytest.raises(InvalidNotificationTemplateError):
        render_notification("user_controlled_template", {})


@pytest.mark.parametrize(
    ("attempt", "seconds"),
    [(1, 60), (2, 120), (3, 240), (7, 3600), (20, 3600)],
)
def test_retry_backoff_is_exponential_and_bounded(attempt: int, seconds: int) -> None:
    now = datetime(2026, 8, 9, 12, tzinfo=UTC)

    assert calculate_next_attempt(attempt, now=now) == now + timedelta(seconds=seconds)


@pytest.mark.asyncio
async def test_enqueue_rejects_unknown_template_before_database_access() -> None:
    db = AsyncMock()

    with pytest.raises(InvalidNotificationTemplateError):
        await enqueue_notification(
            db,
            event_type="event",
            aggregate_type="loan",
            aggregate_id=uuid4(),
            recipient_type="borrower",
            recipient_id=uuid4(),
            template_key="unknown",
            payload={},
        )

    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_enqueue_rejects_unimplemented_channel() -> None:
    db = AsyncMock()

    with pytest.raises(InvalidNotificationChannelError):
        await enqueue_notification(
            db,
            event_type="event",
            aggregate_type="loan",
            aggregate_id=uuid4(),
            recipient_type="borrower",
            recipient_id=uuid4(),
            template_key="loan_disbursed",
            payload={},
            channel="sms",
        )


@pytest.mark.asyncio
async def test_enqueue_rejects_unknown_recipient_domain() -> None:
    db = AsyncMock()

    with pytest.raises(InvalidRecipientTypeError):
        await enqueue_notification(
            db,
            event_type="event",
            aggregate_type="loan",
            aggregate_id=uuid4(),
            recipient_type="staff",
            recipient_id=uuid4(),
            template_key="loan_disbursed",
            payload={},
        )
