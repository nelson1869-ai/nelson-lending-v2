"""Payment persistence model for canonical Flexible Reducing-Balance allocation history."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import MONEY_SQL_TYPE

if TYPE_CHECKING:
    from app.features.loans.models import Loan


class Payment(TimestampMixin, Base):
    """A durable payment record posted against an active loan."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="payment_amount_positive",
        ),
        CheckConstraint(
            "interest_paid >= 0",
            name="interest_paid_non_negative",
        ),
        CheckConstraint(
            "principal_paid >= 0",
            name="principal_paid_non_negative",
        ),
        CheckConstraint(
            "unapplied_credit >= 0",
            name="unapplied_credit_non_negative",
        ),
        CheckConstraint(
            "remaining_interest >= 0",
            name="remaining_interest_non_negative",
        ),
        CheckConstraint(
            "remaining_principal >= 0",
            name="remaining_principal_non_negative",
        ),
        Index("ix_payments_loan_id", "loan_id"),
        Index("ix_payments_posted_at", "posted_at"),
        Index("ix_payments_payment_date", "payment_date"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    loan_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("loans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        MONEY_SQL_TYPE,
        nullable=False,
    )
    interest_paid: Mapped[Decimal] = mapped_column(
        MONEY_SQL_TYPE,
        nullable=False,
    )
    principal_paid: Mapped[Decimal] = mapped_column(
        MONEY_SQL_TYPE,
        nullable=False,
    )
    unapplied_credit: Mapped[Decimal] = mapped_column(
        MONEY_SQL_TYPE,
        nullable=False,
    )
    remaining_interest: Mapped[Decimal] = mapped_column(
        MONEY_SQL_TYPE,
        nullable=False,
    )
    remaining_principal: Mapped[Decimal] = mapped_column(
        MONEY_SQL_TYPE,
        nullable=False,
    )
    payment_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    loan: Mapped["Loan"] = relationship("Loan", lazy="raise")
