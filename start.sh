#!/usr/bin/env bash
set -euo pipefail

# 1. Project paths resolution
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
OWNER_APP_DIR="${PROJECT_ROOT}/apps/owner_mobile"
BORROWER_APP_DIR="${PROJECT_ROOT}/apps/borrower_mobile"
PYTHON_BIN="${BACKEND_DIR}/.venv/bin/python"

# Usage help display
show_help() {
    cat << 'EOF'
==================================================
 Lending Nelson V2 — Local Development Launcher
==================================================

Usage:
  ./start.sh [target]

Available Targets:
  backend   Runs Alembic migrations and starts FastAPI backend in foreground on 0.0.0.0:8000.
  owner     Verifies backend readiness and launches Owner Flutter application.
  borrower  Verifies backend readiness and launches Borrower Flutter application.
  help      Displays this usage message.

Environment Overrides:
  API_BASE_URL        Base API URL for Flutter apps (default: http://10.0.2.2:8000).
  FLUTTER_DEVICE_ID   Specific Flutter device ID (e.g. emulator-5554).
  ANDROID_EMULATOR    Target emulator AVD name to launch if none active (default: Small_Phone).

Examples:
  Terminal 1: ./start.sh backend
  Terminal 2: ./start.sh owner
  Terminal 3: ./start.sh borrower

  Physical Device:
    API_BASE_URL=http://192.168.1.50:8000 ./start.sh borrower

EOF
}

TARGET_ARG="${1:-}"

if [[ "$TARGET_ARG" == "help" || "$TARGET_ARG" == "--help" || "$TARGET_ARG" == "-h" ]]; then
    show_help
    exit 0
fi

if [[ -z "$TARGET_ARG" ]]; then
    echo "Notice: No target specified. Defaulting to 'owner' (use './start.sh help' for usage)."
    TARGET_APP="owner"
else
    TARGET_APP="$TARGET_ARG"
fi

if [[ "$TARGET_APP" != "backend" && "$TARGET_APP" != "owner" && "$TARGET_APP" != "borrower" ]]; then
    echo "ERROR: Invalid target '${TARGET_APP}'."
    echo ""
    show_help
    exit 1
fi

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
echo " Target: ${TARGET_APP}"
echo "=================================================="

# -----------------------------------------------------------------------------
# TARGET: BACKEND
# -----------------------------------------------------------------------------
if [[ "$TARGET_APP" == "backend" ]]; then
    echo "[1/3] Validating backend environment..."
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

    # Check if backend is already running on http://127.0.0.1:8000
    if curl -fsS http://127.0.0.1:8000/health/live >/dev/null 2>&1; then
        echo "Backend is already running at http://127.0.0.1:8000"
        exit 0
    fi

    echo "[2/3] Applying database migrations..."
    (
        cd "$BACKEND_DIR"
        "$PYTHON_BIN" -m alembic upgrade head
    )
    echo "✓ Database migrations complete."

    echo "[3/3] Starting FastAPI backend on http://0.0.0.0:8000..."
    echo "  - API Base:   http://127.0.0.1:8000/api/v1"
    echo "  - Health:     http://127.0.0.1:8000/health/ready"
    echo "Press Ctrl+C to stop."
    echo ""

    cd "$BACKEND_DIR"
    exec "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi

# -----------------------------------------------------------------------------
# TARGET: OWNER / BORROWER
# -----------------------------------------------------------------------------
APP_LAUNCH_DIR=""
if [[ "$TARGET_APP" == "owner" ]]; then
    APP_LAUNCH_DIR="$OWNER_APP_DIR"
elif [[ "$TARGET_APP" == "borrower" ]]; then
    APP_LAUNCH_DIR="$BORROWER_APP_DIR"
fi

if [[ ! -f "${APP_LAUNCH_DIR}/pubspec.yaml" ]]; then
    echo "ERROR: Missing pubspec.yaml in ${APP_LAUNCH_DIR}"
    exit 1
fi

echo "[1/3] Verifying backend availability..."
if ! curl -fsS http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
    echo "ERROR: Backend is not running or not ready at http://127.0.0.1:8000."
    echo ""
    echo "Please start the backend in another terminal first:"
    echo "  ./start.sh backend"
    echo ""
    exit 1
fi
echo "✓ Backend available at http://127.0.0.1:8000"

echo "[2/3] Preparing Android device/emulator..."
FLUTTER_DEVICE_ID="${FLUTTER_DEVICE_ID:-}"
ANDROID_EMULATOR="${ANDROID_EMULATOR:-Small_Phone}"
DEVICE_ID=""

if [[ -n "$FLUTTER_DEVICE_ID" ]]; then
    DEVICE_ID="$FLUTTER_DEVICE_ID"
else
    CONNECTED_DEVICES="$(run_flutter devices 2>/dev/null || true)"
    if echo "$CONNECTED_DEVICES" | grep -i "android" >/dev/null 2>&1; then
        DEVICE_ID="$(echo "$CONNECTED_DEVICES" | grep -i "android" | head -n 1 | awk -F'•' '{print $2}' | xargs || true)"
    fi
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

API_BASE_URL="${API_BASE_URL:-${OWNER_API_BASE_URL:-http://10.0.2.2:8000}}"

if [[ "$DEVICE_ID" != *"emulator"* ]] && [[ "$API_BASE_URL" == "http://10.0.2.2:8000" ]]; then
    echo "WARNING: Target device '${DEVICE_ID}' appears to be physical hardware."
    echo "  10.0.2.2 is valid for Android Emulator host loopback."
    echo "  For physical devices, set API_BASE_URL to your LAN IP (e.g. API_BASE_URL=http://192.168.1.50:8000 ./start.sh ${TARGET_APP})"
fi

echo "[3/3] Launching ${TARGET_APP} Mobile App..."
echo "  - Target App:   ${TARGET_APP}"
echo "  - Device:       ${DEVICE_ID}"
echo "  - API Base:     ${API_BASE_URL}"
echo ""

cd "$APP_LAUNCH_DIR"
run_flutter run -d "$DEVICE_ID" "--dart-define=API_BASE_URL=${API_BASE_URL}"
