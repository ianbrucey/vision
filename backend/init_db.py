#!/usr/bin/env python3
"""
Vision — Database Initialization Script.

Idempotent. Run this once on a new machine (or after nuking the DB) before
starting the API. Safe to run repeatedly — all schema files use IF NOT EXISTS.

Usage:
    cd scripts/vision/backend
    source ../.venv/bin/activate
    python init_db.py

Also callable from start.sh as: python init_db.py
"""

from __future__ import annotations

import sys
import time

from core.db import (
    connect,
    ensure_schema,
    ensure_strategy_schema,
    ensure_chat_schema,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_db(timeout: int = 30) -> bool:
    """Wait for PostgreSQL to accept connections. Returns True on success."""
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            conn = connect()
            conn.close()
            return True
        except Exception as e:
            last_err = e
            time.sleep(1)
    print(f"  FAILED to connect after {timeout}s: {last_err}", file=sys.stderr)
    return False


def _check_extensions() -> dict[str, bool]:
    """Verify required extensions are installed."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm')"
            )
            installed = {row[0] for row in cur.fetchall()}
    finally:
        conn.close()
    return {
        "pgvector": "vector" in installed,
        "pg_trgm": "pg_trgm" in installed,
    }


def _list_tables() -> list[str]:
    """Return sorted list of vision schema tables."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT tablename FROM pg_tables
                   WHERE schemaname = 'vision'
                   ORDER BY tablename"""
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("Vision — Database Initialization")
    print("=" * 60)

    # 1. Wait for PostgreSQL
    print("\n[1/4] Connecting to PostgreSQL...")
    if not _wait_for_db():
        return 1
    print("  OK — PostgreSQL is accepting connections.")

    # 2. Check extensions
    print("\n[2/4] Checking extensions...")
    exts = _check_extensions()
    for name, ok in exts.items():
        status = "OK" if ok else "MISSING"
        print(f"  {name}: {status}")
    if not all(exts.values()):
        print("  ERROR: Missing extensions. Install with:")
        print("    CREATE EXTENSION IF NOT EXISTS vector;")
        print("    CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        print("  Or use the docker image: pgvector/pgvector:pg15")
        return 1

    # 3. Apply schemas
    print("\n[3/4] Applying schemas...")
    try:
        core = ensure_schema()
        for path in core:
            print(f"  Core:    {path}")

        strat = ensure_strategy_schema()
        for path in strat:
            print(f"  Strategy: {path}")

        chat = ensure_chat_schema()
        for path in chat:
            print(f"  Chat:     {path}")
    except Exception as e:
        print(f"  ERROR applying schemas: {e}", file=sys.stderr)
        return 1

    # 4. Verify
    print("\n[4/4] Verifying...")
    tables = _list_tables()
    print(f"  Tables created: {len(tables)}")

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version, name FROM vision.schema_migrations ORDER BY version")
            migrations = cur.fetchall()
    finally:
        conn.close()

    print(f"  Migrations recorded: {len(migrations)}")
    for version, name in migrations:
        print(f"    v{version} — {name}")

    # Expected tables from all three schema files
    expected = {
        # 001_core.sql
        "cases", "parties", "allegations", "documents", "sections",
        "blocks", "block_headings", "citations", "events", "workspaces",
        "embedding_cache", "users", "schema_migrations", "jobs",
        # 002_strategy.sql
        "rhetorical_moves", "case_facts", "strategies", "doctrine_elements",
        "strategy_propositions", "strategy_facts", "proposition_fact_mappings",
        "proposition_authorities", "adversarial_attacks", "adversarial_turns",
        "proposition_overlay_gates", "gauntlet_check_categories",
        "gauntlet_check_definitions", "strategy_gauntlet_results",
        # 003_chat.sql
        "session_store_entries", "chat_sessions", "chat_messages",
    }
    actual = set(tables)
    missing = expected - actual
    extra = actual - expected

    if missing:
        print(f"\n  ⚠️  Missing tables: {missing}")
    if extra:
        print(f"  ℹ️  Extra tables: {extra}")

    if not missing:
        print(f"\n  ✅ All {len(expected)} expected tables present.")

    print("\n" + "=" * 60)
    print("Database initialization complete.")
    print("You can now start the API: python -m uvicorn api.main:app --port 8400")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
