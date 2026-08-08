#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
PYTHON_BIN="${BACKEND_DIR}/.venv/bin/python"

echo "=========================================="
echo " Starting Lending Nelson V2 Application"
echo "=========================================="

echo "[1/4] Stopping existing processes on port 8000..."
if command -v fuser >/dev/null 2>&1; then
    fuser -k 8000/tcp >/dev/null 2>&1 || true
fi

pkill -f "uvicorn app.main:app" >/dev/null 2>&1 || true
sleep 1

if [ ! -x "$PYTHON_BIN" ]; then
    echo "ERROR: Backend virtualenv not found at ${PYTHON_BIN}"
    echo "Please set up backend/.venv first according to backend/README.md"
    exit 1
fi

echo "[2/4] Applying Alembic database migrations..."
cd "$BACKEND_DIR"
"$PYTHON_BIN" -m alembic upgrade head

echo "[3/4] Starting FastAPI backend on http://0.0.0.0:8000..."
nohup "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > uvicorn.log 2>&1 &
BACKEND_PID=$!

echo "Backend started with PID: ${BACKEND_PID} (Logs: ${BACKEND_DIR}/uvicorn.log)"

echo "[4/4] Verifying backend liveness..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:8000/health/live >/dev/null; then
        echo "✓ Backend is live and responding at http://127.0.0.1:8000"
        break
    fi
    sleep 1
done

echo ""
echo "=========================================="
echo " Lending Nelson V2 Ready!"
echo " - Backend API:  http://127.0.0.1:8000/api/v1"
echo " - Health Probe: http://127.0.0.1:8000/health/ready"
echo " - Owner App:    cd apps/owner_mobile && flutter run"
echo "=========================================="
