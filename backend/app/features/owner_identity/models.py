"""Persistence model for the one business Owner identity."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, false, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin


class OwnerUser(TimestampMixin, Base):
    """The single business-side identity."""

    __tablename__ = "owner_users"
    __table_args__ = (
        Index(
            "uq_owner_users_single_active",
            text("(true)"),
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    refresh_tokens: Mapped[list["OwnerRefreshToken"]] = relationship(
        back_populates="owner_user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="OwnerRefreshToken.owner_user_id",
    )


class OwnerRefreshToken(Base):
    """Hashed, revocable, single-use refresh session for the Owner."""

    __tablename__ = "owner_refresh_tokens"
    __table_args__ = (
        Index(
            "ix_owner_refresh_tokens_active_owner_expires",
            "owner_user_id",
            "expires_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("owner_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_to_token_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("owner_refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    owner_user: Mapped[OwnerUser] = relationship(
        back_populates="refresh_tokens",
        foreign_keys=[owner_user_id],
    )
    rotated_to_token: Mapped["OwnerRefreshToken | None"] = relationship(
        remote_side="OwnerRefreshToken.id",
        foreign_keys=[rotated_to_token_id],
    )
