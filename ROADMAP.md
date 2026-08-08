# Lending Nelson V2 — Full-Stack Learning Roadmap

This roadmap makes application delivery and professional Git practice equally visible. Each
milestone is developed on its named feature branch, reviewed and verified, then merged into
`main` with `--no-ff`. Local milestone branches remain available for study. Completion and
merge SHAs, decisions, and lessons are recorded here when each milestone finishes.

## Working Method

```text
main
  → git switch -c feature/mXX-description
  → learn and implement the milestone
  → inspect diff and run quality gates
  → create meaningful Conventional Commits
  → review
  → git merge --no-ff feature/mXX-description
```

`main` contains completed, verified milestones. Feature implementation never happens directly
on `main`. Authorized feature branches are pushed so GitHub mirrors the learning history; they are
never force-pushed or merged without explicit review approval.

## Phase A — Foundations

### M01 — Architecture & Governance Foundation

- **Status:** Completed
- **Branch:** `feature/m01-architecture-foundation`
- **Goal:** Define the system, domain boundaries, repository governance, and learning workflow before implementation.
- **Topics to Learn:** System architecture; monorepo organization; domain boundaries; agent governance; technical documentation; Git status, branches, switches, commits, logs, shows, and non-fast-forward merges.
- **Concepts Learned:** Separate identity/security domains; backend and PostgreSQL authority; feature-oriented boundaries; transaction/idempotency principles; canonical lending rules; intentional feature-branch commits and review-before-merge workflow.
- **Deliverables:** Created `AGENTS.md`, `docs/architecture/ARCHITECTURE.md`, `docs/domain/LOAN_RULES.md`, and `docs/development/DEVELOPMENT_WORKFLOW.md`; updated `README.md` and this roadmap. No application scaffold was created.
- **Tests / Quality Gates:** Required-file/link checks passed; documentation consistency and prohibited-concept contexts reviewed; M02–M16 remain Not Started; repository tree contains no application directories; staged patches and whitespace checks passed.
- **Completion Commits:**
  - `2557faf` — `docs: define v2 architecture and agent rules`
  - `3edc666` — `docs: define loan rules and learning workflow`
  - `f10cad9` — `docs: mark m01 ready for review`
- **Merge Commit:** `d3a5c882f37b2de4c3b37aa24cbc0ec467c42373` — `merge: complete m01 architecture foundation`
- **Notes / Lessons Learned:** Defining product prohibitions and authority boundaries before scaffolding prevents accidental legacy design carryover. The feature-branch lifecycle used multiple meaningful commits, explicit review before merge, and a non-fast-forward merge that preserves the milestone boundary. Keeping the M01 branch makes its implementation history available for later study.

### M02 — Backend Foundation

- **Status:** Completed
- **Branch:** `feature/m02-backend-foundation`
- **Goal:** Establish a minimal, testable FastAPI backend and its development toolchain.
- **Topics to Learn:** Python project structure; FastAPI; Pydantic Settings; dependency management; async SQLAlchemy; pytest; Ruff; mypy; health checks.
- **Concepts Learned:** Python 3.12 packaging with editable development installs; environment-backed settings; application factories; async SQLAlchemy engine/session lifecycles; deterministic constraint naming; Decimal-backed PostgreSQL types; liveness versus dependency-aware readiness; async HTTP unit tests; async Alembic configuration; layered local quality gates.
- **Deliverables:** Added the backend package scaffold, safe configuration template, FastAPI application factory and route composition, async SQLAlchemy session foundation, canonical money/rate types, liveness and readiness endpoints, async Alembic environment with no revisions, baseline tests, executable verification script, and learner setup documentation. Business features remain deferred.
- **Tests / Quality Gates:** `Backend import OK`; pytest 5 passed; Ruff lint passed; Ruff format check passed for 19 files; mypy passed for 13 application source files; `alembic heads` succeeded with no revisions; live Uvicorn smoke test returned 200 for liveness and a sanitized 503 for readiness without PostgreSQL.
- **Completion Commits:**
  - `a0d83ad` — `chore(backend): establish python project tooling`
  - `93309b6` — `feat(backend): add api and database infrastructure`
  - `5d27975` — `test(backend): add foundation quality gates`
  - `a492030` — `docs: mark m02 ready for review`
  - `28a76ad` — `chore(backend): finalize m02 review hygiene`
