# Lending Nelson V2 Backend

M03 adds the first persistent identity and business-settings schema to the Python 3.12 FastAPI
service. It deliberately contains no authentication behavior, lending, payment, or accounting
features.

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
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pytest
ruff check .
ruff format --check .
mypy app
./verify.sh
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
tokens, and deleting a device cascades its tokens. Authentication, token issuance, hashing, and
Owner bootstrap remain later milestones.
