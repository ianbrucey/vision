#!/bin/bash
# ============================================================================
# Vision — Deploy to Remote Server (run from local machine)
# ============================================================================
# Pushes the current branch, pulls on the server, rebuilds, and deploys.
# Prerequisite: SSH config entry "vision" must be configured.
#
# Usage:
#   ./deploy-remote.sh            # push + deploy current branch
#   ./deploy-remote.sh --no-push  # deploy without pushing (server already has code)
# ============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ "${1:-}" != "--no-push" ]; then
    echo "[1/3] Pushing $BRANCH to GitHub..."
    git push origin "$BRANCH"
else
    echo "[1/3] Skipping push (--no-push)"
fi

echo "[2/3] Pulling on server + deploying..."
ssh vision "cd /root/vision-new && git pull && ./deploy.sh"

echo "[3/3] Done."
