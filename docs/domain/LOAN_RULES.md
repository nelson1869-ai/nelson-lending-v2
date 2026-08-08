# Lending Nelson V2 — Canonical Loan Rules

## 1. Purpose and Authority

This document defines the product rules that future loan, quote, schedule, and payment code must
follow. It is a domain specification, not an implementation. The backend will be the authoritative
calculator; mobile applications will display its results rather than reproduce financial logic.

## 2. Supported Repayment Model

New V2 loans use exactly one repayment model:

```text
Flexible Reducing-Balance
```

Interest is calculated from the applicable outstanding principal under the loan's agreed terms.
A payment first satisfies accrued or due interest, then reduces principal. Once principal is
reduced, future interest uses that reduced outstanding principal according to the applicable
accrual period and contractual rate.

The following new-loan modes are explicitly not supported:

- Interest-Only repayment
- flat-interest repayment
- fixed-principal repayment
- balloon repayment

No API or client may expose a repayment-model selector unless a future approved product decision
changes this specification and its tests.

## 3. Payment Allocation

Every accepted payment is allocated in this order:

```text
1. accrued or due interest
2. outstanding principal
3. unapplied credit, only under an explicit overpayment policy
```

Fees or penalties are not silently inserted into this order. If a later milestone introduces
them, their definition and allocation priority require an explicit domain decision, migration,
documentation, and regression tests.

### 3.1 Canonical Example

Given:

```text
Outstanding principal = ₱2,000
Accrued/due interest  = ₱200
```

A payment of ₱200 is allocated as:

```text
Interest paid       = ₱200
Principal paid      = ₱0
Remaining principal = ₱2,000
```

A payment of ₱700 is allocated as:

```text
Interest paid       = ₱200
Principal paid      = ₱500
Remaining principal = ₱1,500
```

Future interest is based on the remaining ₱1,500 principal under the agreed rate and accrual
rules. These amounts demonstrate allocation only; they do not define or hardcode a 10% rate.

## 4. Supported Payment Frequencies

New V2 loans support exactly:

```text
Monthly
Twice a Month
```

Weekly, daily, and biweekly schedules are not supported.

### 4.1 Monthly Calendar Anchoring

Monthly schedules retain the intended calendar anchor rather than treating a month as a fixed
number of days. When the anchor day does not exist, the occurrence uses that month's last valid
day without permanently losing the original anchor:

```text
January 31 → February 28/29 → March 31
```

The schedule generator must handle leap years and different month lengths deterministically.

### 4.2 Twice-a-Month Calendar Rules

Twice a Month means two calendar occurrences per month, preferably:

```text
15th + last calendar day
```

It is not an endless `previous date + 15 days` recurrence. The second occurrence is February
28/29, April 30, or the relevant month's 31st as appropriate. Exact first-period handling and
disbursement-date edge cases will be finalized with executable schedule examples in M09.

## 5. Precision and Rounding

- Python uses `Decimal` for money, rates, interest, balances, allocations, and totals.
- PostgreSQL uses explicitly sized `NUMERIC` columns. Binary floating-point is prohibited for
  authoritative financial values.
- Rates are stored as decimal fractions: for example, a configured ten-percent rate is represented
  as `Decimal("0.10")`, not a binary float.
- Monetary results are quantized to the smallest supported currency unit (`0.01 PHP`) using an
  explicitly configured `ROUND_HALF_UP` policy at documented calculation boundaries.
- Intermediate calculations retain sufficient precision and are not repeatedly rounded without a
  domain reason.
- The exact database precision/scale and rate-accrual precision are finalized with the M03/M09
  schemas and regression tests; they must safely preserve the documented behavior.

## 6. Quotes, Estimates, and Final Terms

- Quote and estimate calculations are backend-owned and call the same canonical calculator used
  by later loan creation workflows.
- A Borrower estimate is calculation-only: it does not create a request, loan, schedule, approval,
  or financial entry.
- The Owner controls final loan terms and approval. A preview does not promise approval or lock
  terms unless a future explicit feature defines a valid offer lifecycle.
- If required estimate configuration is absent, the backend reports that an estimate is
  unavailable rather than inventing a default financial rate.
- Client applications must not calculate authoritative interest, schedules, balances, or totals.

## 7. Flexible Payments and Early Payoff

- Partial payments are allowed and follow the canonical allocation order.
- Payments above currently due interest may reduce principal early.
- Early principal reduction affects future interest because future interest uses outstanding
  principal.
- A loan is not `Paid` while any principal or required accrued charge remains outstanding.
- Once a valid early payoff satisfies all principal and required accrued charges, no future
  unaccrued interest is collected merely because it appeared in an earlier projection.
- An overpayment cannot disappear or silently become income. It follows a future explicit
  unapplied-credit/refund policy and balanced accounting treatment.
- Recording, retrying, and reversing payments must be transactional and idempotent when those
  capabilities are implemented.

## 8. Conceptual Loan Lifecycle

The product lifecycle is currently conceptual:

```text
Draft
→ Approved
→ Funds Released / Disbursed
→ Active
→ Paid / Cancelled / Defaulted
```

This diagram does not require every label to become a persisted status. M11 will deliberately
decide which concepts are durable states, which are transition timestamps/events, and which
transitions are valid. Until then, no implementation should guess or prematurely lock the schema.

## 9. Required Financial Tests

When financial implementation begins, tests must cover:

- the ₱200 and ₱700 canonical allocations above;
- partial and early principal payments;
- future interest based on reduced principal;
- exact Decimal behavior and rounding boundaries;
- month-end anchoring and leap years;
- the 15th and last-day Twice-a-Month rules;
- rejection of unsupported repayment modes and frequencies;
- payoff without future unaccrued interest;
- idempotent retries and complete rollback on financial-operation failure.
