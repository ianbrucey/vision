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
    ensure_correspondence_schema,
    ensure_journal_schema,
    ensure_folders_schema,
    ensure_solicitations_schema,
    ensure_solicitation_triage_schema,
    ensure_vendors_schema,
    ensure_vendor_matching_schema,
    ensure_vendor_matches_manual_schema,
    ensure_vendor_matches_cap_schema,
    ensure_vendor_outreach_schema,
    ensure_vendor_outreach_email_schema,
    ensure_vendor_outreach_messages_schema,
    ensure_workspace_pdf_filetype_schema,
    ensure_sam_notices_schema,
    ensure_sam_notice_import_job_schema,
    ensure_forecast_opportunities_schema,
    ensure_saved_reports_schema,
    ensure_ga_doas_opportunities_schema,
    ensure_dibbs_rfqs_schema,
    ensure_pipeline_processing_schema,
    ensure_subcontracting_leads_schema,
    ensure_fix_sam_notices_unique_schema,
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
        print("  Creating missing extensions...")
        conn = connect()
        try:
            with conn.cursor() as cur:
                if not exts["pgvector"]:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    print("  pgvector: CREATED")
                if not exts["pg_trgm"]:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                    print("  pg_trgm: CREATED")
        finally:
            conn.close()

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

        corr = ensure_correspondence_schema()
        for path in corr:
            print(f"  Corr:     {path}")

        journal = ensure_journal_schema()
        for path in journal:
            print(f"  Journal:  {path}")

        folders = ensure_folders_schema()
        for path in folders:
            print(f"  Folders:  {path}")

        solicitations = ensure_solicitations_schema()
        for path in solicitations:
            print(f"  Solicit:  {path}")

        triage = ensure_solicitation_triage_schema()
        for path in triage:
            print(f"  Triage:   {path}")

        vendors = ensure_vendors_schema()
        for path in vendors:
            print(f"  Vendors:  {path}")

        vendor_matching = ensure_vendor_matching_schema()
        for path in vendor_matching:
            print(f"  Matching: {path}")

        vendor_matches_manual = ensure_vendor_matches_manual_schema()
        for path in vendor_matches_manual:
            print(f"  ManualVM: {path}")

        vendor_matches_cap = ensure_vendor_matches_cap_schema()
        for path in vendor_matches_cap:
            print(f"  VMCap:    {path}")

        vendor_outreach = ensure_vendor_outreach_schema()
        for path in vendor_outreach:
            print(f"  Outreach: {path}")

        vendor_outreach_email = ensure_vendor_outreach_email_schema()
        for path in vendor_outreach_email:
            print(f"  OutreachEmail: {path}")

        vendor_outreach_messages = ensure_vendor_outreach_messages_schema()
        for path in vendor_outreach_messages:
            print(f"  OutreachMsgs: {path}")

        workspace_pdf = ensure_workspace_pdf_filetype_schema()
        for path in workspace_pdf:
            print(f"  WkspPDF:   {path}")

        sam_notices = ensure_sam_notices_schema()
        for path in sam_notices:
            print(f"  SamNotices:{path}")

        sam_import = ensure_sam_notice_import_job_schema()
        for path in sam_import:
            print(f"  SamImport:{path}")

        forecasts = ensure_forecast_opportunities_schema()
        for path in forecasts:
            print(f"  Forecasts:{path}")

        reports = ensure_saved_reports_schema()
        for path in reports:
            print(f"  Reports:  {path}")

        ga_doas = ensure_ga_doas_opportunities_schema()
        for path in ga_doas:
            print(f"  GaDoas:   {path}")

        dibbs = ensure_dibbs_rfqs_schema()
        for path in dibbs:
            print(f"  DIBBS:    {path}")

        pipeline = ensure_pipeline_processing_schema()
        for path in pipeline:
            print(f"  Pipeline: {path}")

        sub_leads = ensure_subcontracting_leads_schema()
        for path in sub_leads:
            print(f"  SubLeads: {path}")

        fix_unique = ensure_fix_sam_notices_unique_schema()
        for path in fix_unique:
            print(f"  FixUnique:{path}")
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

    # Expected tables from all four schema files + migrations
    expected = {
        # 001_core.sql
        "cases", "parties", "allegations", "documents", "sections",
        "blocks", "block_headings", "citations", "events", "workspaces",
        "embedding_cache", "users", "schema_migrations", "jobs",
        "drafts", "tasks", "task_documents", "company_profiles",
        "business_vault", "vault_documents",
        # 002_strategy.sql
        "rhetorical_moves", "case_facts", "strategies", "doctrine_elements",
        "strategy_propositions", "strategy_facts", "proposition_fact_mappings",
        "proposition_authorities", "adversarial_attacks", "adversarial_turns",
        "proposition_overlay_gates", "gauntlet_check_categories",
        "gauntlet_check_definitions", "strategy_gauntlet_results",
        # 003_chat.sql
        "session_store_entries", "chat_sessions", "chat_messages",
        # 004_correspondence.sql
        "correspondence_threads", "correspondence_items",
        "correspondence_attachments",
        # 005_journal.sql
        "journal_entries",
        # 007_solicitations.sql
        "solicitations",
        # 009_vendors.sql
        "vendors",
        # 010_vendor_matching.sql
        "vendor_matches",
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
