#!/bin/bash
# ============================================================================
# Vision — Production Deploy (manual pull-and-rebuild)
# ============================================================================
# Run this ON THE SERVER after SSHing in:
#   ssh root@50.116.38.57
#   cd vision && ./deploy.sh
# ============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/4] Pulling latest code..."
git pull

echo "[2/4] Building images..."
docker compose -f docker-compose.prod.yml --env-file .env.prod build

echo "[3/4] Applying migrations + restarting services..."
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

echo "[4/4] Pruning old images..."
docker image prune -f

echo ""
echo "Deploy complete. Tailing logs (Ctrl+C to stop watching, services keep running):"
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f --tail=50
