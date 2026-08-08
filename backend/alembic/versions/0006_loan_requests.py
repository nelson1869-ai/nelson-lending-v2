"""loan_requests schema

Revision ID: 0006_loan_requests
Revises: 0005_loans
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_loan_requests"
down_revision: str | None = "0005_loans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "loan_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("borrower_id", sa.UUID(), nullable=False),
        sa.Column(
            "requested_principal",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
        ),
        sa.Column(
            "requested_monthly_rate",
            sa.Numeric(precision=12, scale=10),
            nullable=False,
        ),
        sa.Column("requested_term_months", sa.Integer(), nullable=False),
        sa.Column(
            "requested_payment_frequency",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column("requested_first_due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_owner_id", sa.UUID(), nullable=True),
        sa.Column("owner_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "requested_principal > 0",
            name=op.f("ck_loan_requests_requested_principal_positive"),
        ),
        sa.CheckConstraint(
            "requested_monthly_rate >= 0",
            name=op.f("ck_loan_requests_requested_monthly_rate_non_negative"),
        ),
        sa.CheckConstraint(
            "requested_term_months > 0",
            name=op.f("ck_loan_requests_requested_term_months_positive"),
        ),
        sa.CheckConstraint(
            "requested_payment_frequency IN ('monthly', 'twice_monthly')",
            name=op.f("ck_loan_requests_requested_payment_frequency_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
            name=op.f("ck_loan_requests_loan_request_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["borrower_id"],
            ["borrowers.id"],
            name=op.f("fk_loan_requests_borrower_id_borrowers"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_owner_id"],
            ["owner_users.id"],
            name=op.f("fk_loan_requests_reviewed_by_owner_id_owner_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_loan_requests")),
    )
    op.create_index(
        op.f("ix_loan_requests_borrower_id"),
        "loan_requests",
        ["borrower_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_loan_requests_created_at"),
        "loan_requests",
        ["created_at"],
        unique=False,
    )

    # Partial unique index enforcing 1 pending request per borrower
    op.create_index(
        "ix_loan_requests_one_pending_per_borrower",
        "loan_requests",
        ["borrower_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        op.f("ix_loan_requests_status"),
        "loan_requests",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_loan_requests_status"),
        table_name="loan_requests",
    )
    op.drop_index(
        "ix_loan_requests_one_pending_per_borrower",
        table_name="loan_requests",
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_index(
        op.f("ix_loan_requests_created_at"),
        table_name="loan_requests",
    )
    op.drop_index(
        op.f("ix_loan_requests_borrower_id"),
        table_name="loan_requests",
    )
    op.drop_table("loan_requests")
