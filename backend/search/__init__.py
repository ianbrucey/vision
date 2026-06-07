"""
Vision — Hybrid Search Primitives.

Composable multi-step search: keyword (FTS), semantic (vector), structural
(section hierarchy), and contextual (block windows). Every primitive is a
plain SQL function — the agent composes them depending on the question.

Part of the Agent Query Interface (Layer 4).
"""

from __future__ import annotations

from typing import Any

import psycopg2.extras

from core.db import connect


# ---------------------------------------------------------------------------
# Keyword Search (Full-Text Search via tsvector)
# ---------------------------------------------------------------------------

def search_by_keyword(
    query: str,
    document_id: int | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
    block_types: list[str] | None = None,
    limit: int = 50,
) -> list[dict]:
    """Full-text search across blocks using PostgreSQL tsvector.

    Args:
        query: Natural language query, converted to tsquery.
        document_id: Optional scope to a single document.
        page_start, page_end: Optional page range.
        block_types: Optional filter (e.g., ['Text', 'Table']).
        limit: Max results.

    Returns:
        List of blocks ranked by ts_rank, with snippet (headline).
    """
    # Build filters
    clauses = ["text_tsv @@ plainto_tsquery('english', %s)"]
    params: list[Any] = [query]

    if document_id is not None:
        clauses.append("document_id = %s")
        params.append(document_id)
    if page_start is not None:
        clauses.append("page >= %s")
        params.append(page_start)
    if page_end is not None:
        clauses.append("page <= %s")
        params.append(page_end)
    if block_types:
        clauses.append("block_type = ANY(%s)")
        params.append(block_types)

    where = " AND ".join(clauses)
    params.append(limit)

    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""SELECT id, document_id, section_id, block_type, page,
                           ts_rank(text_tsv, plainto_tsquery('english', %s)) AS rank,
                           ts_headline('english', text_content,
                                       plainto_tsquery('english', %s),
                                       'MaxWords=40, MinWords=10') AS snippet,
                           text_content
                    FROM blocks
                    WHERE {where}
                    ORDER BY rank DESC
                    LIMIT %s""",
                tuple([query, query] + params),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Semantic Search (Vector Similarity via pgvector)
# ---------------------------------------------------------------------------

def search_by_vector(
    query_text: str,
    document_id: int | None = None,
    limit: int = 25,
) -> list[dict]:
    """Semantic search across section embeddings using pgvector cosine similarity.

    Embeds the query text via Mistral embed, then finds the most similar
    sections. Falls back gracefully if no embeddings exist yet.

    Args:
        query_text: Natural language query to embed and compare.
        document_id: Optional scope to a single document.
        limit: Max results.

    Returns:
        List of sections ranked by cosine similarity, with their blocks.
    """
    from search.embed import _get_client, _truncate, EMBED_MODEL

    # Step 1: Embed the query
    client = _get_client()
    resp = client.embeddings.create(
        model=EMBED_MODEL,
        inputs=[_truncate(query_text)],
    )
    query_vec = resp.data[0].embedding

    # Build pgvector literal
    vec_literal = "[" + ",".join(repr(float(v)) for v in query_vec) + "]"

    # Step 2: Find nearest sections
    clauses = ["embedding IS NOT NULL"]
    params: list[Any] = [vec_literal]

    if document_id is not None:
        clauses.append("document_id = %s")
        params.append(document_id)

    where = " AND ".join(clauses)
    params.extend([vec_literal, limit])

    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""SELECT id, document_id, title, heading_level,
                           page_start, page_end, block_count,
                           1 - (embedding <=> %s::vector) AS similarity
                    FROM sections
                    WHERE {where}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s""",
                tuple(params),
            )
            sections = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    return sections


# ---------------------------------------------------------------------------
# Hybrid Search (FTS + Vector Fusion)
# ---------------------------------------------------------------------------

