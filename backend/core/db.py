"""
Vision — Database Connection & Schema Management.

Provides the connection primitives and insert helpers for the evidence store
and case core. Schema definitions live in .sql files (not Python strings) so
they can be reviewed, versioned, and migrated independently.

Port of section_mapping_20260505/pipeline/db.py — cleaned up and aligned with
the vision/schema.sql contract.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection

# ---------------------------------------------------------------------------
# Configuration — override via environment or .env
# ---------------------------------------------------------------------------

# Path to the schema files, relative to this module
_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
_SCHEMA_FILES = [
    "001_core.sql",
    # 002_strategy.sql is applied separately when the strategy
    # engine is initialized. It depends on tables in 001_core.sql.
]


def _load_dotenv() -> None:
    """Load environment variables from .env files if not already set.

    Checks, in order:
      1. The project root .env (war_room/.env)
      2. The vision directory .env (war_room/scripts/vision/.env)

    Existing environment variables take precedence (never overwritten).
    """
    candidates = [
        _SCHEMA_DIR.parents[1] / ".env",                    # vision/.env
    ]
    for env_path in candidates:
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and key not in os.environ:
                os.environ[key] = value


# Load .env BEFORE reading config values from os.environ
_load_dotenv()

_DEFAULT_HOST = os.environ.get("VISION_DB_HOST", "127.0.0.1")
_DEFAULT_PORT = int(os.environ.get("VISION_DB_PORT", "5433"))
_DEFAULT_DB = os.environ.get("VISION_DB_DATABASE", "vision")
_DEFAULT_USER = os.environ.get("VISION_DB_USERNAME", "vision")
_DEFAULT_PASSWORD = os.environ.get("VISION_DB_PASSWORD", "vision_dev")


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def connect() -> connection:
    """Return a new psycopg2 connection using configured credentials."""
    conn = psycopg2.connect(
        host=_DEFAULT_HOST,
        port=_DEFAULT_PORT,
        dbname=_DEFAULT_DB,
        user=_DEFAULT_USER,
        password=_DEFAULT_PASSWORD,
    )
    with conn.cursor() as cur:
        cur.execute("SET search_path TO vision, agent_work, public")
    return conn


@contextmanager
def tx():
    """Context manager yielding a connection with autocommit off.

    Commits on clean exit, rolls back on exception, always closes.
    """
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema management
# ---------------------------------------------------------------------------

def ensure_schema() -> list[str]:
    """Apply all schema files in order. Idempotent — uses IF NOT EXISTS.

    Returns the list of schema file paths that were applied.
    """
    applied = []
    with tx() as conn:
        with conn.cursor() as cur:
            for filename in _SCHEMA_FILES:
                sql_path = _SCHEMA_DIR / filename
                if not sql_path.exists():
                    raise FileNotFoundError(
                        f"Schema file not found: {sql_path}"
                    )
                cur.execute(sql_path.read_text())
                applied.append(str(sql_path))
    return applied


def ensure_strategy_schema() -> list[str]:
    """Apply the strategy engine schema. Call after ensure_schema().

    Requires schema.sql tables to already exist.
    """
    sql_path = _SCHEMA_DIR / "002_strategy.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Strategy schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_chat_schema() -> list[str]:
    """Apply the chat infrastructure schema. Call after ensure_schema().

    Creates session_store_entries, chat_sessions, and chat_messages tables.
    Idempotent — uses IF NOT EXISTS.
    """
    sql_path = _SCHEMA_DIR / "003_chat.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Chat schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_correspondence_schema() -> list[str]:
    """Apply the correspondence tracker schema.

    Creates correspondence_threads, correspondence_items, and
    correspondence_attachments tables. Idempotent — uses IF NOT EXISTS.
    """
    sql_path = _SCHEMA_DIR / "004_correspondence.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Correspondence schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


# ---------------------------------------------------------------------------
# Workspace management
# ---------------------------------------------------------------------------

def ensure_default_workspace(conn: connection, case_id: int) -> int:
    """Ensure a 'Main' workspace exists for the given case. Returns the workspace id.
    If one already exists, returns the first workspace found. Idempotent.
    """
    import psycopg2.extras
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT id FROM workspaces WHERE case_id = %s ORDER BY id LIMIT 1",
            (case_id,),
        )
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute(
            """INSERT INTO workspaces (case_id, name, phase, status)
               VALUES (%s, 'Main', 'other', 'active')
               RETURNING id""",
            (case_id,),
        )
        return cur.fetchone()["id"]


def list_workspaces(conn: connection, case_id: int) -> list[dict]:
    """List all workspaces for a case."""
    import psycopg2.extras
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """SELECT id, case_id, name, phase, description, parent_id, status,
                      metadata, created_at, updated_at
               FROM workspaces WHERE case_id = %s
               ORDER BY created_at""",
            (case_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def ensure_folders_schema() -> list[str]:
    """Apply the nested folders schema.

    Creates the folders table for hierarchical file organization.
    Idempotent — uses IF NOT EXISTS.
    """
    sql_path = _SCHEMA_DIR / "006_folders.sql"
    if not sql_path.exists():
        raise FileNotFoundError(f"Folders schema file not found: {sql_path}")
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


# ---------------------------------------------------------------------------
# Folder CRUD
# ---------------------------------------------------------------------------

def insert_folder(
    conn: connection,
    case_id: int,
    name: str,
    parent_id: int | None = None,
    workspace_id: int | None = None,
) -> int:
    """Insert a folder. Returns the new folder ID."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO folders (case_id, workspace_id, name, parent_id)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (case_id, workspace_id, parent_id, name) DO UPDATE
               SET updated_at = now()
               RETURNING id""",
            (case_id, workspace_id, name, parent_id),
        )
        return cur.fetchone()[0]


def list_folders(
    conn: connection,
    case_id: int,
    workspace_id: int | None = None,
    parent_id: int | None = 0,
) -> list[dict]:
    """List folders for a case/workspace. parent_id=None/0 returns root folders, -1 returns all."""
    import psycopg2.extras
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if parent_id == -1:  # sentinel for all folders
            cur.execute(
                """SELECT id, case_id, workspace_id, name, parent_id, sort_order,
                          created_at, updated_at
                   FROM folders WHERE case_id = %s
                   AND workspace_id IS NOT DISTINCT FROM %s
                   ORDER BY sort_order, name""",
                (case_id, workspace_id),
            )
        elif parent_id == 0 or parent_id is None:  # sentinel for root folders
            cur.execute(
                """SELECT id, case_id, workspace_id, name, parent_id, sort_order,
                          created_at, updated_at
                   FROM folders WHERE case_id = %s
                   AND workspace_id IS NOT DISTINCT FROM %s
                   AND parent_id IS NULL
                   ORDER BY sort_order, name""",
                (case_id, workspace_id),
            )
        else:
            cur.execute(
                """SELECT id, case_id, workspace_id, name, parent_id, sort_order,
                          created_at, updated_at
                   FROM folders WHERE case_id = %s
                   AND workspace_id IS NOT DISTINCT FROM %s
                   AND parent_id IS NOT DISTINCT FROM %s
                   ORDER BY sort_order, name""",
                (case_id, workspace_id, parent_id),
            )
        return [dict(row) for row in cur.fetchall()]


def get_folder(conn: connection, folder_id: int) -> dict | None:
    """Fetch a single folder by ID."""
    import psycopg2.extras
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM folders WHERE id = %s", (folder_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def ensure_journal_schema() -> list[str]:
    """Apply the journal entries schema.

    Creates the journal_entries table for cross-session agent continuity.
    Idempotent — uses IF NOT EXISTS.
    """
    sql_path = _SCHEMA_DIR / "005_journal.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Journal schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_solicitations_schema() -> list[str]:
    """Apply the solicitation ingestion schema.

    Creates the solicitations table (Option A: domain table backed by a
    `cases` row via case_id) and extends jobs.job_type/documents.source
    with 'sam_fetch'/'sam_gov'. Idempotent — uses IF NOT EXISTS.
    """
    sql_path = _SCHEMA_DIR / "007_solicitations.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Solicitations schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_solicitation_triage_schema() -> list[str]:
    """Apply the solicitation triage pipeline schema.

    Adds triage classification, quick-kill, and the 5 partner-facing HTML
    artifact columns to `solicitations`, plus the 'solicitation_triage'
    job_type. Idempotent — uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS.
    """
    sql_path = _SCHEMA_DIR / "008_solicitation_triage.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Solicitation triage schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_vendors_schema() -> list[str]:
    """Apply the unified vendor registry schema.

    Creates the vendors table with full-text search, trigram indexes,
    and socioeconomic flag indexes. Idempotent — uses IF NOT EXISTS.
    """
    sql_path = _SCHEMA_DIR / "009_vendors.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Vendors schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_vendor_matching_schema() -> list[str]:
    """Apply the vendor matching schema.

    Creates the vendor_matches table (ranked candidate vendors per
    solicitation) plus matching/outreach-template columns on
    `solicitations`, and extends `jobs.job_type` with 'vendor_matching'.
    Idempotent — uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS.
    """
    sql_path = _SCHEMA_DIR / "010_vendor_matching.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Vendor matching schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_vendor_matches_manual_schema() -> list[str]:
    """Apply the manual vendor match migration.

    Extends `vendor_matches.naics_match_type` to allow 'manual', for
    vendors attached directly by a user (T7 — inline vendor creation).
    Idempotent — drops/re-adds the CHECK constraint each run.
    """
    sql_path = _SCHEMA_DIR / "011_vendor_matches_manual.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Manual vendor matches schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_vendor_matches_cap_schema() -> list[str]:
    """Apply the vendor matches cap increase migration.

    Raises `vendor_matches.rank`'s hard cap from 25 to 30, giving manual
    adds (T7) headroom on top of a full 25-match automated result set.
    Idempotent — drops/re-adds the CHECK constraint each run.
    """
    sql_path = _SCHEMA_DIR / "012_vendor_matches_cap.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Vendor matches cap schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_vendor_outreach_schema() -> list[str]:
    """Apply the vendor outreach tracking migration.

    Adds `outreach_status`, `outreach_requested_at`, `outreach_received_at`,
    and `outreach_doc_id` to `vendor_matches` (T8). Idempotent — uses
    ADD COLUMN IF NOT EXISTS / drop-then-add for the CHECK constraint.
    """
    sql_path = _SCHEMA_DIR / "013_vendor_outreach.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Vendor outreach schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_vendor_outreach_email_schema() -> list[str]:
    """Apply the vendor outreach email migration (T10).

    Adds outreach_message_id/outreach_reply_token to vendor_matches and
    extends jobs.job_type with 'inbound_email'. Idempotent.
    """
    sql_path = _SCHEMA_DIR / "014_vendor_outreach_email.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Vendor outreach email schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_vendor_outreach_messages_schema() -> list[str]:
    """Apply vendor outreach messages migrations (T10c, v31).

    Creates vendor_outreach_messages table, then adds 'received' status.
    Idempotent.
    """
    applied = []
    for filename in ("015_vendor_outreach_messages.sql", "022_vendor_outreach_received_status.sql", "023_inbound_read_at.sql"):
        sql_path = _SCHEMA_DIR / filename
        if not sql_path.exists():
            raise FileNotFoundError(f"Vendor outreach messages schema file not found: {sql_path}")
        with tx() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_path.read_text())
        applied.append(str(sql_path))
    return applied


def ensure_workspace_pdf_filetype_schema() -> list[str]:
    """Apply the workspace PDF file type migration (v25).

    Adds 'pdf' to the drafts.file_type CHECK constraint.
    Idempotent — drops and re-adds the constraint.
    """
    sql_path = _SCHEMA_DIR / "016_workspace_pdf_filetype.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Workspace PDF file type schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_sam_notices_schema() -> list[str]:
    """Apply the SAM.gov databank notices migration (v26).

    Creates sam_notices table with full-text search and indexes.
    Idempotent.
    """
    sql_path = _SCHEMA_DIR / "017_sam_notices.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"SAM notices schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_sam_notice_import_job_schema() -> list[str]:
    """Apply the SAM notice import job type migration (v27).

    Adds 'sam_notice_import' to jobs.job_type CHECK constraint.
    Idempotent — drops and re-adds the constraint.
    """
    sql_path = _SCHEMA_DIR / "018_sam_notice_import_job.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"SAM notice import job schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_forecast_opportunities_schema() -> list[str]:
    """Apply the forecast opportunities migration (v28).

    Creates forecast_opportunities table with full-text search.
    Idempotent.
    """
    sql_path = _SCHEMA_DIR / "019_forecast_opportunities.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"Forecast opportunities schema file not found: {sql_path}"
        )
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_saved_reports_schema() -> list[str]:
    """Apply saved reports migrations (v29–v30).

    Creates saved_reports table, then makes case_id nullable so reports
    can be global (not tied to a single case).
    Idempotent.
    """
    applied = []
    for filename in ("020_saved_reports.sql", "021_saved_reports_nullable_case_id.sql"):
        sql_path = _SCHEMA_DIR / filename
        if not sql_path.exists():
            raise FileNotFoundError(f"Saved reports schema file not found: {sql_path}")
        with tx() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_path.read_text())
        applied.append(str(sql_path))
    return applied


def ensure_ga_doas_opportunities_schema() -> list[str]:
    """Apply the GA DOAS opportunities migration (v31).

    Creates ga_doas_opportunities table for Georgia state procurement.
    Idempotent.
    """
    sql_path = _SCHEMA_DIR / "021_ga_doas_opportunities.sql"
    if not sql_path.exists():
        raise FileNotFoundError(f"GA DOAS opportunities schema file not found: {sql_path}")
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_dibbs_rfqs_schema() -> list[str]:
    """Apply the DIBBS RFQs migration (v32). Idempotent."""
    sql_path = _SCHEMA_DIR / "022_dibbs_rfqs.sql"
    if not sql_path.exists():
        raise FileNotFoundError(f"DIBBS RFQs schema file not found: {sql_path}")
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


def ensure_publog_flis_schema() -> list[str]:
    """Apply the Publog FLIS migration (v33). Idempotent."""
    sql_path = _SCHEMA_DIR / "023_publog_flis.sql"
    if not sql_path.exists():
        raise FileNotFoundError(f"Publog FLIS schema file not found: {sql_path}")
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]


# ---------------------------------------------------------------------------
# Journal CRUD
# ---------------------------------------------------------------------------

def insert_journal_entry(
    conn: connection,
    case_id: int,
    entry_type: str,
    content: str,
    title: str | None = None,
    metadata: dict | None = None,
) -> int:
    """Insert a journal entry. Returns the new entry ID."""
    import json as _json
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO journal_entries (case_id, entry_type, title, content, metadata)
               VALUES (%s, %s, %s, %s, %s::jsonb)
               RETURNING id""",
            (case_id, entry_type, title, content,
             _json.dumps(metadata or {})),
        )
        return cur.fetchone()[0]


