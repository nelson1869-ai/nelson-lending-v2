"""borrower registrations

Revision ID: 0003_borrower_registrations
Revises: 0002_owner_auth_sessions
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_borrower_registrations"
down_revision: str | None = "0002_owner_auth_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the pending registration and Owner decision record."""

    op.create_table(
        "borrower_registrations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("national_id", sa.String(length=100), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("phone_number_normalized", sa.String(length=32), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_owner_user_id", sa.UUID(), nullable=True),
        sa.Column("borrower_id", sa.UUID(), nullable=True),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
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
        sa.CheckConstraint(
            "btrim(address) <> ''",
            name=op.f("ck_borrower_registrations_borrower_registration_address"),
        ),
        sa.CheckConstraint(
            "btrim(first_name) <> ''",
            name=op.f("ck_borrower_registrations_borrower_registration_first_name"),
        ),
        sa.CheckConstraint(
            "btrim(last_name) <> ''",
            name=op.f("ck_borrower_registrations_borrower_registration_last_name"),
        ),
        sa.CheckConstraint(
            "btrim(national_id) <> ''",
            name=op.f("ck_borrower_registrations_borrower_registration_national_id"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name=op.f("ck_borrower_registrations_borrower_registration_status"),
        ),
        sa.ForeignKeyConstraint(
            ["borrower_id"],
            ["borrowers.id"],
            name=op.f("fk_borrower_registrations_borrower_id_borrowers"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_owner_user_id"],
            ["owner_users.id"],
            name=op.f("fk_borrower_registrations_reviewed_by_owner_user_id_owner_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_borrower_registrations")),
        sa.UniqueConstraint("borrower_id", name=op.f("uq_borrower_registrations_borrower_id")),
    )
    op.create_index(
        "ix_borrower_registrations_status_submitted",
        "borrower_registrations",
        ["status", "submitted_at"],
        unique=False,
    )
    op.create_index(
        "uq_borrower_registrations_pending_national_id",
        "borrower_registrations",
        ["national_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "uq_borrower_registrations_pending_phone",
        "borrower_registrations",
        ["phone_number_normalized"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    """Remove only the M05 registration workflow schema."""

    op.drop_index(
        "uq_borrower_registrations_pending_phone",
        table_name="borrower_registrations",
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_index(
        "uq_borrower_registrations_pending_national_id",
        table_name="borrower_registrations",
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_index("ix_borrower_registrations_status_submitted", table_name="borrower_registrations")
    op.drop_table("borrower_registrations")
