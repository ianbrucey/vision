#!/bin/bash
# ============================================================================
# Vision — Fresh Install & Start
# ============================================================================
# Sets up the Vision application from scratch. Safe to re-run — all steps
# are idempotent (skip if already done).
#
# Usage:
#   chmod +x setup.sh && ./setup.sh
#
# What it does:
#   1. Checks prerequisites (python3, node, psql, minio)
#   2. Creates the PostgreSQL database (if missing)
#   3. Creates .env from template (if missing)
#   4. Creates Python venv + installs backend dependencies
#   5. Installs frontend npm dependencies
#   6. Applies database schemas
#   7. Creates the MinIO bucket
#   8. Starts API, Worker, and Frontend
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
# Configuration (override with environment variables)
# ---------------------------------------------------------------------------
DB_HOST="${VISION_DB_HOST:-127.0.0.1}"
DB_PORT="${VISION_DB_PORT:-5432}"
DB_NAME="${VISION_DB_DATABASE:-vision}"
DB_USER="${VISION_DB_USERNAME:-ianbruce}"
DB_PASSWORD="${VISION_DB_PASSWORD:-}"

MINIO_ENDPOINT="${MINIO_ENDPOINT:-127.0.0.1:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_BUCKET="${MINIO_BUCKET:-vision-uploads}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

step()  { echo -e "${CYAN}[$1/$TOTAL_STEPS]${NC} $2"; }
ok()    { echo -e "       ${GREEN}$1${NC}"; }
warn()  { echo -e "       ${YELLOW}WARNING:${NC} $1"; }
err()   { echo -e "       ${RED}ERROR:${NC} $1"; }

TOTAL_STEPS=8

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
echo "  Vision — War Room Agent Setup"
echo "============================================"
echo ""

# ===========================================================================
# STEP 1: Prerequisites
# ===========================================================================
step 1 "Checking prerequisites..."

# Python
if ! command -v python3 &>/dev/null; then
    err "python3 not found. Install Python 3.11+ and try again."
    exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
ok "python3 $PY_VER"

# Node
if ! command -v node &>/dev/null; then
    err "node not found. Install Node.js 20+ and try again."
    exit 1
fi
NODE_VER=$(node --version)
ok "node $NODE_VER"

# PostgreSQL (check via psql)
if ! command -v psql &>/dev/null; then
    warn "psql not found. Database setup will be skipped."
    PSQL_OK=false
else
    PSQL_OK=true
    ok "psql available"
fi

