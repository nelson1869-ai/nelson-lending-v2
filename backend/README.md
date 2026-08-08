# Lending Nelson V2 Backend

M02 provides the infrastructure for a Python 3.12 FastAPI service. It deliberately contains no
identity, authentication, lending, payment, or accounting features.

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