- **Merge Commit:** `2e0bfb577ce83544744254540ac96dac9bdf4a07` — `merge: complete m02 backend foundation`
- **Notes / Lessons Learned:** `pyproject.toml` centralizes Python packaging and pytest, Ruff, and mypy configuration. The FastAPI application factory composes routes without connecting during import; Pydantic Settings owns environment configuration; and the async SQLAlchemy engine/session foundation leaves transaction ownership explicit for future domain services. Alembic shares application settings and metadata while M02 intentionally has no revisions. Liveness checks process availability, readiness checks PostgreSQL, and mocked infrastructure tests remain distinct from real integration tests. Feature-branch review followed by a two-parent `--no-ff` merge preserves the complete milestone history. CORS remains deferred until a web client can supply explicit allowed origins. M02 has no schema migration or business model.

### M03 — PostgreSQL & Database Foundation

- **Status:** Completed
- **Branch:** `feature/m03-database-foundation`
- **Goal:** Create the first persistent identity and business-settings schema on real local PostgreSQL.
- **Topics to Learn:** PostgreSQL; SQLAlchemy ORM; relationships; constraints; indexes; UUIDs; `NUMERIC` and `Decimal`; Alembic migrations; integration-test isolation.
- **Concepts Learned:** Feature-oriented SQLAlchemy models; application-generated UUIDv4 identifiers; timezone-aware PostgreSQL timestamps; exact `NUMERIC`/`Decimal` rates; deterministic constraints; indexed foreign keys; partial and composite indexes; separate Borrower records and app accounts; reversible Alembic migrations; local dev/test database isolation; fail-closed real PostgreSQL tests.
- **Deliverables:** Added `OwnerUser`, `Borrower`, `BorrowerAccount`, `BorrowerDevice`, `BorrowerRefreshToken`, and singleton `BusinessSetting` models; shared timestamp/model discovery infrastructure; one reversible initial identity migration with the safe settings seed; guarded PostgreSQL integration tests; and local database/migration/schema-inspection documentation. Authentication and lending behavior remain deferred.
- **Tests / Quality Gates:** PostgreSQL 16.14 databases were recreated locally after old schema inspection; migration from zero, downgrade to base, and re-upgrade passed; `alembic current` and `heads` report `0001_initial_identity_schema`; `alembic check` reports no new operations; 16 real integration tests passed; full pytest 21 passed; Ruff lint passed; Ruff format checked 31 files; mypy passed 21 application files; FastAPI import passed; catalog inspection found only the seven expected tables, zero Owner rows, and the seeded settings singleton with a null estimate rate.
- **Completion Commits:**
  - `f7801f3` — `feat(db): add identity and borrower models`
  - `55d785a` — `feat(db): add initial identity schema migration`
  - `a73a8c2` — `test(db): add PostgreSQL schema integration tests`
  - `4aed4a9` — `docs: mark m03 ready for review`
  - `a2a0e67` — `chore(db): finalize m03 review record`
- **Merge Commit:** `50be1abc9864634f5c0b263f8ce785f528e6c6a0` — `merge: complete m03 database foundation`
- **Notes / Lessons Learned:** Inspecting before reset exposed an older migration in both named databases, so only those two local project databases were recreated. Unique and CHECK constraints protect identity invariants, a partial unique index permits zero or one active Owner, and the token device/account composite FK prevents cross-account device references. Borrower deletion is restricted while account/device/token cleanup uses deliberate cascades. Integration tests use a dedicated exact-name loopback database, rollback each case, and remain distinct from mocked health tests. Feature-branch review followed by a two-parent `--no-ff` merge preserves the complete milestone history.

## Phase B — Authentication & Identity

### M04 — Owner Authentication

