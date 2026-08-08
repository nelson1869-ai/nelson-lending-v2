# AGENTS.md — Coding Agent Governance

This file defines mandatory operating rules for coding agents working on Lending Nelson V2.
The project is both a production-quality application and a deliberate full-stack learning
history, so implementation quality and Git traceability are equally important.

## 1. Product Boundaries

1. **Clean V2 design:** Treat V2 as a fresh architecture. The previous repository is reference
   material for domain understanding only; never copy its structure or code blindly.
2. **One business Owner:** The only business-side identity is `Owner`. Application roles named
   `admin`, `administrator`, `officer`, `manager`, `staff`, `collector`, `cashier`, or
   `supervisor` are prohibited. Do not build a role matrix.
3. **Separate Borrower identity:** Owner authentication and Borrower authentication use distinct
   identities, credentials, claims, sessions, and authorization dependencies. A Borrower account
   can never gain Owner privileges.
4. **One repayment model:** New V2 loans support only Flexible Reducing-Balance repayment.
   Interest-Only, flat-interest, fixed-principal, and balloon modes are not supported.
5. **Two payment frequencies:** New V2 loans support only Monthly and Twice a Month. Weekly,
   daily, and biweekly schedules are not supported. Twice a Month is calendar-based.
6. **Backend financial authority:** Quotes, interest, schedules, balances, payment allocations,
   and totals are calculated and enforced by the backend. Clients only present backend results.
7. **Exact financial precision:** Use Python `Decimal` and PostgreSQL `NUMERIC` for money and
   rates. Never use binary floating-point for authoritative financial values.
8. **PostgreSQL persistence authority:** PostgreSQL is the durable system of record. All schema
   changes must be explicit, reviewable Alembic migrations.

## 2. Agent Operating Rules

Before and during every task, agents must follow these rules:

1. Read this file and the relevant architecture, domain, workflow, and feature documentation
   before coding.
2. Inspect current source, configuration, migrations, tests, and Git state before modifying.
3. Do not copy V1 architecture blindly; re-evaluate every design for V2 boundaries.
4. Do not introduce legacy business-side roles or staff-management abstractions.
5. Do not introduce Interest-Only repayment or Weekly schedules.
6. Keep authoritative financial calculations and validation in backend domain services.
7. Use `Decimal` throughout financial calculations and conversion boundaries.
8. Preserve transaction atomicity: a failed financial mutation or required side effect must
   roll back the complete database transaction.
9. Add or update tests whenever behavior changes.
10. Never bypass Alembic with ad-hoc persistent schema edits.
11. Never weaken authentication, authorization, or borrower isolation to make a test pass; fix
    the implementation or test setup.
12. Never expose or commit passwords, signing keys, database credentials, API tokens, or other
    secrets.
13. Keep related backend code together in feature-oriented modules.
14. Avoid giant model, service, utility, router, and schema files; split by cohesive feature and
    responsibility.
15. Reuse canonical services for calculations and state transitions instead of duplicating
    business logic across handlers or clients.
16. Protect payment, disbursement, reversal, activation-style, and other duplicate-sensitive
    mutations with idempotency appropriate to the operation.
17. Run focused tests first, then the relevant broad regression and quality gates.
18. Report failures accurately, including the failed command and useful error details. Never
    hide failures, remove assertions, or claim an unrun check passed.
19. Do not modify or commit unrelated work. Preserve pre-existing user changes.
20. Do not push, configure a remote, or publish changes unless the project owner explicitly
    requests it.

## 3. Security and Data Integrity

- Resolve Borrower identity from the authenticated Borrower session. Never trust a payload's
  `borrower_id` or account identifier as authorization proof.
- Enforce cross-borrower isolation at API and service boundaries and prove it with tests.
- Hash passwords, PINs, activation codes, refresh tokens, and sensitive device identifiers when
  their plaintext form is not required. Never log them.
- Financial writes, accounting effects, receipts, and required outbox records belong in one
  transaction when introduced.
- Use explicit database constraints for invariants where practical; services and UI checks are
  not substitutes for durable integrity.
- Do not introduce tenant identifiers. Lending Nelson V2 serves one business.

## 4. Architecture and Migration Discipline

- Organize backend implementation by feature under `backend/app/features/<feature>/` when the
  backend is introduced.
- Keep cross-cutting configuration, database infrastructure, and narrowly reusable primitives in
  explicit core/shared packages.
- Use one canonical implementation for loan calculations, schedules, allocations, and state
  transitions.
- Every PostgreSQL change requires an Alembic revision that upgrades from the prior head and has
  a tested downgrade where safe.
- Never reuse an old local database silently. Inspect migration state and data before destructive
  development or test operations.
- Destructive integration tests must use a dedicated local test database and fail closed if the
  configured target is unsafe.

## 5. Incremental Milestone Workflow

Normal mode completes one coherent milestone incrementally:

```text
Inspect → Plan → Implement → Focused Test → Broad Verification → Review → Report
```

When the project owner explicitly requests **step-by-step mode**, perform exactly one requested
step, report its result, and wait for confirmation before continuing.

Milestone work happens on `feature/mXX-description`. Inspect diffs and run required checks before
committing. Keep local milestone branches for study. A reviewed milestone is merged into `main`
with `--no-ff` only when explicitly requested; implementation tasks do not merge automatically.

## 6. Completion Standard

A task is complete only when its requested scope is implemented, relevant focused and regression
checks pass, the diff contains no unrelated or secret material, documentation remains accurate,
and failures or remaining concerns are reported honestly.
