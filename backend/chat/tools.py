"""
Vision — Database Tools for the Agent SDK.

These are the functions the agent can call to interact with the case database.
Each function is a self-contained tool with typed inputs and documented outputs.

The agent uses these to explore cases, search evidence, and read/write strategy
data. All tools are read-only except where noted.

Pattern: each tool accepts a psycopg2 connection factory as its first argument
(not exposed to the agent — injected by the ChatManager when registering tools).
"""

from __future__ import annotations

import json
from typing import Any


# ---------------------------------------------------------------------------
# DB helpers — not exposed as tools, used internally
# ---------------------------------------------------------------------------

def _query(conn_factory, sql: str, params: tuple | None = None) -> list[dict]:
    """Execute a read-only SQL query and return dict rows."""
    import psycopg2.extras
    conn = conn_factory()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def _query_one(conn_factory, sql: str, params: tuple | None = None) -> dict | None:
    rows = _query(conn_factory, sql, params)
    return rows[0] if rows else None


def _execute(conn_factory, sql: str, params: tuple | None = None) -> int:
    """Execute a write SQL and return the new row id (or affected count)."""
    import psycopg2.extras
    conn = conn_factory()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            conn.commit()
            try:
                return cur.fetchone()["id"]
            except Exception:
                return cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Case tools
# ---------------------------------------------------------------------------

def list_cases(conn_factory, *, status: str | None = None, limit: int = 20) -> dict:
    """List cases in the system, newest first."""
    sql = """SELECT id, name, case_type, status, jurisdiction, description, created_at
             FROM cases"""
    params = []
    if status:
        sql += " WHERE status = %s"
        params.append(status)
    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    return {"cases": _query(conn_factory, sql, tuple(params))}


def get_case(conn_factory, *, case_id: int) -> dict:
    """Get full case details with parties, allegations, and documents."""
    case = _query_one(conn_factory, "SELECT * FROM cases WHERE id = %s", (case_id,))
    if not case:
        return {"error": f"Case {case_id} not found"}
    case["parties"] = _query(
        conn_factory,
        "SELECT * FROM parties WHERE case_id = %s ORDER BY name",
        (case_id,),
    )
    case["allegations"] = _query(
        conn_factory,
        "SELECT * FROM allegations WHERE case_id = %s ORDER BY sort_order, allegation_id",
        (case_id,),
    )
    case["documents"] = _query(
        conn_factory,
        """SELECT id, name, page_count, document_type, ocr_status, source, created_at
           FROM documents WHERE case_id = %s ORDER BY created_at DESC""",
        (case_id,),
    )
    case["events"] = _query(
        conn_factory,
        "SELECT * FROM events WHERE case_id = %s ORDER BY event_date, sequence_hint",
        (case_id,),
    )
    # Convert non-serializable types
    case.pop("narrative", None)  # too large for chat context — fetched separately if needed
    return {"case": _serialize_row(case)}


# ---------------------------------------------------------------------------
# Evidence store tools
# ---------------------------------------------------------------------------

def search_blocks(
    conn_factory,
    *,
    case_id: int,
    query: str,
    document_id: int | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
    limit: int = 20,
) -> dict:
    """Full-text search across evidence store blocks for a case.

    Uses PostgreSQL tsvector for keyword/phrase search. Returns ranked
    results with page number, section context, and text snippets.
    """
    params: list[Any] = [case_id, _plainto_tsquery(query)]
    doc_filter = ""
    if document_id is not None:
        doc_filter += " AND b.document_id = %s"
        params.append(document_id)
    if page_start is not None:
        doc_filter += " AND b.page >= %s"
        params.append(page_start)
    if page_end is not None:
        doc_filter += " AND b.page <= %s"
        params.append(page_end)

    sql = f"""SELECT b.id, b.document_id, b.page, b.block_type, b.section_id,
                     ts_rank(b.text_tsv, to_tsquery('english', %s)) AS rank,
                     left(b.text_content, 500) AS snippet,
                     d.name AS document_name,
                     s.title AS section_title
              FROM blocks b
              JOIN documents d ON b.document_id = d.id
              LEFT JOIN sections s ON b.section_id = s.id
              WHERE d.case_id = %s
                AND b.text_tsv @@ to_tsquery('english', %s)
                {doc_filter}
              ORDER BY rank DESC
              LIMIT %s"""
    # params order: case_id, query, query, (optional doc_id/doc filters), limit
    params_full = [case_id, params[1], params[1]] + params[2:] + [limit]
    return {"blocks": _query(conn_factory, sql, tuple(params_full))}


