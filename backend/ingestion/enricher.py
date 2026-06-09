"""
Vision — Document Enrichment (Post-Ingest Classification).

After a document is ingested and normalized, a short-lived Agent SDK
sub-agent inspects the first pages and classifies it: document_type + tags.
Runs as a background job — does not block the upload response.

Flow:
  ingest complete → enqueue job(type='enrich') → worker claims
  → asyncio.run(run_enrichment(doc_id, case_id)) → agent reads intro
  → agent calls classify_document → tags written to documents row
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from core.db import connect, tx

# ---------------------------------------------------------------------------
# System prompt — tells the agent what it is and what to do
# ---------------------------------------------------------------------------

ENRICHER_SYSTEM_PROMPT = """You are a document classifier. Your job is to inspect a newly
ingested document and determine what type it is and what subject tags apply.

You have two tools:
  read_document_intro  — Returns the document name, section outline, and first
                         pages of text. Call this first.
  classify_document    — Writes your classification to the database. Call this
                         after you've read enough to make a decision.

CLASSIFICATION GUIDELINES

document_type must be one of:
  medical_record    — Clinical notes, lab results, operative reports, imaging
  tax_return        — IRS forms, W-2, 1099, tax filings
  contract          — Agreements, terms, MSA, SOW
  resume            — Individual CV or professional resume
  capability_statement — Company capability statement for government contracting
  correspondence    — Letters, emails, communications
  pleading          — Court filings, complaints, motions, answers
  transcript        — Deposition or hearing transcript
  spreadsheet       — Tabular data, financial models
  legal_memo        — Legal analysis or memorandum
  other             — None of the above

tags should be 3-8 lowercase subject tags. Use dashes for multi-word tags.
Good tags are specific and useful for later retrieval:
  - Subject: "cardiac-surgery", "breach-of-contract", "past-performance"
  - Document form: "operative-report", "form-w2", "motion-to-dismiss"
  - Parties/entities: "dr-chen", "acme-corp"
  - Time period: "2024-tax-year"

summary should be one sentence describing what this document contains and
why it matters to a legal case.

Read enough of the document to be confident in your classification. For short
documents (under 10 pages), skim the full outline. For long documents, focus on
the first 3-5 pages — that's usually enough to determine type and subject."""


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def _read_document_intro_impl(document_id: int) -> dict:
    """Fetch document metadata, section outline, and first blocks."""
    from core.db import connect as _connect

    conn = _connect()
    try:
        import psycopg2.extras

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            # Document metadata
            cur.execute(
                "SELECT id, name, page_count FROM documents WHERE id = %s",
                (document_id,),
            )
            doc = cur.fetchone()
            if not doc:
                return {"error": f"Document {document_id} not found"}
            doc = dict(doc)

            # Section outline
            cur.execute(
                """SELECT id, title, heading_level, page_start, page_end,
                          block_count
                   FROM sections WHERE document_id = %s
                   ORDER BY page_start, id""",
                (document_id,),
            )
            sections = [dict(row) for row in cur.fetchall()]

            # First N blocks (up to ~3 pages of content, max 50 blocks)
            cur.execute(
                """SELECT id, block_type, page, text_content
                   FROM blocks
                   WHERE document_id = %s
                   ORDER BY page, id
                   LIMIT 50""",
                (document_id,),
            )
            blocks = [dict(row) for row in cur.fetchall()]

            return {
                "document": doc,
                "section_count": len(sections),
                "sections": sections[:30],  # top-level outline
                "intro_blocks": blocks,
            }
    finally:
        conn.close()


