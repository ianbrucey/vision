"""
Vision — Company Profile Synthesis Agent.

Reads uploaded company documents and extracts structured profile data:
company info, CAGE/UEI, NAICS codes, certifications, past performance,
key personnel, and contact details. Writes to company_profiles.content.

Flow:
  user uploads docs → ingested into profile's docs_case
  → user clicks "Synthesize" → POST /api/profiles/{id}/synthesize
  → enqueue job(type='profile_synthesis') → worker claims
  → agent reads docs → calls save_profile_fields → profile updated
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from core.db import connect, tx


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

PROFILE_SYNTH_PROMPT = """You are a GovCon company profile analyst. Your job is to read
a company's uploaded documents (capability statements, SAM.gov printouts, certifications,
resumes, etc.) and extract structured profile data.

You have two tools:
  read_profile_docs   — Returns all documents and their content for analysis.
  save_profile_fields — Writes the extracted profile data to the database.

EXTRACTION GUIDELINES

Company Info:
  - company_name: The official company name from the docs
  - legal_name: Legal entity name if different from company_name
  - dba: "Doing Business As" name if any
  - tax_id: EIN/TIN if found in any document

Codes & Identifiers:
  - cage_code: 5-character CAGE code (alphanumeric)
  - uei: 12-character UEI (formerly DUNS). Format: typically alphanumeric
  - psc_codes: Array of Product Service Codes found (e.g., ["DA01", "R425"])

NAICS Codes:
  - naics_codes: Array of NAICS codes found (e.g., ["541511", "541512"])
  - Look for 6-digit numeric codes labeled as NAICS

Certifications:
  - certifications: Array of certifications found. Look for:
    8(a), SDVOSB, VOSB, WOSB, EDWOSB, HUBZone, MBE, DBE, SDB
    Also note expiration dates if mentioned

Past Performance:
  - past_performance: Array of {client, contract_value, description, period_of_performance}
  - Extract from capability statements and past performance documents
  - Include dollar amounts, client names, project descriptions, and date ranges

Key Personnel:
  - key_personnel: Array of {name, title, years_experience, resume_document_id, clearance}
  - Extract from resumes and key personnel sections
  - resume_document_id: the document ID of the resume PDF (use the document IDs returned by read_profile_docs)

Contact:
  - contact: {address_line1, address_line2, city, state, zip, phone, email}
  - Get from letterhead, contact sections, or SAM.gov registration

Field Status:
  For every field you populate, set its status:
  - "agent_filled" if you found clear evidence in the documents
  - "uncertain" if you found something but aren't 100% sure
  - "needs_input" if the field was not found in any document
  Mark all fields you populate. Leave un-populated fields unset.

