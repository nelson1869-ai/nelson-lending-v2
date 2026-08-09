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

- **Status:** Completed
- **Branch:** `feature/m06-borrower-auth`
- **Goal:** Activate approved borrowers and provide authentication fully isolated from Owner sessions.
- **Topics to Learn:** Activation codes; PIN hashing; borrower JWTs; refresh-token rotation; device registration; trusted devices; account and borrower isolation.
- **Deliverables:** Added HMAC-protected six-digit activation codes with Owner-only issuance, expiry, reissue revocation, attempt limits, and single use; six-digit Argon2id PIN activation; typed Borrower access JWTs; canonical Borrower auth context; hashed device identifiers; device-bound opaque refresh sessions with row-locked rotation and logout.
- **Tests / Quality Gates:** FastAPI import, Ruff, Ruff format, and mypy passed; full pytest passed 119 tests; real PostgreSQL M06 lifecycle passed 24 tests; activation and refresh concurrency each allowed exactly one winner; `0004_borrower_activation` downgrade/re-upgrade and fresh-install chains passed; Alembic reports one head and no drift; redacted local API lifecycle smoke passed with exact cleanup.
- **Completion Commits:**
  - `ab00e61` — `docs: align m06 learning branch`
  - `f676e8f` — `feat(auth): add borrower activation foundation`
  - `83cec1c` — `feat(auth): implement borrower authentication`
  - `2b03531` — `test(auth): cover borrower activation and session lifecycle`
  - `01d3f8e` — `docs: mark m06 ready for review`
- **Merge Commit:** `456f53a148b7a6f7ec8365751c4f06b9ee073ac1` — `merge: complete m06 borrower authentication`
- **Notes / Lessons Learned:** Registration approval is distinct from activation, and activation is distinct from authentication. Human PIN secrets use Argon2id hashing, while low-entropy 6-digit activation codes use account-bound HMAC hashes at rest, and high-entropy refresh tokens use SHA-256 lookup hashes. Owner access JWTs and Borrower access JWTs enforce `token_type` domain isolation and reject one another. `SELECT FOR UPDATE` protects against concurrent activation attempts and concurrent refresh token reuse. Device identifier hashing and device-bound refresh sessions enable safe multi-device token rotation. Generic authentication failure responses prevent username/phone enumeration, and raw secrets are minimized in logs and database storage.

## Phase C — Flutter Foundations

### M07 — Owner Flutter Application Foundation

- **Status:** Completed
- **Branch:** `feature/m07-owner-flutter-foundation`
- **Goal:** Establish the separate Owner mobile client and connect it securely to the backend.
- **Topics to Learn:** Flutter architecture; Riverpod; Dio; GoRouter; secure storage; API integration; Owner session handling.
- **Deliverables:** Owner app scaffold at `apps/owner_mobile`; environment/API client; navigation; session state; login and protected-shell UI.
- **Tests / Quality Gates:** `flutter analyze` passed; 23 unit/widget/router/auth tests passed in `flutter test`; `dart format` passed; backend regression quality gates passed.
- **Educational Commits:**
  - `chore(owner): scaffold flutter application`
  - `feat(owner): add app architecture and navigation`
  - `feat(owner): add api client and secure session storage`
  - `feat(owner): implement owner authentication flow`
  - `test(owner): cover owner app foundation`
  - `fix(owner): propagate expired sessions to auth state`
  - `chore(dev): add reliable local application launcher`
- **Completion Commit:** `44e7007376b02e30c982491e4b7bddc5b15a7f39`
- **Merge Commit:** `1ed1b6b8e8be380474bf3356ac9f8c0cbe899c6b`
- **Notes / Lessons Learned:** The Owner mobile application uses a clean feature-oriented architecture with Flutter Riverpod for state management, GoRouter for declarative protected routing, Dio for HTTP communication, and FlutterSecureStorage for sensitive session persistence. Short-lived access JWTs are held in memory, while high-entropy refresh tokens are securely stored and rotated atomically on refresh. Single-flight refresh prevents concurrency race conditions. The app strictly enforces the single-Owner business model without staff roles or RBAC matrices and isolates Owner authentication from Borrower identity.