def list_journal_entries(
    conn: connection,
    case_id: int,
    limit: int = 20,
    entry_type: str | None = None,
) -> list[dict]:
    """List journal entries for a case, newest first. Optionally filter by type."""
    import psycopg2.extras
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if entry_type:
            cur.execute(
                """SELECT id, case_id, entry_type, title, content, metadata, created_at
                   FROM journal_entries
                   WHERE case_id = %s AND entry_type = %s
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (case_id, entry_type, limit),
            )
        else:
            cur.execute(
                """SELECT id, case_id, entry_type, title, content, metadata, created_at
                   FROM journal_entries
                   WHERE case_id = %s
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (case_id, limit),
            )
        return [dict(row) for row in cur.fetchall()]


def drop_schema() -> None:
    """Drop all vision tables. DESTRUCTIVE — for development only."""
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS vision CASCADE")
            cur.execute("DROP SCHEMA IF EXISTS agent_work CASCADE")
    print("[db] vision + agent_work schemas dropped.")


def reset_schema() -> list[str]:
    """drop_schema() + ensure_schema(). Fresh start."""
    drop_schema()
    return ensure_schema()


# ---------------------------------------------------------------------------
# Insert helpers — thin wrappers that return the new row id
# ---------------------------------------------------------------------------

def _j(d: dict | None) -> str:
    """Serialize a dict to a JSONB-safe string."""
    return json.dumps(d) if d else "{}"


