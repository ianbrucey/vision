"""
Vision — SDK-Native Database Tools.

SDK @tool handlers registered on the "vision" MCP server.
The agent discovers them as mcp__vision__search_blocks, etc.

Security:
  - case_id injected via contextvars — never a tool parameter
  - Every resource-ID tool verifies the resource belongs to the current case
  - Errors return is_error=True so the agent can react without crashing the loop
"""

from __future__ import annotations

import contextvars
import json
from datetime import date, datetime
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool, ToolAnnotations

from core.db import connect, ensure_schema

# ---------------------------------------------------------------------------
# Context — case_id injected by AgentSession.send_message()
# ---------------------------------------------------------------------------

_current_case_id: contextvars.ContextVar[int] = contextvars.ContextVar(
    "current_case_id"
)


def set_current_case_id(case_id: int) -> None:
    _current_case_id.set(case_id)


def get_current_case_id() -> int:
    return _current_case_id.get()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _conn():
    ensure_schema()
    return connect()


def _query(sql: str, params: tuple | None = None) -> list[dict]:
    import psycopg2.extras

    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def _query_one(sql: str, params: tuple | None = None) -> dict | None:
    rows = _query(sql, params)
    return rows[0] if rows else None


def _serialize(obj: Any) -> Any:
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    return obj


def _json(obj: Any) -> str:
    return json.dumps(_serialize(obj), indent=2, default=str)


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------

def _doc_in_case(document_id: int, case_id: int) -> bool:
    return _query_one(
        "SELECT 1 FROM documents WHERE id = %s AND case_id = %s",
        (document_id, case_id),
    ) is not None


def _block_in_case(block_id: int, case_id: int) -> bool:
    return _query_one(
        """SELECT 1 FROM blocks b
           JOIN documents d ON b.document_id = d.id
           WHERE b.id = %s AND d.case_id = %s""",
        (block_id, case_id),
    ) is not None


def _section_in_case(section_id: int, case_id: int) -> bool:
    return _query_one(
        """SELECT 1 FROM sections s
           JOIN documents d ON s.document_id = d.id
           WHERE s.id = %s AND d.case_id = %s""",
        (section_id, case_id),
    ) is not None


def _strategy_in_case(strategy_id: int, case_id: int) -> bool:
    return _query_one(
        "SELECT 1 FROM strategies WHERE id = %s AND case_id = %s",
        (strategy_id, case_id),
    ) is not None


# ---------------------------------------------------------------------------
# Embedding helper (for semantic search)
# ---------------------------------------------------------------------------

def _embed_query(query_text: str) -> str:
    """Embed query text via Mistral. Returns pgvector literal string."""
    from search.embed import _get_client, _truncate, EMBED_MODEL

    client = _get_client()
    resp = client.embeddings.create(
        model=EMBED_MODEL,
        inputs=[_truncate(query_text)],
    )
    vec = resp.data[0].embedding
    return "[" + ",".join(repr(float(v)) for v in vec) + "]"


# ---------------------------------------------------------------------------
# Layer 1 — Orientation
# ---------------------------------------------------------------------------


