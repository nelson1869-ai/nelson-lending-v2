"""Tests for double-entry accounting domain service invariants."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.accounting.constants import (
    ACCOUNT_CASH_CODE,
    ACCOUNT_INTEREST_INCOME_CODE,
    ACCOUNT_LOANS_RECEIVABLE_CODE,
)
from app.features.accounting.service import (
    CannotReverseReversalError,
    InvalidJournalEntryError,
    JournalAlreadyReversedError,
    UnbalancedJournalError,
    ensure_system_accounts,
    post_journal,
    reverse_journal,
)


async def test_post_journal_balanced_success(db_session: AsyncSession) -> None:
    """Verify posting a balanced journal persists header and entries cleanly."""
    accounts = await ensure_system_accounts(db_session)
    cash = accounts[ACCOUNT_CASH_CODE]
    receivable = accounts[ACCOUNT_LOANS_RECEIVABLE_CODE]

    source_id = uuid4()
    entries = [
        (receivable, Decimal("1000.00"), Decimal("0.00")),
        (cash, Decimal("0.00"), Decimal("1000.00")),
    ]

    tx = await post_journal(
        db_session,
        event_type="loan_disbursement",
        source_id=source_id,
        description="Balanced disbursement test",
        effective_date=date(2026, 6, 1),
        entries=entries,
    )

    assert tx.id is not None
    assert tx.event_type == "loan_disbursement"
    assert tx.source_id == source_id
    assert len(tx.entries) == 2

    # Verify balance
    tot_debit = sum(e.debit for e in tx.entries)
    tot_credit = sum(e.credit for e in tx.entries)
    assert tot_debit == Decimal("1000.00")
    assert tot_credit == Decimal("1000.00")


async def test_post_journal_unbalanced_rejected(db_session: AsyncSession) -> None:
    """Verify attempting to post an unbalanced journal raises UnbalancedJournalError."""
    accounts = await ensure_system_accounts(db_session)
    cash = accounts[ACCOUNT_CASH_CODE]
    receivable = accounts[ACCOUNT_LOANS_RECEIVABLE_CODE]

    entries = [
        (receivable, Decimal("1000.00"), Decimal("0.00")),
        (cash, Decimal("0.00"), Decimal("999.00")),
    ]

    with pytest.raises(UnbalancedJournalError) as exc_info:
        await post_journal(
            db_session,
            event_type="loan_disbursement",
            source_id=uuid4(),
            description="Unbalanced test",
            effective_date=date(2026, 6, 1),
            entries=entries,
        )

    assert "unbalanced" in str(exc_info.value).lower()


async def test_post_journal_single_sided_rejected(db_session: AsyncSession) -> None:
    """Verify posting a line with both debit and credit raises InvalidJournalEntryError."""
    accounts = await ensure_system_accounts(db_session)
    cash = accounts[ACCOUNT_CASH_CODE]

    entries = [
        (cash, Decimal("100.00"), Decimal("100.00")),
        (cash, Decimal("0.00"), Decimal("0.00")),
    ]

    with pytest.raises(InvalidJournalEntryError):
        await post_journal(
            db_session,
            event_type="payment",
            source_id=uuid4(),
            description="Invalid line test",
            effective_date=date(2026, 6, 1),
            entries=entries,
        )


async def test_journal_reversal_creates_compensating_journal(db_session: AsyncSession) -> None:
    """Verify reversing a journal creates an exact opposite compensating transaction."""
    accounts = await ensure_system_accounts(db_session)
    cash = accounts[ACCOUNT_CASH_CODE]
    income = accounts[ACCOUNT_INTEREST_INCOME_CODE]
    receivable = accounts[ACCOUNT_LOANS_RECEIVABLE_CODE]

    orig_entries = [
        (cash, Decimal("700.00"), Decimal("0.00")),
        (income, Decimal("0.00"), Decimal("200.00")),
        (receivable, Decimal("0.00"), Decimal("500.00")),
    ]

    orig_tx = await post_journal(
        db_session,
        event_type="payment",
        source_id=uuid4(),
        description="Original payment",
        effective_date=date(2026, 6, 15),
        entries=orig_entries,
    )

    rev_tx = await reverse_journal(db_session, orig_tx.id, reason="Customer error")

    assert rev_tx.reversal_of_id == orig_tx.id
    assert rev_tx.event_type == "reversal"
    assert len(rev_tx.entries) == 3

    # Check reversed line entries
    rev_by_acc = {e.account.code: e for e in rev_tx.entries}
    assert rev_by_acc[ACCOUNT_CASH_CODE].credit == Decimal("700.00")
    assert rev_by_acc[ACCOUNT_CASH_CODE].debit == Decimal("0.00")
    assert rev_by_acc[ACCOUNT_INTEREST_INCOME_CODE].debit == Decimal("200.00")
    assert rev_by_acc[ACCOUNT_LOANS_RECEIVABLE_CODE].debit == Decimal("500.00")

    # Reversing again must be rejected
    with pytest.raises(JournalAlreadyReversedError):
        await reverse_journal(db_session, orig_tx.id)

    # Reversing a reversal transaction must be rejected
    with pytest.raises(CannotReverseReversalError):
        await reverse_journal(db_session, rev_tx.id)
