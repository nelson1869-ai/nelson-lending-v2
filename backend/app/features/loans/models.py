"""Loan persistence models and domain status definitions."""

from datetime import date, datetime
from decimal import Decimal
from typing import Final
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import MONEY_SQL_TYPE, RATE_SQL_TYPE

LOAN_STATUSES: Final = ("draft", "approved", "active", "paid", "cancelled", "defaulted")
PAYMENT_FREQUENCIES: Final = ("monthly", "twice_monthly")


class Loan(TimestampMixin, Base):
    """A durable loan contract belonging to a borrower."""

    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint(
            "original_principal > 0",
            name="original_principal_positive",
        ),
        CheckConstraint(
            "outstanding_principal >= 0",
            name="outstanding_principal_non_negative",
        ),
        CheckConstraint(
            "monthly_rate >= 0",
            name="monthly_rate_non_negative",
        ),
        CheckConstraint(
            "term_months > 0",
            name="term_months_positive",
        ),
        CheckConstraint(
            "number_of_payments > 0",
            name="number_of_payments_positive",
        ),
        CheckConstraint(
            "payment_frequency IN ('monthly', 'twice_monthly')",
            name="payment_frequency_valid",
        ),
        CheckConstraint(
            "status IN ('draft', 'approved', 'active', 'paid', 'cancelled', 'defaulted')",
            name="loan_status_valid",
        ),
        CheckConstraint(
            "final_due_date >= first_due_date",
            name="final_due_date_after_first",
        ),
        Index("ix_loans_borrower_id", "borrower_id"),
        Index("ix_loans_status", "status"),
        Index("ix_loans_borrower_id_status", "borrower_id", "status"),
        Index("ix_loans_final_due_date", "final_due_date"),
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
    original_principal: Mapped[Decimal] = mapped_column(
        MONEY_SQL_TYPE,
        nullable=False,
    )
    outstanding_principal: Mapped[Decimal] = mapped_column(
        MONEY_SQL_TYPE,
        nullable=False,
    )
    monthly_rate: Mapped[Decimal] = mapped_column(
        RATE_SQL_TYPE,
        nullable=False,
    )
    term_months: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    payment_frequency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    number_of_payments: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
    )
    first_due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    final_due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    borrower: Mapped["Borrower"] = relationship("Borrower", lazy="raise")