Be thorough. Read every document. Extract EVERY piece of information you find.
Do not invent data. If a document doesn't contain a specific field, set its
status to "needs_input" and leave the value empty."""


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------

def _read_profile_docs_impl(profile_id: int, case_id: int) -> dict:
    """Read ONLY the documents explicitly uploaded as profile source docs.

    Uses source_docs on the profile (set by the upload handler) to identify
    which documents are for profile building, avoiding contamination from
    other documents that happen to be in the same case.
    """
    conn = connect()
    try:
        import psycopg2.extras
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT source_docs FROM company_profiles WHERE id = %s",
                (profile_id,),
            )
            row = cur.fetchone()
            if not row or not row["source_docs"]:
                return {"error": "No source documents uploaded yet. Upload docs first."}

            source_docs = row["source_docs"] if isinstance(row["source_docs"], list) else json.loads(str(row["source_docs"]))
            doc_ids = [d["document_id"] for d in source_docs if d.get("document_id")]

            if not doc_ids:
                return {"error": "No valid document IDs in source_docs."}

            cur.execute(
                "SELECT id, name, page_count, document_type, ocr_status "
                "FROM documents WHERE id = ANY(%s) ORDER BY created_at",
                (doc_ids,),
            )
            docs = [dict(r) for r in cur.fetchall()]

            for doc in docs:
                cur.execute(
                    """SELECT id, block_type, page, text_content
                       FROM blocks WHERE document_id = %s
                       ORDER BY page, id LIMIT 200""",
                    (doc["id"],),
                )
                doc["blocks"] = [dict(r) for r in cur.fetchall()]

            return {"document_count": len(docs), "documents": docs}
    finally:
        conn.close()


def _save_profile_fields_impl(profile_id: int, content: dict) -> dict:
    """Write extracted fields to the company profile."""
    from core.db import update_company_profile, get_company_profile

    conn = connect()
    try:
        # Merge with existing content — don't overwrite verified fields
        existing = get_company_profile(conn, profile_id)
        if not existing:
            return {"error": f"Profile {profile_id} not found"}

        existing_content = existing.get("content") or {}
        if isinstance(existing_content, str):
            existing_content = json.loads(existing_content)

        existing_status = existing_content.get("field_status") or {}
        new_status = content.get("field_status") or {}

        # Only overwrite fields that aren't verified
        for key, val in new_status.items():
            if existing_status.get(key) != "verified":
                existing_status[key] = val

        merged = {**existing_content, **content, "field_status": existing_status}
    finally:
        conn.close()

    with tx() as conn2:
        updated = update_company_profile(conn2, profile_id, content=merged)
        if updated:
            updated["content"] = updated.get("content") or {}
        return {
            "profile_id": profile_id,
            "fields_populated": len(content) - 1 if "field_status" in content else len(content),
            "updated_at": str(updated.get("updated_at", "") if updated else ""),
        }


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------


async def _run_profile_synthesis(profile_id: int, case_id: int) -> dict:
    """Spawn the profile synthesis agent."""
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
    from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

    @tool(
        "read_profile_docs",
        "Read all uploaded company documents with their text content. "
        "Call this first to understand what information is available.",
        {},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def read_profile_docs(args: dict[str, Any]) -> dict[str, Any]:
        try:
            data = _read_profile_docs_impl(profile_id, case_id)
            return {
                "content": [{"type": "text", "text": json.dumps(data, indent=2, default=str)}],
            }
        except Exception as exc:
            return {
                "content": [{"type": "text", "text": f"Failed: {exc}"}],
                "is_error": True,
            }

    @tool(
        "save_profile_fields",
        "Write the extracted profile fields. Include ALL fields you found "
        "and their status. Fields you populate should have status "
        "'agent_filled' or 'uncertain'. Fields you cannot find should "
        "have status 'needs_input' with empty values.",
        {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "legal_name": {"type": "string"},
                "dba": {"type": "string"},
                "tax_id": {"type": "string"},
                "cage_code": {"type": "string"},
                "uei": {"type": "string"},
                "psc_codes": {"type": "array", "items": {"type": "string"}},
                "naics_codes": {"type": "array", "items": {"type": "string"}},
                "certifications": {"type": "array", "items": {"type": "string"}},
                "capabilities_summary": {"type": "string"},
                "past_performance": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "client": {"type": "string"},
                            "contract_value": {"type": "string"},
                            "description": {"type": "string"},
                            "period_of_performance": {"type": "string"},
                        },
                        "required": ["client", "description"],
                    },
                },
                "key_personnel": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "title": {"type": "string"},
                            "years_experience": {"type": "integer"},
                            "resume_document_id": {"type": "integer"},
                            "clearance": {"type": "string"},
                        },
                        "required": ["name", "title"],
                    },
                },
                "contact": {
                    "type": "object",
                    "properties": {
                        "address_line1": {"type": "string"},
                        "address_line2": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "zip": {"type": "string"},
                        "phone": {"type": "string"},
                        "email": {"type": "string"},
                    },
                },
                "field_status": {
                    "type": "object",
                    "description": "Status per field: agent_filled, uncertain, or needs_input",
                },
            },
        },
    )
    async def save_profile_fields(args: dict[str, Any]) -> dict[str, Any]:
        try:
            result = _save_profile_fields_impl(profile_id, dict(args))
            return {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            }
        except Exception as exc:
            return {
                "content": [{"type": "text", "text": f"Failed: {exc}"}],
                "is_error": True,
            }

    synth_server = create_sdk_mcp_server(
        name="profile_synthesizer",
        version="1.0.0",
        tools=[read_profile_docs, save_profile_fields],
    )

    workdir = Path(os.environ.get("VISION_SDK_TMP", "/tmp/vision/sdk"))
    workdir.mkdir(parents=True, exist_ok=True)

    options = ClaudeAgentOptions(
        system_prompt=PROFILE_SYNTH_PROMPT,
        mcp_servers={"profile_synthesizer": synth_server},
        allowed_tools=["mcp__profile_synthesizer__*"],
        cwd=str(workdir),
        permission_mode="bypassPermissions",
        setting_sources=[],
    )

    client = ClaudeSDKClient(options=options)
    await client.connect()

    try:
        # Read profile description as north star
        conn = connect()
        desc = ""
        try:
            from core.db import get_company_profile
            p = get_company_profile(conn, profile_id)
            desc = (p.get("description") or "").strip()
        finally:
            conn.close()

        prompt = (
            f"Read all documents for profile {profile_id} in case {case_id}. "
            f"Extract company information and populate the profile fields. "
            f"Be thorough — read every document before calling save_profile_fields."
        )
        if desc:
            prompt = (
                f"PROFILE DESCRIPTION (north star — guide your extraction):\n{desc}\n\n"
                + prompt
            )
        await client.query(prompt)

        from claude_agent_sdk.types import ResultMessage
        async for msg in client.receive_response():
            if isinstance(msg, ResultMessage):
                pass  # consume stream

        # Read back the result
        conn = connect()
        try:
            from core.db import get_company_profile
            profile = get_company_profile(conn, profile_id)
            content = profile.get("content") if profile else {}
            if isinstance(content, str):
                content = json.loads(content)
            field_count = len(content) - 1 if content and "field_status" in content else 0
            return {"fields_populated": field_count}
        finally:
            conn.close()

        return {"fields_populated": 0}
    finally:
        await client.disconnect()


def synthesize_profile(profile_id: int, case_id: int) -> dict:
    """Synchronous wrapper — called by the background worker."""
    return asyncio.run(_run_profile_synthesis(profile_id, case_id))


# ---------------------------------------------------------------------------
# Capability Statement Generator
# ---------------------------------------------------------------------------

CAPABILITY_STATEMENT_PROMPT = """You are a GovCon proposal writer. Generate a professional
capability statement for a company based on its profile data.

