"""payments schema

Revision ID: 0008_payments
Revises: 0007_loan_lifecycle
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_payments"
down_revision: str | None = "0007_loan_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("loan_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.NUMERIC(precision=18, scale=2), nullable=False),
        sa.Column("interest_paid", sa.NUMERIC(precision=18, scale=2), nullable=False),
        sa.Column("principal_paid", sa.NUMERIC(precision=18, scale=2), nullable=False),
        sa.Column("unapplied_credit", sa.NUMERIC(precision=18, scale=2), nullable=False),
        sa.Column("remaining_interest", sa.NUMERIC(precision=18, scale=2), nullable=False),
        sa.Column("remaining_principal", sa.NUMERIC(precision=18, scale=2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at" if False else "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="payment_amount_positive"),
        sa.CheckConstraint("interest_paid >= 0", name="interest_paid_non_negative"),
        sa.CheckConstraint("principal_paid >= 0", name="principal_paid_non_negative"),
        sa.CheckConstraint("unapplied_credit >= 0", name="unapplied_credit_non_negative"),
        sa.CheckConstraint("remaining_interest >= 0", name="remaining_interest_non_negative"),
        sa.CheckConstraint("remaining_principal >= 0", name="remaining_principal_non_negative"),
        sa.ForeignKeyConstraint(
            ["loan_id"],
            ["loans.id"],
            name="fk_payments_loan_id_loans",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
    )
    op.create_index("ix_payments_loan_id", "payments", ["loan_id"], unique=False)
    op.create_index("ix_payments_posted_at", "payments", ["posted_at"], unique=False)
    op.create_index("ix_payments_payment_date", "payments", ["payment_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payments_payment_date", table_name="payments")
    op.drop_index("ix_payments_posted_at", table_name="payments")
    op.drop_index("ix_payments_loan_id", table_name="payments")
    op.drop_table("payments")
