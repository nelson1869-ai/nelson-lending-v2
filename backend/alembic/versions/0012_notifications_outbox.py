"""M14 Transactional Outbox and Notifications schema.

Revision ID: 0012_notifications_outbox
Revises: 0011_accounting
Create Date: 2026-08-09
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0012_notifications_outbox"
down_revision: str | None = "0011_accounting"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Notification Outbox Table
    op.create_table(
        "notification_outbox",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("aggregate_type", sa.String(50), nullable=False),
        sa.Column("aggregate_id", UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_type", sa.String(20), nullable=False),
        sa.Column("recipient_id", UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False, server_default="in_app"),
        sa.Column("template_key", sa.String(50), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_notification_outbox_idempotency_key"),
        sa.CheckConstraint(
            "status IN ('pending', 'delivered', 'failed', 'dead_letter')",
            name="ck_outbox_status",
        ),
        sa.CheckConstraint(
            "channel IN ('in_app')",
            name="ck_outbox_channel",
        ),
        sa.CheckConstraint(
            "recipient_type IN ('borrower', 'owner')",
            name="ck_outbox_recipient_type",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 AND max_attempts BETWEEN 1 AND 20 "
            "AND attempt_count <= max_attempts",
            name="ck_outbox_attempts",
        ),
    )
    op.create_index(
        "ix_notification_outbox_status_next_attempt",
        "notification_outbox",
        ["status", "next_attempt_at"],
    )
    op.create_index(
        "ix_notification_outbox_recipient",
        "notification_outbox",
        ["recipient_type", "recipient_id"],
    )

    # 2. Delivered Notifications Table
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column("source_outbox_id", UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_type", sa.String(20), nullable=False),
        sa.Column("recipient_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("body", sa.String(500), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_outbox_id"],
            ["notification_outbox.id"],
            name="fk_notifications_source_outbox_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("source_outbox_id", name="uq_notifications_source_outbox_id"),
        sa.CheckConstraint(
            "recipient_type IN ('borrower', 'owner')",
            name="ck_notifications_recipient_type",
        ),
    )
    op.create_index(
        "ix_notifications_recipient_read",
        "notifications",
        ["recipient_type", "recipient_id", "read_at"],
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("notification_outbox")