### M08 — Borrower Flutter Application Foundation

- **Status:** Completed
- **Branch:** `feature/m08-borrower-flutter-foundation`
- **Goal:** Establish the isolated Borrower mobile client and activation/login experience.
- **Topics to Learn:** Separate Flutter applications; Borrower session state; activation UI; login UI; API integration; device identity.
- **Deliverables:** Borrower app scaffold at `apps/borrower_mobile`; API/session layer; activation/login routes; secure token storage; device registration integration.
- **Tests / Quality Gates:** `flutter analyze` passed; 25 unit/widget/router/auth tests passed in `flutter test`; `dart format` passed; debug APK built (`build\app\outputs\flutter-apk\app-debug.apk`); Owner Flutter regression passed (23 tests); backend regression quality gates passed (119 pytest, mypy, Ruff lint & format, Alembic 0004_borrower_activation current/head, Alembic drift check clean).
- **Educational Commits:**
  - `96df8e0` — `chore(borrower): scaffold flutter application`
  - `f3c99ed` — `feat(borrower): add app architecture and navigation`
  - `7b1ab24` — `feat(borrower): add api client and secure device session`
  - `f7ab814` — `chore(dev): support borrower app launcher in start.sh`
  - `74a80f8` — `docs: mark m08 ready for review`
  - `16928aa` — `test(borrower): cover borrower app foundation`
  - `c0a2439` — `fix(borrower): ensure local logout on network failure`
  - `9e5c279` — `chore(dev): separate backend and mobile launcher targets`
- **Completion Commit:** `9e5c279bf7f348216d88a58ae37b507084441361` — `chore(dev): separate backend and mobile launcher targets`
- **Merge Commit:** `4e47f4ff14740914269a32be603e074eb391465b` — `merge: complete m08 borrower flutter foundation`
- **Notes / Lessons Learned:** The Borrower mobile application is built at `apps/borrower_mobile` as a separate Flutter project. It communicates exclusively with Borrower endpoints (`/api/v1/borrower/...`), maintaining strict identity, credential, and session isolation from Owner authentication. Access tokens are kept in memory, while high-entropy refresh tokens and stable app installation UUIDs (`borrower_device_identifier`) are securely persisted. Single-flight refresh prevents token rotation race conditions and automatically redirects to login on session expiration. The app provides public registration submission, activation code & 6-digit PIN verification, device-bound login, session restoration, and authenticated home profile display.

## Phase D — Lending Domain

### M09 — Loan Domain & Calculator

- **Status:** Completed
- **Branch:** `feature/m09-loan-domain-calculator`
- **Goal:** Implement the canonical Flexible Reducing-Balance model and calendar-safe schedules.
- **Topics to Learn:** Financial `Decimal` arithmetic; reducing balance; interest; Monthly and Twice-a-Month schedules; calendar-safe dates; quotes; regression tests.
- **Deliverables:** Loan domain model & `0005_loans` migration; canonical Flexible Reducing-Balance calculator; pure flexible payment allocation rules; Owner loan quote API (`POST /api/v1/owner/loans/quote`); financial unit & integration regression tests.
- **Tests / Quality Gates:** `Backend import OK`; full pytest 149 passed (unit + integration); Ruff lint passed; Ruff format checked 71 files; mypy passed 45 application source files; `0005_loans` current/head; Alembic drift check clean; Owner & Borrower Flutter apps regression clean.
- **Educational Commits:**
  - `3d7b34a` — `feat(loans): add loan domain persistence`
  - `9bc29a7` — `feat(loans): implement reducing balance calculator`
  - `8720254` — `feat(loans): add flexible payment allocation rules`
  - `bb7ed9f` — `feat(loans): expose owner loan quote api`
  - `0811d3d` — `test(loans): cover financial calculator regressions`
  - `e29463f` — `fix(loans): defer lifecycle persistence decisions`
  - `7889c32` — `fix(loans): validate twice-monthly first due date`
  - `e9f3fb0` — `docs: record m09 review fixes`
  - `ae2174f` — `chore(loans): format twice-monthly validation code`