# MinIO (just check if something is listening)
if lsof -ti:${MINIO_ENDPOINT##*:} > /dev/null 2>&1; then
    ok "MinIO running on $MINIO_ENDPOINT"
    MINIO_OK=true
else
    warn "MinIO not detected on $MINIO_ENDPOINT — document uploads will fail"
    MINIO_OK=false
fi

echo ""

# ===========================================================================
# STEP 2: Database
# ===========================================================================
step 2 "Setting up PostgreSQL database..."

if [ "$PSQL_OK" = false ]; then
    warn "Skipping database setup (psql not available)"
else
    # Try to create the database. If it already exists, this is a no-op.
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -tc \
        "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" postgres 2>/dev/null | grep -q 1; then
        ok "Database '$DB_NAME' already exists"
    else
        createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null && \
            ok "Created database '$DB_NAME'" || \
            warn "Could not create database — it may already exist or credentials may differ"
    fi
fi

echo ""

# ===========================================================================
# STEP 3: Environment file
# ===========================================================================
step 3 "Setting up .env file..."

if [ -f "$SCRIPT_DIR/.env" ]; then
    ok ".env file already exists"
else
    cat > "$SCRIPT_DIR/.env" << EOF
# Vision — Environment Configuration
# Database (DBngin — PostgreSQL)
VISION_DB_HOST=$DB_HOST
VISION_DB_PORT=$DB_PORT
VISION_DB_DATABASE=$DB_NAME
VISION_DB_USERNAME=$DB_USER
VISION_DB_PASSWORD=$DB_PASSWORD

# DeepSeek API (Agent SDK backend)
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_AUTH_TOKEN=
ANTHROPIC_MODEL=deepseek-v4-pro[1m]
ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-v4-pro[1m]
ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-v4-pro[1m]
ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-v4-flash[1m]

# DataLab API (PDF OCR/parsing)
DATALAB_API_KEY=
DATALAB_API_URL=https://api.datalab.to

# MinIO (S3-compatible document storage via DBngin)
MINIO_ENDPOINT=$MINIO_ENDPOINT
MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY
MINIO_SECRET_KEY=$MINIO_SECRET_KEY
MINIO_BUCKET=$MINIO_BUCKET
EOF
    ok "Created .env file (edit to add API keys)"
fi

echo ""

# ===========================================================================
# STEP 4: Python venv + backend dependencies
# ===========================================================================
step 4 "Setting up Python virtual environment..."

if [ -f "$VENV" ]; then
    ok "Python venv already exists"
else
    python3 -m venv "$SCRIPT_DIR/.venv"
    ok "Created Python venv"
fi

echo "       Installing backend dependencies..."
"$VENV" -m pip install -r "$BACKEND_DIR/requirements.txt" --quiet 2>&1 | tail -1
ok "Backend dependencies installed"

echo ""

# ===========================================================================
# STEP 5: Frontend dependencies
# ===========================================================================
step 5 "Installing frontend dependencies..."

if [ -d "$FRONTEND_DIR/node_modules" ]; then
    ok "node_modules already exists"
else
    cd "$FRONTEND_DIR"
    npm install --silent 2>&1 | tail -1
    cd "$SCRIPT_DIR"
    ok "Frontend dependencies installed"
fi

echo ""

# ===========================================================================
# STEP 6: Apply database schemas
# ===========================================================================
step 6 "Applying database schemas (init_db.py)..."

if [ "$PSQL_OK" = false ]; then
    warn "Skipping schema setup (psql not available)"
else
    VISION_DB_HOST="$DB_HOST" \
    VISION_DB_PORT="$DB_PORT" \
    VISION_DB_DATABASE="$DB_NAME" \
    VISION_DB_USERNAME="$DB_USER" \
    VISION_DB_PASSWORD="$DB_PASSWORD" \
    "$VENV" "$BACKEND_DIR/init_db.py"
    ok "All schemas applied"
fi

echo ""

# ===========================================================================
# STEP 7: MinIO bucket
# ===========================================================================
step 7 "Setting up MinIO bucket..."

if [ "$MINIO_OK" = false ]; then
    warn "Skipping MinIO setup (not running)"
else
    "$VENV" -c "
from minio import Minio
client = Minio('$MINIO_ENDPOINT', access_key='$MINIO_ACCESS_KEY',
               secret_key='$MINIO_SECRET_KEY', secure=False)
buckets = [b.name for b in client.list_buckets()]
if '$MINIO_BUCKET' not in buckets:
    client.make_bucket('$MINIO_BUCKET')
    print('  Created bucket: $MINIO_BUCKET')
else:
    print('  Bucket already exists: $MINIO_BUCKET')
" 2>&1
    ok "MinIO bucket ready"
fi

echo ""

# ===========================================================================
# STEP 8: Start services
# ===========================================================================
step 8 "Starting services..."

# Clear stale processes
lsof -ti:8400 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true

# --- API Server ---
echo "       Starting API server on :8400..."
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
    ok "API:       http://127.0.0.1:8400"
    ok "Docs:      http://127.0.0.1:8400/docs"
else
    err "API failed to start"
    cleanup
fi

# --- Worker ---
echo "       Starting background worker..."
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
    ok "Worker:    pid=$WORKER_PID (polling every 2s)"
else
    err "Worker failed to start"
    cleanup
fi

# --- Frontend ---
echo "       Starting frontend dev server on :3000..."
cd "$FRONTEND_DIR"
npm run dev -- -p 3000 &
FRONTEND_PID=$!
sleep 3
if kill -0 $FRONTEND_PID 2>/dev/null; then
    ok "Frontend:  http://127.0.0.1:3000"
else
    err "Frontend failed to start"
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