# -- documents ---------------------------------------------------------------

def insert_document(
    conn: connection,
    case_id: int,
    name: str,
    page_count: int | None = None,
    storage_path: str | None = None,
    document_type: str | None = None,
    source: str = "user_upload",
    metadata: dict | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO documents (case_id, name, page_count,
               storage_path, document_type, source, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
               ON CONFLICT (case_id, name)
               DO UPDATE SET page_count = EXCLUDED.page_count,
                             updated_at = now()
               RETURNING id""",
            (case_id, name, page_count, storage_path, document_type,
             source, _j(metadata)),
        )
        return cur.fetchone()[0]


# -- sections ----------------------------------------------------------------

def insert_section(
    conn: connection,
    document_id: int,
    datalab_id: str | None = None,
    parent_id: int | None = None,
    heading_level: int | None = None,
    title: str | None = None,
    page_start: int = 0,
    page_end: int | None = None,
    block_count: int = 0,
    search_text: str = "",
    heading_chain: list[str] | None = None,
    metadata: dict | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO sections (document_id, datalab_id, parent_id,
               heading_level, title, page_start, page_end, block_count,
               search_text, heading_chain, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::text[], %s::jsonb)
               RETURNING id""",
            (document_id, datalab_id, parent_id, heading_level, title,
             page_start, page_end, block_count, search_text,
             heading_chain or [], _j(metadata)),
        )
        return cur.fetchone()[0]


# -- blocks ------------------------------------------------------------------

def insert_block(
    conn: connection,
    document_id: int,
    datalab_id: str | None = None,
    section_id: int | None = None,
    block_type: str = "Text",
    page: int = 0,
    html_content: str | None = None,
    text_content: str | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    metadata: dict | None = None,
) -> int:
    bbox_x1, bbox_y1, bbox_x2, bbox_y2 = bbox or (None, None, None, None)
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO blocks (document_id, datalab_id, section_id,
               block_type, page, html_content, text_content,
               bbox_x1, bbox_y1, bbox_x2, bbox_y2, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
               RETURNING id""",
            (document_id, datalab_id, section_id, block_type, page,
             html_content, text_content, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
             _j(metadata)),
        )
        return cur.fetchone()[0]


# -- block headings ----------------------------------------------------------

def insert_block_heading(
    conn: connection,
    block_id: int,
    section_id: int,
    heading_level: int,
    depth: int = 1,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO block_headings (block_id, section_id,
               heading_level, depth)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (block_id, section_id, heading_level)
               DO NOTHING""",
            (block_id, section_id, heading_level, depth),
        )


# -- cases -------------------------------------------------------------------

def insert_case(
    conn: connection,
    name: str,
    case_type: str,
    narrative: str | None = None,
    description: str | None = None,
    case_number: str | None = None,
    jurisdiction: str | None = None,
    filing_date: str | None = None,
    metadata: dict | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO cases (name, case_type, narrative, description,
               case_number, jurisdiction, filing_date, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
               RETURNING id""",
            (name, case_type, narrative, description, case_number,
             jurisdiction, filing_date, _j(metadata)),
        )
        return cur.fetchone()[0]


# -- parties -----------------------------------------------------------------

def insert_party(
    conn: connection,
    case_id: int,
    name: str,
    party_kind: str = "individual",
    roles: list[str] | None = None,
    notes: str | None = None,
    discovered_by: str = "user",
    metadata: dict | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO parties (case_id, name, party_kind, roles,
               notes, discovered_by, metadata)
               VALUES (%s, %s, %s, %s::text[], %s, %s, %s::jsonb)
               RETURNING id""",
            (case_id, name, party_kind, roles or [], notes,
             discovered_by, _j(metadata)),
        )
        return cur.fetchone()[0]


# -- allegations -------------------------------------------------------------

def insert_allegation(
    conn: connection,
    case_id: int,
    allegation_id: str,
    text: str,
    category: str | None = None,
    targets: list[int] | None = None,
    extraction_focus: list[str] | None = None,
    metadata: dict | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO allegations (case_id, allegation_id, text,
               category, targets, extraction_focus, metadata)
               VALUES (%s, %s, %s, %s, %s::int[], %s::text[], %s::jsonb)
               ON CONFLICT (case_id, allegation_id)
               DO UPDATE SET text = EXCLUDED.text,
                             category = EXCLUDED.category,
                             updated_at = now()
               RETURNING id""",
            (case_id, allegation_id, text, category,
             targets or [], extraction_focus or [], _j(metadata)),
        )
        return cur.fetchone()[0]


# -- events ------------------------------------------------------------------

def insert_event(
    conn: connection,
    case_id: int,
    summary: str,
    kind: str = "other",
    event_at: str | None = None,
    event_date: str | None = None,
    actor: str | None = None,
    actor_id: int | None = None,
    source: str = "agent",
    sequence_hint: int = 0,
    metadata: dict | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO events (case_id, summary, kind, event_at,
               event_date, actor, actor_id, source, sequence_hint, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
               RETURNING id""",
            (case_id, summary, kind, event_at, event_date, actor,
             actor_id, source, sequence_hint, _j(metadata)),
        )
        return cur.fetchone()[0]


# -- citations ---------------------------------------------------------------

def insert_citation(
    conn: connection,
    case_id: int,
    source_type: str,
    source_id: int,
    block_id: int,
    quote: str | None = None,
    page: int | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO citations (case_id, source_type, source_id,
               block_id, quote, page)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (case_id, source_type, source_id, block_id, quote, page),
        )
        return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# Query helpers — the read side of the query interface (Phase 4)
# ---------------------------------------------------------------------------

def get_document_structure(conn: connection, document_id: int) -> list[dict]:
    """Return the section outline for a document — the table of contents."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """SELECT id, title, heading_level, page_start, page_end,
                      block_count, heading_chain
               FROM sections
               WHERE document_id = %s
               ORDER BY page_start, id""",
            (document_id,),
        )
        return cur.fetchall()


def get_block_context(
    conn: connection,
    block_id: int,
    window: int = 3,
) -> list[dict]:
    """Return a block plus ±N surrounding blocks for reading in context."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """WITH target AS (
                   SELECT document_id, page, id FROM blocks WHERE id = %s
               )
               SELECT b.*
               FROM blocks b, target t
               WHERE b.document_id = t.document_id
                 AND b.page BETWEEN t.page - 1 AND t.page + 1
               ORDER BY b.page, b.id""",
            (block_id,),
        )
        return cur.fetchall()


# -- drafts ------------------------------------------------------------------

def insert_draft(
    conn: connection,
    case_id: int,
    name: str,
    document_type: str = "letter",
    content: list | dict | None = None,
    created_by: str = "agent",
    status: str = "draft",
    file_type: str = "structured_draft",
    folder: str = "artifacts",
    workspace_id: int | None = None,
    folder_id: int | None = None,
    metadata: dict | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO drafts (case_id, name, document_type, content,
               created_by, status, file_type, folder, workspace_id, folder_id,
               metadata)
               VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s::jsonb)
               RETURNING id""",
            (case_id, name, document_type,
             json.dumps(content if content is not None else []),
             created_by, status, file_type, folder, workspace_id, folder_id,
             json.dumps(metadata) if metadata else "{}"),
        )
        return cur.fetchone()[0]


def update_draft(
    conn: connection,
    draft_id: int,
    name: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    content: list | dict | None = None,
    file_type: str | None = None,
    folder: str | None = None,
    metadata: dict | None = None,
    folder_id: int | None = None,
) -> dict | None:
    sets = []
    params: list[Any] = []
    if name is not None:
        sets.append("name = %s"); params.append(name)
    if document_type is not None:
        sets.append("document_type = %s"); params.append(document_type)
    if status is not None:
        sets.append("status = %s"); params.append(status)
    if content is not None:
        sets.append("content = %s::jsonb"); params.append(json.dumps(content))
    if file_type is not None:
        sets.append("file_type = %s"); params.append(file_type)
    if folder is not None:
        sets.append("folder = %s"); params.append(folder)
    if metadata is not None:
        sets.append("metadata = %s::jsonb"); params.append(json.dumps(metadata))
    if folder_id is not None:
        sets.append("folder_id = %s"); params.append(folder_id)
    if not sets:
        return None
    sets.append("updated_at = now()")
    params.append(draft_id)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"UPDATE drafts SET {', '.join(sets)} WHERE id = %s RETURNING *",
            tuple(params),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def update_folder(
    conn: connection, folder_id: int, name: str | None = None, parent_id: int | None = None
) -> dict | None:
    """Update a folder's name or parent."""
    updates = []
    params = []
    if name is not None:
        updates.append("name = %s"); params.append(name)
    if parent_id is not None:
        updates.append("parent_id = %s"); params.append(parent_id)

    if not updates:
        return get_folder(conn, folder_id)

    updates.append("updated_at = now()")
    params.append(folder_id)

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"UPDATE folders SET {', '.join(updates)} WHERE id = %s RETURNING *",
            tuple(params),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete_folder(conn: connection, folder_id: int) -> bool:
    """Delete a folder and cascade delete all its files and subfolders."""
    with conn.cursor() as cur:
        # 1. Delete all files (drafts) inside this folder and any subfolders
        cur.execute("""
            WITH RECURSIVE folder_tree AS (
                SELECT id FROM folders WHERE id = %s
                UNION ALL
                SELECT f.id FROM folders f
                INNER JOIN folder_tree ft ON f.parent_id = ft.id
            )
            DELETE FROM drafts WHERE folder_id IN (SELECT id FROM folder_tree)
        """, (folder_id,))

        # 2. Delete the folder (subfolders cascade automatically via ON DELETE CASCADE)
        cur.execute("DELETE FROM folders WHERE id = %s", (folder_id,))
        return cur.rowcount > 0


def get_draft(conn: connection, draft_id: int) -> dict | None:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM drafts WHERE id = %s", (draft_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_drafts(
    conn: connection,
    case_id: int,
    folder: str | None = None,
    folder_id: int | None = None,
    workspace_id: int | None = None,
) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        base_sql = """SELECT id, case_id, name, document_type, file_type, folder, folder_id,
                             status, created_by, workspace_id,
                             CASE
                               WHEN jsonb_typeof(content) = 'array'
                                 THEN jsonb_array_length(content)
                               WHEN jsonb_typeof(content) = 'object' AND content ? 'views'
                                 THEN jsonb_array_length(content->'views')
                               WHEN jsonb_typeof(content) = 'object'
                                 THEN 1
                               ELSE 0
                             END AS block_count,
                             created_at, updated_at
                      FROM drafts WHERE case_id = %s"""
        params: list = [case_id]

        if folder is not None:
            base_sql += " AND folder = %s"
            params.append(folder)
        if folder_id is not None:
            base_sql += " AND folder_id = %s"
            params.append(folder_id)
        if workspace_id is not None:
            base_sql += " AND workspace_id = %s"
            params.append(workspace_id)

        base_sql += " ORDER BY updated_at DESC"
        cur.execute(base_sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]


