"""M12 review fixes: add next_interest_due_date to loans for contractual accrual

Revision ID: 0010_m12_accrual_periods
Revises: 0009_m12_review_fixes
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_m12_accrual_periods"
down_revision: str | None = "0009_m12_review_fixes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add next_interest_due_date to loans table for contractual accrual tracking.
    # Initialized to first_due_date for existing loans.
    op.add_column(
        "loans",
        sa.Column("next_interest_due_date", sa.Date(), nullable=True),
    )
    op.execute(
        "UPDATE loans SET next_interest_due_date = first_due_date "
        "WHERE next_interest_due_date IS NULL"
    )
    op.alter_column("loans", "next_interest_due_date", nullable=False)


def downgrade() -> None:
    op.drop_column("loans", "next_interest_due_date")
