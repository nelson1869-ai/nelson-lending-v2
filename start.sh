#!/usr/bin/env bash
set -euo pipefail

# 1. Project paths resolution
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
OWNER_APP_DIR="${PROJECT_ROOT}/apps/owner_mobile"
PYTHON_BIN="${BACKEND_DIR}/.venv/bin/python"

BACKEND_PID=""

# Cleanup trap to ensure background backend process is stopped on exit or interrupt
cleanup() {
    if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo ""
        echo "Stopping background FastAPI process (PID: ${BACKEND_PID})..."
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# Helper function to invoke Flutter across WSL / Windows seamlessly
run_flutter() {
    if command -v cmd.exe >/dev/null 2>&1; then
        cmd.exe /C "flutter $*"
    elif command -v flutter >/dev/null 2>&1; then
        flutter "$@"
    elif command -v flutter.bat >/dev/null 2>&1; then
        flutter.bat "$@"
    else
        echo "ERROR: Flutter executable not found." >&2
        return 1
    fi
}

echo "=================================================="
echo " Lending Nelson V2 — Local Development Launcher"
echo "=================================================="

# [1/7] Validate environment
echo "[1/7] Validating development environment..."

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "ERROR: Backend Python virtual environment not found at:"
    echo "  ${PYTHON_BIN}"
    echo "Please set up backend/.venv first according to backend/README.md"
    exit 1
fi

if [[ ! -f "${BACKEND_DIR}/alembic.ini" ]]; then
    echo "ERROR: Missing alembic.ini in ${BACKEND_DIR}"
    exit 1
fi

if [[ ! -f "${OWNER_APP_DIR}/pubspec.yaml" ]]; then
    echo "ERROR: Missing pubspec.yaml in ${OWNER_APP_DIR}"
    exit 1
fi

echo "✓ Environment validated."

# [2/7] Stop existing backend process on port 8000
echo "[2/7] Stopping previous backend instances on port 8000..."
if command -v fuser >/dev/null 2>&1; then
    fuser -k 8000/tcp >/dev/null 2>&1 || true
fi
pkill -f "uvicorn app.main:app" >/dev/null 2>&1 || true
sleep 1

# [3/7] Run Alembic migrations
echo "[3/7] Applying Alembic database migrations..."
(
    cd "$BACKEND_DIR"
    "$PYTHON_BIN" -m alembic upgrade head
)

# [4/7] Start FastAPI backend
echo "[4/7] Starting FastAPI backend on http://0.0.0.0:8000..."
UVICORN_LOG="${BACKEND_DIR}/uvicorn.log"
rm -f "$UVICORN_LOG"

(
    cd "$BACKEND_DIR"
    nohup "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$UVICORN_LOG" 2>&1 &
    echo $! > "${BACKEND_DIR}/.uvicorn.pid"
)
BACKEND_PID="$(cat "${BACKEND_DIR}/.uvicorn.pid")"
rm -f "${BACKEND_DIR}/.uvicorn.pid"

echo "Backend process launched with PID: ${BACKEND_PID} (Logs: ${UVICORN_LOG})"

# [5/7] Check backend liveness and readiness
echo "[5/7] Verifying backend health..."
BACKEND_LIVE=false

for _ in {1..20}; do
    if curl -fsS http://127.0.0.1:8000/health/live >/dev/null 2>&1; then
        BACKEND_LIVE=true
        break
    fi

    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "ERROR: Backend process exited prematurely."
        if [[ -f "$UVICORN_LOG" ]]; then
            echo "--- Recent Uvicorn Logs ---"
            tail -n 50 "$UVICORN_LOG" || true
        fi
        exit 1
    fi

    sleep 1
done

if [[ "$BACKEND_LIVE" != true ]]; then
    echo "ERROR: Backend failed health liveness check after 20 seconds."
    if [[ -f "$UVICORN_LOG" ]]; then
        echo "--- Recent Uvicorn Logs ---"
        tail -n 50 "$UVICORN_LOG" || true
    fi
    exit 1
fi
echo "✓ Backend liveness verified at http://127.0.0.1:8000/health/live"

# Check database readiness
if ! curl -fsS http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
    echo "ERROR: Backend process is alive but database readiness probe failed."
    if [[ -f "$UVICORN_LOG" ]]; then
        echo "--- Recent Uvicorn Logs ---"
        tail -n 50 "$UVICORN_LOG" || true
    fi
    exit 1
fi
echo "✓ Backend database readiness verified at http://127.0.0.1:8000/health/ready"

# [6/7] Prepare Android Device / Emulator
echo "[6/7] Preparing Android emulator/device..."
ANDROID_EMULATOR="${ANDROID_EMULATOR:-Small_Phone}"
DEVICE_ID=""

# Check if an Android device is already connected
CONNECTED_DEVICES="$(run_flutter devices 2>/dev/null || true)"

if echo "$CONNECTED_DEVICES" | grep -i "android" >/dev/null 2>&1; then
    DEVICE_ID="$(echo "$CONNECTED_DEVICES" | grep -i "android" | head -n 1 | awk -F'•' '{print $2}' | xargs || true)"
fi

if [[ -z "$DEVICE_ID" ]]; then
    echo "No active Android device found. Checking available emulators..."
    AVAILABLE_EMULATORS="$(run_flutter emulators 2>/dev/null || true)"

    if ! echo "$AVAILABLE_EMULATORS" | grep -w "$ANDROID_EMULATOR" >/dev/null 2>&1; then
        echo "ERROR: Configured emulator '${ANDROID_EMULATOR}' not found."
        echo "Available emulators:"
        echo "$AVAILABLE_EMULATORS"
        exit 1
    fi

    echo "Launching Android emulator '${ANDROID_EMULATOR}'..."
    run_flutter emulators --launch "$ANDROID_EMULATOR" >/dev/null 2>&1 &

    echo "Waiting for Android emulator to become ready (up to 90s)..."
    for _ in {1..90}; do
        CONNECTED_DEVICES="$(run_flutter devices 2>/dev/null || true)"
        if echo "$CONNECTED_DEVICES" | grep -i "android" >/dev/null 2>&1; then
            DEVICE_ID="$(echo "$CONNECTED_DEVICES" | grep -i "android" | head -n 1 | awk -F'•' '{print $2}' | xargs || true)"
            break
        fi
        sleep 1
    done

    if [[ -z "$DEVICE_ID" ]]; then
        echo "ERROR: Android emulator failed to register in Flutter devices within 90 seconds."
        exit 1
    fi
fi

echo "✓ Android device target ready: ${DEVICE_ID}"

# [7/7] Launch Owner Flutter application
OWNER_API_BASE_URL="${OWNER_API_BASE_URL:-http://10.0.2.2:8000}"

if [[ "$DEVICE_ID" != *"emulator"* ]] && [[ "$OWNER_API_BASE_URL" == "http://10.0.2.2:8000" ]]; then
    echo "WARNING: Target device '${DEVICE_ID}' appears to be physical hardware."
    echo "  10.0.2.2 is valid for Android Emulator host loopback."
    echo "  For physical devices, set OWNER_API_BASE_URL to your LAN IP (e.g. OWNER_API_BASE_URL=http://192.168.1.50:8000 ./start.sh)"
fi

echo ""
echo "=================================================="
echo " Lending Nelson V2 Ready!"
echo " - Backend API:  http://127.0.0.1:8000/api/v1"
echo " - Health Probe: http://127.0.0.1:8000/health/ready"
echo " - Target Device: ${DEVICE_ID}"
echo " - App API Base:  ${OWNER_API_BASE_URL}"
echo "=================================================="
echo "Launching Owner Mobile App..."

# Disable trap for normal foreground Flutter session so Ctrl+C gracefully closes app
trap - EXIT INT TERM

cd "$OWNER_APP_DIR"
run_flutter run -d "$DEVICE_ID" "--dart-define=API_BASE_URL=${OWNER_API_BASE_URL}"