def _classify_document_impl(
    document_id: int,
    document_type: str,
    tags: list[str],
    summary: str | None = None,
) -> dict:
    """Write classification to the document row."""
    from core.db import connect as _connect

    conn = _connect()
    try:
        with conn.cursor() as cur:
            # Fetch current metadata
            cur.execute(
                "SELECT metadata FROM documents WHERE id = %s",
                (document_id,),
            )
            row = cur.fetchone()
            if not row:
                return {"error": f"Document {document_id} not found"}

            current_meta = row[0] or {}
            if isinstance(current_meta, str):
                current_meta = json.loads(current_meta)

            # Merge classification into metadata
            current_meta["tags"] = tags
            current_meta["tag_source"] = "agent"
            current_meta["auto_summary"] = summary

            cur.execute(
                """UPDATE documents
                   SET document_type = %s,
                       metadata = %s::jsonb,
                       updated_at = now()
                   WHERE id = %s""",
                (document_type, json.dumps(current_meta), document_id),
            )
        conn.commit()

        return {
            "classified": True,
            "document_type": document_type,
            "tags": tags,
            "summary": summary,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Agent runner — spawns an SDK session, runs classification, returns result
# ---------------------------------------------------------------------------


async def run_enrichment(document_id: int, case_id: int) -> dict:
    """Run the enrichment agent for a single document.

    Spawns a ClaudeSDKClient session with the enricher prompt and tools.
    The agent calls read_document_intro, then classify_document.
    Returns the classification result dict.
    """
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
    from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

    # Build tools dynamically with document_id in closure (same pattern as
    # the chat vision server — no contextvars needed)
    @tool(
        "read_document_intro",
        "Read the document name, section outline, and first pages of "
        "text content. Call this first to understand what you're "
        "classifying.",
        {},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def read_document_intro(args: dict[str, Any]) -> dict[str, Any]:
        try:
            data = _read_document_intro_impl(document_id)
            if "error" in data:
                return {
                    "content": [{"type": "text", "text": data["error"]}],
                    "is_error": True,
                }
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(data, indent=2, default=str),
                    }
                ]
            }
        except Exception as exc:
            return {
                "content": [
                    {"type": "text", "text": f"Failed: {exc}"}
                ],
                "is_error": True,
            }

    @tool(
        "classify_document",
        "Write your classification: document_type, tags, and a one-sentence "
        "summary. Call this after reading the document intro. Be confident "
        "in your classification before calling.",
        {
            "type": "object",
            "properties": {
                "document_type": {
                    "type": "string",
                    "enum": [
                        "medical_record",
                        "tax_return",
                        "contract",
                        "resume",
                        "capability_statement",
                        "correspondence",
                        "pleading",
                        "transcript",
                        "spreadsheet",
                        "legal_memo",
                        "other",
                    ],
                    "description": "The document type.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "3-8 lowercase subject tags. Use dashes "
                    "for multi-word tags. Be specific.",
                },
                "summary": {
                    "type": "string",
                    "description": "One sentence describing what this "
                    "document contains and its relevance.",
                },
            },
            "required": ["document_type", "tags"],
        },
    )
    async def classify_document(args: dict[str, Any]) -> dict[str, Any]:
        try:
            result = _classify_document_impl(
                document_id=document_id,
                document_type=args["document_type"],
                tags=args["tags"],
                summary=args.get("summary"),
            )
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, default=str),
                    }
                ]
            }
        except Exception as exc:
            return {
                "content": [
                    {"type": "text", "text": f"Failed: {exc}"}
                ],
                "is_error": True,
            }

    enricher_server = create_sdk_mcp_server(
        name="enricher",
        version="1.0.0",
        tools=[read_document_intro, classify_document],
    )

    # Working directory for the SDK (unused but required)
    workdir = Path(os.environ.get("VISION_SDK_TMP", "/tmp/vision/sdk"))
    workdir.mkdir(parents=True, exist_ok=True)

    options = ClaudeAgentOptions(
        system_prompt=ENRICHER_SYSTEM_PROMPT,
        mcp_servers={"enricher": enricher_server},
        allowed_tools=["mcp__enricher__*"],
        cwd=str(workdir),
        permission_mode="bypassPermissions",
        setting_sources=[],
    )

    client = ClaudeSDKClient(options=options)
    await client.connect()

    try:
        prompt = (
            f"Classify document {document_id}. "
            f"Call read_document_intro first, then classify_document "
            f"with your classification."
        )
        await client.query(prompt)

        classification = None
        from claude_agent_sdk.types import ResultMessage

        async for msg in client.receive_response():
            if isinstance(msg, ResultMessage):
                # Extract the final result
                pass

        # Fall back to reading what was written to the DB directly
        conn = connect()
        try:
            import psycopg2.extras

            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cur:
                cur.execute(
                    "SELECT document_type, metadata FROM documents WHERE id = %s",
                    (document_id,),
                )
                row = cur.fetchone()
                if row:
                    meta = row["metadata"] or {}
                    if isinstance(meta, str):
                        meta = json.loads(meta)
                    classification = {
                        "document_type": row["document_type"],
                        "tags": meta.get("tags", []),
                        "summary": meta.get("auto_summary"),
                        "tag_source": meta.get("tag_source"),
                    }
        finally:
            conn.close()

        return classification or {"error": "Classification not written"}
    finally:
        await client.disconnect()


def enrich_document(document_id: int, case_id: int) -> dict:
    """Synchronous wrapper — called by the background worker."""
    return asyncio.run(run_enrichment(document_id, case_id))
