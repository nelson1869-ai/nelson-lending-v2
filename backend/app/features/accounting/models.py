"""SQLAlchemy ORM models for Double-Entry Accounting."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    pass


class Account(Base):
    """Account in the Chart of Accounts."""

    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('asset', 'liability', 'equity', 'income', 'expense')",
            name="ck_account_type",
        ),
        CheckConstraint(
            "normal_balance IN ('debit', 'credit')",
            name="ck_account_normal_balance",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    normal_balance: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    journal_entries: Mapped[list["JournalEntry"]] = relationship(
        "JournalEntry",
        back_populates="account",
        passive_deletes=True,
    )


class JournalTransaction(Base):
    """Header record for a balanced double-entry accounting transaction."""

    __tablename__ = "journal_transactions"
    __table_args__ = (
        UniqueConstraint("event_type", "source_id", name="uq_journal_transactions_source"),
        CheckConstraint("id != reversal_of_id", name="ck_no_self_reversal"),
        CheckConstraint(
            "event_type IN ('loan_disbursement', 'payment', 'reversal')",
            name="ck_journal_event_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    reversal_of_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("journal_transactions.id", ondelete="RESTRICT"),
        unique=True,
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    entries: Mapped[list["JournalEntry"]] = relationship(
        "JournalEntry",
        back_populates="transaction",
        cascade="all, delete-orphan",
        passive_deletes=False,
        order_by="JournalEntry.id",
    )

    reversal_of: Mapped["JournalTransaction | None"] = relationship(
        "JournalTransaction",
        remote_side=[id],
        back_populates="reversal",
        uselist=False,
    )

    reversal: Mapped["JournalTransaction | None"] = relationship(
        "JournalTransaction",
        remote_side=[reversal_of_id],
        back_populates="reversal_of",
        uselist=False,
    )


class JournalEntry(Base):
    """Line item in a balanced accounting transaction."""

    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint("debit >= 0 AND credit >= 0", name="ck_entry_non_negative"),
        CheckConstraint(
            "(debit > 0 AND credit = 0) OR (debit = 0 AND credit > 0)",
            name="ck_entry_one_sided",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    journal_transaction_id: Mapped[UUID] = mapped_column(
        ForeignKey("journal_transactions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    debit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    transaction: Mapped["JournalTransaction"] = relationship(
        "JournalTransaction",
        back_populates="entries",
    )
    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="journal_entries",
    )
