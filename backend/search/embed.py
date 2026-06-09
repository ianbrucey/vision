"""
Vision — Section Embedding Pipeline.

Embeds every section's `search_text` via Mistral embed API (1024-dim)
into `sections.embedding`, with caching to avoid re-embedding identical text.

Port of section_mapping_20260505/pipeline/stage3_embed.py
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

from core.db import connect, tx

EMBED_MODEL = "mistral-embed"
EMBED_DIMS = 1024
MAX_INPUT_CHARS = 16_000       # safe under Mistral's 8,192 token limit (worst case ~2 chars/token)
BATCH_SIZE = 16                # inputs per API request
INTER_BATCH_SLEEP_S = 1.0      # rate-limit buffer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(text: str) -> str:
    return text if len(text) <= MAX_INPUT_CHARS else text[:MAX_INPUT_CHARS]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _vec_literal(vec: list[float]) -> str:
    """Render a Python list as a pgvector literal: '[0.1,0.2,...]'"""
    return "[" + ",".join(repr(float(v)) for v in vec) + "]"


def _load_mistral_key() -> str:
    """Load MISTRAL_API_KEY from env or .env files."""
    key = os.environ.get("MISTRAL_API_KEY")
    if key:
        return key.strip()
    for env_path in [
        Path(__file__).resolve().parents[3] / ".env",
        Path(__file__).resolve().parents[3] / "mcp-server" / ".env",
    ]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("MISTRAL_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        return key
    raise RuntimeError("MISTRAL_API_KEY not found in env or .env files")


def _get_client():
    """Return a Mistral client configured with the API key."""
    from mistralai.client import Mistral
    return Mistral(api_key=_load_mistral_key())


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def _fetch_cache_hits(conn, hashes: list[str]) -> dict[str, str]:
    """Return {content_hash → vector_text} for any cached rows."""
    if not hashes:
        return {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content_hash, embedding::text "
            "FROM embedding_cache WHERE content_hash = ANY(%s)",
            (hashes,),
        )
        return {h: v for h, v in cur.fetchall()}


def _write_cache(conn, content_hash: str, vec_text: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO embedding_cache (content_hash, embedding, model)
               VALUES (%s, %s::vector, %s)
               ON CONFLICT (content_hash) DO NOTHING""",
            (content_hash, vec_text, EMBED_MODEL),
        )


def embed_document(document_id: int) -> dict:
    """Embed all un-embedded sections for a document.

    Skips sections that already have an embedding. Uses the embedding_cache
    to avoid re-embedding text that was previously embedded elsewhere.

    Returns:
        dict with embedded_count, cached_count, skipped_count, elapsed_seconds.
    """
    client = _get_client()
    t0 = time.time()

    # Fetch sections that need embedding
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, search_text
                   FROM sections
                   WHERE document_id = %s
                     AND search_text IS NOT NULL
                     AND search_text != ''
                     AND embedding IS NULL""",
                (document_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        print(f"  All sections already embedded for document {document_id}.")
        return {"embedded_count": 0, "cached_count": 0, "skipped_count": 0, "elapsed_seconds": 0.0}

    # Truncate + hash
    section_texts: dict[int, str] = {}
    hashes: dict[str, list[int]] = {}  # content_hash → [section_id, ...]

    for section_id, raw_text in rows:
        text = _truncate(raw_text or "")
        section_texts[section_id] = text
        h = _hash(text)
        hashes.setdefault(h, []).append(section_id)

    print(f"  Sections to embed: {len(rows)} (unique texts: {len(hashes)})")

    # Check cache
    cached_vectors: dict[str, str] = {}
    with tx() as conn:
        cached_vectors = _fetch_cache_hits(conn, list(hashes.keys()))

    cached_count = 0
    if cached_vectors:
        # Apply cached vectors immediately
        with tx() as conn:
            for content_hash, vec_text in cached_vectors.items():
                for sid in hashes.pop(content_hash, []):
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE sections SET embedding = %s::vector WHERE id = %s",
                            (vec_text, sid),
                        )
                    cached_count += 1
        print(f"  Cache hits: {cached_count}")

    # Remaining: call Mistral embed API
    remaining = [(h, hashes[h][0]) for h in hashes]
    embedded_count = 0

    if remaining:
        print(f"  API calls needed: {len(remaining)} texts in batches of {BATCH_SIZE}")
        for batch_start in range(0, len(remaining), BATCH_SIZE):
            batch = remaining[batch_start:batch_start + BATCH_SIZE]
            texts = [section_texts[sid] for _, sid in batch]

            resp = client.embeddings.create(
                model=EMBED_MODEL,
                inputs=texts,
            )
            vectors = [d.embedding for d in resp.data]

            with tx() as conn:
                for (content_hash, sid), vec in zip(batch, vectors):
                    vec_text = _vec_literal(vec)
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE sections SET embedding = %s::vector WHERE id = %s",
                            (vec_text, sid),
                        )
                    _write_cache(conn, content_hash, vec_text)
                    embedded_count += 1

            if batch_start + BATCH_SIZE < len(remaining):
                time.sleep(INTER_BATCH_SLEEP_S)

    elapsed = time.time() - t0
    result = {
        "embedded_count": embedded_count,
        "cached_count": cached_count,
        "skipped_count": 0,
        "elapsed_seconds": round(elapsed, 1),
    }
    print(
        f"  Done: {embedded_count} embedded, {cached_count} cached "
        f"in {elapsed:.1f}s"
    )
    return result


def embed_case(case_id: int) -> dict:
    """Embed all un-embedded sections across all documents in a case."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM documents WHERE case_id = %s", (case_id,)
            )
            doc_ids = [r[0] for r in cur.fetchall()]
    finally:
        conn.close()

    if not doc_ids:
        print(f"  No documents found for case {case_id}.")
        return {"embedded_count": 0, "cached_count": 0, "elapsed_seconds": 0.0}

    print(f"Embedding case {case_id}: {len(doc_ids)} document(s)")
    totals = {"embedded_count": 0, "cached_count": 0, "elapsed_seconds": 0.0}
    for doc_id in doc_ids:
        r = embed_document(doc_id)
        totals["embedded_count"] += r["embedded_count"]
        totals["cached_count"] += r["cached_count"]
        totals["elapsed_seconds"] += r["elapsed_seconds"]

    print(
        f"Case {case_id} complete: "
        f"{totals['embedded_count']} embedded, "
        f"{totals['cached_count']} cached, "
        f"{totals['elapsed_seconds']:.1f}s"
    )
    return totals
