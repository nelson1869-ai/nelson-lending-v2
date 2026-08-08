"""Authenticated notification API privacy and operational-boundary tests."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.borrowers.auth_security import create_borrower_access_token, hash_pin
from app.features.borrowers.models import Borrower, BorrowerAccount
from app.features.notifications.dispatcher import dispatch_pending_notifications
from app.features.notifications.models import Notification
from app.features.notifications.service import enqueue_notification

pytestmark = pytest.mark.integration


async def _borrower_auth(db: AsyncSession) -> tuple[Borrower, dict[str, str]]:
    suffix = uuid4().hex[:8]
    borrower = Borrower(
        first_name="Inbox",
        last_name="Borrower",
        national_id=f"NAT-INBOX-{suffix}",
        address="1 Privacy Street",
        phone_number=f"0918{suffix[:7]}",
        phone_number_normalized=f"+63918{suffix[:7]}",
        date_of_birth=date(1990, 1, 1),
        status="active",
    )
    db.add(borrower)
    await db.flush()
    account = BorrowerAccount(
        borrower_id=borrower.id,
        phone_number=borrower.phone_number,
        phone_number_normalized=borrower.phone_number_normalized,
        account_status="activated",
        pin_hash=hash_pin("123456"),
        phone_verified_at=datetime.now(UTC),
    )
    db.add(account)
    await db.flush()
    token = create_borrower_access_token(account.id, borrower.id)
    return borrower, {"Authorization": f"Bearer {token.value}"}


async def _deliver(db: AsyncSession, borrower: Borrower) -> str:
    outbox = await enqueue_notification(
        db,
        event_type="payment_received",
        aggregate_type="payment",
        aggregate_id=uuid4(),
        recipient_type="borrower",
        recipient_id=borrower.id,
        template_key="payment_received",
        payload={"amount": "700.00"},
    )
    await dispatch_pending_notifications(db)
    notification = await db.scalar(
        select(Notification).where(Notification.source_outbox_id == outbox.id)
    )
    assert notification is not None
    return str(notification.id)


async def test_borrower_lists_only_own_notifications_without_internals(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    borrower, headers = await _borrower_auth(db_session)
    other, _ = await _borrower_auth(db_session)
    own_id = await _deliver(db_session, borrower)
    await _deliver(db_session, other)

    response = await api_client.get("/api/v1/borrower/notifications", headers=headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [own_id]
    forbidden = {"payload", "last_error", "attempt_count", "idempotency_key"}
    assert forbidden.isdisjoint(response.json()[0])


async def test_borrower_cannot_mark_another_borrowers_notification_read(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, headers = await _borrower_auth(db_session)
    other, _ = await _borrower_auth(db_session)
    other_id = await _deliver(db_session, other)

    response = await api_client.post(
        f"/api/v1/borrower/notifications/{other_id}/read", headers=headers
    )

    assert response.status_code == 404


async def test_notification_endpoints_require_correct_identity_domain(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, borrower_headers = await _borrower_auth(db_session)

    owner_response = await api_client.get(
        "/api/v1/owner/notifications/outbox", headers=borrower_headers
    )
    anonymous_response = await api_client.get("/api/v1/borrower/notifications")

    assert owner_response.status_code == 401
    assert anonymous_response.status_code == 401
