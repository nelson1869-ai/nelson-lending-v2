"""Pending Borrower registration and Owner review persistence."""

from datetime import date, datetime
from typing import Final
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.features.borrowers.models import Borrower
from app.features.owner_identity.models import OwnerUser

REGISTRATION_STATUSES: Final = ("pending", "approved", "rejected")


class BorrowerRegistration(TimestampMixin, Base):
    """Public registration awaiting a single terminal Owner decision."""

    __tablename__ = "borrower_registrations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="borrower_registration_status",
        ),
        CheckConstraint("btrim(first_name) <> ''", name="borrower_registration_first_name"),
        CheckConstraint("btrim(last_name) <> ''", name="borrower_registration_last_name"),
        CheckConstraint("btrim(national_id) <> ''", name="borrower_registration_national_id"),
        CheckConstraint("btrim(address) <> ''", name="borrower_registration_address"),
        Index(
            "uq_borrower_registrations_pending_national_id",
            "national_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "uq_borrower_registrations_pending_phone",
            "phone_number_normalized",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_borrower_registrations_status_submitted", "status", "submitted_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    national_id: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    phone_number_normalized: Mapped[str] = mapped_column(String(32), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_owner_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("owner_users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    borrower_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("borrowers.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    reviewer: Mapped[OwnerUser | None] = relationship()
    borrower: Mapped[Borrower | None] = relationship()