def _plainto_tsquery(text: str) -> str:
    """Convert user text to a tsquery-safe string using plainto_tsquery logic."""
    # Split into words, prefix-match with :* for stemming, join with &
    words = text.strip().split()
    if not words:
        return text
    # Build a simple tsquery: word1 & word2 & ...
    return " & ".join(f"{w}:*" for w in words if w.isalnum())


def get_document_structure(conn_factory, *, document_id: int) -> dict:
    """Return the section outline (table of contents) for a document."""
    sections = _query(
        conn_factory,
        """SELECT id, title, heading_level, page_start, page_end,
                  block_count, heading_chain
           FROM sections
           WHERE document_id = %s
           ORDER BY page_start, id""",
        (document_id,),
    )
    doc = _query_one(
        conn_factory,
        "SELECT id, name, page_count FROM documents WHERE id = %s",
        (document_id,),
    )
    return {"document": doc, "sections": sections}


def get_block_context(
    conn_factory,
    *,
    block_id: int,
    window: int = 3,
) -> dict:
    """Return a block plus surrounding blocks for reading in context."""
    # Get the target block first
    target = _query_one(conn_factory, "SELECT * FROM blocks WHERE id = %s", (block_id,))
    if not target:
        return {"error": f"Block {block_id} not found"}
    # Get surrounding blocks
    neighbors = _query(
        conn_factory,
        """SELECT b.* FROM blocks b
           WHERE b.document_id = %s
             AND b.page BETWEEN %s AND %s
           ORDER BY b.page, b.id""",
        (target["document_id"], target["page"] - 1, target["page"] + 1),
    )
    return {"target": _serialize_row(target), "context": _serialize_rows(neighbors)}


# ---------------------------------------------------------------------------
# Strategy tools (read)
# ---------------------------------------------------------------------------

def get_strategies(conn_factory, *, case_id: int) -> dict:
    """List all strategies for a case."""
    strategies = _query(
        conn_factory,
        """SELECT id, name, strategy_type, posture, jurisdiction, status,
                  objective, filing_deadline, created_at
           FROM strategies WHERE case_id = %s ORDER BY created_at DESC""",
        (case_id,),
    )
    return {"strategies": strategies}


def get_strategy_tree(conn_factory, *, strategy_id: int) -> dict:
    """Return the full proposition tree for a strategy."""
    strategy = _query_one(
        conn_factory, "SELECT * FROM strategies WHERE id = %s", (strategy_id,)
    )
    if not strategy:
        return {"error": f"Strategy {strategy_id} not found"}

    # Recursive CTE to get the tree
    propositions = _query(
        conn_factory,
        """WITH RECURSIVE tree AS (
               SELECT id, parent_proposition_id, proposition_type, gate_type,
                      party_id, label, proposition_text, current_status,
                      sort_order, 0 AS depth, ARRAY[sort_order, id] AS path
               FROM strategy_propositions
               WHERE strategy_id = %s AND parent_proposition_id IS NULL
               UNION ALL
               SELECT sp.id, sp.parent_proposition_id, sp.proposition_type, sp.gate_type,
                      sp.party_id, sp.label, sp.proposition_text, sp.current_status,
                      sp.sort_order, t.depth + 1, t.path || sp.sort_order || sp.id
               FROM strategy_propositions sp
               JOIN tree t ON sp.parent_proposition_id = t.id
               WHERE sp.strategy_id = %s
           )
           SELECT * FROM tree ORDER BY path""",
        (strategy_id, strategy_id),
    )
    strategy["propositions"] = propositions
    strategy["proposition_count"] = len(propositions)
    return {"strategy": _serialize_row(strategy)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_row(row: dict) -> dict:
    """Convert non-JSON-safe types in a dict row."""
    from datetime import date, datetime
    for k, v in row.items():
        if isinstance(v, (date, datetime)):
            row[k] = v.isoformat()
        elif isinstance(v, bytes):
            row[k] = v.decode("utf-8", errors="replace")
    return row


def _serialize_rows(rows: list[dict]) -> list[dict]:
    return [_serialize_row(r) for r in rows]