You have two tools:
  read_profile_data    — Returns the company's profile fields.
  create_capability_draft — Creates the capability statement as a structured draft.

The capability statement should follow this structure:
1. Company Overview — who they are, what they do, their differentiators
2. Core Capabilities — organized by NAICS/service area
3. Certifications — all set-asides and certifications with expiration dates
4. Past Performance — 3-5 key contracts with client, value, scope, dates
5. Key Personnel — brief bios of key team members
6. Contact Information

Use ALL available data from the profile. Write in professional proposal language.
Be specific — reference actual NAICS codes, contract values, and certification names.
Each section should be a section_heading block followed by numbered_paragraph blocks.

Block types available: section_heading, numbered_paragraph, list_item, signature"""


async def _run_capability_statement(profile_id: int, case_id: int) -> dict:
    """Generate a capability statement draft from profile data."""
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
    from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

    @tool(
        "read_profile_data",
        "Read the company profile content — all fields, certifications, "
        "past performance, and key personnel.",
        {},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def read_profile_data(args: dict[str, Any]) -> dict[str, Any]:
        import sys
        print("[profile_synth] read_profile_data CALLED", file=sys.stderr)
        try:
            conn = connect()
            try:
                from core.db import get_company_profile
                profile = get_company_profile(conn, profile_id)
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "name": profile["name"],
                            "content": profile.get("content", {}),
                        }, indent=2, default=str),
                    }],
                }
            finally:
                conn.close()
        except Exception as exc:
            return {"content": [{"type": "text", "text": f"Failed: {exc}"}], "is_error": True}

    @tool(
        "create_capability_draft",
        "Create the capability statement as a structured draft. "
        "Use section_heading for each major section and numbered_paragraph "
        "for the body text. Include a company name/contact signature block.",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Draft title."},
                "content": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "type": {"type": "string", "enum": ["section_heading", "numbered_paragraph", "list_item", "signature"]},
                            "content": {"type": "string"},
                        },
                        "required": ["id", "type", "content"],
                    },
                    "description": "Array of blocks forming the capability statement.",
                },
            },
            "required": ["name", "content"],
        },
    )
    async def create_capability_draft(args: dict[str, Any]) -> dict[str, Any]:
        import sys
        print(f"[profile_synth] create_capability_draft CALLED with name={args.get('name')} blocks={len(args.get('content',[]))}", file=sys.stderr)
        try:
            from core.db import connect as _db_connect, insert_draft, get_draft, update_company_profile
            conn = _db_connect()
            try:
                print(f"[profile_synth] case_id={case_id} profile_id={profile_id}", file=sys.stderr)
                draft_id = insert_draft(
                    conn, case_id=case_id,
                    name=args["name"],
                    document_type="capability_statement",
                    content=args["content"],
                    created_by="agent",
                )
                print(f"[profile_synth] draft_id={draft_id}", file=sys.stderr)
                update_company_profile(conn, profile_id, statement_draft_id=draft_id)
                conn.commit()
                print(f"[profile_synth] committed draft_id={draft_id} to profile {profile_id}", file=sys.stderr)
                draft = get_draft(conn, draft_id)
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "draft_id": draft_id,
                        "name": args["name"],
                        "block_count": len(args["content"]),
                    }, indent=2),
                }],
            }
        except Exception as exc:
            return {"content": [{"type": "text", "text": f"Failed: {exc}"}], "is_error": True}

    server = create_sdk_mcp_server(
        name="capability_gen",
        version="1.0.0",
        tools=[read_profile_data, create_capability_draft],
    )

    workdir = Path(os.environ.get("VISION_SDK_TMP", "/tmp/vision/sdk"))
    workdir.mkdir(parents=True, exist_ok=True)

    options = ClaudeAgentOptions(
        system_prompt=CAPABILITY_STATEMENT_PROMPT,
        mcp_servers={"capability_gen": server},
        allowed_tools=["mcp__capability_gen__*"],
        cwd=str(workdir),
        permission_mode="bypassPermissions",
        setting_sources=[],
    )

    client = ClaudeSDKClient(options=options)
    await client.connect()

    try:
        await client.query(
            f"Generate a capability statement for profile {profile_id}. "
            f"Step 1: call read_profile_data. "
            f"Step 2: call create_capability_draft with a complete "
            f"capability statement using ALL available data. "
            f"Do NOT write the statement as text — you MUST call "
            f"the create_capability_draft tool to save it. "
            f"The name should be '{profile_id} Capability Statement'."
        )
        from claude_agent_sdk.types import ResultMessage
        async for msg in client.receive_response():
            if isinstance(msg, ResultMessage):
                pass
        return {"generated": True}
    finally:
        await client.disconnect()


def generate_capability_statement(profile_id: int, case_id: int) -> dict:
    """Synchronous wrapper — called by the background worker."""
    return asyncio.run(_run_capability_statement(profile_id, case_id))
