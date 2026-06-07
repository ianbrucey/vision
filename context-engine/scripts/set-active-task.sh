#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_CONTX_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$PROJECT_CONTX_DIR/.." && pwd)"
CE_DIR="$PROJECT_ROOT/context-engine"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 tasks/task-<...> [--title \"Title\"] [--status in-progress] [--priority P1]" >&2
  exit 1
fi

TASK_REL="$1"; shift || true
TITLE=""
STATUS="in-progress"
PRIORITY="P2"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title) TITLE="$2"; shift 2;;
    --status) STATUS="$2"; shift 2;;
    --priority) PRIORITY="$2"; shift 2;;
    *) echo "Unknown option: $1" >&2; exit 1;;
  esac
done

TASK_DIR="$CE_DIR/$TASK_REL"
if [[ ! -d "$TASK_DIR" ]]; then
  echo "Task directory not found: $TASK_DIR" >&2
  exit 1
fi

mkdir -p "$CE_DIR"

BASENAME="$(basename "$TASK_DIR")"
# Expected: task-CAT-001-some-slug or task-123-some-slug
ID_PART="$(echo "$BASENAME" | awk -F'-' '{if (NF>=4) print toupper($2"-"$3); else if (NF>=3) print toupper($2"-"$3); else print toupper($0)}')"
SLUG_PART="$(echo "$BASENAME" | cut -d'-' -f4-)"
[[ -z "$SLUG_PART" ]] && SLUG_PART="$BASENAME"

cat > "$CE_DIR/active-task.json" <<EOF
{
  "$schema": "./task-metadata.schema.json",
  "id": "${ID_PART}",
  "slug": "${SLUG_PART}",
  "title": "${TITLE}",
  "status": "${STATUS}",
  "priority": "${PRIORITY}",
  "path": "${TASK_REL}"
}
EOF

echo "Active task set: $TASK_REL"
echo "Pointer written to: $CE_DIR/active-task.json"
