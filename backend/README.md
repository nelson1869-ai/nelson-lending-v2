# Lending Nelson V2 Backend

M06 adds secure Borrower activation and device-bound authentication to the Python 3.12 FastAPI
service. Flutter, lending, payment, accounting, and automated code delivery remain deferred.

## Local setup in WSL

Run these commands from `backend/`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

The committed `.env.example` contains local-development values only. The copied `.env` is ignored
by Git. Set an explicit production database URL; never reuse the example credentials outside a
local development database.

## Run and verify

```bash
./start.sh backend
pytest
ruff check .
ruff format --check .
mypy app
```

Running `./start.sh backend` from the repository root validates the backend environment, applies Alembic migrations, and launches the FastAPI service in the foreground on port 8000.

In separate terminals, launch the mobile clients:

```bash
# Terminal 2: Owner Mobile App
./start.sh owner

# Terminal 3: Borrower Mobile App
./start.sh borrower
```

To target a specific emulator/device or override the API URL for physical hardware:

```bash
FLUTTER_DEVICE_ID=emulator-5554 ./start.sh owner
API_BASE_URL=http://<LAN-IP>:8000 ./start.sh borrower
```

`GET /health/live` proves that the API process can answer without contacting PostgreSQL.
`GET /health/ready` runs `SELECT 1`; it returns HTTP 503 with a safe response when PostgreSQL is
unavailable. M02 unit tests replace that probe and are not real database integration tests.

## Alembic

Alembic reads the database URL from application settings instead of storing it in `alembic.ini`:

```bash
alembic heads
alembic current
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

M02 intentionally has no migration revisions. Persistent schema changes begin in M03 and must use
reviewed Alembic migrations.

Browser CORS is deferred. A future web client must use an explicit allow-list; wildcard origins
will not be enabled by default.

## Local PostgreSQL

M03 was developed against PostgreSQL 16 on loopback only:

```text
host:     127.0.0.1
port:     5432
role:     lending_v2
dev DB:   lending_nelson_v2
test DB:  lending_nelson_v2_test
```

The two databases are intentionally separate. Development migrations and schema inspection use
`lending_nelson_v2`; rollback-only integration tests use `lending_nelson_v2_test`. Never point
`TEST_DATABASE_URL` at development, production, or a remote host. The test guard accepts only the
exact test database name on a loopback host and skips safely when the variable is absent.

On this WSL workspace, the local server was already installed in a project-specific data
directory. M03 inspected both named databases before replacing their old, pre-roadmap schema with
clean databases owned by `lending_v2`. On another workstation, install PostgreSQL locally, create
that role, then create only the two project databases:

```bash
createdb -h /tmp -O lending_v2 lending_nelson_v2
createdb -h /tmp -O lending_v2 lending_nelson_v2_test
cp .env.example .env
```

Edit the ignored `.env` with actual local credentials. Keep `.env.example` generic and never
commit `.env`.

## Migration workflow

Apply and inspect the schema from `backend/`:

```bash
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
.venv/bin/python -m alembic heads
.venv/bin/python -m alembic check
```

Test a reversible migration on the development database and always finish at head:

```bash
.venv/bin/python -m alembic downgrade base
.venv/bin/python -m alembic upgrade head
```

Inspect the local schema without displaying credentials:

```bash
psql -h 127.0.0.1 -p 5432 -U lending_v2 -d lending_nelson_v2
```

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

SELECT * FROM alembic_version;
SELECT COUNT(*) FROM owner_users;
```

Run unit tests without infrastructure, or configure the exact test URL and run real PostgreSQL
tests:

```bash
.venv/bin/python -m pytest -m "not integration"
.venv/bin/python -m pytest -m integration -v
.venv/bin/python -m pytest
```

The schema keeps the Borrower business record separate from its app account. Borrower deletion is
restricted while an account exists; deleting an account cascades to its devices and hashed refresh
tokens, and deleting a device cascades its tokens.

## Owner authentication

Set these values in the ignored `.env` file:

```text
JWT_SECRET_KEY=<random secret of at least 32 characters>
JWT_ALGORITHM=HS256
OWNER_ACCESS_TOKEN_MINUTES=15
OWNER_REFRESH_TOKEN_DAYS=30
```

Generate a local secret without saving it to shell history, then place the result directly in
`.env` without committing it:

