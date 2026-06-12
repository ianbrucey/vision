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
    content: list | None = None,
    created_by: str = "agent",
    status: str = "draft",
    file_type: str = "structured_draft",
    folder: str = "artifacts",
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO drafts (case_id, name, document_type, content,
               created_by, status, file_type, folder)
               VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s)
               RETURNING id""",
            (case_id, name, document_type,
             json.dumps(content or []), created_by, status, file_type, folder),
        )
        return cur.fetchone()[0]


def update_draft(
    conn: connection,
    draft_id: int,
    name: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    content: list | None = None,
    file_type: str | None = None,
    folder: str | None = None,
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


def get_draft(conn: connection, draft_id: int) -> dict | None:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM drafts WHERE id = %s", (draft_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_drafts(conn: connection, case_id: int, folder: str | None = None) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if folder is not None:
            cur.execute(
                """SELECT id, case_id, name, document_type, file_type, folder,
                          status, created_by,
                          jsonb_array_length(content) AS block_count,
                          created_at, updated_at
                   FROM drafts WHERE case_id = %s AND folder = %s
                   ORDER BY updated_at DESC""",
                (case_id, folder),
            )
        else:
            cur.execute(
                """SELECT id, case_id, name, document_type, file_type, folder,
                          status, created_by,
                          jsonb_array_length(content) AS block_count,
                          created_at, updated_at
                   FROM drafts WHERE case_id = %s
                   ORDER BY updated_at DESC""",
                (case_id,),
            )
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
]