def delete_draft(conn: connection, draft_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM drafts WHERE id = %s", (draft_id,))
        return cur.rowcount > 0


def update_block(
    conn: connection,
    draft_id: int,
    block_id: str,
    content: str,
) -> dict | None:
    """Update a single block's content within a draft's content array."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """UPDATE drafts
               SET content = (
                   SELECT jsonb_agg(
                       CASE WHEN elem->>'id' = %s
                            THEN jsonb_set(elem, '{content}', to_jsonb(%s::text))
                            ELSE elem
                       END
                   )
                   FROM jsonb_array_elements(content) AS elem
               ),
               updated_at = now()
               WHERE id = %s
               RETURNING *""",
            (block_id, content, draft_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


# -- tasks -------------------------------------------------------------------

def insert_task(
    conn: connection,
    case_id: int,
    title: str,
    notes: str | None = None,
    assignee_id: str | None = None,
    deadline: str | None = None,
    priority: str = "medium",
    created_by: str | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO tasks (case_id, title, notes, assignee_id,
               deadline, priority, created_by)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (case_id, title, notes, assignee_id, deadline, priority,
             created_by),
        )
        return cur.fetchone()[0]


def update_task(
    conn: connection,
    task_id: int,
    title: str | None = None,
    notes: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assignee_id: str | None = None,
    deadline: str | None = None,
) -> dict | None:
    sets = []
    params: list[Any] = []
    for col, val in [("title", title), ("notes", notes), ("status", status),
                      ("priority", priority), ("assignee_id", assignee_id),
                      ("deadline", deadline)]:
        if val is not None:
            sets.append(f"{col} = %s"); params.append(val)
    if status == "complete":
        sets.append("completed_at = now()")
    if not sets:
        return None
    sets.append("updated_at = now()")
    params.append(task_id)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"UPDATE tasks SET {', '.join(sets)} WHERE id = %s RETURNING *",
            tuple(params),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_task(conn: connection, task_id: int) -> dict | None:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
        row = cur.fetchone()
        if not row:
            return None
        task = dict(row)
        cur.execute(
            """SELECT d.id, d.name, d.page_count, d.document_type
               FROM task_documents td
               JOIN documents d ON td.document_id = d.id
               WHERE td.task_id = %s
               ORDER BY td.attached_at""",
            (task_id,),
        )
        task["documents"] = [dict(r) for r in cur.fetchall()]
        return task


def list_tasks(
    conn: connection,
    case_id: int,
    status: str | None = None,
    assignee_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    clauses = ["case_id = %s"]
    params: list[Any] = [case_id]
    if status:
        clauses.append("status = %s"); params.append(status)
    if assignee_id:
        clauses.append("assignee_id = %s"); params.append(assignee_id)
    params.append(limit)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"""SELECT t.*,
                       (SELECT count(*) FROM task_documents
                        WHERE task_id = t.id) AS document_count
                FROM tasks t
                WHERE {' AND '.join(clauses)}
                ORDER BY
                  CASE WHEN t.deadline IS NULL THEN 1 ELSE 0 END,
                  t.deadline ASC NULLS LAST,
                  t.priority = 'urgent' DESC,
                  t.priority = 'high' DESC,
                  t.created_at DESC
                LIMIT %s""",
            tuple(params),
        )
        return [dict(row) for row in cur.fetchall()]


def delete_task(conn: connection, task_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        return cur.rowcount > 0


def attach_task_documents(
    conn: connection,
    task_id: int,
    document_ids: list[int],
) -> int:
    count = 0
    with conn.cursor() as cur:
        for did in document_ids:
            cur.execute(
                """INSERT INTO task_documents (task_id, document_id)
                   VALUES (%s, %s)
                   ON CONFLICT (task_id, document_id) DO NOTHING""",
                (task_id, did),
            )
            count += cur.rowcount
    return count


def detach_task_document(
    conn: connection,
    task_id: int,
    document_id: int,
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM task_documents WHERE task_id = %s AND document_id = %s",
            (task_id, document_id),
        )
        return cur.rowcount > 0


# -- company profiles --------------------------------------------------------

def insert_company_profile(
    conn: connection,
    name: str,
    content: dict | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO company_profiles (name, content)
               VALUES (%s, %s::jsonb)
               RETURNING id""",
            (name, json.dumps(content or {})),
        )
        return cur.fetchone()[0]