- **Completion Commit:** `docs: record m09 completion`
- **Merge Commit:** `c2840540d246f38a9cb2adfb9db9b8eee72d244f`
- **Notes / Lessons Learned:** The backend is the sole authoritative calculator for loans. New V2 loans support exclusively the Flexible Reducing-Balance model with Monthly or Twice-a-Month (15th and month-end) payment frequencies. All financial arithmetic uses Python `Decimal` with explicit `ROUND_HALF_UP` centavo quantization. Monthly schedules handle month-end re-expansion (e.g. Jan 31 -> Feb 28 -> Mar 31) and leap years deterministically. Twice-a-Month `firstDueDate` is strictly validated to be either the 15th or last calendar day of the month, returning HTTP 422 for invalid dates rather than silently transforming them. Durable loan lifecycle states and transition timestamps are deferred to M11. The Owner loan quote API is stateless and does not persist loan records.

### M10 — Borrower Loan Requests

- **Status:** Completed
- **Branch:** `feature/m10-borrower-loan-requests`
- **Goal:** Let authenticated borrowers request loans and let the Owner review them safely.
- **Topics to Learn:** Request workflows; duplicate-pending protection; quote previews; Owner review; API authorization; cross-borrower isolation.
- **Deliverables:** Request persistence and endpoints; stateless quote preview; Owner approval/rejection flow; authorization policies; borrower privacy protection; server-controlled estimate rate.
- **Tests / Quality Gates:** Duplicate/race cases; borrower-context enforcement; Owner-only review; quote consistency; cross-borrower denial; privacy response boundary tests; rate-control snapshot tests.
- **Completion Commit:** `docs: record m10 completion`
- **Merge Commit:** `399061e0088b5f3e4b8ad6a2b3d2dba8eb7bf4ed`
- **Notes / Lessons Learned:** Implemented borrower loan request persistence (`loan_requests` table with partial unique index `ix_loan_requests_one_pending_per_borrower` enforcing max 1 pending request per borrower) and review API. Borrower identity is resolved strictly from authenticated session context. Added borrower-safe response boundary (`BorrowerLoanRequestResponse`), ensuring internal Owner review metadata (`owner_note`, `reviewed_by_owner_id`) never leaks across borrower endpoints. Borrower quote preview and request submission derive the interest rate server-side from `BusinessSetting.default_monthly_estimate_rate` (handling `NULL` safely with HTTP 400), snapshotting the exact rate used into `requested_monthly_rate` so subsequent rate setting changes do not alter historical request terms. Implemented Owner list, detail, and approval/rejection endpoints protected with row locking (`SELECT ... FOR UPDATE`). Owner approval sets request status to `approved` ONLY and does NOT create a `Loan` instance, disburse funds, or post accounting entries (deferred to M11). Delivered Borrower Flutter loan request workflow and Owner Flutter review workflow with full widget, unit, integration, and build quality gates passed. Initial feature commits: `c7f166b`, `e19edd9`, `e9d5e5f`, `17efa38`. Review fix commits: `08ee76d`, `41c4189`, `4d82298`.

### M11 — Loan Lifecycle

