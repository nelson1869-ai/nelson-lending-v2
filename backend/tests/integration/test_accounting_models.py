"""Tests for double-entry accounting models and DB constraints."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.accounting.constants import (
    ACCOUNT_CASH_CODE,
    ACCOUNT_CUSTOMER_CREDIT_CODE,
    ACCOUNT_INTEREST_INCOME_CODE,
    ACCOUNT_LOANS_RECEIVABLE_CODE,
)
from app.features.accounting.models import Account, JournalEntry, JournalTransaction
from app.features.accounting.service import ensure_system_accounts


async def test_ensure_system_accounts_creates_all_four_accounts(db_session: AsyncSession) -> None:
    """Verify ensure_system_accounts seeds standard system accounts."""
    accounts = await ensure_system_accounts(db_session)
    assert ACCOUNT_CASH_CODE in accounts
    assert ACCOUNT_LOANS_RECEIVABLE_CODE in accounts
    assert ACCOUNT_CUSTOMER_CREDIT_CODE in accounts
    assert ACCOUNT_INTEREST_INCOME_CODE in accounts

    cash = accounts[ACCOUNT_CASH_CODE]
    assert cash.name == "Cash"
    assert cash.account_type == "asset"
    assert cash.normal_balance == "debit"

    income = accounts[ACCOUNT_INTEREST_INCOME_CODE]
    assert income.account_type == "income"
    assert income.normal_balance == "credit"


async def test_duplicate_account_code_rejected(db_session: AsyncSession) -> None:
    """Verify unique constraint on account.code prevents duplicates."""
    acc1 = Account(
        code="9999",
        name="Test Account 1",
        account_type="asset",
        normal_balance="debit",
    )
    db_session.add(acc1)
    await db_session.flush()

    acc2 = Account(
        code="9999",
        name="Test Account 2",
        account_type="asset",
        normal_balance="debit",
    )
    db_session.add(acc2)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_invalid_account_type_rejected(db_session: AsyncSession) -> None:
    """Verify check constraint ck_account_type rejects invalid type."""
    acc = Account(
        code="9998",
        name="Invalid Type Acc",
        account_type="invalid_type",
        normal_balance="debit",
    )
    db_session.add(acc)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_journal_entry_one_sided_constraint(db_session: AsyncSession) -> None:
    """Verify check constraint ck_entry_one_sided rejects simultaneous debit and credit."""
    accounts = await ensure_system_accounts(db_session)
    cash = accounts[ACCOUNT_CASH_CODE]

    tx = JournalTransaction(
        event_type="payment",
        source_id=cash.id,
        description="Constraint test",
        effective_date=date.today(),
    )
    db_session.add(tx)
    await db_session.flush()

    # Entry with both debit > 0 and credit > 0
    entry = JournalEntry(
        journal_transaction_id=tx.id,
        account_id=cash.id,
        debit=Decimal("100.00"),
        credit=Decimal("50.00"),
    )
    db_session.add(entry)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
