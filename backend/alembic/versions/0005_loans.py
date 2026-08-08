"""loans schema

Revision ID: 0005_loans
Revises: 0004_borrower_activation
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_loans"
down_revision: str | None = "0004_borrower_activation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "loans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("borrower_id", sa.UUID(), nullable=False),
        sa.Column("original_principal", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("outstanding_principal", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("monthly_rate", sa.Numeric(precision=12, scale=10), nullable=False),
        sa.Column("term_months", sa.Integer(), nullable=False),
        sa.Column("payment_frequency", sa.String(length=20), nullable=False),
        sa.Column("number_of_payments", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("first_due_date", sa.Date(), nullable=False),
        sa.Column("final_due_date", sa.Date(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
            "original_principal > 0",
            name=op.f("ck_loans_original_principal_positive"),
        ),
        sa.CheckConstraint(
            "outstanding_principal >= 0",
            name=op.f("ck_loans_outstanding_principal_non_negative"),
        ),
        sa.CheckConstraint(
            "monthly_rate >= 0",
            name=op.f("ck_loans_monthly_rate_non_negative"),
        ),
        sa.CheckConstraint(
            "term_months > 0",
            name=op.f("ck_loans_term_months_positive"),
        ),
        sa.CheckConstraint(
            "number_of_payments > 0",
            name=op.f("ck_loans_number_of_payments_positive"),
        ),
        sa.CheckConstraint(
            "payment_frequency IN ('monthly', 'twice_monthly')",
            name=op.f("ck_loans_payment_frequency_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'active', 'paid', 'cancelled', 'defaulted')",
            name=op.f("ck_loans_loan_status_valid"),
        ),
        sa.CheckConstraint(
            "final_due_date >= first_due_date",
            name=op.f("ck_loans_final_due_date_after_first"),
        ),
        sa.ForeignKeyConstraint(
            ["borrower_id"],
            ["borrowers.id"],
            name=op.f("fk_loans_borrower_id_borrowers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_loans")),
    )
    op.create_index(op.f("ix_loans_borrower_id"), "loans", ["borrower_id"], unique=False)
    op.create_index(op.f("ix_loans_status"), "loans", ["status"], unique=False)
    op.create_index(
        op.f("ix_loans_borrower_id_status"),
        "loans",
        ["borrower_id", "status"],
        unique=False,
    )
    op.create_index(op.f("ix_loans_final_due_date"), "loans", ["final_due_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_loans_final_due_date"), table_name="loans")
    op.drop_index(op.f("ix_loans_borrower_id_status"), table_name="loans")
    op.drop_index(op.f("ix_loans_status"), table_name="loans")
    op.drop_index(op.f("ix_loans_borrower_id"), table_name="loans")
    op.drop_table("loans")
