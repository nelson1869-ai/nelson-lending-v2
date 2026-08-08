"""Persistence model for borrower loan requests and owner reviews."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Final
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import MONEY_SQL_TYPE, RATE_SQL_TYPE

if TYPE_CHECKING:
    from app.features.borrowers.models import Borrower
    from app.features.loans.models import Loan
    from app.features.owner_identity.models import OwnerUser

LOAN_REQUEST_STATUSES: Final = ("pending", "approved", "rejected", "cancelled")


class LoanRequest(TimestampMixin, Base):
    """Borrower application for a loan prior to owner review."""

    __tablename__ = "loan_requests"
    __table_args__ = (
        CheckConstraint(
            "requested_principal > 0",
            name="requested_principal_positive",
        ),
        CheckConstraint(
            "requested_monthly_rate >= 0",
            name="requested_monthly_rate_non_negative",
        ),
        CheckConstraint(
            "requested_term_months > 0",
            name="requested_term_months_positive",
        ),
        CheckConstraint(
            "requested_payment_frequency IN ('monthly', 'twice_monthly')",
            name="requested_payment_frequency_valid",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
            name="loan_request_status_valid",
        ),
        Index(
            "ix_loan_requests_one_pending_per_borrower",
            "borrower_id",
            unique=True,
            postgresql_where=(mapped_column("status") == "pending"),
        ),
        Index("ix_loan_requests_borrower_id", "borrower_id"),
        Index("ix_loan_requests_status", "status"),
        Index("ix_loan_requests_created_at", "created_at"),
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
    )
    requested_principal: Mapped[Decimal] = mapped_column(
        MONEY_SQL_TYPE,
        nullable=False,
    )
    requested_monthly_rate: Mapped[Decimal] = mapped_column(
        RATE_SQL_TYPE,
        nullable=False,
    )
    requested_term_months: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    requested_payment_frequency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    requested_first_due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reviewed_by_owner_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("owner_users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    owner_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    borrower: Mapped["Borrower"] = relationship("Borrower", lazy="raise")
    reviewed_by_owner: Mapped["OwnerUser | None"] = relationship("OwnerUser", lazy="raise")
    loan: Mapped["Loan | None"] = relationship(
        "Loan", back_populates="loan_request", uselist=False, lazy="raise"
    )
