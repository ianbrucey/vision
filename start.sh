#!/bin/bash
# ============================================================================
# Vision — Start All Services
# ============================================================================
# Launches the API, background worker, and frontend dev server.
# Auto-detects DBngin vs Docker for PostgreSQL and MinIO.
#
# Usage:
#   chmod +x start.sh && ./start.sh
#
# Press Ctrl+C to stop all services.
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV="$SCRIPT_DIR/.venv/bin/python3"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# ---------------------------------------------------------------------------
# Configuration — override via environment or .env
# ---------------------------------------------------------------------------
# Load .env if present (existing env vars take precedence)
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

DB_HOST="${VISION_DB_HOST:-127.0.0.1}"
DB_PORT="${VISION_DB_PORT:-5433}"
DB_NAME="${VISION_DB_DATABASE:-vision}"
DB_USER="${VISION_DB_USERNAME:-vision}"
DB_PASSWORD="${VISION_DB_PASSWORD:-vision_dev}"

MINIO_ENDPOINT="${MINIO_ENDPOINT:-127.0.0.1:9002}"
MINIO_HOST="${MINIO_ENDPOINT%:*}"
MINIO_PORT="${MINIO_ENDPOINT##*:}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Trap Ctrl+C for clean shutdown
# ---------------------------------------------------------------------------
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $API_PID $WORKER_PID $FRONTEND_PID 2>/dev/null || true
    wait $API_PID $WORKER_PID $FRONTEND_PID 2>/dev/null || true
    echo "All services stopped."
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "============================================"
echo "  Vision — War Room Agent"
echo "============================================"
echo ""

# ---------------------------------------------------------------------------
# Check prerequisites
# ---------------------------------------------------------------------------
if [ ! -f "$VENV" ]; then
    echo -e "${RED}ERROR: Python venv not found at $VENV${NC}"
    echo "  Run: ./setup.sh"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Frontend node_modules not found. Running npm install..."
    cd "$FRONTEND_DIR" && npm install && cd "$SCRIPT_DIR"
fi

# ---------------------------------------------------------------------------
# PostgreSQL — detect DBngin vs Docker
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[postgres]${NC} Checking PostgreSQL on ${DB_HOST}:${DB_PORT}..."

if lsof -ti:"$DB_PORT" > /dev/null 2>&1; then
    echo "       PostgreSQL already running on ${DB_HOST}:${DB_PORT}"
else
    # Try Docker Compose
    if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
        echo "       Starting PostgreSQL via docker compose..."
        docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d vision-db
        sleep 3
        if lsof -ti:"$DB_PORT" > /dev/null 2>&1; then
            echo "       PostgreSQL ready on ${DB_HOST}:${DB_PORT}"
        else
            echo -e "${RED}       ERROR: PostgreSQL failed to start${NC}"
            echo "       Is DBngin running? Is docker compose available?"
            exit 1
        fi
    else
        echo -e "${RED}       ERROR: No PostgreSQL on port ${DB_PORT} and Docker not available${NC}"
        echo "       Start DBngin or run: docker compose -f docker-compose.yml up -d vision-db"
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# MinIO — detect DBngin vs Docker
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[minio]${NC} Checking MinIO on ${MINIO_ENDPOINT}..."

if lsof -ti:"$MINIO_PORT" > /dev/null 2>&1; then
    echo "       MinIO already running on ${MINIO_ENDPOINT}"
elif command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    echo "       Starting MinIO via docker compose..."
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d vision-minio vision-minio-init
    sleep 3
    if lsof -ti:"$MINIO_PORT" > /dev/null 2>&1; then
        echo "       MinIO:    http://${MINIO_ENDPOINT} (console: http://${MINIO_HOST}:9003)"
    else
        echo -e "${YELLOW}       WARNING: MinIO may not have started. Uploads will fail.${NC}"
    fi
else
    echo -e "${YELLOW}       WARNING: MinIO not detected and Docker not available.${NC}"
    echo "       Document uploads will fail until MinIO is running."
fi
echo ""

# ---------------------------------------------------------------------------
# Apply schemas (idempotent — safe on every restart)
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[schema]${NC} Ensuring database schemas are up to date..."
VISION_DB_HOST="$DB_HOST" \
VISION_DB_PORT="$DB_PORT" \
VISION_DB_DATABASE="$DB_NAME" \
VISION_DB_USERNAME="$DB_USER" \
VISION_DB_PASSWORD="$DB_PASSWORD" \
"$VENV" "$BACKEND_DIR/init_db.py" 2>&1 | while IFS= read -r line; do
    echo "       $line"
done
echo ""

# ---------------------------------------------------------------------------
# Clear stale processes on our ports
# ---------------------------------------------------------------------------
lsof -ti:8400 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true

# ---------------------------------------------------------------------------
# API Server
# ---------------------------------------------------------------------------
echo "[1/3] Starting API server on :8400..."
cd "$BACKEND_DIR"
VISION_DB_HOST="$DB_HOST" \
VISION_DB_PORT="$DB_PORT" \
VISION_DB_DATABASE="$DB_NAME" \
VISION_DB_USERNAME="$DB_USER" \
VISION_DB_PASSWORD="$DB_PASSWORD" \
"$VENV" -m uvicorn api.main:app --host 127.0.0.1 --port 8400 &
API_PID=$!
sleep 2
if kill -0 $API_PID 2>/dev/null; then
    echo -e "       ${GREEN}API:      http://127.0.0.1:8400${NC}"
    echo -e "       ${GREEN}Docs:     http://127.0.0.1:8400/docs${NC}"
else
    echo -e "${RED}       ERROR: API failed to start${NC}"
    cleanup
fi

# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
echo "[2/3] Starting background worker..."
cd "$BACKEND_DIR"
VISION_DB_HOST="$DB_HOST" \
VISION_DB_PORT="$DB_PORT" \
VISION_DB_DATABASE="$DB_NAME" \
VISION_DB_USERNAME="$DB_USER" \
VISION_DB_PASSWORD="$DB_PASSWORD" \
"$VENV" ingestion/worker.py &
WORKER_PID=$!
sleep 1
if kill -0 $WORKER_PID 2>/dev/null; then
    echo "       Worker:   pid=$WORKER_PID (polling every 2s)"
else
    echo -e "${RED}       ERROR: Worker failed to start${NC}"
    cleanup
fi

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
echo "[3/3] Starting frontend dev server on :3000..."
cd "$FRONTEND_DIR"
npm run dev -- -p 3000 &
FRONTEND_PID=$!
sleep 3
if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "       ${GREEN}Frontend: http://127.0.0.1:3000${NC}"
else
    echo -e "${RED}       ERROR: Frontend failed to start${NC}"
    cleanup
fi

echo ""
echo "============================================"
echo -e "  ${GREEN}All services running.${NC}"
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
