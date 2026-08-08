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
    BusinessEventJournalReversalError,
    InvalidJournalEntryError,
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


async def test_reverse_journal_rejects_business_events(db_session: AsyncSession) -> None:
    """Verify reverse_journal raises BusinessEventJournalReversalError for business events."""
    accounts = await ensure_system_accounts(db_session)
    cash = accounts[ACCOUNT_CASH_CODE]
    receivable = accounts[ACCOUNT_LOANS_RECEIVABLE_CODE]
    income = accounts[ACCOUNT_INTEREST_INCOME_CODE]

    # 1. Loan disbursement reversal rejected
    disb_tx = await post_journal(
        db_session,
        event_type="loan_disbursement",
        source_id=uuid4(),
        description="Disbursement event",
        effective_date=date(2026, 6, 15),
        entries=[
            (receivable, Decimal("1000.00"), Decimal("0.00")),
            (cash, Decimal("0.00"), Decimal("1000.00")),
        ],
    )
    with pytest.raises(BusinessEventJournalReversalError) as exc_disb:
        await reverse_journal(db_session, disb_tx.id)
    assert "cannot be reversed independently" in str(exc_disb.value)

    # 2. Payment reversal rejected
    pay_tx = await post_journal(
        db_session,
        event_type="payment",
        source_id=uuid4(),
        description="Payment event",
        effective_date=date(2026, 6, 15),
        entries=[
            (cash, Decimal("200.00"), Decimal("0.00")),
            (income, Decimal("0.00"), Decimal("200.00")),
        ],
    )
    with pytest.raises(BusinessEventJournalReversalError) as exc_pay:
        await reverse_journal(db_session, pay_tx.id)
    assert "cannot be reversed independently" in str(exc_pay.value)
