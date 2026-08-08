"""Persistence model for the one business Owner identity."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, String, false, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class OwnerUser(TimestampMixin, Base):
    """The single business-side identity; authentication behavior starts in M04."""

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
    # Nullable until the deliberate secure bootstrap and hashing workflow is added in M04.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
