"""M13 Double-Entry Accounting schema and system accounts.

Revision ID: 0011_accounting
Revises: 0010_m12_accrual_periods
Create Date: 2026-08-09
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0011_accounting"
down_revision: str | None = "0010_m12_accrual_periods"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Accounts Table (Chart of Accounts)
    accounts_table = op.create_table(
        "accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("normal_balance", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "account_type IN ('asset', 'liability', 'equity', 'income', 'expense')",
            name="ck_account_type",
        ),
        sa.CheckConstraint(
            "normal_balance IN ('debit', 'credit')",
            name="ck_account_normal_balance",
        ),
    )
    op.create_index("ix_accounts_code", "accounts", ["code"], unique=True)

    # Seed system accounts
    op.bulk_insert(
        accounts_table,
        [
            {
                "id": uuid4(),
                "code": "1000",
                "name": "Cash",
                "account_type": "asset",
                "normal_balance": "debit",
                "is_active": True,
            },
            {
                "id": uuid4(),
                "code": "1100",
                "name": "Loans Receivable",
                "account_type": "asset",
                "normal_balance": "debit",
                "is_active": True,
            },
            {
                "id": uuid4(),
                "code": "2000",
                "name": "Customer Credit",
                "account_type": "liability",
                "normal_balance": "credit",
                "is_active": True,
            },
            {
                "id": uuid4(),
                "code": "4000",
                "name": "Interest Income",
                "account_type": "income",
                "normal_balance": "credit",
                "is_active": True,
            },
        ],
    )

    # 2. Journal Transactions Table (Header)
    op.create_table(
        "journal_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "posted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reversal_of_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["reversal_of_id"],
            ["journal_transactions.id"],
            name="fk_journal_transactions_reversal_of_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("event_type", "source_id", name="uq_journal_transactions_source"),
        sa.CheckConstraint("id != reversal_of_id", name="ck_no_self_reversal"),
        sa.CheckConstraint(
            "event_type IN ('loan_disbursement', 'payment', 'reversal')",
            name="ck_journal_event_type",
        ),
    )
    op.create_index("ix_journal_transactions_source_id", "journal_transactions", ["source_id"])
    op.create_index(
        "ix_journal_transactions_reversal_of_id",
        "journal_transactions",
        ["reversal_of_id"],
        unique=True,
    )

    # 3. Journal Entries Table (Lines)
    op.create_table(
        "journal_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column("journal_transaction_id", UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", UUID(as_uuid=True), nullable=False),
        sa.Column("debit", sa.Numeric(18, 2), server_default="0.00", nullable=False),
        sa.Column("credit", sa.Numeric(18, 2), server_default="0.00", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["journal_transaction_id"],
            ["journal_transactions.id"],
            name="fk_journal_entries_journal_transaction_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_journal_entries_account_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("debit >= 0 AND credit >= 0", name="ck_entry_non_negative"),
        sa.CheckConstraint(
            "(debit > 0 AND credit = 0) OR (debit = 0 AND credit > 0)",
            name="ck_entry_one_sided",
        ),
    )
    op.create_index(
        "ix_journal_entries_journal_transaction_id",
        "journal_entries",
        ["journal_transaction_id"],
    )
    op.create_index("ix_journal_entries_account_id", "journal_entries", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_journal_entries_account_id", table_name="journal_entries")
    op.drop_index("ix_journal_entries_journal_transaction_id", table_name="journal_entries")
    op.drop_table("journal_entries")

    op.drop_index("ix_journal_transactions_reversal_of_id", table_name="journal_transactions")
    op.drop_index("ix_journal_transactions_source_id", table_name="journal_transactions")
    op.drop_table("journal_transactions")

    op.drop_index("ix_accounts_code", table_name="accounts")
    op.drop_table("accounts")
