"""SQLAlchemy ORM models for Notification Outbox and Delivered Notifications."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGBUILD_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NotificationOutbox(Base):
    """Durable notification intent captured inside a business transaction."""

    __tablename__ = "notification_outbox"

    id: Mapped[UUID] = mapped_column(PGBUILD_UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(PGBUILD_UUID(as_uuid=True), nullable=False)
    recipient_type: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_id: Mapped[UUID] = mapped_column(PGBUILD_UUID(as_uuid=True), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="in_app")
    template_key: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    delivered_notification: Mapped["Notification | None"] = relationship(
        "Notification", back_populates="source_outbox", uselist=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'delivered', 'failed', 'dead_letter')",
            name="ck_outbox_status",
        ),
        CheckConstraint(
            "channel IN ('in_app')",
            name="ck_outbox_channel",
        ),
        CheckConstraint(
            "recipient_type IN ('borrower', 'owner')",
            name="ck_outbox_recipient_type",
        ),
        CheckConstraint(
            "attempt_count >= 0 AND max_attempts > 0",
            name="ck_outbox_attempts",
        ),
        Index("ix_notification_outbox_status_next_attempt", "status", "next_attempt_at"),
        Index("ix_notification_outbox_recipient", "recipient_type", "recipient_id"),
    )


class Notification(Base):
    """Delivered in-app notification record visible to recipients."""

    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(PGBUILD_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_outbox_id: Mapped[UUID] = mapped_column(
        PGBUILD_UUID(as_uuid=True),
        ForeignKey("notification_outbox.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    recipient_type: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_id: Mapped[UUID] = mapped_column(PGBUILD_UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    body: Mapped[str] = mapped_column(String(500), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[UUID] = mapped_column(PGBUILD_UUID(as_uuid=True), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    source_outbox: Mapped["NotificationOutbox"] = relationship(
        "NotificationOutbox", back_populates="delivered_notification"
    )

    __table_args__ = (
        CheckConstraint(
            "recipient_type IN ('borrower', 'owner')",
            name="ck_notifications_recipient_type",
        ),
        Index("ix_notifications_recipient_read", "recipient_type", "recipient_id", "read_at"),
    )