@tool(
    "get_case",
    "Complete overview of the current case: metadata, parties, allegations, "
    "documents list, events timeline, and strategies. Use this FIRST to "
    "understand what you're working with before searching.",
    {},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_case(args: dict[str, Any]) -> dict[str, Any]:
    case_id = get_current_case_id()
    try:
        case = _query_one("SELECT * FROM cases WHERE id = %s", (case_id,))
        if not case:
            return _error(f"Case {case_id} not found.")

        case["parties"] = _query(
            "SELECT * FROM parties WHERE case_id = %s ORDER BY name", (case_id,)
        )
        case["allegations"] = _query(
            "SELECT * FROM allegations WHERE case_id = %s ORDER BY sort_order, allegation_id",
            (case_id,),
        )
        case["documents"] = _query(
            """SELECT id, name, page_count, document_type, ocr_status, source, created_at
               FROM documents WHERE case_id = %s ORDER BY created_at DESC""",
            (case_id,),
        )
        case["events"] = _query(
            "SELECT * FROM events WHERE case_id = %s ORDER BY event_date, sequence_hint",
            (case_id,),
        )
        case["strategies"] = _query(
            """SELECT id, name, strategy_type, posture, jurisdiction, status,
                      objective, filing_deadline, created_at
               FROM strategies WHERE case_id = %s ORDER BY created_at DESC""",
            (case_id,),
        )
        case.pop("narrative", None)  # too large — fetch separately if needed
        return _result({"case": case})
    except Exception as exc:
        return _error(f"get_case failed: {exc}")


@tool(
    "list_documents",
    "List all documents in the current case. Optionally filter by document type. "
    "Use this to see what evidence is available before searching within it.",
    {
        "type": "object",
        "properties": {
            "document_type": {
                "type": "string",
                "description": "Filter by type: medical_record, contract, transcript, "
                "correspondence, pleading, tax_return, etc.",
            },
        },
        "required": [],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_documents(args: dict[str, Any]) -> dict[str, Any]:
    case_id = get_current_case_id()
    document_type = args.get("document_type")
    try:
        params: list[Any] = [case_id]
        filt = ""
        if document_type:
            filt = " AND document_type = %s"
            params.append(document_type)
        rows = _query(
            f"""SELECT id, name, page_count, document_type, ocr_status,
                       source, created_at
                FROM documents WHERE case_id = %s{filt}
                ORDER BY created_at DESC""",
            tuple(params),
        )
        return _result({
            "count": len(rows),
            "filter": document_type or "all",
            "documents": rows,
        })
    except Exception as exc:
        return _error(f"list_documents failed: {exc}")


# ---------------------------------------------------------------------------
# Layer 2 — Search
# ---------------------------------------------------------------------------


@tool(
    "search_blocks",
    "Full-text keyword/phrase search across all documents in the case. "
    "Best for: specific names, dates, medical terms, legal phrases, "
    "or any exact wording. Returns ranked results with page numbers, "
    "document names, section titles, and text snippets. "
    "Use this when you know the words you're looking for. "
    "For thematic/conceptual queries, use semantic_search instead.",
    {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords or phrase to search for. "
                "Examples: 'cardiac arrest', 'breach of contract', 'Dr. Chen'.",
            },
            "document_id": {
                "type": "integer",
                "description": "Restrict to a specific document.",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 20, max 50).",
            },
        },
        "required": ["query"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def search_blocks(args: dict[str, Any]) -> dict[str, Any]:
    case_id = get_current_case_id()
    query_text = args["query"]
    document_id = args.get("document_id")
    limit = min(args.get("limit", 20), 50)

    try:
        tsq = " & ".join(w + ":*" for w in query_text.strip().split() if w.isalnum())
        if not tsq:
            return _error("Query contains no searchable terms.")

        params: list[Any] = [case_id, tsq]
        doc_filt = ""
        if document_id is not None:
            if not _doc_in_case(document_id, case_id):
                return _error(f"Document {document_id} not in case {case_id}.")
            doc_filt = " AND b.document_id = %s"
            params.append(document_id)

        sql = f"""SELECT b.id, b.document_id, b.page, b.block_type,
                         b.section_id,
                         ts_rank(b.text_tsv, to_tsquery('english', %s)) AS rank,
                         ts_headline('english', b.text_content,
                                     to_tsquery('english', %s),
                                     'MaxWords=40, MinWords=10') AS snippet,
                         d.name AS document_name,
                         s.title AS section_title
                  FROM blocks b
                  JOIN documents d ON b.document_id = d.id
                  LEFT JOIN sections s ON b.section_id = s.id
                  WHERE d.case_id = %s
                    AND b.text_tsv @@ to_tsquery('english', %s)
                    {doc_filt}
                  ORDER BY rank DESC
                  LIMIT %s"""
        params_full = [case_id, tsq, tsq] + params[2:] + [limit]
        rows = _query(sql, tuple(params_full))

        return _result({
            "query": query_text,
            "count": len(rows),
            "results": rows,
        })
    except Exception as exc:
        return _error(f"search_blocks failed: {exc}")


@tool(
    "semantic_search",
    "Concept/meaning search across all documents in the case using vector "
    "embeddings. Best for: thematic queries where you don't know the exact "
    "wording, finding related concepts, or discovering relevant sections "
    "that use different terminology. "
    "Returns sections ranked by semantic similarity with their document info. "
    "For exact terms, use search_blocks. For both, use search_hybrid.",
    {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Concept or question to find. "
                "Examples: 'standard of care for post-operative infection', "
                "'evidence of prior knowledge of the defect'.",
            },
            "document_id": {
                "type": "integer",
                "description": "Restrict to a specific document.",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 15, max 30).",
            },
        },
        "required": ["query"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def semantic_search(args: dict[str, Any]) -> dict[str, Any]:
    case_id = get_current_case_id()
    query_text = args["query"]
    document_id = args.get("document_id")
    limit = min(args.get("limit", 15), 30)

    try:
        vec_literal = _embed_query(query_text)
    except Exception as exc:
        return _error(f"Embedding failed — embeddings may not be generated yet. "
                      f"Use search_blocks for keyword search instead. Error: {exc}")

    try:
        params: list[Any] = [case_id, vec_literal]
        doc_filt = ""
        if document_id is not None:
            if not _doc_in_case(document_id, case_id):
                return _error(f"Document {document_id} not in case {case_id}.")
            doc_filt = " AND s.document_id = %s"
            params.append(document_id)

        sql = f"""SELECT s.id AS section_id, s.document_id, s.title,
                         s.heading_level, s.page_start, s.page_end,
                         s.block_count, s.heading_chain,
                         ROUND((1 - (s.embedding <=> %s::vector))::numeric, 4)
                           AS similarity,
                         d.name AS document_name
                  FROM sections s
                  JOIN documents d ON s.document_id = d.id
                  WHERE d.case_id = %s
                    AND s.embedding IS NOT NULL
                    {doc_filt}
                  ORDER BY s.embedding <=> %s::vector
                  LIMIT %s"""
        params_full = [case_id, vec_literal] + params[2:] + [vec_literal, limit]
        rows = _query(sql, tuple(params_full))

        if not rows:
            return _result({
                "query": query_text,
                "count": 0,
                "note": "No sections with embeddings found. "
                        "Embeddings may not have been generated yet for this case. "
                        "Try search_blocks for keyword search.",
            })

        return _result({
            "query": query_text,
            "count": len(rows),
            "results": rows,
        })
    except Exception as exc:
        return _error(f"semantic_search failed: {exc}")


@tool(
    "search_hybrid",
    "Combined keyword + semantic search. Runs both search_blocks and "
    "semantic_search, then merges results into a single ranked list. "
    "Best for: important queries where missing a relevant result matters, "
    "or when you're unsure whether keyword or semantic will work better. "
    "Returns sections with similarity scores and supporting keyword snippets.",
    {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query. Used for both keyword and semantic.",
            },
            "document_id": {
                "type": "integer",
                "description": "Restrict to a specific document.",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 20, max 40).",
            },
        },
        "required": ["query"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def search_hybrid(args: dict[str, Any]) -> dict[str, Any]:
    case_id = get_current_case_id()
    query_text = args["query"]
    document_id = args.get("document_id")
    limit = min(args.get("limit", 20), 40)

    if document_id is not None and not _doc_in_case(document_id, case_id):
        return _error(f"Document {document_id} not in case {case_id}.")

    # Keyword search
    kw_results: list[dict] = []
    try:
        tsq = " & ".join(w + ":*" for w in query_text.strip().split() if w.isalnum())
        if tsq:
            params: list[Any] = [case_id, tsq]
            doc_filt = ""
            if document_id is not None:
                doc_filt = " AND b.document_id = %s"
                params.append(document_id)
            kw_results = _query(
                f"""SELECT b.id AS block_id, b.document_id, b.page,
                           b.section_id,
                           ts_headline('english', b.text_content,
                                       to_tsquery('english', %s),
                                       'MaxWords=30, MinWords=5') AS snippet,
                           d.name AS document_name
                    FROM blocks b
                    JOIN documents d ON b.document_id = d.id
                    WHERE d.case_id = %s
                      AND b.text_tsv @@ to_tsquery('english', %s)
                      {doc_filt}
                    ORDER BY ts_rank(b.text_tsv, to_tsquery('english', %s)) DESC
                    LIMIT %s""",
                tuple([case_id, tsq] + params[2:] + [tsq, limit * 2]),
            )
    except Exception:
        pass  # keyword failed — continue with semantic only

    # Semantic search
    sem_results: list[dict] = []
    try:
        vec_literal = _embed_query(query_text)
        params_s: list[Any] = [case_id, vec_literal]
        doc_filt_s = ""
        if document_id is not None:
            doc_filt_s = " AND s.document_id = %s"
            params_s.append(document_id)
        sem_results = _query(
            f"""SELECT s.id AS section_id, s.document_id, s.title,
                       s.heading_level, s.page_start, s.page_end,
                       s.block_count, s.heading_chain,
                       ROUND((1 - (s.embedding <=> %s::vector))::numeric, 4)
                         AS similarity,
                       d.name AS document_name
                FROM sections s
                JOIN documents d ON s.document_id = d.id
                WHERE d.case_id = %s
                  AND s.embedding IS NOT NULL
                  {doc_filt_s}
                ORDER BY s.embedding <=> %s::vector
                LIMIT %s""",
            tuple([case_id, vec_literal] + params_s[2:] + [vec_literal, limit]),
        )
    except Exception:
        pass  # semantic failed — continue with keyword only

    # Merge: keyword snippets grouped by section, attached to semantic results
    kw_by_section: dict[int, list[dict]] = {}
    for r in kw_results:
        sid = r.get("section_id")
        if sid:
            kw_by_section.setdefault(sid, []).append(r)

    merged = []
    seen = set()
    for sec in sem_results:
        sid = sec["section_id"]
        if sid in seen:
            continue
        seen.add(sid)
        merged.append({
            "section_id": sid,
            "document_id": sec["document_id"],
            "document_name": sec["document_name"],
            "title": sec.get("title"),
            "page_start": sec.get("page_start"),
            "page_end": sec.get("page_end"),
            "block_count": sec.get("block_count"),
            "heading_chain": sec.get("heading_chain"),
            "similarity": sec.get("similarity"),
            "keyword_snippets": [
                {"block_id": b["block_id"], "page": b["page"],
                 "snippet": b.get("snippet", "")}
                for b in kw_by_section.get(sid, [])[:3]
            ],
        })

    # Add keyword-only results not covered by semantic
    for r in kw_results:
        sid = r.get("section_id")
        if sid and sid not in seen:
            seen.add(sid)
            merged.append({
                "section_id": sid,
                "document_id": r["document_id"],
                "document_name": r["document_name"],
                "keyword_only": True,
                "keyword_snippets": [
                    {"block_id": r["block_id"], "page": r["page"],
                     "snippet": r.get("snippet", "")}
                ],
            })

    return _result({
        "query": query_text,
        "count": len(merged[:limit]),
        "keyword_hits": len(kw_results),
        "semantic_hits": len(sem_results),
        "results": merged[:limit],
    })


# ---------------------------------------------------------------------------
# Layer 3 — Structure
# ---------------------------------------------------------------------------


@tool(
    "get_document_structure",
    "Section outline (table of contents) for a document. Shows heading "
    "hierarchy, page ranges, and block counts per section. Use this to "
    "understand a document's organization before reading specific sections.",
    {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "integer",
                "description": "Document ID from get_case or list_documents.",
            },
        },
        "required": ["document_id"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_document_structure(args: dict[str, Any]) -> dict[str, Any]:
    case_id = get_current_case_id()
    document_id = args["document_id"]
    try:
        if not _doc_in_case(document_id, case_id):
            return _error(f"Document {document_id} not in case {case_id}.")

        doc = _query_one(
            "SELECT id, name, page_count, document_type FROM documents WHERE id = %s",
            (document_id,),
        )
        sections = _query(
            """SELECT id, title, heading_level, page_start, page_end,
                      block_count, heading_chain
               FROM sections WHERE document_id = %s
               ORDER BY page_start, id""",
            (document_id,),
        )
        return _result({
            "document": doc,
            "section_count": len(sections),
            "sections": sections,
        })
    except Exception as exc:
        return _error(f"get_document_structure failed: {exc}")


@tool(
    "search_sections",
    "Find sections by title text. Supports fuzzy matching — finds sections "
    "even when the title isn't an exact match. Use this to jump to a "
    "specific part of a document (e.g., 'find the operative report section').",
    {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "integer",
                "description": "Document to search within.",
            },
            "title": {
                "type": "string",
                "description": "Title text to search for. Partial matches work.",
            },
        },
        "required": ["document_id", "title"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def search_sections(args: dict[str, Any]) -> dict[str, Any]:
    case_id = get_current_case_id()
    document_id = args["document_id"]
    title = args["title"]
    try:
        if not _doc_in_case(document_id, case_id):
            return _error(f"Document {document_id} not in case {case_id}.")

        rows = _query(
            """SELECT id, title, heading_level, page_start, page_end,
                      block_count, similarity(title, %s) AS sim
               FROM sections
               WHERE document_id = %s AND title %% %s
               ORDER BY sim DESC
               LIMIT 20""",
            (title, document_id, title),
        )
        return _result({
            "document_id": document_id,
            "query": title,
            "count": len(rows),
            "sections": rows,
        })
    except Exception as exc:
        return _error(f"search_sections failed: {exc}")


# ---------------------------------------------------------------------------
# Layer 4 — Read
# ---------------------------------------------------------------------------


@tool(
    "get_block_context",
    "Read a specific block with surrounding text on adjacent pages. "
    "Returns the target block plus neighbors for full context. "
    "ALWAYS use this after search to verify a match before citing it. "
    "Never cite a search snippet alone — read the block in context first.",
    {
        "type": "object",
        "properties": {
            "block_id": {
                "type": "integer",
                "description": "Block ID from search_blocks results.",
            },
        },
        "required": ["block_id"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_block_context(args: dict[str, Any]) -> dict[str, Any]:
    case_id = get_current_case_id()
    block_id = args["block_id"]
    try:
        if not _block_in_case(block_id, case_id):
            return _error(f"Block {block_id} not in case {case_id}.")

        target = _query_one("SELECT * FROM blocks WHERE id = %s", (block_id,))
        if not target:
            return _error(f"Block {block_id} not found.")

        doc = _query_one(
            "SELECT id, name FROM documents WHERE id = %s",
            (target["document_id"],),
        )
        section = None
        if target["section_id"]:
            section = _query_one(
                "SELECT id, title, heading_level, heading_chain "
                "FROM sections WHERE id = %s",
                (target["section_id"],),
            )

        neighbors = _query(
            """SELECT b.id, b.block_type, b.page, b.text_content,
                      b.datalab_id, s.title AS section_title
               FROM blocks b
               LEFT JOIN sections s ON b.section_id = s.id
               WHERE b.document_id = %s
                 AND b.page BETWEEN %s AND %s
               ORDER BY b.page, b.id""",
            (
                target["document_id"],
                max(0, (target["page"] or 0) - 1),
                (target["page"] or 0) + 1,
            ),
        )
        return _result({
            "target": target,
            "document": doc,
            "section": section,
            "context_block_count": len(neighbors),
            "context": neighbors,
        })
    except Exception as exc:
        return _error(f"get_block_context failed: {exc}")


@tool(
    "get_blocks_in_section",
    "Read all blocks within a specific section. Use this after "
    "get_document_structure or search_sections to read an entire "
    "section's content. Returns blocks in page order.",
    {
        "type": "object",
        "properties": {
            "section_id": {
                "type": "integer",
                "description": "Section ID from get_document_structure, "
                "search_sections, or semantic_search results.",
            },
            "block_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: filter to specific block types "
                "(e.g., ['Text'] to skip headers).",
            },
            "limit": {
                "type": "integer",
                "description": "Max blocks to return (default 100, max 200).",
            },
        },
        "required": ["section_id"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_blocks_in_section(args: dict[str, Any]) -> dict[str, Any]:
    case_id = get_current_case_id()
    section_id = args["section_id"]
    block_types = args.get("block_types")
    limit = min(args.get("limit", 100), 200)

    try:
        if not _section_in_case(section_id, case_id):
            return _error(f"Section {section_id} not in case {case_id}.")

        section = _query_one(
            "SELECT id, title, heading_level, page_start, page_end, block_count "
            "FROM sections WHERE id = %s",
            (section_id,),
        )

        params: list[Any] = [section_id]
        type_filt = ""
        if block_types:
            type_filt = " AND block_type = ANY(%s)"
            params.append(block_types)
        params.append(limit)

        blocks = _query(
            f"""SELECT id, block_type, page, text_content, datalab_id
                FROM blocks
                WHERE section_id = %s{type_filt}
                ORDER BY page, id
                LIMIT %s""",
            tuple(params),
        )
        return _result({
            "section": section,
            "block_count_returned": len(blocks),
            "blocks": blocks,
        })
    except Exception as exc:
        return _error(f"get_blocks_in_section failed: {exc}")


# ---------------------------------------------------------------------------
# Layer 5 — Strategy
# ---------------------------------------------------------------------------


@tool(
    "get_strategies",
    "List all legal strategy trees built for the current case. "
    "Each strategy models a legal claim. Use this to see what "
    "analysis exists before diving into a specific strategy.",
    {},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_strategies(args: dict[str, Any]) -> dict[str, Any]:
    case_id = get_current_case_id()
    try:
        rows = _query(
            """SELECT id, name, strategy_type, posture, jurisdiction,
                      status, objective, filing_deadline, created_at
               FROM strategies WHERE case_id = %s ORDER BY created_at DESC""",
            (case_id,),
        )
        return _result({"count": len(rows), "strategies": rows})
    except Exception as exc:
        return _error(f"get_strategies failed: {exc}")


@tool(
    "get_strategy_tree",
    "Complete recursive proposition tree for a strategy. Returns claims, "
    "elements, AND/OR gates, fact mappings, and current status per node. "
    "Use this to analyze a specific legal claim in detail.",
    {
        "type": "object",
        "properties": {
            "strategy_id": {
                "type": "integer",
                "description": "Strategy ID from get_strategies.",
            },
        },
        "required": ["strategy_id"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_strategy_tree(args: dict[str, Any]) -> dict[str, Any]:
    case_id = get_current_case_id()
    strategy_id = args["strategy_id"]
    try:
        if not _strategy_in_case(strategy_id, case_id):
            return _error(f"Strategy {strategy_id} not in case {case_id}.")

        strategy = _query_one(
            "SELECT * FROM strategies WHERE id = %s", (strategy_id,)
        )
        if not strategy:
            return _error(f"Strategy {strategy_id} not found.")

        propositions = _query(
            """WITH RECURSIVE tree AS (
                   SELECT id, parent_proposition_id, proposition_type,
                          gate_type, party_id, label, proposition_text,
                          current_status, sort_order,
                          0 AS depth,
                          ARRAY[sort_order, id] AS path
                   FROM strategy_propositions
                   WHERE strategy_id = %s AND parent_proposition_id IS NULL
                   UNION ALL
                   SELECT sp.id, sp.parent_proposition_id, sp.proposition_type,
                          sp.gate_type, sp.party_id, sp.label,
                          sp.proposition_text, sp.current_status,
                          sp.sort_order, t.depth + 1,
                          t.path || sp.sort_order || sp.id
                   FROM strategy_propositions sp
                   JOIN tree t ON sp.parent_proposition_id = t.id
                   WHERE sp.strategy_id = %s
               )
               SELECT * FROM tree ORDER BY path""",
            (strategy_id, strategy_id),
        )
        strategy["propositions"] = propositions
        strategy["proposition_count"] = len(propositions)
        return _result({"strategy": strategy})
    except Exception as exc:
        return _error(f"get_strategy_tree failed: {exc}")


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

def _result(data: dict) -> dict:
    return {"content": [{"type": "text", "text": _json(data)}]}


def _error(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}], "is_error": True}


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

vision_server = create_sdk_mcp_server(
    name="vision",
    version="1.0.0",
    tools=[
        # Layer 1 — Orientation
        get_case,
        list_documents,
        # Layer 2 — Search
        search_blocks,
        semantic_search,
        search_hybrid,
        # Layer 3 — Structure
        get_document_structure,
        search_sections,
        # Layer 4 — Read
        get_block_context,
        get_blocks_in_section,
        # Layer 5 — Strategy
        get_strategies,
        get_strategy_tree,
    ],
)