- **Status:** Completed
- **Branch:** `feature/m11-loan-lifecycle`
- **Goal:** Model deliberate, auditable loan transitions from draft through terminal outcomes.
- **Topics to Learn:** State machines; authorization; idempotency; transaction boundaries; audit events; persisted states versus transition timestamps.
- **Deliverables:** Loan persistence; guarded Draft → Approved → Disbursed/Active → Paid/Cancelled/Defaulted transitions; idempotent disbursement; audit records.
- **Tests / Quality Gates:** Transition matrix; invalid transitions; concurrency/idempotency; transactional rollback; authorization; audit completeness.
- **Completion Commits:**
  - `58a73c7` — `feat(loans): add durable loan lifecycle schema`
  - `46e4f43` — `feat(loans): convert approved requests into loans`
  - `9b54a32` — `test(loans): cover loan lifecycle transitions`
  - `6354a8a` — `feat(owner_mobile): add loan contract lifecycle experiences`
  - `a166d25` — `feat(borrower_mobile): add borrower loan contracts view`
  - `9057a85` — `docs: mark m11 ready for review`
  - `2f6dab3` — `fix(loans): enforce loan request source invariant`
  - `efe16e0` — `test(loans): cover loan source persistence invariant`
  - `a2bdbe6` — `fix(launcher): enforce LF line endings on shell scripts`
- **Merge Commit:** `5e9f4548d547eeb3e291c99a88647bec98069aca` — `merge: complete m11 loan lifecycle`
- **Notes / Lessons Learned:** Established durable `Loan` entity (`loans` table) linked 1:1 with approved `LoanRequest` via `loan_request_id` NOT NULL FK and unique index `ix_loans_loan_request_id`. Implemented explicit loan state machine supporting `pending_disbursement` (initial state upon request conversion), `active` (set when Owner confirms disbursement), `cancelled` (set when Owner cancels before disbursement), `paid`, and `defaulted` (schema-supported for future payment milestones). Enforced strict state transition matrix and protected conversion, disbursement, and cancellation endpoints with pessimistic row-locking (`SELECT ... FOR UPDATE OF loans`). Preserved financial precision using `Decimal` / `NUMERIC(14,2)` and `NUMERIC(12,10)` rates. Implemented Owner loan list/detail views (with quote preview) and Borrower own-loan list/detail views with strict cross-borrower and role authorization isolation. Delivered Flutter loan lifecycle experiences for both `owner_mobile` (list, detail with disbursement/cancellation actions, request-to-loan conversion) and `borrower_mobile` (my loans list and contract detail with schedule preview). Passed full quality gates (Alembic migration 0007 upgrade/downgrade, 173 backend tests, Ruff, mypy, Flutter analyze 0 issues, Flutter test suites, and APK builds). LF shell-script normalization (`.gitattributes`) prevents WSL shebang failures upon checkout.



### M12 — Flexible Payments

- **Status:** Completed
- **Branch:** `feature/m12-flexible-payments`
- **Goal:** Record flexible payments with authoritative interest-first allocation and principal reduction.
- **Topics to Learn:** Payment recording; interest-first allocation; partial and early payments; late/on-time classification; balances; receipts; idempotency.
- **Deliverables:** Canonical payment allocation service; payment and receipt persistence; balance updates; reversal-ready audit data.
- **Tests / Quality Gates:** ₱2,000/₱200 examples for ₱200 and ₱700 payments; future interest on reduced principal; rounding; duplicate prevention; atomic rollback.
- **Completion Commit:** `30edb15999ad5241533cfe47db0103802dc019e1`
- **Merge Commit:** `6b65adb25c689b3a420beada07daf748c66c9406`
- **Notes / Lessons Learned:** Payment posting is an immutable financial operation. Payments allocate strictly: accrued interest → outstanding principal → unapplied credit. Interest accrues by contractual due date arrival (`payment_date >= next_interest_due_date`), NOT per payment request event. Multiple payments within the same contractual period do not double-accrue interest. Future period interest is calculated strictly on reduced outstanding principal. Early payoff satisfies remaining principal and current accrued interest, excluding future unaccrued scheduled interest. `payment_date` is the business-effective date (must not be in the future, predate disbursement, or be backdated). `posted_at` is the server recording timestamp. Payment posting requires mandatory `Idempotency-Key` passed as an HTTP header (key in JSON body is forbidden via `extra="forbid"`). Retries with identical key and payload return `200 OK` with original payment without double-mutating balances or status. Retries with conflicting payload return `409 Conflict`. Database composite unique index `uq_payments_loan_idempotency_key` and pessimistic row-locking (`SELECT ... FOR UPDATE`) protect against concurrent race conditions. Borrower payment responses hide Owner internal notes and operational `idempotency_key` metadata. Payment posting is decoupled from general-ledger accounting (owned by M13).

