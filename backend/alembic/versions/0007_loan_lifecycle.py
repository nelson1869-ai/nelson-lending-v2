"""loan_lifecycle schema

Revision ID: 0007_loan_lifecycle
Revises: 0006_loan_requests
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_loan_lifecycle"
down_revision: str | None = "0006_loan_requests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "loans",
        sa.Column("loan_request_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "loans",
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="pending_disbursement",
        ),
    )
    op.add_column(
        "loans",
        sa.Column("disbursed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "loans",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "loans",
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "loans",
        sa.Column("defaulted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_loans_loan_request_id_loan_requests",
        "loans",
        "loan_requests",
        ["loan_request_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_loans_loan_request_id",
        "loans",
        ["loan_request_id"],
        unique=True,
    )
    op.create_index(
        "ix_loans_status",
        "loans",
        ["status"],
    )
    op.create_check_constraint(
        "loan_status_valid",
        "loans",
        "status IN ('pending_disbursement', 'active', 'paid', 'cancelled', 'defaulted')",
    )


def downgrade() -> None:
    op.drop_constraint("loan_status_valid", "loans", type_="check", if_exists=True)
    op.drop_index("ix_loans_status", table_name="loans", if_exists=True)
    op.drop_index("ix_loans_loan_request_id", table_name="loans", if_exists=True)
    op.drop_constraint(
        "uq_loans_loan_request_id",
        "loans",
        type_="unique",
        if_exists=True,
    )
    op.drop_constraint(
        "fk_loans_loan_request_id_loan_requests",
        "loans",
        type_="foreignkey",
        if_exists=True,
    )
    op.drop_column("loans", "defaulted_at")
    op.drop_column("loans", "paid_at")
    op.drop_column("loans", "cancelled_at")
    op.drop_column("loans", "disbursed_at")
    op.drop_column("loans", "status")
    op.drop_column("loans", "loan_request_id")
