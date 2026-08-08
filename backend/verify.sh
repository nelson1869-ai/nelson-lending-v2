#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python_bin=".venv/bin/python"

if [[ ! -x "$python_bin" ]]; then
  echo "Missing backend/.venv. Follow backend/README.md before running verification." >&2
  exit 1
fi

echo "==> App import"
"$python_bin" -c "from app.main import app; print('Backend import OK')"

echo "==> pytest"
"$python_bin" -m pytest

echo "==> Ruff lint"
"$python_bin" -m ruff check .

echo "==> Ruff format"
"$python_bin" -m ruff format --check .

echo "==> mypy"
"$python_bin" -m mypy app

echo "==> Alembic heads"
"$python_bin" -m alembic heads

echo "==> Backend verification complete"
