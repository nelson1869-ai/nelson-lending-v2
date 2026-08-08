"""Borrower business records and separate app-account persistence models."""

from datetime import date, datetime
from typing import Final
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

BORROWER_STATUSES: Final = ("active", "inactive", "deleted")
BORROWER_ACCOUNT_STATUSES: Final = (
    "pending",
    "approved",
    "activated",
    "suspended",
    "disabled",
)


class Borrower(TimestampMixin, Base):
    """A business borrower record, distinct from an authentication account."""

    __tablename__ = "borrowers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'deleted')",
            name="borrower_status",
        ),
        Index("ix_borrowers_phone_number_normalized", "phone_number_normalized"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    national_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    # Contact phones may be shared; only the login phone on BorrowerAccount is unique.
    phone_number_normalized: Mapped[str] = mapped_column(String(32), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )

    account: Mapped["BorrowerAccount | None"] = relationship(
        back_populates="borrower",
        uselist=False,
        passive_deletes=True,
    )


class BorrowerAccount(TimestampMixin, Base):
    """Borrower App login account, intentionally separate from the Borrower record."""

    __tablename__ = "borrower_accounts"
    __table_args__ = (
        CheckConstraint(
            "account_status IN ('pending', 'approved', 'activated', 'suspended', 'disabled')",
            name="borrower_account_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    borrower_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("borrowers.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    phone_number_normalized: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    # Nullable until PIN creation and hashing are implemented in M06.
    pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    phone_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    borrower: Mapped[Borrower] = relationship(back_populates="account")
    devices: Mapped[list["BorrowerDevice"]] = relationship(
        back_populates="borrower_account",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    refresh_tokens: Mapped[list["BorrowerRefreshToken"]] = relationship(
        back_populates="borrower_account",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="BorrowerRefreshToken.borrower_account_id",
    )


class BorrowerDevice(TimestampMixin, Base):
    """A hashed Borrower App device registration without delivery logic."""

    __tablename__ = "borrower_devices"
    __table_args__ = (
        UniqueConstraint(
            "borrower_account_id",
            "device_identifier_hash",
            name="uq_borrower_devices_account_device_hash",
        ),
        UniqueConstraint(
            "id",
            "borrower_account_id",
            name="uq_borrower_devices_id_account",
        ),
        Index("ix_borrower_devices_borrower_account_id", "borrower_account_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    borrower_account_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("borrower_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_identifier_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    push_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    is_trusted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    borrower_account: Mapped[BorrowerAccount] = relationship(back_populates="devices")
    refresh_tokens: Mapped[list["BorrowerRefreshToken"]] = relationship(
        back_populates="device",
        primaryjoin="BorrowerDevice.id == BorrowerRefreshToken.device_id",
        viewonly=True,
    )


class BorrowerRefreshToken(Base):
    """Hashed Borrower refresh-token record; issuance and verification start in M06."""

    __tablename__ = "borrower_refresh_tokens"
    __table_args__ = (
        ForeignKeyConstraint(
            ["device_id", "borrower_account_id"],
            ["borrower_devices.id", "borrower_devices.borrower_account_id"],
            ondelete="CASCADE",
            name="fk_borrower_refresh_tokens_device_account",
        ),
        Index("ix_borrower_refresh_tokens_borrower_account_id", "borrower_account_id"),
        Index("ix_borrower_refresh_tokens_device_id", "device_id"),
        Index(
            "ix_borrower_refresh_tokens_active_account_expires",
            "borrower_account_id",
            "expires_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    borrower_account_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("borrower_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_to_token_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("borrower_refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    borrower_account: Mapped[BorrowerAccount] = relationship(
        back_populates="refresh_tokens",
        foreign_keys=[borrower_account_id],
    )
    device: Mapped[BorrowerDevice] = relationship(
        back_populates="refresh_tokens",
        primaryjoin="BorrowerDevice.id == BorrowerRefreshToken.device_id",
        viewonly=True,
    )
    rotated_to_token: Mapped["BorrowerRefreshToken | None"] = relationship(
        remote_side="BorrowerRefreshToken.id",
        foreign_keys=[rotated_to_token_id],
    )
