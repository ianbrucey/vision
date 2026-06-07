#!/bin/bash
# ============================================================================
# Vision — Start All Services
# ============================================================================
# Launches the API, background worker, and frontend dev server.
#
# Usage:
#   chmod +x start.sh && ./start.sh
#
# Press Ctrl+C to stop all services.
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Clear any stale processes on our ports
lsof -ti:8400 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true
cd "$SCRIPT_DIR"

VENV="$SCRIPT_DIR/.venv/bin/python3"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Check prerequisites
if [ ! -f "$VENV" ]; then
    echo "ERROR: Python venv not found at $VENV"
    echo "  Run: cd scripts/vision && python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Frontend node_modules not found. Running npm install..."
    cd "$FRONTEND_DIR" && npm install
    cd "$SCRIPT_DIR"
fi

# Trap Ctrl+C to kill all background processes
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $API_PID $WORKER_PID $FRONTEND_PID 2>/dev/null
    wait $API_PID $WORKER_PID $FRONTEND_PID 2>/dev/null
    echo "All services stopped."
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "============================================"
echo "  Vision — War Room Agent"
echo "============================================"
echo ""

# --- MinIO ---
MINIO_ENDPOINT="${MINIO_ENDPOINT:-127.0.0.1:9002}"
MINIO_HOST="${MINIO_ENDPOINT%:*}"
MINIO_PORT="${MINIO_ENDPOINT##*:}"

if lsof -ti:"$MINIO_PORT" > /dev/null 2>&1; then
    echo "[minio] Already running on $MINIO_ENDPOINT"
else
    echo "[minio] Starting MinIO via docker compose..."
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d vision-minio vision-minio-init
    sleep 3
    if lsof -ti:"$MINIO_PORT" > /dev/null 2>&1; then
        echo "       MinIO:    http://$MINIO_ENDPOINT (console: http://127.0.0.1:9003)"
    else
        echo "       WARNING: MinIO may not have started. Check docker compose logs."
    fi
fi
echo ""

# --- API Server ---
echo "[1/4] Starting API server on :8400..."
cd "$BACKEND_DIR"
VISION_DB_PORT=5432 "$VENV" -m uvicorn api.main:app \
    --host 127.0.0.1 --port 8400 &
API_PID=$!
sleep 2
if kill -0 $API_PID 2>/dev/null; then
    echo "       API:      http://127.0.0.1:8400"
    echo "       Docs:     http://127.0.0.1:8400/docs"
else
    echo "       ERROR: API failed to start"
    cleanup
fi

# --- Worker ---
echo "[2/4] Starting background worker..."
cd "$BACKEND_DIR"
VISION_DB_PORT=5432 "$VENV" ingestion/worker.py &
WORKER_PID=$!
sleep 1
if kill -0 $WORKER_PID 2>/dev/null; then
    echo "       Worker:   pid=$WORKER_PID (polling every 2s)"
else
    echo "       ERROR: Worker failed to start"
    cleanup
fi

# --- Frontend ---
echo "[3/4] Starting frontend dev server on :3000..."
cd "$FRONTEND_DIR"
npm run dev -- -p 3000 &
FRONTEND_PID=$!
sleep 3
if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "       Frontend: http://127.0.0.1:3000"
else
    echo "       ERROR: Frontend failed to start"
    cleanup
fi

echo ""
echo "============================================"
echo "  All services running."
echo ""
echo "  API:       http://127.0.0.1:8400"
echo "  Docs:      http://127.0.0.1:8400/docs"
echo "  Frontend:  http://127.0.0.1:3000"
echo ""
echo "  Press Ctrl+C to stop."
echo "============================================"
echo ""

# Wait for any to exit
wait
