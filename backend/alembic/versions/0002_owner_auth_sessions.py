"""owner auth sessions

Revision ID: 0002_owner_auth_sessions
Revises: 0001_initial_identity_schema
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_owner_auth_sessions"
down_revision: str | None = "0001_initial_identity_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Require Owner credentials and add hashed refresh-session persistence."""

    op.alter_column("owner_users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.create_table(
        "owner_refresh_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_to_token_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["owner_users.id"],
            name=op.f("fk_owner_refresh_tokens_owner_user_id_owner_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rotated_to_token_id"],
            ["owner_refresh_tokens.id"],
            name=op.f("fk_owner_refresh_tokens_rotated_to_token_id_owner_refresh_tokens"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_owner_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_owner_refresh_tokens_token_hash")),
    )
    op.create_index(
        "ix_owner_refresh_tokens_active_owner_expires",
        "owner_refresh_tokens",
        ["owner_user_id", "expires_at"],
        unique=False,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )


def downgrade() -> None:
    """Remove Owner refresh sessions and restore phased nullable credentials."""

    op.drop_index(
        "ix_owner_refresh_tokens_active_owner_expires",
        table_name="owner_refresh_tokens",
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.drop_table("owner_refresh_tokens")
    op.alter_column("owner_users", "password_hash", existing_type=sa.String(255), nullable=True)