## Phase E — Financial Infrastructure

### M13 — Double-Entry Accounting

- **Status:** Completed
- **Branch:** `feature/m13-double-entry-accounting`
- **Goal:** Represent every financial movement with balanced, transactional journal entries.
- **Topics to Learn:** Chart of accounts; journals; debit/credit; balanced transactions; disbursement/payment accounting; reversals; financial integrity.
- **Deliverables:**
  - Standard Chart of Accounts (`1000 Cash`, `1100 Loans Receivable`, `2000 Customer Credit`, `4000 Interest Income`).
  - PostgreSQL ORM models (`Account`, `JournalTransaction`, `JournalEntry`) with database check constraints (`ck_account_type`, `ck_account_normal_balance`, `uq_journal_transactions_source`, `ck_no_self_reversal`, `ck_entry_non_negative`, `ck_entry_one_sided`).
  - Canonical accounting service (`post_journal`, `post_disbursement_journal`, `post_payment_journal`, `reverse_journal`, `list_accounts`, `list_journals`, `get_journal_detail`).
  - Atomic transaction integration into `disburse_loan` and `post_payment`.
  - Owner REST APIs under `/api/v1/owner/accounting`.
  - Owner Mobile Flutter UI for General Ledger & Chart of Accounts.
  - Reversible Alembic migration `0011_accounting.py`.
  - Comprehensive unit and integration test suite.
  - Domain documentation (`docs/domain/ACCOUNTING_RULES.md`).
- **Tests / Quality Gates:**
  - Backend `pytest`: 225 passed (100% pass rate).
  - `ruff check`: 0 errors.
  - `ruff format`: 106 files clean.
  - `mypy`: 0 issues across 62 source files.
  - `alembic current` & `heads`: `0011_accounting (head)`.
  - `alembic check`: No changes in schema detected (zero drift).
  - Owner Mobile `flutter analyze`: 0 issues found.
  - Owner Mobile `flutter test`: 24 passed (100% pass rate).
  - Owner Mobile debug APK: Built cleanly (`build\app\outputs\flutter-apk\app-debug.apk`).
  - Borrower Mobile `flutter analyze`: 0 issues found.
  - Borrower Mobile `flutter test`: 27 passed (100% pass rate).
  - Borrower Mobile debug APK: Built cleanly (`build\app\outputs\flutter-apk\app-debug.apk`).
- **Merge Commit:** `ff124b6a1a30df66b324539cd0893db9e4759de9`
- **Educational Commits:**
  - `47e68c2`: feat(accounting): add double-entry models, schema migration, and canonical service
  - `76e2e90`: feat(accounting): integrate accounting posting with disbursements and payments
  - `0612682`: test(accounting): add double-entry models, service, disbursement, payment, and API tests
  - `4d9f22a`: feat(owner_mobile): add double-entry general ledger UI and API client
  - `ff06dbf`: docs(roadmap): mark m13 ready for review
  - `2045eb4`: fix(accounting): protect business-event journals from generic reversal
  - `43e23d6`: test(accounting): cover protected business-event reversal integrity
  - `47137b1`: docs(accounting): document business-event reversal boundaries