- **Status:** Completed
- **Branch:** `feature/m04-owner-auth`
- **Goal:** Implement secure authentication for the single business Owner.
- **Topics to Learn:** Argon2id; password hashing; secure bootstrap; JWT access tokens; refresh sessions; authentication dependencies; logout and revocation; security testing.
- **Deliverables:** Added a race-safe one-time Owner CLI bootstrap; Argon2id credential handling; typed Owner-only access JWTs; hashed opaque refresh-session persistence with locking, rotation, and revocation; login, refresh, logout, and `/me` APIs; and a canonical active-Owner dependency. Borrower authentication remains deferred.
- **Tests / Quality Gates:** FastAPI import passed; full pytest 43 passed; real PostgreSQL integration suite 32 passed with 11 deselected; Ruff lint passed; Ruff format checked 41 files; mypy passed 27 application files; `0002_owner_auth_sessions` is current/head; Alembic reports no drift; test DB fresh install through 0001/0002 passed; redacted local API lifecycle smoke passed.
- **Completion Commits:**
  - `040707f` — `feat(auth): add owner security primitives`
  - `9bf384d` — `feat(auth): add owner refresh session persistence`
  - `4a4b788` — `feat(auth): implement owner authentication flow`
  - `6e58523` — `test(auth): cover owner authentication lifecycle`
  - `dc5ed23` — `fix(auth): align generic login verification`
  - `8631018` — `docs: mark m04 ready for review`
- **Merge Commit:** `d3c96603047710169d3f354abaedc856c6332d99` — `merge: complete m04 owner authentication`
- **Notes / Lessons Learned:** The only business identity remains Owner, with no role matrix. Human passwords require salted Argon2id while random high-entropy refresh tokens use deterministic SHA-256 lookup hashes. Login writes and refresh-session creation share a transaction; refresh uses `SELECT FOR UPDATE` so revocation and replacement are single-use and atomic. Logout revokes refresh capability while short-lived access JWTs expire naturally. Password recovery, MFA, Borrower authentication, and distributed login throttling remain deliberately deferred.

### M05 — Borrower Registration

- **Status:** Completed
- **Branch:** `feature/m05-borrower-registration`
- **Goal:** Build a validated public registration workflow controlled by Owner approval.
- **Topics to Learn:** Public input boundaries; Owner approval; validation; phone normalization; duplicate protection; activation-code lifecycle design.
- **Deliverables:** Added a dedicated pending registration model and reversible migration; canonical Philippine mobile and national-ID normalization; privacy-preserving public submission; authenticated Owner list/detail review APIs; row-locked atomic approval/rejection; resulting Borrower linkage; and pre-activation BorrowerAccount creation with a null PIN.
- **Tests / Quality Gates:** FastAPI import passed; full pytest 85 passed; real PostgreSQL integration suite 56 passed with 29 deselected; Ruff lint passed; Ruff format checked 50 files; mypy passed 33 application files; `0003_borrower_registrations` is current/head; Alembic reports no drift; test DB fresh install through 0001/0002/0003 passed; real concurrent approval and forced rollback tests passed; redacted local approve/reject API smoke passed.
- **Completion Commits:**
  - `9205f2f` — `feat(borrowers): add registration domain model`
  - `78d4474` — `feat(borrowers): add public registration workflow`
  - `f0f303b` — `feat(borrowers): add owner registration review workflow`
  - `483929b` — `test(borrowers): cover registration and approval lifecycle`
  - `d6154c2` — `docs: mark m05 ready for review`
- **Merge Commit:** `bbe73a6c5e2a725bcbdc7ec642322a468a1e0235` — `merge: complete m05 borrower registration`
- **Notes / Lessons Learned:** Public registration and Owner-authenticated review are separate API boundaries, and public responses avoid leaking borrower PII or confirming which identity matched a conflict. Philippine phone canonicalization gives identity comparisons one stable form, while partial PostgreSQL unique indexes protect concurrent pending national-ID and phone submissions. Owner review reuses the canonical Owner dependency; `SELECT FOR UPDATE`, terminal-state checks, and database uniqueness make each decision single-use. Approval atomically creates and links `Borrower(active)` and `BorrowerAccount(approved, pin_hash=NULL)`; any failure rolls back the registration transition and both identities. This preserves the Borrower business identity versus BorrowerAccount authentication identity distinction: approval is deliberately not M06 activation or login.

### M06 — Borrower Authentication & Activation

- **Status:** Not Started
- **Branch:** `feature/m06-borrower-auth-activation`
- **Goal:** Activate approved borrowers and provide authentication fully isolated from Owner sessions.
- **Topics to Learn:** Activation codes; PIN hashing; borrower JWTs; refresh-token rotation; device registration; trusted devices; account and borrower isolation.
- **Deliverables:** Activation and borrower login APIs; hashed codes/PINs/tokens; device binding; refresh rotation; logout/revocation.
- **Tests / Quality Gates:** Code expiry/attempt limits; token reuse detection; device and account status checks; cross-borrower isolation; Owner-token rejection.
- **Completion Commit:** Pending
- **Merge Commit:** Pending
- **Notes / Lessons Learned:** Borrower identity always comes from authenticated session context.