def update_company_profile(
    conn: connection,
    profile_id: int,
    name: str | None = None,
    description: str | None = None,
    content: dict | None = None,
    status: str | None = None,
    source_docs: list | None = None,
    docs_case_id: int | None = None,
    statement_draft_id: int | None = None,
) -> dict | None:
    sets = []
    params: list[Any] = []
    if name is not None:
        sets.append("name = %s"); params.append(name)
    if description is not None:
        sets.append("description = %s"); params.append(description)
    if content is not None:
        sets.append("content = %s::jsonb"); params.append(json.dumps(content))
    if status is not None:
        sets.append("status = %s"); params.append(status)
    if source_docs is not None:
        sets.append("source_docs = %s::jsonb"); params.append(json.dumps(source_docs))
    if docs_case_id is not None:
        sets.append("docs_case_id = %s"); params.append(docs_case_id)
    if statement_draft_id is not None:
        sets.append("statement_draft_id = %s"); params.append(statement_draft_id)
    if not sets:
        return None
    sets.append("updated_at = now()")
    params.append(profile_id)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"UPDATE company_profiles SET {', '.join(sets)} WHERE id = %s RETURNING *",
            tuple(params),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_company_profile(conn: connection, profile_id: int) -> dict | None:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM company_profiles WHERE id = %s", (profile_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_company_profiles(conn: connection) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM company_profiles ORDER BY updated_at DESC"
        )
        return [dict(row) for row in cur.fetchall()]


