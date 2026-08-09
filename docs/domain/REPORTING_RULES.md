# Lending Nelson V2 — Reports and Dashboard Rules

## 1. Scope and Authority

M15 provides read-only Owner reporting. PostgreSQL domain and accounting records remain the
source of truth; report requests never create, repair, or mutate financial records. Borrower
reports, overdue/arrears reporting, charts, exports, detailed rows, pagination, caching,
materialized views, persistent aggregates, and background generation are outside M15.

All money is calculated with PostgreSQL `NUMERIC` and Python `Decimal`, then serialized using the
existing two-decimal PHP convention. Reports preserve unexpected negative balances so
reconciliation defects remain visible.

## 2. Portfolio Snapshot

The snapshot returns counts for every value in the canonical `LOAN_STATUSES` tuple, including
zero-count and cancelled/defaulted states.

- `total_original_principal`: sum for `active` and `paid` loans only.
- `outstanding_principal`: current stored balance for `active` loans only.
- `accrued_interest`: current stored accrued interest for `active` loans only.
- Active and paid counts are also returned explicitly.

Cancelled, defaulted, and pending-disbursement loans remain visible in status counts but do not
enter monetary portfolio totals. Loan requests never enter loan portfolio money.

## 3. Collections

Collections use `Payment.payment_date`, the canonical effective business date used by payment
validation and contractual accrual. Owner inputs are Philippine calendar dates. Both displayed
boundaries are inclusive; the query uses the half-open interval:

```text
payment_date >= from_date
payment_date < to_date + 1 day
```

`from_date` after `to_date` is rejected. Each durable Payment represents a successfully posted
payment, so the query aggregates Payment rows directly without joins or duplicate risk. It returns
separate totals for `amount`, `principal_paid`, `interest_paid`, and `unapplied_credit`. The three
allocation totals must reconcile with payment amount under canonical allocation rules. Accounting
reversals are not recalculated at the Payment layer.

The maximum database date (`9999-12-31`) is rejected as `to_date` because its required following
day cannot be represented as the exclusive interval bound. Invalid ranges are rejected before any
report queries run.

## 4. Accounting Balances

Current balances come only from immutable `JournalEntry` rows grouped by canonical account code:

- `1000` Cash
- `1100` Loans Receivable
- `2000` Customer Credit
- `4000` Interest Income

Debit-normal accounts use `debits - credits`; credit-normal accounts use `credits - debits`.
Reversal journal entries therefore affect balances naturally. Reporting never matches accounts by
display name and never posts balancing or repair entries.

## 5. Loan-Request Snapshot

The snapshot returns counts for every value in canonical `LOAN_REQUEST_STATUSES`, including zero
counts and the existing cancelled state. Request counts do not affect portfolio money.

## 6. API, Privacy, and Client Behavior

`GET /api/v1/owner/reports/dashboard` requires Owner authentication and the required `from_date`
and `to_date` query parameters. Borrower and anonymous credentials cannot access it. Results use
canonical status ordering and canonical system-account ordering for deterministic output.

The Owner Flutter application displays summary cards and compact rows, accepts Philippine date
ranges, and provides loading, success, empty, error, refresh, and retry states. It parses backend
money as strings and never reproduces report formulas. When the selected dates are reversed, it
hides previously loaded metrics and disables refresh until the Owner restores a valid range. M15
makes no Borrower application changes.

## 7. Performance and Safe Extension

M15 uses bounded aggregate queries over existing indexed status, payment-date, and account-entry
paths. No schema change is required. A future metric must document its formula, source records,
status treatment, date semantics, authorization, reconciliation rule, deterministic output, and
tests before being added. Overdue or arrears metrics require a separately approved contractual
definition and persisted due-state model; `next_interest_due_date` is not an overdue proxy.
