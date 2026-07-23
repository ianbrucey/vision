#!/bin/bash
# ============================================================================
# Vision — Publog FLIS Extraction Protocol
# ============================================================================
# Extracts all FLIS tables from a DLA Publog DVD using Decomp.exe via Wine.
#
# Usage:
#   ./extract_publog.sh [PUBLOG_DIR] [OUTPUT_DIR]
#
#   PUBLOG_DIR  — Path to the Publog DVD/files (default: ./PublogDVD)
#   OUTPUT_DIR  — Where to write pipe-delimited .txt exports (default: ./publog_export)
#
# Requirements:
#   - Wine (brew install --cask wine-stable)
#   - Publog DVD mounted or directory containing:
#       TOOLS/UTILITIES/Decomp.exe
#       IMD.LST
#       *.TAB files (P_FLIS_NSN.TAB, V_FLIS_MANAGEMENT.TAB, etc.)
#
# Cadence: Run monthly when new Publog DVD arrives (published ~1st week of month).
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PUBLOG_DIR="${1:-$SCRIPT_DIR/PublogDVD}"
OUTPUT_DIR="${2:-$SCRIPT_DIR/publog_export}"
DECOMP="${PUBLOG_DIR}/TOOLS/UTILITIES/Decomp.exe"
WINEPREFIX="${WINEPREFIX:-$HOME/.wine_publog}"
export WINEPREFIX
export WINEARCH=win64

# Convert macOS path to Wine Z: drive path
mac2wine() { echo "Z:$(echo "$1" | sed 's|/|\\|g')"; }

WINE_PUBLOG="$(mac2wine "$PUBLOG_DIR")"
WINE_OUT="$(mac2wine "$OUTPUT_DIR")"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()  { echo -e "${RED}[FATAL]${NC} $*"; exit 1; }

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
[ -f "$DECOMP" ] || die "Decomp.exe not found at $DECOMP. Is the Publog DVD mounted?"
command -v wine >/dev/null 2>&1 || die "Wine not found. Install: brew install --cask wine-stable"
mkdir -p "$OUTPUT_DIR"

# Initialize Wine if needed
if [ ! -d "$WINEPREFIX" ]; then
    log "Initializing Wine prefix at $WINEPREFIX..."
    wineboot --init 2>&1 | tail -1
fi

# ---------------------------------------------------------------------------
# Table definitions — name, table, key_field, query (null = select *)
# ---------------------------------------------------------------------------
declare -A TABLES
# Format: "export_name|table_name|key_field|select_clause"
TABLES=(
    [flis_nsn]="P_FLIS_NSN|NIIN|FSC,NIIN,INC,ITEM_NAME,SOS,END_ITEM_NAME,CANCELLED_NIIN"
    [flis_management]="V_FLIS_MANAGEMENT|NIIN|*"
    [flis_identification]="V_FLIS_IDENTIFICATION|NIIN|*"
    [moe_rule]="V_MOE_RULE|NIIN|*"
    [cage]="P_CAGE|CAGE_CODE|*"
    [flis_part]="V_FLIS_PART|NIIN|*"
)

# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
log "Publog FLIS Extraction — $(date '+%Y-%m-%d')"
log "Source: $PUBLOG_DIR"
log "Output: $OUTPUT_DIR"
log "Wine:   $WINEPREFIX"
echo ""

TOTAL_START=$(date +%s)

for name in "${!TABLES[@]}"; do
    IFS='|' read -r table key_field columns <<< "${TABLES[$name]}"
    outfile="${OUTPUT_DIR}/publog_${name}.txt"
    gzfile="${outfile}.gz"

    if [ -f "$gzfile" ]; then
        warn "Skipping $name — $gzfile already exists"
        continue
    fi

    log "Exporting $name ($table)..."
    START=$(date +%s)

    # Build query — use key_field='*' for full table extraction
    query="select ${columns} from ${table} where ${key_field}='*'"
    wine_out="$(mac2wine "$outfile")"

    if ! wine "$DECOMP" "$WINE_PUBLOG" "$query" "$wine_out" 2>&1 | grep -E "rows|Error"; then
        die "Export of $name failed. Check Wine/Decomp.exe output above."
    fi

    ELAPSED=$(($(date +%s) - START))
    ROWS=$(wc -l < "$outfile" | tr -d ' ')
    SIZE=$(ls -lh "$outfile" | awk '{print $5}')

    log "  → $ROWS rows, $SIZE, ${ELAPSED}s — compressing..."
    gzip -f "$outfile"
    log "  → $gzfile ($(ls -lh "$gzfile" | awk '{print $5}'))"
    echo ""
done

TOTAL_ELAPSED=$(($(date +%s) - TOTAL_START))
log "All exports complete in ${TOTAL_ELAPSED}s ($(($TOTAL_ELAPSED / 60))m)"
log "Files ready in: $OUTPUT_DIR"
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "==================== EXPORT SUMMARY ===================="
for f in "$OUTPUT_DIR"/publog_*.txt.gz; do
    if [ -f "$f" ]; then
        base=$(basename "$f" .txt.gz)
        rows=$(zcat "$f" | wc -l | tr -d ' ')
        size=$(ls -lh "$f" | awk '{print $5}')
        header=$(zcat "$f" | head -1)
        echo "  $base: $rows rows, $size — $header"
    fi
done
echo "========================================================"
echo ""
echo "Next: upload to server and load into PostgreSQL."
echo "  rsync -avP $OUTPUT_DIR/ vision:/root/vision-new/publog_data/"
echo "  ssh vision 'cd /root/vision-new && ./load_publog.sh'"