## Phase C — Flutter Foundations

### M07 — Owner Flutter Application Foundation

- **Status:** Not Started
- **Branch:** `feature/m07-owner-flutter-foundation`
- **Goal:** Establish the separate Owner mobile client and connect it securely to the backend.
- **Topics to Learn:** Flutter architecture; Riverpod; Dio; GoRouter; secure storage; API integration; Owner session handling.
- **Deliverables:** Owner app scaffold; environment/API client; navigation; session state; login and protected-shell UI.
- **Tests / Quality Gates:** `flutter analyze`; unit/widget tests; navigation/session tests; API error handling; no financial calculations in the client.
- **Completion Commit:** Pending
- **Merge Commit:** Pending
- **Notes / Lessons Learned:** Pending

### M08 — Borrower Flutter Application Foundation

- **Status:** Not Started
- **Branch:** `feature/m08-borrower-flutter-foundation`
- **Goal:** Establish the isolated Borrower mobile client and activation/login experience.
- **Topics to Learn:** Separate Flutter applications; Borrower session state; activation UI; login UI; API integration; device identity.
- **Deliverables:** Borrower app scaffold; API/session layer; activation/login routes; secure token storage; device registration integration.
- **Tests / Quality Gates:** `flutter analyze`; unit/widget tests; activation/login state tests; session isolation; backend-authority review.
- **Completion Commit:** Pending
- **Merge Commit:** Pending
- **Notes / Lessons Learned:** Pending

## Phase D — Lending Domain

### M09 — Loan Domain & Calculator

- **Status:** Not Started
- **Branch:** `feature/m09-loan-domain-calculator`
- **Goal:** Implement the canonical Flexible Reducing-Balance model and calendar-safe schedules.
- **Topics to Learn:** Financial `Decimal` arithmetic; reducing balance; interest; Monthly and Twice-a-Month schedules; calendar-safe dates; quotes; regression tests.
- **Deliverables:** Canonical loan calculator; quote service; Monthly schedules; Twice-a-Month schedules on the 15th and last calendar day; domain tests.
- **Tests / Quality Gates:** Exact Decimal examples; rounding; month-end/leap-year cases; unsupported-model/frequency rejection; no client-authoritative calculations.
- **Completion Commit:** Pending
- **Merge Commit:** Pending
- **Notes / Lessons Learned:** Only Flexible Reducing-Balance is supported; no Interest-Only, flat-interest, balloon, fixed-principal, or Weekly modes.

### M10 — Borrower Loan Requests

- **Status:** Not Started
- **Branch:** `feature/m10-borrower-loan-requests`
- **Goal:** Let authenticated borrowers request loans and let the Owner review them safely.
- **Topics to Learn:** Request workflows; duplicate-pending protection; quote previews; Owner review; API authorization; cross-borrower isolation.
- **Deliverables:** Request persistence and endpoints; stateless quote preview; Owner approval/rejection flow; authorization policies.
- **Tests / Quality Gates:** Duplicate/race cases; borrower-context enforcement; Owner-only review; quote consistency; cross-borrower denial.
- **Completion Commit:** Pending
- **Merge Commit:** Pending
- **Notes / Lessons Learned:** Pending

### M11 — Loan Lifecycle

- **Status:** Not Started
- **Branch:** `feature/m11-loan-lifecycle`
- **Goal:** Model deliberate, auditable loan transitions from draft through terminal outcomes.
- **Topics to Learn:** State machines; authorization; idempotency; transaction boundaries; audit events; persisted states versus transition timestamps.
- **Deliverables:** Loan persistence; guarded Draft → Approved → Disbursed/Active → Paid/Cancelled/Defaulted transitions; idempotent disbursement; audit records.
- **Tests / Quality Gates:** Transition matrix; invalid transitions; concurrency/idempotency; transactional rollback; authorization; audit completeness.
- **Completion Commit:** Pending
- **Merge Commit:** Pending
- **Notes / Lessons Learned:** Exact persisted states versus event timestamps must be decided during this milestone.

### M12 — Flexible Payments

