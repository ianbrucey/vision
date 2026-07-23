#!/bin/bash
# ============================================================================
# Vision — Publog FLIS Server-Side Loader
# ============================================================================
# Run ON THE SERVER after syncing publog_export/*.txt.gz files.
#
# Usage (on server):
#   ssh vision
#   cd /root/vision-new
#   ./load_publog.sh [DATA_DIR]
#
# What it does:
#   1. Gunzips the pipe-delimited exports
#   2. Runs the DB migration (023_publog_flis.sql)
#   3. Uses PostgreSQL COPY to load each table efficiently
#   4. Cleans up temp files
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${1:-$SCRIPT_DIR/publog_data}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-vision}"
DB_USER="${DB_USER:-vision}"
DB_PASS="${DB_PASS:-}"

export PGPASSWORD="${DB_PASS}"
PSQL="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()  { echo -e "${RED}[FATAL]${NC} $*"; exit 1; }

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
[ -d "$DATA_DIR" ] || die "Data directory not found: $DATA_DIR"
command -v psql >/dev/null 2>&1 || die "psql not found"

# ---------------------------------------------------------------------------
# Run migration
# ---------------------------------------------------------------------------
log "Running Publog schema migration..."
$PSQL -f "$SCRIPT_DIR/backend/schemas/023_publog_flis.sql" -q || die "Migration failed"

# ---------------------------------------------------------------------------
# Load helper — gunzip, clean, and COPY into PostgreSQL
# ---------------------------------------------------------------------------
load_table() {
    local name="$1"
    local table="$2"
    local gzfile="${DATA_DIR}/publog_${name}.txt.gz"

    if [ ! -f "$gzfile" ]; then
        warn "Skipping $name — $gzfile not found"
        return 0
    fi

    log "Loading $name → $table..."
    local rows=$(zcat "$gzfile" | wc -l | tr -d ' ')
    log "  Source: $rows rows (including header)"

    # Truncate and load — gunzip, strip header, pipe to COPY
    $PSQL -c "TRUNCATE TABLE $table RESTART IDENTITY CASCADE;" -q

    zcat "$gzfile" | tail -n +2 | \
        $PSQL -c "COPY $table FROM STDIN WITH (FORMAT csv, DELIMITER '|', HEADER false, NULL '', QUOTE E'\x01')" -q

    local loaded=$($PSQL -t -c "SELECT COUNT(*) FROM $table" | tr -d ' ')
    log "  Loaded: $loaded rows into $table"
    echo ""
}

# ---------------------------------------------------------------------------
# Load all tables
# ---------------------------------------------------------------------------
log "Publog FLIS Load — $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

TOTAL_START=$(date +%s)

load_table "flis_nsn"         "vision.publog_flis_nsn"
load_table "flis_management"  "vision.publog_flis_management"
load_table "flis_identification" "vision.publog_flis_identification"
load_table "moe_rule"         "vision.publog_moe_rule"
load_table "cage"             "vision.publog_cage"
load_table "flis_part"        "vision.publog_flis_part"

TOTAL_ELAPSED=$(($(date +%s) - TOTAL_START))
log "All loads complete in ${TOTAL_ELAPSED}s ($(($TOTAL_ELAPSED / 60))m)"

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
echo ""
echo "==================== VERIFY ===================="
for table in publog_flis_nsn publog_flis_management publog_flis_identification publog_moe_rule publog_cage publog_flis_part; do
    count=$($PSQL -t -c "SELECT COUNT(*) FROM vision.$table" | tr -d ' ')
    printf "  %-35s %'12d rows\n" "$table" "$count" 2>/dev/null || echo "  $table: ERROR"
done
echo "================================================"
echo ""
log "Load complete. Run a test query:"
echo "  $PSQL -c \"SELECT fsc, niin, item_name FROM vision.publog_flis_nsn WHERE niin = '014532373';\""
