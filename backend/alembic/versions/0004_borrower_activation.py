"""borrower activation and refresh rotation

Revision ID: 0004_borrower_activation
Revises: 0003_borrower_registrations
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_borrower_activation"
down_revision: str | None = "0003_borrower_registrations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "borrower_activation_codes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("borrower_account_id", sa.UUID(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "failed_attempts >= 0",
            name=op.f("ck_borrower_activation_codes_activation_failed_nonnegative"),
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name=op.f("ck_borrower_activation_codes_activation_max_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["borrower_account_id"],
            ["borrower_accounts.id"],
            name=op.f("fk_borrower_activation_codes_borrower_account_id_borrower_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_borrower_activation_codes")),
    )
    op.create_index(
        "ix_borrower_activation_codes_active_account_expires",
        "borrower_activation_codes",
        ["borrower_account_id", "expires_at"],
        unique=False,
        postgresql_where=sa.text("used_at IS NULL AND revoked_at IS NULL"),
    )
    op.add_column(
        "borrower_refresh_tokens", sa.Column("rotated_to_token_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_borrower_refresh_tokens_rotated_to_token_id_borrower_refresh_tokens"),
        "borrower_refresh_tokens",
        "borrower_refresh_tokens",
        ["rotated_to_token_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_borrower_refresh_tokens_rotated_to_token_id_borrower_refresh_tokens"),
        "borrower_refresh_tokens",
        type_="foreignkey",
    )
    op.drop_column("borrower_refresh_tokens", "rotated_to_token_id")
    op.drop_index(
        "ix_borrower_activation_codes_active_account_expires",
        table_name="borrower_activation_codes",
        postgresql_where=sa.text("used_at IS NULL AND revoked_at IS NULL"),
    )
    op.drop_table("borrower_activation_codes")
