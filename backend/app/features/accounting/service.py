"""Double-Entry Accounting domain service enforcing transactional balance invariants."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.features.accounting.constants import (
    ACCOUNT_CASH_CODE,
    ACCOUNT_CUSTOMER_CREDIT_CODE,
    ACCOUNT_INTEREST_INCOME_CODE,
    ACCOUNT_LOANS_RECEIVABLE_CODE,
    SYSTEM_ACCOUNTS,
)
from app.features.accounting.models import Account, JournalEntry, JournalTransaction
from app.features.loans.calculator import quantize_money
from app.features.loans.models import Loan
from app.features.payments.models import Payment


class AccountingError(Exception):
    """Base exception for accounting domain errors."""


class AccountNotFoundError(AccountingError):
    """Raised when a required account is missing."""


class JournalNotFoundError(AccountingError):
    """Raised when a journal transaction is missing."""


class UnbalancedJournalError(AccountingError):
    """Raised when total debits do not equal total credits."""


class InvalidJournalEntryError(AccountingError):
    """Raised when a journal entry fails structural validation."""


class DuplicateJournalError(AccountingError):
    """Raised when an automatic event journal already exists for a source."""


class JournalAlreadyReversedError(AccountingError):
    """Raised when attempting to reverse an already reversed journal."""


class CannotReverseReversalError(AccountingError):
    """Raised when attempting to reverse a reversal transaction."""


class BusinessEventJournalReversalError(AccountingError):
    """Raised when attempting to independently reverse an automatic business-event journal."""


async def ensure_system_accounts(db: AsyncSession) -> dict[str, Account]:
    """Ensure system-controlled Chart of Accounts exist in DB and return mapping by code."""
    stmt = select(Account)
    res = await db.execute(stmt)
    existing_accounts = {acc.code: acc for acc in res.scalars().all()}

    accounts_by_code: dict[str, Account] = {}
    for sys_acc in SYSTEM_ACCOUNTS:
        code = sys_acc["code"]
        if code in existing_accounts:
            accounts_by_code[code] = existing_accounts[code]
        else:
            acc = Account(
                code=code,
                name=sys_acc["name"],
                account_type=sys_acc["account_type"],
                normal_balance=sys_acc["normal_balance"],
                is_active=True,
            )
            db.add(acc)
            accounts_by_code[code] = acc

    await db.flush()
    return accounts_by_code


async def post_journal(
    db: AsyncSession,
    *,
    event_type: str,
    source_id: UUID,
    description: str,
    effective_date: date,
    entries: list[tuple[Account, Decimal, Decimal]],
    posted_at: datetime | None = None,
    reversal_of_id: UUID | None = None,
) -> JournalTransaction:
    """Central canonical posting mechanism for balanced double-entry accounting transactions."""
    if len(entries) < 2:
        raise InvalidJournalEntryError("A journal transaction must contain at least 2 entries.")

    now = posted_at or datetime.now(UTC)

    # Validate each entry line
    validated_entries: list[tuple[Account, Decimal, Decimal]] = []
    for acc, debit_val, credit_val in entries:
        debit_q = quantize_money(debit_val)
        credit_q = quantize_money(credit_val)

        if debit_q < Decimal("0.00") or credit_q < Decimal("0.00"):
            raise InvalidJournalEntryError(
                f"Entry amounts must be non-negative. Got debit={debit_q}, credit={credit_q}."
            )

        if (debit_q > Decimal("0.00") and credit_q > Decimal("0.00")) or (
            debit_q == Decimal("0.00") and credit_q == Decimal("0.00")
        ):
            raise InvalidJournalEntryError(
                "Entry must have exactly one positive side (debit OR credit). "
                f"Got debit={debit_q}, credit={credit_q}."
            )

        validated_entries.append((acc, debit_q, credit_q))

    total_debit = sum(e[1] for e in validated_entries)
    total_credit = sum(e[2] for e in validated_entries)

    if total_debit != total_credit:
        raise UnbalancedJournalError(
            f"Journal transaction is unbalanced. Total Debit ({total_debit}) "
            f"!= Total Credit ({total_credit})."
        )

    tx = JournalTransaction(
        event_type=event_type,
        source_id=source_id,
        description=description,
        effective_date=effective_date,
        posted_at=now,
        created_at=now,
        reversal_of_id=reversal_of_id,
    )
    db.add(tx)
    await db.flush()

    for acc, debit_q, credit_q in validated_entries:
        entry = JournalEntry(
            journal_transaction_id=tx.id,
            account_id=acc.id,
            debit=debit_q,
            credit=credit_q,
            created_at=now,
        )
        db.add(entry)

    await db.flush()
    return await get_journal_detail(db, tx.id)


async def post_disbursement_journal(
    db: AsyncSession,
    loan: Loan,
) -> JournalTransaction:
    """Post an automatic balanced accounting journal for a loan disbursement."""
    # Source uniqueness check
    existing_stmt = (
        select(JournalTransaction)
        .options(joinedload(JournalTransaction.entries).joinedload(JournalEntry.account))
        .where(
            JournalTransaction.event_type == "loan_disbursement",
            JournalTransaction.source_id == loan.id,
        )
    )
    existing_res = await db.execute(existing_stmt)
    existing_tx = existing_res.scalar_one_or_none()
    if existing_tx is not None:
        return existing_tx

    accounts = await ensure_system_accounts(db)
    receivable_acc = accounts[ACCOUNT_LOANS_RECEIVABLE_CODE]
    cash_acc = accounts[ACCOUNT_CASH_CODE]

    amount = quantize_money(loan.original_principal)
    entries = [
        (receivable_acc, amount, Decimal("0.00")),
        (cash_acc, Decimal("0.00"), amount),
    ]

    effective_dt = loan.disbursed_at.date() if loan.disbursed_at else date.today()
    return await post_journal(
        db,
        event_type="loan_disbursement",
        source_id=loan.id,
        description=f"Disbursement for Loan {loan.id}",
        effective_date=effective_dt,
        entries=entries,
        posted_at=loan.disbursed_at,
    )


async def post_payment_journal(
    db: AsyncSession,
    payment: Payment,
) -> JournalTransaction:
    """Post automatic balanced payment journal using authoritative allocation."""
    existing_stmt = (
        select(JournalTransaction)
        .options(joinedload(JournalTransaction.entries).joinedload(JournalEntry.account))
        .where(
            JournalTransaction.event_type == "payment",
            JournalTransaction.source_id == payment.id,
        )
    )
    existing_res = await db.execute(existing_stmt)
    existing_tx = existing_res.scalar_one_or_none()
    if existing_tx is not None:
        return existing_tx

    accounts = await ensure_system_accounts(db)
    cash_acc = accounts[ACCOUNT_CASH_CODE]
    interest_acc = accounts[ACCOUNT_INTEREST_INCOME_CODE]
    receivable_acc = accounts[ACCOUNT_LOANS_RECEIVABLE_CODE]
    credit_acc = accounts[ACCOUNT_CUSTOMER_CREDIT_CODE]

    entries: list[tuple[Account, Decimal, Decimal]] = [
        (cash_acc, payment.amount, Decimal("0.00")),
    ]

    if payment.interest_paid > Decimal("0.00"):
        entries.append((interest_acc, Decimal("0.00"), payment.interest_paid))

    if payment.principal_paid > Decimal("0.00"):
        entries.append((receivable_acc, Decimal("0.00"), payment.principal_paid))

    if payment.unapplied_credit > Decimal("0.00"):
        entries.append((credit_acc, Decimal("0.00"), payment.unapplied_credit))

    ref_str = f" (Ref: {payment.reference})" if payment.reference else ""
    return await post_journal(
        db,
        event_type="payment",
        source_id=payment.id,
        description=f"Payment for Loan {payment.loan_id}{ref_str}",
        effective_date=payment.payment_date,
        entries=entries,
        posted_at=payment.posted_at,
    )


async def reverse_journal(
    db: AsyncSession,
    journal_id: UUID,
    *,
    reason: str = "",
) -> JournalTransaction:
    """Create a compensating reversal journal for an existing journal transaction."""
    stmt = (
        select(JournalTransaction)
        .options(joinedload(JournalTransaction.entries).joinedload(JournalEntry.account))
        .where(JournalTransaction.id == journal_id)
        .with_for_update(of=JournalTransaction)
    )
    res = await db.execute(stmt)
    journal = res.unique().scalar_one_or_none()

    if journal is None:
        raise JournalNotFoundError(f"Journal transaction '{journal_id}' not found.")

    if journal.event_type in {"loan_disbursement", "payment"}:
        raise BusinessEventJournalReversalError(
            f"Automatic '{journal.event_type}' journals cannot be reversed independently of "
            "their business domain workflow."
        )

    if journal.reversal_of_id is not None:
        raise CannotReverseReversalError("Cannot reverse a reversal transaction.")

    # Check if already reversed
    existing_rev_stmt = select(JournalTransaction).where(
        JournalTransaction.reversal_of_id == journal_id
    )
    existing_rev_res = await db.execute(existing_rev_stmt)
    if existing_rev_res.scalar_one_or_none() is not None:
        raise JournalAlreadyReversedError(
            f"Journal transaction '{journal_id}' is already reversed."
        )

    reversed_entries: list[tuple[Account, Decimal, Decimal]] = []
    for entry in journal.entries:
        # Swap debit and credit
        reversed_entries.append((entry.account, entry.credit, entry.debit))

    reason_str = f": {reason.strip()}" if reason and reason.strip() else ""
    return await post_journal(
        db,
        event_type="reversal",
        source_id=journal.id,
        description=f"Reversal of Journal {journal.id}{reason_str}",
        effective_date=date.today(),
        entries=reversed_entries,
        reversal_of_id=journal.id,
    )


async def list_accounts(db: AsyncSession) -> list[Account]:
    """Retrieve Chart of Accounts ordered by code."""
    await ensure_system_accounts(db)
    stmt = select(Account).order_by(Account.code.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def list_journals(db: AsyncSession) -> list[JournalTransaction]:
    """Retrieve journal transactions with entries ordered by posted_at desc."""
    stmt = (
        select(JournalTransaction)
        .options(joinedload(JournalTransaction.entries).joinedload(JournalEntry.account))
        .order_by(JournalTransaction.posted_at.desc(), JournalTransaction.id.desc())
    )
    res = await db.execute(stmt)
    return list(res.unique().scalars().all())


async def get_journal_detail(db: AsyncSession, journal_id: UUID) -> JournalTransaction:
    """Retrieve a single journal transaction by ID."""
    stmt = (
        select(JournalTransaction)
        .options(joinedload(JournalTransaction.entries).joinedload(JournalEntry.account))
        .where(JournalTransaction.id == journal_id)
    )
    res = await db.execute(stmt)
    journal = res.unique().scalar_one_or_none()
    if journal is None:
        raise JournalNotFoundError(f"Journal transaction '{journal_id}' not found.")
    return journal
