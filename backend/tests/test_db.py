#!/usr/bin/env python3
"""
Vision — Schema Smoke Test.

Verifies that the database is reachable, the schema applied cleanly, every
table and critical index exists, and extensions are loaded.

Usage:
    cd scripts/vision && python3 db_test.py
    cd scripts/vision && python3 db_test.py --strategy

Requires: a running Postgres instance with the vision database created.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the scripts directory is on the path so we can import from vision/
_SCRIPTS_DIR = Path(__file__).resolve().parents[3]  # backend/tests → backend → vision → scripts
sys.path.insert(0, str(_SCRIPTS_DIR))

# Support both direct execution and package import
try:
    from core.db import connect, ensure_schema, ensure_strategy_schema
except (ImportError, ValueError):
    # Direct execution fallback
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # backend/
    from core.db import connect, ensure_schema, ensure_strategy_schema  # type: ignore


# ---------------------------------------------------------------------------
# Expected inventory
# ---------------------------------------------------------------------------

# Every table the schema should create, grouped by layer.
EXPECTED_TABLES = {
    # Case core
    "cases",
    "parties",
    "allegations",
    "events",
    "citations",
    # Evidence store
    "documents",
    "sections",
    "blocks",
    "block_headings",
    # Workspaces (deferred but schema must exist)
    "workspaces",
    # Infrastructure
    "embedding_cache",
    "schema_migrations",
}

# Strategy tables (only checked if --strategy flag is passed)
EXPECTED_STRATEGY_TABLES = {
    "rhetorical_moves",
    "case_facts",
    "strategies",
    "doctrine_elements",
    "strategy_propositions",
    "strategy_facts",
    "proposition_fact_mappings",
    "proposition_authorities",
    "adversarial_attacks",
    "adversarial_turns",
    "proposition_overlay_gates",
    "gauntlet_check_categories",
    "gauntlet_check_definitions",
    "strategy_gauntlet_results",
}

# Critical indexes that must exist. If these are missing, queries will scan.
EXPECTED_INDEXES = {
    "idx_blocks_document",
    "idx_blocks_section",
    "idx_blocks_page",
    "idx_blocks_tsv",
    "idx_sections_document",
    "idx_sections_parent",
    "idx_sections_title_trgm",
    "idx_sections_embedding",
    "idx_citations_source",
    "idx_citations_block",
    "idx_events_case",
    "idx_events_date",
    "idx_parties_case_id",
    "idx_allegations_case_id",
    "idx_documents_case_id",
    "idx_block_headings_section",
    "idx_cases_external_id",
    "idx_workspaces_case",
}

# Extensions the schema requires
REQUIRED_EXTENSIONS = {"vector", "pg_trgm"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_column(conn, query: str, *args) -> set:
    """Execute a query and return the first column as a set."""
    with conn.cursor() as cur:
        cur.execute(query, args)
        return {row[0] for row in cur.fetchall()}


def check(label: str, ok: bool, detail: str = "") -> bool:
    """Print a pass/fail line. Returns ok for chaining."""
    status = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
    suffix = f"  — {detail}" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    strategy = "--strategy" in sys.argv

    print("Vision — Schema Smoke Test")
    print(f"  DB: vision@127.0.0.1:5433\n")

    # -- Connection ----------------------------------------------------------
    try:
        conn = connect()
        print("\033[32m[OK]\033[0m Database connection established.\n")
    except Exception as e:
        print(f"\033[31m[FATAL]\033[0m Cannot connect to database: {e}")
        print("\n  Is the database running?")
        print("    docker compose -f vision/docker-compose.yml up -d\n")
        return 1

    # -- Schema application --------------------------------------------------
    print("—" * 60)
    print("Schema Application\n")

    try:
        schema_paths = ensure_schema()
        for path in schema_paths:
            print(f"  Applied: {path}")
        print()
    except Exception as e:
        print(f"\033[31m[FATAL]\033[0m Schema application failed: {e}\n")
        conn.close()
        return 1

    if strategy:
        try:
            strategy_paths = ensure_strategy_schema()
            for path in strategy_paths:
                print(f"  Applied (strategy): {path}")
            print()
        except Exception as e:
            print(f"\033[31m[FATAL]\033[0m Strategy schema application failed: {e}\n")
            conn.close()
            return 1

    # -- Extensions ----------------------------------------------------------
    print("—" * 60)
    print("Extensions\n")

    extensions = _fetch_column(conn, "SELECT extname FROM pg_extension")
    all_extensions_ok = True
    for ext in sorted(REQUIRED_EXTENSIONS):
        ok = ext in extensions
        all_extensions_ok &= ok
        check(f"Extension: {ext}", ok,
              "loaded" if ok else "missing — run CREATE EXTENSION")
    print()

    # -- Tables --------------------------------------------------------------
    print("—" * 60)
    print("Tables\n")

    existing = _fetch_column(
        conn,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'vision'"
    )
    all_tables = EXPECTED_TABLES.copy()
    if strategy:
        all_tables |= EXPECTED_STRATEGY_TABLES

    all_tables_ok = True
    for tbl in sorted(all_tables):
        ok = tbl in existing
        all_tables_ok &= ok
        check(f"Table: vision.{tbl}", ok,
              "exists" if ok else "MISSING")
    print()

    # -- Indexes -------------------------------------------------------------
    print("—" * 60)
    print("Indexes\n")

    indexes = _fetch_column(
        conn,
        "SELECT indexname FROM pg_indexes "
        "WHERE schemaname = 'vision'"
    )
    all_indexes_ok = True
    for idx in sorted(EXPECTED_INDEXES):
        ok = idx in indexes
        all_indexes_ok &= ok
        check(f"Index: {idx}", ok,
              "exists" if ok else "MISSING")
    print()

    # -- Constraints ---------------------------------------------------------
    print("—" * 60)
    print("Constraints (smoke check)\n")

    # Verify a few key CHECK constraints by attempting invalid inserts
    constraint_ok = True

    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO cases (name, case_type) "
                "VALUES ('test', 'invalid_type')"
            )
        constraint_ok &= check("CHECK: cases.case_type rejects invalid value",
                               False, "should have raised")
    except Exception:
        constraint_ok &= check("CHECK: cases.case_type rejects invalid value",
                               True, "correctly rejected")

    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO blocks (document_id, block_type, page) "
                "VALUES (999999, 'InvalidType', 1)"
            )
        constraint_ok &= check("CHECK: blocks.block_type rejects invalid value",
                               False, "should have raised")
    except Exception:
        constraint_ok &= check("CHECK: blocks.block_type rejects invalid value",
                               True, "correctly rejected")

    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO parties (case_id, name, party_kind) "
                "VALUES (999999, 'test', 'corporation')"
            )
        constraint_ok &= check("CHECK: parties.party_kind rejects invalid value",
                               False, "should have raised")
    except Exception:
        constraint_ok &= check("CHECK: parties.party_kind rejects invalid value",
                               True, "correctly rejected")

    conn.rollback()
    print()

    # -- Summary -------------------------------------------------------------
    print("—" * 60)
    all_ok = all_extensions_ok and all_tables_ok and all_indexes_ok and constraint_ok

    if all_ok:
        print("\033[32mAll checks passed.\033[0m")
        print(f"  Tables:     {len(all_tables)} verified")
        print(f"  Indexes:    {len(EXPECTED_INDEXES)} verified")
        print(f"  Extensions: {len(REQUIRED_EXTENSIONS)} loaded")
        print(f"  Strategy:   {'loaded' if strategy else 'skipped (use --strategy)'}")
    else:
        print("\033[31mSome checks failed. Review output above.\033[0m")

    conn.close()
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