- **Notes / Lessons Learned:** Double-entry accounting ensures append-only financial audit trails where every transaction satisfies `SUM(debit) == SUM(credit)` using Python `Decimal` and PostgreSQL `NUMERIC`. Loan disbursements post `DR 1100 Loans Receivable` / `CR 1000 Cash`. Payment allocation uses authoritative M12 backend allocation (`Interest Income` for interest, `Loans Receivable` for principal, `Customer Credit` liability for excess unapplied credit). Every payment and disbursement mutation is committed atomically with its journal transaction. Replaying idempotent payments does not duplicate journals or balances. Automatic business events (`loan_disbursement` and `payment`) cannot be independently reversed via generic accounting reversal endpoints (`BusinessEventJournalReversalError` / `HTTP 409 Conflict`), ensuring business domain state and accounting general ledger never diverge. Reversing a financial business event requires an authoritative business-domain workflow that updates both domain entities and ledgers atomically. Borrowers are strictly forbidden from accessing accounting records.

### M14 — Notifications & Outbox

- **Status:** Completed
- **Branch:** `feature/m14-notifications-outbox`
- **Goal:** Reliably capture notification intent inside business transactions and deliver asynchronously.
- **Topics to Learn:** Transactional outbox; notification records; asynchronous boundaries; retries; deduplication; future push notifications.
- **Deliverables:** Outbox schema/service; delivery worker boundary; retry and deduplication policy; notification status APIs where appropriate.
- **Tests / Quality Gates:** Atomic domain/outbox writes; retry behavior; duplicate suppression; failure recovery; no external call inside financial transactions.
- **Verified Results:**
  - Backend `pytest`: 254 passed (100% pass rate).
  - Focused notification tests: 29 passed (100% pass rate).
  - PostgreSQL integration tests include two-session `FOR UPDATE SKIP LOCKED` coverage.
  - Fresh empty PostgreSQL migration chain: base through `0012_notifications_outbox` passed; M14 downgrade/re-upgrade and Alembic drift check passed.
  - `ruff check`: 0 errors; `ruff format`: 120 files clean.
  - `mypy`: 0 issues across 70 source files.
  - Owner Mobile: 27 tests passed; analyze, format, and debug APK build passed.
  - Borrower Mobile: 28 tests passed; analyze, format, and debug APK build passed.
- **Educational Commits:**
  - `2f477fa`: feat(notifications): add transactional outbox and notification models and schema migration
  - `1adae52`: feat(notifications): implement canonical enqueue service, renderer, and in-app provider
  - `c0274e5`: feat(notifications): integrate transactional outbox into business workflows
  - `0a67337`: feat(notifications): add outbox dispatcher with locking, backoff, and dead-letter handling
  - `258e898`: feat(notifications): add borrower notification and owner outbox operational APIs
  - `c3f0594`: feat(borrower_mobile): add notification inbox experience
  - `bd4c2bc`: test(notifications): harden outbox reliability and privacy
  - `bc2951a`: feat(mobile): wire notification views and versioned feature APIs
  - `3a4561f`: docs(notifications): define outbox delivery rules
  - `a7d587d`: docs: mark m14 ready for review
  - `d0458d2`: chore(notifications): normalize loan service formatting
  - `538da87`: fix(owner_mobile): parse accounting api response fields
  - `3943d84`: fix(notifications): validate versioned outbox payloads
- **Merge Commit:** `bb478a5d58faecec6e6f8741e95c69e5fe450591`
- **Notes / Lessons Learned:** Business mutations and notification intents share one PostgreSQL transaction while delivery remains outside FastAPI business requests. The in-app provider writes immutable user-visible notifications, and deterministic SHA-256 intent keys plus a unique outbox source prevent duplicate intents and visible deliveries. Versioned payload contracts reject malformed historical events instead of rendering misleading defaults. Bounded exponential retry terminates in durable dead-letter state; Owner operations can inspect and safely reset dead letters. PostgreSQL `FOR UPDATE SKIP LOCKED` allows concurrent short-lived in-app dispatcher transactions, while rollback releases claims after worker crashes. Delivery is at-least-once attempted and visible in-app delivery remains idempotent. Borrower inbox access is derived exclusively from the authenticated Borrower identity. M14 also corrected versioned mobile feature API paths and Owner accounting response parsing after device screenshots exposed client integration defects.

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
