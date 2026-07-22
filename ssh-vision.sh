#!/bin/bash
# ============================================================================
# Vision — SSH to production server
# ============================================================================
# Usage:
#   ./ssh-vision.sh          — interactive shell
#   ./ssh-vision.sh "uptime" — run a single command
# ============================================================================
HOST="vision"

if [ -n "$1" ]; then
    ssh "$HOST" "$@"
else
    ssh "$HOST"
fi
