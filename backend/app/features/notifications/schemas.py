"""Pydantic schemas for Notifications & Outbox APIs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BorrowerNotificationResponse(BaseModel):
    """Borrower-visible notification schema omitting internal infrastructure metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    body: str
    event_type: str
    source_id: UUID
    read_at: datetime | None
    created_at: datetime


class UnreadCountResponse(BaseModel):
    """Schema for Borrower notification unread count."""

    unread_count: int


class OutboxItemResponse(BaseModel):
    """Owner-visible operational outbox item schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    aggregate_type: str
    aggregate_id: UUID
    recipient_type: str
    recipient_id: UUID
    channel: str
    template_key: str
    status: str
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime | None
    last_attempt_at: datetime | None
    delivered_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class OutboxListResponse(BaseModel):
    """Schema for list of outbox items."""

    items: list[OutboxItemResponse]
    total_count: int
