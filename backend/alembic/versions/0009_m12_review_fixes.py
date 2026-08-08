"""M12 review fixes: accrued_interest on loans, idempotency_key on payments

Revision ID: 0009_m12_review_fixes
Revises: 0008_payments
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_m12_review_fixes"
down_revision: str | None = "0008_payments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add accrued_interest to loans so unpaid interest carries forward correctly.
    # Default 0 means existing active loans start with zero accrued interest, which is
    # correct — the first post-migration payment will compute and add new-period interest.
    op.add_column(
        "loans",
        sa.Column(
            "accrued_interest",
            sa.NUMERIC(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # Add idempotency_key to payments for safe client retries.
    op.add_column(
        "payments",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )

    # Unique index per loan so different loans may reuse the same client-generated key
    # without collision.  Partial (WHERE idempotency_key IS NOT NULL) so NULL rows are
    # freely allowed without conflicting.
    op.create_index(
        "uq_payments_loan_idempotency_key",
        "payments",
        ["loan_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_payments_loan_idempotency_key", table_name="payments")
    op.drop_column("payments", "idempotency_key")
    op.drop_column("loans", "accrued_interest")