def search_hybrid(
    query: str,
    document_id: int | None = None,
    scope_section_ids: list[int] | None = None,
    limit: int = 30,
) -> list[dict]:
    """Combine keyword and semantic search with result fusion.

    Runs both searches, normalizes scores, and merges into a single
    ranked result set. Section-scoping narrows to specific structural
    areas (e.g., "only search within the Operative Report section").

    Args:
        query: Natural language query.
        document_id: Optional document scope.
        scope_section_ids: Optional list of section IDs to limit search to.
        limit: Max results.

    Returns:
        Merged blocks with combined relevance scores.
    """
    # Run keyword + vector in parallel candidate collection
    keyword_results = search_by_keyword(query, document_id=document_id, limit=limit * 2)

    # Collect section IDs from keyword hits to scope vector search
    kw_section_ids = {r["section_id"] for r in keyword_results if r.get("section_id")}

    # Vector search — scope to sections that had keyword hits, or all sections
    vector_scope = list(kw_section_ids) if kw_section_ids else None
    if scope_section_ids:
        vector_scope = (
            list(set(vector_scope) & set(scope_section_ids))
            if vector_scope else scope_section_ids
        )

    vector_results = search_by_vector(query, document_id=document_id, limit=limit)

    # If section-scoped, filter to matching section IDs
    if scope_section_ids:
        scope_set = set(scope_section_ids)
        vector_results = [s for s in vector_results if s["id"] in scope_set]

    # Merge: return sections ranked by vector similarity, with keyword
    # snippet context attached where available
    merged = []
    seen_section_ids = set()

    # Build a lookup from section_id → best keyword snippet
    kw_by_section: dict[int, list[dict]] = {}
    for r in keyword_results:
        sid = r.get("section_id")
        if sid:
            kw_by_section.setdefault(sid, []).append(r)

    for sec in vector_results:
        sid = sec["id"]
        if sid in seen_section_ids:
            continue
        seen_section_ids.add(sid)

        merged.append({
            "section_id": sid,
            "title": sec.get("title"),
            "page_start": sec.get("page_start"),
            "page_end": sec.get("page_end"),
            "similarity": round(sec.get("similarity", 0), 4),
            "keyword_hits": [
                {
                    "block_id": b["id"],
                    "page": b["page"],
                    "snippet": b.get("snippet", ""),
                }
                for b in kw_by_section.get(sid, [])[:3]
            ],
        })

    return merged[:limit]


# ---------------------------------------------------------------------------
# Structural Search (Section Hierarchy)
# ---------------------------------------------------------------------------

def get_sections_by_title(
    document_id: int,
    title_pattern: str,
    fuzzy: bool = True,
) -> list[dict]:
    """Find sections whose title matches a pattern.

    Args:
        document_id: Document to search within.
        title_pattern: Pattern to match (ILIKE).
        fuzzy: If True, use trigram similarity for fuzzy matching.

    Returns:
        Matching sections with page ranges.
    """
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if fuzzy:
                search_term = f"%{title_pattern}%"
                cur.execute(
                    """SELECT id, title, heading_level, page_start, page_end,
                              block_count, similarity(title, %s) AS sim
                       FROM sections
                       WHERE document_id = %s AND title %% %s
                       ORDER BY sim DESC
                       LIMIT 20""",
                    (title_pattern, document_id, search_term),
                )
            else:
                cur.execute(
                    """SELECT id, title, heading_level, page_start, page_end,
                              block_count
                       FROM sections
                       WHERE document_id = %s AND title ILIKE %s
                       ORDER BY page_start
                       LIMIT 20""",
                    (document_id, f"%{title_pattern}%"),
                )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_blocks_in_section(
    section_id: int,
    block_types: list[str] | None = None,
    limit: int = 100,
) -> list[dict]:
    """Return all blocks within a given section."""
    clauses = ["section_id = %s"]
    params: list[Any] = [section_id]
    if block_types:
        clauses.append("block_type = ANY(%s)")
        params.append(block_types)
    params.append(limit)

    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""SELECT id, block_type, page, text_content
                    FROM blocks
                    WHERE {' AND '.join(clauses)}
                    ORDER BY page, id
                    LIMIT %s""",
                tuple(params),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Block Context
# ---------------------------------------------------------------------------

def get_block_context(block_id: int, window: int = 3) -> list[dict]:
    """Return a block plus ±N surrounding blocks for reading in context."""
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """WITH target AS (
                       SELECT document_id, page, id FROM blocks WHERE id = %s
                   )
                   SELECT b.id, b.block_type, b.page, b.text_content,
                          b.datalab_id, s.title AS section_title
                   FROM blocks b
                   JOIN target t ON b.document_id = t.document_id
                   LEFT JOIN sections s ON b.section_id = s.id
                   WHERE b.page BETWEEN t.page - 1 AND t.page + 1
                   ORDER BY b.page, b.id""",
                (block_id,),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
