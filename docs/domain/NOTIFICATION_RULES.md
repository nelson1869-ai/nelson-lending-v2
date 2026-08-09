# Lending Nelson V2 — Notification and Outbox Rules

## 1. Reliability Boundary

Notification intent is part of the business transaction that caused it. Loan-request review,
loan disbursement, and payment posting therefore write their domain state and required
`notification_outbox` row in one PostgreSQL transaction. The canonical enqueue service flushes
but never commits and never invokes a delivery provider. Provider availability cannot block or
roll back an otherwise valid business operation after commit.

The dispatcher is an explicit worker boundary. It is invoked separately from FastAPI requests
and processes a bounded batch of committed intents.

## 2. Supported Delivery

M14 supports only the `in_app` channel. SMS, email, push providers, and destination-snapshot
semantics are deferred. The provider protocol isolates dispatcher policy from delivery details.
In-app delivery creates an immutable `notifications` row; only `read_at` may change.

Supported templates are centralized and render plain text from minimal event snapshots:

- `borrower_registration_approved`
- `loan_request_submitted`
- `loan_request_approved`
- `loan_request_rejected`
- `loan_disbursed`
- `payment_received`

Payloads contain only values needed to render the historical event. ORM objects, credentials,
activation secrets, PINs, tokens, provider credentials, and accounting internals are prohibited.
Every persisted payload includes `schema_version: 1`. The enqueue service validates the required
string fields for the selected template and assigns the version; callers cannot override it.
Dispatch rejects unsupported versions or malformed payloads visibly, records a sanitized failure,
and applies normal retry/dead-letter policy. Adding a template requires one central template
constant, its event mapping, its required-field contract, renderer coverage, and an atomic business
integration test.

## 3. Identity, Privacy, and Visibility

Recipients are represented by durable `recipient_type` (`borrower` or `owner`) and
`recipient_id`. Borrower APIs derive identity from the authenticated Borrower context and query
both fields, so identifiers supplied by a client never authorize access. Borrower responses omit
payloads, retry state, error details, idempotency keys, and provider internals.

Owner outbox endpoints are operational diagnostics protected by Owner authentication. They show
delivery metadata and sanitized errors but not the JSON payload. There is no delete endpoint.

## 4. Idempotency and Delivery Deduplication

The enqueue service derives a deterministic SHA-256 idempotency key from event type, aggregate
ID, recipient ID, template key, and channel. PostgreSQL uniquely constrains that key. A payment
idempotency replay returns before business mutation and therefore retains exactly one Payment,
one accounting journal, and one notification intent.

The delivered `notifications.source_outbox_id` is also unique. If delivery outcome is uncertain,
retrying the same outbox row cannot create a second visible in-app notification.

## 5. Status, Retry, and Dead Letter

Outbox status is constrained to `pending`, `failed`, `delivered`, or `dead_letter`. Each eligible
attempt increments `attempt_count` and records `last_attempt_at`. Failure records a fixed,
sanitized summary and schedules bounded exponential backoff starting at 60 seconds and capped at
one hour. The default maximum is five attempts, and the supported range is 1 through 20, enforced
by both the service and database. Exhausted intents become `dead_letter`, retain
their history, and receive no further automatic attempts.

An Owner may reset a dead-letter record to pending through the manual retry endpoint. This resets
retry metadata on the existing intent; it does not create or edit a business event.

## 6. Concurrency and Recovery

The dispatcher selects at most 50 eligible rows by default using PostgreSQL
`FOR UPDATE SKIP LOCKED`. The in-app provider performs no network operation, so delivery and the
outbox status update remain in the same short worker transaction. Concurrent workers skip rows
locked by another worker. A crash rolls the transaction back and releases the row lock, leaving
the committed intent eligible for a later attempt rather than stuck in a `processing` state.

The in-app path is **at-least-once attempted**. Since notification insertion and acknowledgement
share one transaction, a crash rolls both back. If a future external provider succeeds before the
acknowledgement is committed and the process then crashes, the provider can be invoked again and
must use an idempotency key derived from the outbox ID. M14 exposes the async dispatcher function
for a future scheduler or dedicated worker process; FastAPI does not start a hidden background
thread.

Future external providers must not hold database locks across slow network requests. Their claim
and stale-claim recovery design requires a separate reviewed milestone decision.
