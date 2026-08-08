# Lending Nelson V2 — Double-Entry Accounting Rules

## 1. Purpose and Financial Authority

This document defines the canonical double-entry accounting specification for Lending Nelson V2.
PostgreSQL is the durable system of record. Every financial mutation (disbursement, payment, reversal)
must generate an append-only, balanced double-entry journal transaction within the same database transaction.

## 2. Standard Chart of Accounts

Lending Nelson V2 uses four system accounts:

| Code | Account Name | Type | Normal Balance |
| :--- | :--- | :--- | :--- |
| **1000** | Cash | Asset | Debit |
| **1100** | Loans Receivable | Asset | Debit |
| **2000** | Customer Credit | Liability | Credit |
| **4000** | Interest Income | Revenue | Credit |

## 3. Fundamental Invariants

1. **Balanced Transaction Invariant:**
   Every `JournalTransaction` must satisfy `SUM(debit) == SUM(credit)`. Unbalanced transactions are rejected.
2. **One-Sided Line Entry Invariant:**
   Every `JournalEntry` must be strictly positive and single-sided: `(debit > 0 AND credit == 0) OR (credit > 0 AND debit == 0)`.
3. **Source Uniqueness Invariant:**
   Automatic business event journals enforce uniqueness on `(event_type, source_id)`. Replaying disbursements or payments returns the existing journal without duplicating records.
4. **Append-Only Ledger & Compensating Reversals:**
   Journal transactions cannot be deleted or modified. Corrections are performed exclusively by posting compensating `reversal` journal transactions (`reversal_of_id`) that swap debits and credits.

## 4. Business Event Journal Definitions

### 4.1 Loan Disbursement (`loan_disbursement`)
Triggered automatically when an approved loan request is disbursed:

```text
DR 1100 Loans Receivable    [Principal Amount]
CR 1000 Cash                [Principal Amount]
```

### 4.2 Loan Payment (`payment`)
Triggered automatically when a payment is posted against an active loan using backend authoritative allocation:

```text
DR 1000 Cash                [Total Payment Amount]
  CR 4000 Interest Income   [Interest Allocated]     (if Interest Allocated > 0)
  CR 1100 Loans Receivable  [Principal Allocated]    (if Principal Allocated > 0)
  CR 2000 Customer Credit   [Unapplied Credit]       (if Unapplied Credit > 0)
```

### 4.3 Compensating Reversal (`reversal`)
Triggered by Owner reversal action against an eligible accounting-only transaction:

```text
Swap Debits and Credits of all entries in the original transaction
Set reversal_of_id = [Original Journal Transaction ID]
```

## 5. Business-Event Journal Integrity & Reversal Protection

Automatic business-event journals generated from:
- `loan_disbursement`
- `payment`

are immutable accounting representations of authoritative business domain mutations.

1. **Independent Reversal Prohibition:**
   Automatic business-event journals (`loan_disbursement`, `payment`) **MUST NOT** be independently reversed through generic accounting reversal endpoints (`POST /owner/accounting/journals/{id}/reverse`). Attempting to do so returns `HTTP 409 Conflict` and `BusinessEventJournalReversalError`.
2. **Domain-Atomic Reversals:**
   Reversing a financial business event requires an authoritative business-domain workflow that atomically updates BOTH the underlying domain state (e.g., Loan, Payment) and the accounting ledger within a single database transaction. Generic accounting reversals cannot alter loan balances or payment history.
3. **Reversal Invariance:**
   Reversal transactions (`reversal`) cannot themselves be reversed (`CannotReverseReversalError`). A journal cannot be reversed more than once (`JournalAlreadyReversedError`).