```bash
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Staging and production reject the committed development placeholder. Bootstrap the one Owner from
an interactive terminal; the password is prompted twice without echo and must contain at least 12
characters:

```bash
.venv/bin/python scripts/bootstrap_owner.py --username nelson
```

Bootstrap refuses when any Owner row already exists. Usernames are trimmed and lowercased;
passwords are never trimmed. Login failures do not reveal whether the username, password, or
account state failed.

The versioned endpoints are:

```text
POST /api/v1/owner/auth/login
POST /api/v1/owner/auth/refresh
POST /api/v1/owner/auth/logout
GET  /api/v1/owner/auth/me
```

Example request bodies use camelCase:

```json
{"username": "nelson", "password": "<entered securely>"}
```

```json
{"refreshToken": "<redacted>"}
```

Login and refresh return a short-lived HS256 Owner access JWT plus a random opaque refresh token.
Only the SHA-256 refresh-token hash is stored because the token itself is a high-entropy random
secret; passwords instead use salted Argon2id. Refresh rotates the session under a row lock, so
the old token cannot be reused. Logout revokes the submitted refresh session; an already-issued
access JWT remains valid only until its short expiration. Password recovery, MFA, distributed
login throttling, and Borrower authentication are intentionally deferred.

## Borrower registration and Owner review

Public registration accepts names, a generic national ID, Philippine mobile number, address, and
past date of birth. Mobile inputs `09XXXXXXXXX`, `639XXXXXXXXX`, and `+639XXXXXXXXX` normalize to
`+639XXXXXXXXX`; national IDs are trimmed and uppercased. Duplicate pending or existing identities
return a generic conflict without revealing another Borrower's information.

```text
POST /api/v1/borrower/registrations
GET  /api/v1/owner/borrower-registrations?limit=50&offset=0
GET  /api/v1/owner/borrower-registrations/<REGISTRATION_ID>
POST /api/v1/owner/borrower-registrations/<REGISTRATION_ID>/approve
POST /api/v1/owner/borrower-registrations/<REGISTRATION_ID>/reject
```

The four Owner endpoints require the existing Owner access token:

```text
Authorization: Bearer <OWNER_ACCESS_TOKEN>
```

Safe conceptual requests:

```json
{
  "firstName": "Juan",
  "lastName": "Dela Cruz",
  "nationalId": "SYNTHETIC-ID-123",
  "phoneNumber": "09171234567",
  "address": "Bacolod City",
  "dateOfBirth": "1995-05-10"
}
```

```json
{"reason": "Unable to verify submitted information."}
```

Approval locks the pending request and atomically creates `Borrower(status=active)`, creates
`BorrowerAccount(account_status=approved, pin_hash=NULL)`, records the reviewer/time, and links the
resulting Borrower. Rejection records a bounded reason without creating either identity. Both
decisions are terminal and single-use. Registration approval is not mobile-account activation;
M05 creates no PIN, activation code, device, Borrower JWT, or Borrower session.

## Borrower activation and authentication

Configure dedicated random secrets for activation-code and device-identifier HMACs. Production
and staging reject the documented local placeholders. Defaults are a 15-minute activation code,
five activation attempts, a 15-minute Borrower access JWT, and a 30-day refresh session.

```text
POST /api/v1/owner/borrowers/<BORROWER_ID>/activation-code
POST /api/v1/borrower/auth/activate
POST /api/v1/borrower/auth/login
GET  /api/v1/borrower/auth/me
POST /api/v1/borrower/auth/refresh
POST /api/v1/borrower/auth/logout
```

The Owner endpoint returns the six-digit code once for manual delivery until notification
infrastructure exists. The database stores only keyed HMAC code/device digests, Argon2id PIN
hashes, and SHA-256 hashes of high-entropy opaque refresh tokens. Never log any plaintext value.

Approval is not activation; activation is not login. Activation consumes the code and establishes
the six-digit PIN. Login then creates an untrusted device record, a short-lived
`borrower_access` JWT, and a device-bound refresh session. Refresh rotates under a row lock, and
logout revokes refresh capability while an existing access JWT expires naturally. Owner and
Borrower access tokens are deliberately not interchangeable. PIN recovery, distributed login
throttling, trust approval, and automated code delivery are future security decisions.
