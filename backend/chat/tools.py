"""
Vision — SDK-Native Database Tools.

Each tool is an Agent SDK @tool handler registered on a per-session "vision"
MCP server. The server is created by create_vision_server(case_id), which
captures the case_id in each handler's closure — no context propagation needed.

Security:
  - case_id is hardcoded in the handler closure — the agent never sees or provides it
  - Every resource-ID tool verifies the resource belongs to the current case
  - Errors return is_error=True so the agent can react without crashing the loop
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool, ToolAnnotations

from core.db import connect, ensure_schema


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


def _result(data: dict) -> dict:
    return {"content": [{"type": "text", "text": _json(data)}]}


def _error(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}], "is_error": True}


# ---------------------------------------------------------------------------
# Embedding helper
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
# Server factory — creates a fully scoped MCP server per session
# ---------------------------------------------------------------------------


def create_vision_server(case_id: int):
    """Create a vision MCP server with all tools scoped to case_id.

    Each tool handler captures case_id from this function's closure.
    The agent never sees or provides a case_id — it's hardcoded per session.
    """

    # -- verification helpers (capture case_id) -------------------------------

    def _doc_in_case(document_id: int) -> bool:
        return _query_one(
            "SELECT 1 FROM documents WHERE id = %s AND case_id = %s",
            (document_id, case_id),
        ) is not None

    def _block_in_case(block_id: int) -> bool:
        return _query_one(
            """SELECT 1 FROM blocks b
               JOIN documents d ON b.document_id = d.id
               WHERE b.id = %s AND d.case_id = %s""",
            (block_id, case_id),
        ) is not None

    def _section_in_case(section_id: int) -> bool:
        return _query_one(
            """SELECT 1 FROM sections s
               JOIN documents d ON s.document_id = d.id
               WHERE s.id = %s AND d.case_id = %s""",
            (section_id, case_id),
        ) is not None

    def _strategy_in_case(strategy_id: int) -> bool:
        return _query_one(
            "SELECT 1 FROM strategies WHERE id = %s AND case_id = %s",
            (strategy_id, case_id),
        ) is not None

    # -- Layer 1: Orientation ------------------------------------------------

    @tool(
        "get_case",
        "Complete overview of the current case: metadata, parties, "
        "allegations, documents list, events timeline, and strategies. "
        "Use this FIRST to understand what you're working with before "
        "searching.",
        {},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def get_case(args: dict[str, Any]) -> dict[str, Any]:
        try:
            case = _query_one(
                "SELECT * FROM cases WHERE id = %s", (case_id,)
            )
            if not case:
                return _error(f"Case {case_id} not found.")

            case["parties"] = _query(
                "SELECT * FROM parties WHERE case_id = %s ORDER BY name",
                (case_id,),
            )
            case["allegations"] = _query(
                """SELECT * FROM allegations
                   WHERE case_id = %s ORDER BY sort_order, allegation_id""",
                (case_id,),
            )
            case["documents"] = _query(
                """SELECT id, name, page_count, document_type,
                          ocr_status, source, created_at
                   FROM documents WHERE case_id = %s
                   ORDER BY created_at DESC""",
                (case_id,),
            )
            case["events"] = _query(
                """SELECT * FROM events
                   WHERE case_id = %s
                   ORDER BY event_date, sequence_hint""",
                (case_id,),
            )
            case["strategies"] = _query(
                """SELECT id, name, strategy_type, posture, jurisdiction,
                          status, objective, filing_deadline, created_at
                   FROM strategies WHERE case_id = %s
                   ORDER BY created_at DESC""",
                (case_id,),
            )
            case.pop("narrative", None)
            return _result({"case": case})
        except Exception as exc:
            return _error(f"get_case failed: {exc}")

    @tool(
        "list_documents",
        "List all documents in the current case. Optionally filter by "
        "document type. Use this to see what evidence is available before "
        "searching within it.",
        {
            "type": "object",
            "properties": {
                "document_type": {
                    "type": "string",
                    "description": "Filter by type: medical_record, contract, "
                    "transcript, correspondence, pleading, tax_return, etc.",
                },
            },
            "required": [],
        },
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_documents(args: dict[str, Any]) -> dict[str, Any]:
        doc_type = args.get("document_type")
        try:
            params: list[Any] = [case_id]
            filt = ""
            if doc_type:
                filt = " AND document_type = %s"
                params.append(doc_type)
            rows = _query(
                f"""SELECT id, name, page_count, document_type,
                           ocr_status, source, created_at
                    FROM documents WHERE case_id = %s{filt}
                    ORDER BY created_at DESC""",
                tuple(params),
            )
            return _result({
                "count": len(rows),
                "filter": doc_type or "all",
                "documents": rows,
            })
        except Exception as exc:
            return _error(f"list_documents failed: {exc}")

    # -- Layer 2: Search -----------------------------------------------------

    @tool(
        "search_blocks",
        "Full-text keyword/phrase search across all documents in the case. "
        "Best for: specific names, dates, medical terms, legal phrases, "
        "or any exact wording. Returns ranked results with page numbers, "
        "document names, section titles, and highlighted text snippets. "
        "Use this when you know the words you're looking for. "
        "For thematic/conceptual queries, use semantic_search instead.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords or phrase. "
                    "Examples: 'cardiac arrest', 'breach of contract', "
                    "'Dr. Chen', 'January 2024'.",
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
        query_text = args["query"]
        document_id = args.get("document_id")
        limit = min(args.get("limit", 20), 50)

        try:
            tsq = " & ".join(
                w + ":*" for w in query_text.strip().split() if w.isalnum()
            )
            if not tsq:
                return _error("Query contains no searchable terms.")

            params: list[Any] = [case_id, tsq]
            doc_filt = ""
            if document_id is not None:
                if not _doc_in_case(document_id):
                    return _error(
                        f"Document {document_id} not in case {case_id}."
                    )
                doc_filt = " AND b.document_id = %s"
                params.append(document_id)

            sql = f"""SELECT b.id, b.document_id, b.page, b.block_type,
                             b.section_id,
                             ts_rank(b.text_tsv,
                                     to_tsquery('english', %s)) AS rank,
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
        "Concept/meaning search across all documents using vector "
        "embeddings. Best for: thematic queries where you don't know "
        "the exact wording, finding related concepts, or discovering "
        "relevant sections that use different terminology. "
        "Returns sections ranked by semantic similarity. "
        "For exact terms, use search_blocks. For both, use search_hybrid.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Concept or question. "
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
        query_text = args["query"]
        document_id = args.get("document_id")
        limit = min(args.get("limit", 15), 30)

        try:
            vec_literal = _embed_query(query_text)
        except Exception as exc:
            return _error(
                f"Embedding failed — embeddings may not be generated yet. "
                f"Use search_blocks for keyword search instead. Error: {exc}"
            )

        try:
            params: list[Any] = [case_id, vec_literal]
            doc_filt = ""
            if document_id is not None:
                if not _doc_in_case(document_id):
                    return _error(
                        f"Document {document_id} not in case {case_id}."
                    )
                doc_filt = " AND s.document_id = %s"
                params.append(document_id)

            sql = f"""SELECT s.id AS section_id, s.document_id, s.title,
                             s.heading_level, s.page_start, s.page_end,
                             s.block_count, s.heading_chain,
                             ROUND((1 - (s.embedding <=> %s::vector))::numeric,
                                   4) AS similarity,
                             d.name AS document_name
                      FROM sections s
                      JOIN documents d ON s.document_id = d.id
                      WHERE d.case_id = %s
                        AND s.embedding IS NOT NULL
                        {doc_filt}
                      ORDER BY s.embedding <=> %s::vector
                      LIMIT %s"""
            params_full = (
                [case_id, vec_literal] + params[2:] + [vec_literal, limit]
            )
            rows = _query(sql, tuple(params_full))

            if not rows:
                return _result({
                    "query": query_text,
                    "count": 0,
                    "note": (
                        "No sections with embeddings found. Embeddings "
                        "may not have been generated yet for this case. "
                        "Try search_blocks for keyword search."
                    ),
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
        "Combined keyword + semantic search. Runs both modalities and "
        "merges results into a single ranked list with similarity scores "
        "and keyword snippets. Best for: important queries where missing "
        "a relevant result matters, or when unsure which modality fits.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query used for both modalities.",
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
        query_text = args["query"]
        document_id = args.get("document_id")
        limit = min(args.get("limit", 20), 40)

        if document_id is not None and not _doc_in_case(document_id):
            return _error(f"Document {document_id} not in case {case_id}.")

        # Keyword pass
        kw_results: list[dict] = []
        try:
            tsq = " & ".join(
                w + ":*" for w in query_text.strip().split() if w.isalnum()
            )
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
                        ORDER BY ts_rank(b.text_tsv,
                                         to_tsquery('english', %s)) DESC
                        LIMIT %s""",
                    tuple(
                        [case_id, tsq] + params[2:] + [tsq, limit * 2]
                    ),
                )
        except Exception:
            pass

        # Semantic pass
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
                           ROUND((1 - (s.embedding <=> %s::vector))::numeric,
                                 4) AS similarity,
                           d.name AS document_name
                    FROM sections s
                    JOIN documents d ON s.document_id = d.id
                    WHERE d.case_id = %s
                      AND s.embedding IS NOT NULL
                      {doc_filt_s}
                    ORDER BY s.embedding <=> %s::vector
                    LIMIT %s""",
                tuple(
                    [case_id, vec_literal] + params_s[2:] + [vec_literal, limit]
                ),
            )
        except Exception:
            pass

        # Merge
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
                    {
                        "block_id": b["block_id"],
                        "page": b["page"],
                        "snippet": b.get("snippet", ""),
                    }
                    for b in kw_by_section.get(sid, [])[:3]
                ],
            })

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
                        {
                            "block_id": r["block_id"],
                            "page": r["page"],
                            "snippet": r.get("snippet", ""),
                        }
                    ],
                })

        return _result({
            "query": query_text,
            "count": len(merged[:limit]),
            "keyword_hits": len(kw_results),
            "semantic_hits": len(sem_results),
            "results": merged[:limit],
        })

    # -- Layer 3: Structure --------------------------------------------------

    @tool(
        "get_document_structure",
        "Section outline (table of contents) for a document. Shows "
        "heading hierarchy, page ranges, and block counts per section. "
        "Use this to understand a document's organization before "
        "reading specific sections.",
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
        document_id = args["document_id"]
        try:
            if not _doc_in_case(document_id):
                return _error(
                    f"Document {document_id} not in case {case_id}."
                )

            doc = _query_one(
                """SELECT id, name, page_count, document_type
                   FROM documents WHERE id = %s""",
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
        "Find sections by title text. Supports fuzzy matching — finds "
        "sections even when the title isn't exact. Use this to jump to "
        "a specific part of a document (e.g., 'find the operative "
        "report section').",
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
        document_id = args["document_id"]
        title = args["title"]
        try:
            if not _doc_in_case(document_id):
                return _error(
                    f"Document {document_id} not in case {case_id}."
                )

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

    # -- Layer 4: Read -------------------------------------------------------

    @tool(
        "get_block_context",
        "Read a specific block with surrounding text on adjacent pages. "
        "Returns the target block plus neighbors for full context. "
        "ALWAYS use this after search to verify a match before citing it. "
        "Never cite from a search snippet alone — read in context first.",
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
        block_id = args["block_id"]
        try:
            if not _block_in_case(block_id):
                return _error(f"Block {block_id} not in case {case_id}.")

            target = _query_one(
                "SELECT * FROM blocks WHERE id = %s", (block_id,)
            )
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
        "Read all blocks within a specific section. Use after "
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
                    "description": "Max blocks (default 100, max 200).",
                },
            },
            "required": ["section_id"],
        },
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def get_blocks_in_section(args: dict[str, Any]) -> dict[str, Any]:
        section_id = args["section_id"]
        block_types = args.get("block_types")
        limit = min(args.get("limit", 100), 200)

        try:
            if not _section_in_case(section_id):
                return _error(
                    f"Section {section_id} not in case {case_id}."
                )

            section = _query_one(
                "SELECT id, title, heading_level, page_start, page_end, "
                "block_count FROM sections WHERE id = %s",
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

    # -- Layer 5: Strategy ---------------------------------------------------

    @tool(
        "get_strategies",
        "List all legal strategy trees built for the current case. "
        "Each strategy models a legal claim. Use this to see what "
        "analysis exists before diving into a specific strategy.",
        {},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def get_strategies(args: dict[str, Any]) -> dict[str, Any]:
        try:
            rows = _query(
                """SELECT id, name, strategy_type, posture, jurisdiction,
                          status, objective, filing_deadline, created_at
                   FROM strategies WHERE case_id = %s
                   ORDER BY created_at DESC""",
                (case_id,),
            )
            return _result({"count": len(rows), "strategies": rows})
        except Exception as exc:
            return _error(f"get_strategies failed: {exc}")

    @tool(
        "get_strategy_tree",
        "Complete recursive proposition tree for a strategy. Returns "
        "claims, elements, AND/OR gates, fact mappings, and current "
        "status per node. Use this to analyze a specific legal claim "
        "in detail.",
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
        strategy_id = args["strategy_id"]
        try:
            if not _strategy_in_case(strategy_id):
                return _error(
                    f"Strategy {strategy_id} not in case {case_id}."
                )

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
                       WHERE strategy_id = %s
                         AND parent_proposition_id IS NULL
                       UNION ALL
                       SELECT sp.id, sp.parent_proposition_id,
                              sp.proposition_type, sp.gate_type,
                              sp.party_id, sp.label, sp.proposition_text,
                              sp.current_status, sp.sort_order,
                              t.depth + 1,
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

    # -- Layer 6: Drafting ---------------------------------------------------

    @tool(
        "list_drafts",
        "List all drafts for the current case. Returns id, name, document_type, "
        "status, block count, and timestamps. Does not return full content — "
        "use get_draft for that. Use this to see what drafts exist before "
        "creating or editing one.",
        {},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_drafts(args: dict[str, Any]) -> dict[str, Any]:
        try:
            conn = _conn()
            try:
                from core.db import list_drafts as _list_drafts
                rows = _list_drafts(conn, case_id)
            finally:
                conn.close()
            return _result({"count": len(rows), "drafts": rows})
        except Exception as exc:
            return _error(f"list_drafts failed: {exc}")

    @tool(
        "get_draft",
        "Read a draft's full content including all blocks. Use this before "
        "editing a draft so you can see the current state and target specific "
        "block IDs.",
        {
            "type": "object",
            "properties": {
                "draft_id": {
                    "type": "integer",
                    "description": "Draft ID from list_drafts.",
                },
            },
            "required": ["draft_id"],
        },
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def get_draft(args: dict[str, Any]) -> dict[str, Any]:
        draft_id = args["draft_id"]
        try:
            conn = _conn()
            try:
                from core.db import get_draft as _get_draft
                draft = _get_draft(conn, draft_id)
            finally:
                conn.close()
            if not draft:
                return _error(f"Draft {draft_id} not found.")
            if draft["case_id"] != case_id:
                return _error(f"Draft {draft_id} not in case {case_id}.")
            return _result({"draft": draft})
        except Exception as exc:
            return _error(f"get_draft failed: {exc}")

    @tool(
        "create_draft",
        "Create a new draft. The content is an array of blocks, each with "
        "a unique id (short string), a type, and text content. "
        "Use this to produce a structured document the user can review "
        "and edit in the Drafts tab.\n\n"
        "Block types:\n"
        "  section_heading    — Centered, bold, underlined section title\n"
        "  numbered_paragraph — Auto-numbered paragraph (1., 2., 3.)\n"
        "  list_item          — Letter-labeled item (a), (b), (c)\n"
        "  signature          — Signature block with top-border line\n\n"
        "Example content array:\n"
        '  [{"id":"h1","type":"section_heading","content":"BACKGROUND"},\n'
        '   {"id":"p1","type":"numbered_paragraph","content":"Vision is a..."}]',
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Display title for the draft.",
                },
                "document_type": {
                    "type": "string",
                    "enum": ["letter", "pleading", "contract", "memo", "other"],
                    "description": "Type of document.",
                },
                "content": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "type": {
                                "type": "string",
                                "enum": [
                                    "section_heading",
                                    "numbered_paragraph",
                                    "list_item",
                                    "signature",
                                ],
                            },
                            "content": {"type": "string"},
                        },
                        "required": ["id", "type", "content"],
                    },
                    "description": "Array of blocks in document order.",
                },
            },
            "required": ["name", "document_type", "content"],
        },
    )
    async def create_draft(args: dict[str, Any]) -> dict[str, Any]:
        try:
            conn = _conn()
            try:
                from core.db import insert_draft as _insert_draft
                draft_id = _insert_draft(
                    conn,
                    case_id=case_id,
                    name=args["name"],
                    document_type=args["document_type"],
                    content=args["content"],
                    created_by="agent",
                )
            finally:
                conn.close()
            return _result({
                "draft_id": draft_id,
                "name": args["name"],
                "document_type": args["document_type"],
                "block_count": len(args["content"]),
            })
        except Exception as exc:
            return _error(f"create_draft failed: {exc}")

    @tool(
        "update_draft",
        "Modify a draft — update its name, status, or replace specific "
        "blocks. For targeted edits, provide only the blocks that changed "
        "(they'll be matched by id). To replace the entire content, provide "
        "a full content array. Use get_draft first to see current block IDs.",
        {
            "type": "object",
            "properties": {
                "draft_id": {
                    "type": "integer",
                    "description": "Draft ID to update.",
                },
                "name": {
                    "type": "string",
                    "description": "New display title (optional).",
                },
                "status": {
                    "type": "string",
                    "enum": ["draft", "review", "final"],
                    "description": "New status (optional).",
                },
                "content": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "type": {
                                "type": "string",
                                "enum": [
                                    "section_heading",
                                    "numbered_paragraph",
                                    "list_item",
                                    "signature",
                                ],
                            },
                            "content": {"type": "string"},
                        },
                        "required": ["id", "type", "content"],
                    },
                    "description": "Full replacement content array (optional). "
                    "Replaces all blocks. Use for significant rewrites.",
                },
            },
            "required": ["draft_id"],
        },
    )
    async def update_draft(args: dict[str, Any]) -> dict[str, Any]:
        draft_id = args["draft_id"]
        try:
            conn = _conn()
            try:
                from core.db import get_draft as _get_draft
                draft = _get_draft(conn, draft_id)
            finally:
                conn.close()
            if not draft:
                return _error(f"Draft {draft_id} not found.")
            if draft["case_id"] != case_id:
                return _error(f"Draft {draft_id} not in case {case_id}.")

            kwargs = {}
            if "name" in args:
                kwargs["name"] = args["name"]
            if "status" in args:
                kwargs["status"] = args["status"]
            if "content" in args:
                kwargs["content"] = args["content"]

            if not kwargs:
                return _error("No fields to update.")

            conn = _conn()
            try:
                from core.db import update_draft as _update_draft
                updated = _update_draft(conn, draft_id, **kwargs)
            finally:
                conn.close()

            return _result({
                "draft_id": draft_id,
                "name": updated["name"],
                "block_count": len(updated.get("content", [])),
                "updated_at": str(updated.get("updated_at", "")),
            })
        except Exception as exc:
            return _error(f"update_draft failed: {exc}")

    # -- Layer 6.5: Workspace ------------------------------------------------

    @tool(
        "list_workspace_items",
        "List workspace items for the current case. Optionally filter by "
        "folder (freestyle, research, artifacts) or file_type. Returns id, "
        "name, file_type, folder, document_type, status, block count, and "
        "timestamps. Does not return full content — use get_workspace_item "
        "for that.",
        {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": "Filter by folder: freestyle, research, artifacts.",
                },
                "file_type": {
                    "type": "string",
                    "enum": ["markdown", "structured_draft", "html", "json_view"],
                    "description": "Filter by file type.",
                },
            },
            "required": [],
        },
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_workspace_items(args: dict[str, Any]) -> dict[str, Any]:
        try:
            conn = _conn()
            try:
                from core.db import list_drafts as _list_drafts
                folder = args.get("folder")
                rows = _list_drafts(conn, case_id, folder=folder)
            finally:
                conn.close()
            file_type = args.get("file_type")
            if file_type is not None:
                rows = [r for r in rows if r.get("file_type") == file_type]
            return _result({"count": len(rows), "items": rows})
        except Exception as exc:
            return _error(f"list_workspace_items failed: {exc}")

    @tool(
        "get_workspace_item",
        "Read a workspace item's full content. The content structure depends "
        "on file_type:\n"
        "  markdown         — {\"markdown\": \"# Title...\"}\n"
        "  structured_draft — [{id, type, content}, ...]\n"
        "  html             — {\"html\": \"<html>...\"}\n"
        "  json_view        — {\"data\": {...}}\n"
        "Use this before editing so you can see the current state.",
        {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "integer",
                    "description": "Workspace item ID from list_workspace_items.",
                },
            },
            "required": ["item_id"],
        },
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def get_workspace_item(args: dict[str, Any]) -> dict[str, Any]:
        item_id = args["item_id"]
        try:
            conn = _conn()
            try:
                from core.db import get_draft as _get_draft
                item = _get_draft(conn, item_id)
            finally:
                conn.close()
            if not item:
                return _error(f"Workspace item {item_id} not found.")
            if item["case_id"] != case_id:
                return _error(f"Workspace item {item_id} not in case {case_id}.")
            return _result({"item": item})
        except Exception as exc:
            return _error(f"get_workspace_item failed: {exc}")

    @tool(
        "create_workspace_item",
        "Create a new workspace item. Content structure depends on file_type:\n"
        "  markdown         — {\"markdown\": \"# Title\\n\\nContent...\"}\n"
        "  structured_draft — [{\"id\":\"b1\",\"type\":\"section_heading\","
        "\"content\":\"TITLE\"}, ...]\n"
        "  html             — {\"html\": \"<html>...</html>\"}\n"
        "  json_view        — {\"data\": {...}}\n\n"
        "For markdown, wrap the full markdown string in an object with a "
        "'markdown' key. For structured_draft, use the block array format "
        "with section_heading, numbered_paragraph, list_item, and signature "
        "block types.",
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Display name for the item.",
                },
                "file_type": {
                    "type": "string",
                    "enum": ["markdown", "structured_draft", "html", "json_view"],
                    "description": "Type of content this item holds.",
                },
                "folder": {
                    "type": "string",
                    "enum": ["freestyle", "research", "artifacts"],
                    "description": "Which folder to place the item in.",
                },
                "document_type": {
                    "type": "string",
                    "enum": ["letter", "pleading", "contract", "memo",
                             "capability_statement", "other"],
                    "description": "Legal document type (optional, defaults to other).",
                },
                "content": {
                    "type": "object",
                    "description": "Content envelope matching file_type.",
                },
            },
            "required": ["name", "file_type", "folder", "content"],
        },
    )
    async def create_workspace_item(args: dict[str, Any]) -> dict[str, Any]:
        try:
            content_raw = args.get("content", {})
            if isinstance(content_raw, list):
                content_list = content_raw
            elif isinstance(content_raw, dict):
                content_list = [content_raw]
            else:
                content_list = [{"raw": str(content_raw)}]

            conn = _conn()
            try:
                from core.db import insert_draft as _insert_draft
                item_id = _insert_draft(
                    conn,
                    case_id=case_id,
                    name=args["name"],
                    document_type=args.get("document_type", "other"),
                    content=content_list,
                    created_by="agent",
                    file_type=args["file_type"],
                    folder=args["folder"],
                )
            finally:
                conn.close()
            return _result({
                "item_id": item_id,
                "name": args["name"],
                "file_type": args["file_type"],
                "folder": args["folder"],
                "block_count": len(content_list),
            })
        except Exception as exc:
            return _error(f"create_workspace_item failed: {exc}")

    @tool(
        "update_workspace_item",
        "Modify a workspace item — update its name, content, folder, or "
        "status. For targeted edits, provide only what changed. To replace "
        "the entire content, provide a full content envelope matching the "
        "item's file_type. Use get_workspace_item first to see current state.",
        {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "integer",
                    "description": "Workspace item ID to update.",
                },
                "name": {
                    "type": "string",
                    "description": "New display name (optional).",
                },
                "content": {
                    "type": "object",
                    "description": "Full replacement content envelope (optional).",
                },
                "folder": {
                    "type": "string",
                    "enum": ["freestyle", "research", "artifacts"],
                    "description": "Move to a different folder (optional).",
                },
                "status": {
                    "type": "string",
                    "enum": ["draft", "review", "final"],
                    "description": "New status (optional).",
                },
            },
            "required": ["item_id"],
        },
    )
    async def update_workspace_item(args: dict[str, Any]) -> dict[str, Any]:
        item_id = args["item_id"]
        try:
            # Verify case scope
            conn = _conn()
            try:
                from core.db import get_draft as _get_draft
                item = _get_draft(conn, item_id)
            finally:
                conn.close()
            if not item:
                return _error(f"Workspace item {item_id} not found.")
            if item["case_id"] != case_id:
                return _error(f"Workspace item {item_id} not in case {case_id}.")

            kwargs = {}
            if "name" in args:
                kwargs["name"] = args["name"]
            if "status" in args:
                kwargs["status"] = args["status"]
            if "folder" in args:
                kwargs["folder"] = args["folder"]
            if "content" in args:
                content_raw = args["content"]
                if isinstance(content_raw, list):
                    kwargs["content"] = content_raw
                elif isinstance(content_raw, dict):
                    kwargs["content"] = [content_raw]
                else:
                    kwargs["content"] = [{"raw": str(content_raw)}]

            if not kwargs:
                return _error("No fields to update.")

            conn = _conn()
            try:
                from core.db import update_draft as _update_draft
                updated = _update_draft(conn, item_id, **kwargs)
            finally:
                conn.close()

            return _result({
                "item_id": item_id,
                "name": updated["name"],
                "file_type": updated.get("file_type", ""),
                "folder": updated.get("folder", ""),
                "block_count": len(updated.get("content", [])),
                "updated_at": str(updated.get("updated_at", "")),
            })
        except Exception as exc:
            return _error(f"update_workspace_item failed: {exc}")

    # -- Layer 7: Tasks ------------------------------------------------------

    @tool(
        "list_tasks",
        "List all tasks for the current case, ordered by urgency. "
        "Overdue tasks first, then nearest deadline, then priority. "
        "Use this to check what needs to be done, what's pending, "
        "or what follow-ups were created from previous analysis.",
        {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["open", "in_progress", "blocked", "complete"],
                    "description": "Filter by status (optional).",
                },
                "assignee_id": {
                    "type": "string",
                    "description": "Filter by assignee user ID (optional).",
                },
            },
            "required": [],
        },
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_tasks(args: dict[str, Any]) -> dict[str, Any]:
        try:
            conn = _conn()
            try:
                from core.db import list_tasks as _list_tasks
                rows = _list_tasks(
                    conn, case_id,
                    status=args.get("status"),
                    assignee_id=args.get("assignee_id"),
                )
            finally:
                conn.close()
            return _result({"count": len(rows), "tasks": rows})
        except Exception as exc:
            return _error(f"list_tasks failed: {exc}")

    @tool(
        "create_task",
        "Create a new task in the case tracker. Use this to create "
        "follow-up items after analysis, reminders for missing evidence, "
        "or action items the user needs to handle.",
        {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Task title. Be specific about what needs to happen.",
                },
                "notes": {
                    "type": "string",
                    "description": "Detailed notes or context (optional).",
                },
                "deadline": {
                    "type": "string",
                    "description": "Deadline date in YYYY-MM-DD format (optional).",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priority level. Default medium.",
                },
                "document_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Document IDs to attach (optional). "
                    "Use document IDs from get_case or list_documents.",
                },
            },
            "required": ["title"],
        },
    )
    async def create_task(args: dict[str, Any]) -> dict[str, Any]:
        try:
            conn = _conn()
            try:
                from core.db import insert_task as _insert_task
                task_id = _insert_task(
                    conn,
                    case_id=case_id,
                    title=args["title"],
                    notes=args.get("notes"),
                    deadline=args.get("deadline"),
                    priority=args.get("priority", "medium"),
                    created_by="agent",
                )
                doc_ids = args.get("document_ids", [])
                if doc_ids:
                    from core.db import attach_task_documents as _attach
                    _attach(conn, task_id, doc_ids)
            finally:
                conn.close()
            return _result({
                "task_id": task_id,
                "title": args["title"],
                "priority": args.get("priority", "medium"),
                "deadline": args.get("deadline"),
                "documents_attached": len(doc_ids) if doc_ids else 0,
            })
        except Exception as exc:
            return _error(f"create_task failed: {exc}")

    @tool(
        "update_task",
        "Update a task's status, notes, or assignment. Use this to "
        "mark tasks complete when follow-up is done, or update notes "
        "with findings.",
        {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "Task ID from list_tasks.",
                },
                "status": {
                    "type": "string",
                    "enum": ["open", "in_progress", "blocked", "complete"],
                    "description": "New status (optional).",
                },
                "notes": {
                    "type": "string",
                    "description": "Updated notes (optional).",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Updated priority (optional).",
                },
                "deadline": {
                    "type": "string",
                    "description": "Updated deadline YYYY-MM-DD (optional).",
                },
            },
            "required": ["task_id"],
        },
    )
    async def update_task(args: dict[str, Any]) -> dict[str, Any]:
        task_id = args["task_id"]
        try:
            kwargs = {}
            for f in ("status", "notes", "priority", "deadline"):
                if f in args:
                    kwargs[f] = args[f]
            if not kwargs:
                return _error("No fields to update.")
            conn = _conn()
            try:
                from core.db import update_task as _update_task
                updated = _update_task(conn, task_id, **kwargs)
            finally:
                conn.close()
            if not updated:
                return _error(f"Task {task_id} not found.")
            return _result({
                "task_id": task_id,
                "status": updated.get("status"),
                "updated_at": str(updated.get("updated_at", "")),
            })
        except Exception as exc:
            return _error(f"update_task failed: {exc}")

    @tool(
        "delete_task",
        "Delete a task. Use when a task is no longer relevant or was created "
        "in error.",
        {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "Task ID from list_tasks.",
                },
            },
            "required": ["task_id"],
        },
    )
    async def delete_task(args: dict[str, Any]) -> dict[str, Any]:
        task_id = args["task_id"]
        try:
            conn = _conn()
            try:
                from core.db import delete_task as _delete_task
                ok = _delete_task(conn, task_id)
            finally:
                conn.close()
            if not ok:
                return _error(f"Task {task_id} not found.")
            return _result({"deleted": True, "task_id": task_id})
        except Exception as exc:
            return _error(f"delete_task failed: {exc}")

    # -- Layer 8: Correspondence ---------------------------------------------

    @tool(
        "list_correspondence_threads",
        "List all correspondence threads for the current case. Returns id, "
        "title, status, item count, and last activity. Use to see existing "
        "threads before adding items.",
        {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "archived"],
                    "description": "Filter by status (optional). Defaults to all.",
                },
            },
            "required": [],
        },
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_correspondence_threads(args: dict[str, Any]) -> dict[str, Any]:
        try:
            conn = _conn()
            try:
                clauses = ["ct.case_id = %s"]
                params: list[Any] = [case_id]
                if args.get("status"):
                    clauses.append("ct.status = %s")
                    params.append(args["status"])
                where = " AND ".join(clauses)
                sql = f"""SELECT ct.*,
                                 (SELECT count(*) FROM correspondence_items
                                  WHERE thread_id = ct.id) AS item_count,
                                 (SELECT max(updated_at) FROM correspondence_items
                                  WHERE thread_id = ct.id) AS last_activity
                          FROM correspondence_threads ct
                          WHERE {where}
                          ORDER BY ct.updated_at DESC"""
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, tuple(params))
                    rows = [dict(r) for r in cur.fetchall()]
            finally:
                conn.close()
            return _result({"count": len(rows), "threads": rows})
        except Exception as exc:
            return _error(f"list_correspondence_threads failed: {exc}")

    @tool(
        "create_correspondence_thread",
        "Create a new correspondence thread. A thread groups related "
        "correspondence items (e.g., 'Discovery letters to opposing counsel'). "
        "Use this before logging individual items.",
        {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Thread title. Be descriptive.",
                },
            },
            "required": ["title"],
        },
    )
    async def create_correspondence_thread(args: dict[str, Any]) -> dict[str, Any]:
        try:
            conn = _conn()
            try:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """INSERT INTO correspondence_threads (case_id, title)
                           VALUES (%s, %s) RETURNING *""",
                        (case_id, args["title"]),
                    )
                    thread = dict(cur.fetchone())
                conn.commit()
            finally:
                conn.close()
            return _result({"thread": thread})
        except Exception as exc:
            return _error(f"create_correspondence_thread failed: {exc}")

    @tool(
        "update_correspondence_thread",
        "Update a correspondence thread's title or status. Archive threads "
        "when they're no longer active.",
        {
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "integer",
                    "description": "Thread ID from list_correspondence_threads.",
                },
                "title": {
                    "type": "string",
                    "description": "New title (optional).",
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "archived"],
                    "description": "New status (optional).",
                },
            },
            "required": ["thread_id"],
        },
    )
    async def update_correspondence_thread(args: dict[str, Any]) -> dict[str, Any]:
        try:
            sets = []
            params: list[Any] = []
            if "title" in args:
                sets.append("title = %s"); params.append(args["title"])
            if "status" in args:
                sets.append("status = %s"); params.append(args["status"])
            if not sets:
                return _error("No fields to update.")
            sets.append("updated_at = now()")
            params.append(args["thread_id"])
            conn = _conn()
            try:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        f"UPDATE correspondence_threads SET {', '.join(sets)} "
                        f"WHERE id = %s AND case_id = %s RETURNING *",
                        tuple(params + [case_id]),
                    )
                    row = cur.fetchone()
                conn.commit()
            finally:
                conn.close()
            if not row:
                return _error("Thread not found in this case.")
            return _result({"thread": dict(row)})
        except Exception as exc:
            return _error(f"update_correspondence_thread failed: {exc}")

    @tool(
        "list_correspondence_items",
        "List all items in a correspondence thread. Returns sender, receiver, "
        "direction, notes, dates, and attached documents.",
        {
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "integer",
                    "description": "Thread ID from list_correspondence_threads.",
                },
            },
            "required": ["thread_id"],
        },
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_correspondence_items(args: dict[str, Any]) -> dict[str, Any]:
        try:
            conn = _conn()
            try:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Verify thread belongs to case
                    cur.execute(
                        "SELECT id FROM correspondence_threads WHERE id = %s AND case_id = %s",
                        (args["thread_id"], case_id),
                    )
                    if not cur.fetchone():
                        return _error("Thread not found in this case.")
                    cur.execute(
                        """SELECT ci.*,
                                  sp.name AS sender_name,
                                  rp.name AS receiver_name,
                                  (SELECT jsonb_agg(
                                      jsonb_build_object(
                                          'id', ca.id,
                                          'document_id', ca.document_id,
                                          'document_name', d.name
                                      )
                                   )
                                   FROM correspondence_attachments ca
                                   JOIN documents d ON ca.document_id = d.id
                                   WHERE ca.item_id = ci.id
                                  ) AS attachments
                           FROM correspondence_items ci
                           LEFT JOIN parties sp ON ci.sender_party_id = sp.id
                           LEFT JOIN parties rp ON ci.receiver_party_id = rp.id
                           WHERE ci.thread_id = %s
                           ORDER BY ci.date_sent DESC, ci.date_received DESC,
                                    ci.created_at DESC""",
                        (args["thread_id"],),
                    )
                    rows = [dict(r) for r in cur.fetchall()]
            finally:
                conn.close()
            return _result({"count": len(rows), "items": rows})
        except Exception as exc:
            return _error(f"list_correspondence_items failed: {exc}")

    @tool(
        "create_correspondence_item",
        "Log a new correspondence item in a thread. Records who sent/received "
        "it, the direction, dates, notes, and optionally attaches documents. "
        "Use party IDs from get_case (parties array).",
        {
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "integer",
                    "description": "Thread ID from list_correspondence_threads.",
                },
                "direction": {
                    "type": "string",
                    "enum": ["sent", "received"],
                    "description": "Whether this was sent by us or received.",
                },
                "sender_party_id": {
                    "type": "integer",
                    "description": "Party ID of the sender (optional).",
                },
                "receiver_party_id": {
                    "type": "integer",
                    "description": "Party ID of the receiver (optional).",
                },
                "notes": {
                    "type": "string",
                    "description": "Notes or summary of the correspondence (optional).",
                },
                "date_sent": {
                    "type": "string",
                    "description": "Date sent in YYYY-MM-DD format (optional).",
                },
                "date_received": {
                    "type": "string",
                    "description": "Date received in YYYY-MM-DD format (optional).",
                },
                "document_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Document IDs to attach (optional).",
                },
            },
            "required": ["thread_id", "direction"],
        },
    )
    async def create_correspondence_item(args: dict[str, Any]) -> dict[str, Any]:
        try:
            conn = _conn()
            try:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Verify thread belongs to case
                    cur.execute(
                        "SELECT id FROM correspondence_threads WHERE id = %s AND case_id = %s",
                        (args["thread_id"], case_id),
                    )
                    if not cur.fetchone():
                        return _error("Thread not found in this case.")
                    cur.execute(
                        """INSERT INTO correspondence_items
                           (thread_id, sender_party_id, receiver_party_id,
                            direction, notes, date_sent, date_received)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)
                           RETURNING *""",
                        (args["thread_id"], args.get("sender_party_id"),
                         args.get("receiver_party_id"), args["direction"],
                         args.get("notes"), args.get("date_sent"),
                         args.get("date_received")),
                    )
                    item = dict(cur.fetchone())
                    doc_ids = args.get("document_ids", [])
                    for did in doc_ids:
                        cur.execute(
                            """INSERT INTO correspondence_attachments
                               (item_id, document_id) VALUES (%s, %s)
                               ON CONFLICT DO NOTHING""",
                            (item["id"], did),
                        )
                conn.commit()
            finally:
                conn.close()
            return _result({
                "item": item,
                "documents_attached": len(doc_ids) if doc_ids else 0,
            })
        except Exception as exc:
            return _error(f"create_correspondence_item failed: {exc}")

    @tool(
        "update_correspondence_item",
        "Update a correspondence item's fields. Use to correct dates, add "
        "notes, or change the direction.",
        {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "integer",
                    "description": "Item ID from list_correspondence_items.",
                },
                "notes": {"type": "string", "description": "Updated notes."},
                "direction": {
                    "type": "string",
                    "enum": ["sent", "received"],
                    "description": "Updated direction.",
                },
                "date_sent": {
                    "type": "string",
                    "description": "Updated date sent YYYY-MM-DD.",
                },
                "date_received": {
                    "type": "string",
                    "description": "Updated date received YYYY-MM-DD.",
                },
                "sender_party_id": {
                    "type": "integer",
                    "description": "Updated sender party ID.",
                },
                "receiver_party_id": {
                    "type": "integer",
                    "description": "Updated receiver party ID.",
                },
            },
            "required": ["item_id"],
        },
    )
    async def update_correspondence_item(args: dict[str, Any]) -> dict[str, Any]:
        try:
            sets = []
            params: list[Any] = []
            for f in ("notes", "direction", "date_sent", "date_received",
                       "sender_party_id", "receiver_party_id"):
                if f in args and args[f] is not None:
                    sets.append(f"{f} = %s"); params.append(args[f])
            if not sets:
                return _error("No fields to update.")
            sets.append("updated_at = now()")
            params.append(args["item_id"])
            params.append(case_id)
            conn = _conn()
            try:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        f"""UPDATE correspondence_items ci SET {', '.join(sets)}
                            FROM correspondence_threads ct
                            WHERE ci.thread_id = ct.id
                              AND ci.id = %s AND ct.case_id = %s
                            RETURNING ci.*""",
                        tuple(params),
                    )
                    row = cur.fetchone()
                conn.commit()
            finally:
                conn.close()
            if not row:
                return _error("Item not found in this case.")
            return _result({"item": dict(row)})
        except Exception as exc:
            return _error(f"update_correspondence_item failed: {exc}")

    @tool(
        "delete_correspondence_item",
        "Delete a correspondence item. Use if an entry was logged in error.",
        {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "integer",
                    "description": "Item ID from list_correspondence_items.",
                },
            },
            "required": ["item_id"],
        },
    )
    async def delete_correspondence_item(args: dict[str, Any]) -> dict[str, Any]:
        try:
            conn = _conn()
            try:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """DELETE FROM correspondence_items ci
                           USING correspondence_threads ct
                           WHERE ci.thread_id = ct.id
                             AND ci.id = %s AND ct.case_id = %s
                           RETURNING ci.id""",
                        (args["item_id"], case_id),
                    )
                    row = cur.fetchone()
                conn.commit()
            finally:
                conn.close()
            if not row:
                return _error("Item not found in this case.")
            return _result({"deleted": True, "item_id": args["item_id"]})
        except Exception as exc:
            return _error(f"delete_correspondence_item failed: {exc}")

    # -- Build server --------------------------------------------------------

    return create_sdk_mcp_server(
        name="vision",
        version="1.0.0",
        tools=[
            get_case,
            list_documents,
            search_blocks,
            semantic_search,
            search_hybrid,
            get_document_structure,
            search_sections,
            get_block_context,
            get_blocks_in_section,
            get_strategies,
            get_strategy_tree,
            list_drafts,
            get_draft,
            create_draft,
            update_draft,
            list_workspace_items,
            get_workspace_item,
            create_workspace_item,
            update_workspace_item,
            list_tasks,
            create_task,
            update_task,
            delete_task,
            list_correspondence_threads,
            create_correspondence_thread,
            update_correspondence_thread,
            list_correspondence_items,
            create_correspondence_item,
            update_correspondence_item,
            delete_correspondence_item,
        ],
    )
