"""Loan persistence models for core financial contract terms."""

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
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import MONEY_SQL_TYPE, RATE_SQL_TYPE

if TYPE_CHECKING:
    from app.features.borrowers.models import Borrower
    from app.features.loan_requests.models import LoanRequest

PAYMENT_FREQUENCIES: Final = ("monthly", "twice_monthly")
LOAN_STATUSES: Final = (
    "pending_disbursement",
    "active",
    "paid",
    "cancelled",
    "defaulted",
)


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
            "final_due_date >= first_due_date",
            name="final_due_date_after_first",
        ),
        CheckConstraint(
            "status IN ('pending_disbursement', 'active', 'paid', 'cancelled', 'defaulted')",
            name="loan_status_valid",
        ),
        Index("ix_loans_borrower_id", "borrower_id"),
        Index("ix_loans_status", "status"),
        Index("ix_loans_final_due_date", "final_due_date"),
        Index("ix_loans_loan_request_id", "loan_request_id", unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    loan_request_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("loan_requests.id", ondelete="RESTRICT"),
        nullable=False,
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
    accrued_interest: Mapped[Decimal] = mapped_column(
        MONEY_SQL_TYPE,
        nullable=False,
        default=Decimal("0.00"),
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
    first_due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    final_due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending_disbursement",
    )
    disbursed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    defaulted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    borrower: Mapped["Borrower"] = relationship("Borrower", lazy="raise")
    loan_request: Mapped["LoanRequest"] = relationship(
        "LoanRequest",
        back_populates="loan",
        lazy="raise",
    )