def delete_company_profile(conn: connection, profile_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM company_profiles WHERE id = %s", (profile_id,))
        return cur.rowcount > 0


# -- business vault ---------------------------------------------------------

def insert_vault_item(
    conn: connection,
    case_id: int | None,
    kind: str,
    name: str,
    status: str = "active",
    notes: str | None = None,
    data: dict | None = None,
    created_by: str = "user",
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO business_vault (case_id, kind, name, status,
               notes, data, created_by)
               VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
               RETURNING id""",
            (case_id, kind, name, status, notes, _j(data), created_by),
        )
        return cur.fetchone()[0]


def update_vault_item(
    conn: connection,
    vault_id: int,
    kind: str | None = None,
    name: str | None = None,
    status: str | None = None,
    notes: str | None = None,
    data: dict | None = None,
    case_id: int | None = None,
) -> dict | None:
    sets: list[str] = []
    params: list[Any] = []
    if kind is not None:
        sets.append("kind = %s"); params.append(kind)
    if name is not None:
        sets.append("name = %s"); params.append(name)
    if status is not None:
        sets.append("status = %s"); params.append(status)
    if notes is not None:
        sets.append("notes = %s"); params.append(notes)
    if data is not None:
        sets.append("data = %s::jsonb"); params.append(_j(data))
    if case_id is not None:
        sets.append("case_id = %s"); params.append(case_id)
    if not sets:
        return None
    sets.append("updated_at = now()")
    params.append(vault_id)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"UPDATE business_vault SET {', '.join(sets)} WHERE id = %s RETURNING *",
            tuple(params),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_vault_item(conn: connection, vault_id: int) -> dict | None:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM business_vault WHERE id = %s", (vault_id,))
        row = cur.fetchone()
        if row:
            d = dict(row)
            # Attach document references
            cur.execute(
                """SELECT d.id, d.name, d.page_count, d.document_type
                   FROM documents d
                   JOIN vault_documents vd ON vd.document_id = d.id
                   WHERE vd.vault_id = %s
                   ORDER BY d.name""",
                (vault_id,),
            )
            d["documents"] = [dict(r) for r in cur.fetchall()]
            return d
        return None


def list_vault_items(
    conn: connection,
    case_id: int | None = None,
    kind: str | None = None,
) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        clauses = []
        params: list[Any] = []
        if case_id is not None:
            clauses.append("case_id = %s"); params.append(case_id)
        else:
            clauses.append("case_id IS NULL")
        if kind is not None:
            clauses.append("kind = %s"); params.append(kind)
        where = " AND ".join(clauses)
        cur.execute(
            f"""SELECT bv.*,
                       (SELECT count(*) FROM vault_documents vd
                        WHERE vd.vault_id = bv.id) AS document_count
                FROM business_vault bv
                WHERE {where}
                ORDER BY updated_at DESC""",
            tuple(params),
        )
        return [dict(row) for row in cur.fetchall()]


def delete_vault_item(conn: connection, vault_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM business_vault WHERE id = %s", (vault_id,))
        return cur.rowcount > 0


def attach_vault_documents(
    conn: connection, vault_id: int, document_ids: list[int]
) -> int:
    """Attach documents to a vault item. Returns count attached."""
    attached = 0
    with conn.cursor() as cur:
        for doc_id in document_ids:
            cur.execute(
                """INSERT INTO vault_documents (vault_id, document_id)
                   VALUES (%s, %s)
                   ON CONFLICT (vault_id, document_id) DO NOTHING""",
                (vault_id, doc_id),
            )
            attached += cur.rowcount
    return attached


def detach_vault_document(
    conn: connection, vault_id: int, document_id: int
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM vault_documents WHERE vault_id = %s AND document_id = %s",
            (vault_id, document_id),
        )
        return cur.rowcount > 0


# ============================================================================
# Calendar Events & Reminders
# ============================================================================

def insert_calendar_event(
    conn: connection,
    case_id: int,
    title: str,
    start_time: str,
    end_time: str | None = None,
    all_day: bool = False,
    category: str = "other",
    description: str | None = None,
    location: str | None = None,
    created_by: str = "user",
    workspace_id: int | None = None,
    metadata: dict | None = None,
) -> int:
    """Create a calendar event. Returns the new event ID."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO calendar_events
               (case_id, workspace_id, title, description, start_time, end_time,
                all_day, category, location, created_by, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (case_id, workspace_id, title, description, start_time, end_time,
             all_day, category, location, created_by,
             json.dumps(metadata) if metadata else "{}"),
        )
        return cur.fetchone()[0]


def update_calendar_event(
    conn: connection,
    event_id: int,
    title: str | None = None,
    description: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    all_day: bool | None = None,
    category: str | None = None,
    location: str | None = None,
) -> dict | None:
    """Partial update. Only provided (non-None) fields are updated."""
    sets = []
    params: list[Any] = []
    for col, val in [
        ("title", title), ("description", description),
        ("start_time", start_time), ("end_time", end_time),
        ("all_day", all_day), ("category", category), ("location", location),
    ]:
        if val is not None:
            sets.append(f"{col} = %s"); params.append(val)
    if not sets:
        return None
    sets.append("updated_at = now()")
    params.append(event_id)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"UPDATE calendar_events SET {', '.join(sets)} WHERE id = %s RETURNING *",
            tuple(params),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_calendar_event(conn: connection, event_id: int) -> dict | None:
    """Get a calendar event with its attached reminders."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM calendar_events WHERE id = %s", (event_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        event = dict(row)
        cur.execute(
            """SELECT * FROM reminders
               WHERE event_id = %s
               ORDER BY remind_at ASC""",
            (event_id,),
        )
        event["reminders"] = [dict(r) for r in cur.fetchall()]
        return event


def list_calendar_events(
    conn: connection,
    case_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
    category: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """List calendar events with optional date range and category filters."""
    clauses = ["case_id = %s"]
    params: list[Any] = [case_id]
    if start_date:
        clauses.append("start_time::DATE >= %s"); params.append(start_date)
    if end_date:
        clauses.append("start_time::DATE <= %s"); params.append(end_date)
    if category:
        clauses.append("category = %s"); params.append(category)
    params.append(limit)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"""SELECT * FROM calendar_events
                WHERE {' AND '.join(clauses)}
                ORDER BY start_time ASC, created_at DESC
                LIMIT %s""",
            tuple(params),
        )
        return [dict(row) for row in cur.fetchall()]


def delete_calendar_event(conn: connection, event_id: int) -> bool:
    """Delete a calendar event. Cascades to reminders via FK ON DELETE CASCADE."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM calendar_events WHERE id = %s", (event_id,))
        return cur.rowcount > 0


def insert_reminder(
    conn: connection,
    case_id: int,
    title: str,
    remind_at: str,
    event_id: int | None = None,
    category: str = "other",
    description: str | None = None,
    created_by: str = "user",
    metadata: dict | None = None,
) -> int:
    """Create a reminder (standalone or event-attached). Returns the new reminder ID."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO reminders
               (case_id, event_id, title, description, remind_at, category,
                created_by, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (case_id, event_id, title, description, remind_at, category,
             created_by, json.dumps(metadata) if metadata else "{}"),
        )
        return cur.fetchone()[0]


def update_reminder(
    conn: connection,
    reminder_id: int,
    title: str | None = None,
    description: str | None = None,
    remind_at: str | None = None,
    category: str | None = None,
    status: str | None = None,
) -> dict | None:
    """Partial update. Only provided (non-None) fields are updated."""
    sets = []
    params: list[Any] = []
    for col, val in [
        ("title", title), ("description", description),
        ("remind_at", remind_at), ("category", category), ("status", status),
    ]:
        if val is not None:
            sets.append(f"{col} = %s"); params.append(val)
    if not sets:
        return None
    sets.append("updated_at = now()")
    params.append(reminder_id)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"UPDATE reminders SET {', '.join(sets)} WHERE id = %s RETURNING *",
            tuple(params),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_reminder(conn: connection, reminder_id: int) -> dict | None:
    """Get a single reminder by ID."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM reminders WHERE id = %s", (reminder_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_reminders(
    conn: connection,
    case_id: int,
    status: str | None = None,
    category: str | None = None,
    event_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    """List reminders with optional filters."""
    clauses = ["case_id = %s"]
    params: list[Any] = [case_id]
    if status:
        clauses.append("status = %s"); params.append(status)
    if category:
        clauses.append("category = %s"); params.append(category)
    if event_id is not None:
        clauses.append("event_id = %s"); params.append(event_id)
    params.append(limit)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"""SELECT * FROM reminders
                WHERE {' AND '.join(clauses)}
                ORDER BY
                  CASE WHEN status = 'pending' THEN 0 ELSE 1 END,
                  remind_at ASC
                LIMIT %s""",
            tuple(params),
        )
        return [dict(row) for row in cur.fetchall()]


def delete_reminder(conn: connection, reminder_id: int) -> bool:
    """Delete a reminder."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM reminders WHERE id = %s", (reminder_id,))
        return cur.rowcount > 0


__all__ = [
    "connect", "tx",
    "ensure_schema", "ensure_strategy_schema", "ensure_chat_schema",
    "ensure_correspondence_schema",
    "drop_schema", "reset_schema",
    "insert_document", "insert_section", "insert_block", "insert_block_heading",
    "insert_case", "insert_party", "insert_allegation", "insert_event",
    "insert_citation",
    "insert_draft", "update_draft", "get_draft", "list_drafts",
    "delete_draft", "update_block",
    "insert_task", "update_task", "get_task", "list_tasks", "delete_task",
    "attach_task_documents", "detach_task_document",
    "insert_company_profile", "update_company_profile",
    "get_company_profile", "list_company_profiles", "delete_company_profile",
    "get_document_structure", "get_block_context",
    "insert_vault_item", "update_vault_item", "get_vault_item",
    "list_vault_items", "delete_vault_item",
    "attach_vault_documents", "detach_vault_document",
    "ensure_journal_schema", "insert_journal_entry", "list_journal_entries",
    "ensure_default_workspace", "list_workspaces",
    "insert_calendar_event", "update_calendar_event", "get_calendar_event",
    "list_calendar_events", "delete_calendar_event",
    "insert_reminder", "update_reminder", "get_reminder",
    "list_reminders", "delete_reminder",
    "ensure_folders_schema", "insert_folder", "list_folders",
    "ensure_solicitations_schema", "ensure_solicitation_triage_schema",
    "ensure_vendors_schema", "ensure_vendor_matching_schema",
    "ensure_vendor_matches_manual_schema", "ensure_vendor_matches_cap_schema",
    "ensure_vendor_outreach_schema",
    "ensure_vendor_outreach_email_schema",
    "ensure_vendor_outreach_messages_schema",
    "ensure_workspace_pdf_filetype_schema",
    "ensure_sam_notices_schema",
    "ensure_sam_notice_import_job_schema",
    "ensure_forecast_opportunities_schema",
    "ensure_saved_reports_schema",
    "ensure_ga_doas_opportunities_schema",
    "ensure_dibbs_rfqs_schema",
]