- **Status:** Not Started
- **Branch:** `feature/m12-flexible-payments`
- **Goal:** Record flexible payments with authoritative interest-first allocation and principal reduction.
- **Topics to Learn:** Payment recording; interest-first allocation; partial and early payments; late/on-time classification; balances; receipts; idempotency.
- **Deliverables:** Canonical payment allocation service; payment and receipt persistence; balance updates; reversal-ready audit data.
- **Tests / Quality Gates:** ₱2,000/₱200 examples for ₱200 and ₱700 payments; future interest on reduced principal; rounding; duplicate prevention; atomic rollback.
- **Completion Commit:** Pending
- **Merge Commit:** Pending
- **Notes / Lessons Learned:** Backend results are authoritative for allocation, balances, schedules, and totals.

## Phase E — Financial Infrastructure

### M13 — Double-Entry Accounting

- **Status:** Not Started
- **Branch:** `feature/m13-double-entry-accounting`
- **Goal:** Represent every financial movement with balanced, transactional journal entries.
- **Topics to Learn:** Chart of accounts; journals; debit/credit; balanced transactions; disbursement/payment accounting; reversals; financial integrity.
- **Deliverables:** Accounts and journal schema; posting service; disbursement/payment/reversal mappings; balance validation.
- **Tests / Quality Gates:** Debits equal credits; rollback on posting failure; immutable audit trail; reversal correctness; Decimal-only values.
- **Completion Commit:** Pending
- **Merge Commit:** Pending
- **Notes / Lessons Learned:** Pending

### M14 — Notifications & Outbox

- **Status:** Not Started
- **Branch:** `feature/m14-notifications-outbox`
- **Goal:** Reliably capture notification intent inside business transactions and deliver asynchronously.
- **Topics to Learn:** Transactional outbox; notification records; asynchronous boundaries; retries; deduplication; future push notifications.
- **Deliverables:** Outbox schema/service; delivery worker boundary; retry and deduplication policy; notification status APIs where appropriate.
- **Tests / Quality Gates:** Atomic domain/outbox writes; retry behavior; duplicate suppression; failure recovery; no external call inside financial transactions.
- **Completion Commit:** Pending
- **Merge Commit:** Pending
- **Notes / Lessons Learned:** Pending

### M15 — Reports & Dashboard

- **Status:** Not Started
- **Branch:** `feature/m15-reports-dashboard`
- **Goal:** Provide trustworthy portfolio, collection, and balance views for the Owner.
- **Topics to Learn:** Reporting queries; portfolio and collection metrics; balances; dashboard APIs; query performance.
- **Deliverables:** Reporting services/endpoints; dashboard summaries; documented metric definitions; performance-aware indexes.
- **Tests / Quality Gates:** Metric fixtures; reconciliation to authoritative records; access control; query-plan/performance review; Decimal serialization.
- **Completion Commit:** Pending
- **Merge Commit:** Pending
- **Notes / Lessons Learned:** Pending

## Phase F — Production Engineering

### M16 — Production Hardening

- **Status:** Not Started
- **Branch:** `feature/m16-production-hardening`
- **Goal:** Prepare the complete system for secure, observable, repeatable release and deployment.
- **Topics to Learn:** Security audit; rate limiting; audit and structured logging; health/readiness; backup concepts; environment configuration; release verification; CI/CD; deployment preparation.
- **Deliverables:** Hardening changes; CI quality gates; deployment configuration; operational runbooks; release checklist; backup/restore documentation.
- **Tests / Quality Gates:** Full regression; dependency/security review; migration rehearsal; configuration validation; CI pass; release smoke tests.
- **Completion Commit:** Pending
- **Merge Commit:** Pending
- **Notes / Lessons Learned:** Pending

## Product Rules That Apply to Every Milestone

- The business has exactly one Owner. Do not add staff roles or an RBAC matrix.
- Owner and Borrower identities, credentials, claims, and sessions remain separate.
- New V2 loans use only Flexible Reducing-Balance repayment.
- Supported frequencies are Monthly and Twice a Month; Twice a Month is calendar-based.
- The backend is authoritative for quotes, interest, schedules, balances, allocations, and totals.
- Financial values use Python `Decimal` and PostgreSQL `NUMERIC`, never binary floating-point.
- Local secrets stay ignored; no remote or push is introduced until explicitly planned.
