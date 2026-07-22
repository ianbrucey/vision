#!/bin/bash
set -e

echo "Waiting for PostgreSQL (${VISION_DB_HOST}:${VISION_DB_PORT})..."
until pg_isready -h "$VISION_DB_HOST" -p "$VISION_DB_PORT" -U "$VISION_DB_USERNAME" 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL ready."

cd /app/backend

if [ "$VISION_ROLE" = "worker" ]; then
    echo "Starting worker (${VISION_WORKER_ID:-worker})..."
    exec python ingestion/worker.py
else
    echo "Applying schemas..."
    python init_db.py
    echo "Starting API on :8400..."
    exec uvicorn api.main:app --host 0.0.0.0 --port 8400
fi
