"""
Vision — Narrative Synthesis (Post-Save Extraction).

After a user saves a case narrative AND documents exist, they can trigger
this agent. It reads the narrative, extracts structured parties and
allegations, and writes them to the database.

Flow:
  user clicks "Extract" → POST /api/cases/{id}/synthesize
  → enqueue job(type='synthesize') → worker claims
  → synthesize_case() spawns Agent SDK session
  → agent reads narrative → extracts parties + allegations
  → writes to DB via tools → job complete
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

SYNTHESIZER_SYSTEM_PROMPT = """You are a legal case analyst. Your job is to read a case
narrative written by an attorney and extract structured data from it.

You have two tools:
  read_narrative   — Returns the full case narrative text. Call this first.
  save_extraction  — Writes extracted parties and allegations to the database.
                     Call this after thorough analysis.

EXTRACTION GUIDELINES

Parties — every person or organization mentioned in the narrative who plays a
role in the case. For each:
  - name: Full name as it appears in the narrative.
  - party_kind: "individual" or "organization".
  - roles: Array of role tags. Choose from: plaintiff, defendant, respondent,
           claimant, petitioner, witness, expert, treating_physician,
           attending_physician, surgeon, nurse, hospital, insurer, employer,
           regulatory_body, opposing_counsel, co_counsel, interested_party,
           other. A party can have multiple roles.
  - notes: Brief context about this party's involvement. 1-2 sentences.

Allegations — every claim, accusation, or legal theory mentioned. For each:
  - allegation_id: "A01", "A02", "A03"... assigned in the order they appear or
                   by importance.
  - text: Clear, concise statement of the allegation. One sentence.
  - category: Choose the best fit from: failure_to_diagnose, failure_to_treat,
              surgical_error, medication_error, diagnostic_delay,
              post_op_management, informed_consent, documentation,
              communication, negligent_referral, negligent_credentialing,
              breach_of_contract, negligence, fraud, breach_of_warranty,
              strict_liability, discrimination, retaliation, other.
  - extraction_focus: Array of phrases to search for in the medical records
                      or evidence. Be specific: "operative report for May 2024
                      surgery", "nursing notes from post-op day 1-3",
                      "informed consent form for the procedure",
                      "communication between Dr. X and Dr. Y about the
                      complication". These guide document searches.

Be thorough. Extract EVERY party and EVERY allegation mentioned. Do not invent
or assume facts not in the narrative. If the narrative is vague about something,
note that. Quality over quantity — but don't miss anything the attorney included."""


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------

def _read_narrative_impl(case_id: int) -> dict:
    """Fetch the case narrative text."""
    conn = connect()
    try:
        import psycopg2.extras

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                "SELECT id, name, narrative FROM cases WHERE id = %s",
                (case_id,),
            )
            case = cur.fetchone()
            if not case:
                return {"error": f"Case {case_id} not found"}
            case = dict(case)
            return {
                "case_name": case["name"],
                "narrative": case["narrative"] or "",
                "narrative_length": len(case["narrative"] or ""),
            }
    finally:
        conn.close()


def _save_extraction_impl(
    case_id: int,
    parties: list[dict],
    allegations: list[dict],
) -> dict:
    """Write extracted parties and allegations to the database.

    Replaces any previously agent-discovered parties (discovered_by='agent').
    Allegations use ON CONFLICT UPDATE — re-running updates, doesn't duplicate.
    """
    from core.case import CaseManager

    mgr = CaseManager()

    # Replace agent-discovered parties
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """DELETE FROM parties
                   WHERE case_id = %s AND discovered_by = 'agent'""",
                (case_id,),
            )

    added_parties = []
    for i, p in enumerate(parties):
        try:
            party = mgr.add_party(
                case_id=case_id,
                name=p["name"],
                party_kind=p.get("party_kind", "individual"),
                roles=p.get("roles", []),
                notes=p.get("notes"),
                discovered_by="agent",
            )
            added_parties.append({"id": party["id"], "name": party["name"]})
        except Exception as exc:
            added_parties.append({"name": p.get("name"), "error": str(exc)})

    # Write allegations (upsert on case_id + allegation_id)
    added_allegations = []
    for i, a in enumerate(allegations):
        try:
            allegation = mgr.add_allegation(
                case_id=case_id,
                allegation_id=a["allegation_id"],
                text=a["text"],
                category=a.get("category"),
                targets=a.get("targets", []),
                extraction_focus=a.get("extraction_focus", []),
                sort_order=i,
            )
            added_allegations.append({
                "id": allegation["id"],
                "allegation_id": allegation["allegation_id"],
            })
        except Exception as exc:
            added_allegations.append({
                "allegation_id": a.get("allegation_id"),
                "error": str(exc),
            })

    return {
        "parties_added": len(added_parties),
        "allegations_added": len(added_allegations),
        "parties": added_parties,
        "allegations": added_allegations,
    }


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------


async def _run_synthesis(case_id: int) -> dict:
    """Spawn the synthesis agent. Reads narrative, writes extraction."""
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
    from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

    @tool(
        "read_narrative",
        "Read the full case narrative text. Call this first to understand "
        "what the attorney has written about the case.",
        {},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def read_narrative(args: dict[str, Any]) -> dict[str, Any]:
        try:
            data = _read_narrative_impl(case_id)
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
                "content": [{"type": "text", "text": f"Failed: {exc}"}],
                "is_error": True,
            }

    @tool(
        "save_extraction",
        "Write the extracted parties and allegations to the database. "
        "Call this after you have thoroughly analyzed the narrative and "
        "identified every party and allegation.",
        {
            "type": "object",
            "properties": {
                "parties": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "party_kind": {
                                "type": "string",
                                "enum": ["individual", "organization"],
                            },
                            "roles": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "notes": {"type": "string"},
                        },
                        "required": ["name", "party_kind", "roles"],
                    },
                    "description": "Every person or organization in the case.",
                },
                "allegations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "allegation_id": {
                                "type": "string",
                                "description": "e.g. A01, A02, A03",
                            },
                            "text": {"type": "string"},
                            "category": {"type": "string"},
                            "extraction_focus": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "allegation_id",
                            "text",
                            "category",
                            "extraction_focus",
                        ],
                    },
                    "description": "Every claim, accusation, or legal theory.",
                },
            },
            "required": ["parties", "allegations"],
        },
    )
    async def save_extraction(args: dict[str, Any]) -> dict[str, Any]:
        try:
            result = _save_extraction_impl(
                case_id=case_id,
                parties=args.get("parties", []),
                allegations=args.get("allegations", []),
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
                "content": [{"type": "text", "text": f"Failed: {exc}"}],
                "is_error": True,
            }

    synth_server = create_sdk_mcp_server(
        name="synthesizer",
        version="1.0.0",
        tools=[read_narrative, save_extraction],
    )

    workdir = Path(os.environ.get("VISION_SDK_TMP", "/tmp/vision/sdk"))
    workdir.mkdir(parents=True, exist_ok=True)

    options = ClaudeAgentOptions(
        system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
        mcp_servers={"synthesizer": synth_server},
        allowed_tools=["mcp__synthesizer__*"],
        cwd=str(workdir),
        permission_mode="bypassPermissions",
        setting_sources=[],
    )

    client = ClaudeSDKClient(options=options)
    await client.connect()

    try:
        prompt = (
            f"Extract all parties and allegations from case {case_id}. "
            f"Read the narrative first, analyze it thoroughly, then "
            f"save your extraction."
        )
        await client.query(prompt)

        from claude_agent_sdk.types import ResultMessage

        async for msg in client.receive_response():
            if isinstance(msg, ResultMessage):
                pass  # consume stream

        # Read back what was written
        conn = connect()
        try:
            import psycopg2.extras

            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cur:
                cur.execute(
                    "SELECT count(*) FROM parties WHERE case_id = %s AND discovered_by = 'agent'",
                    (case_id,),
                )
                party_count = cur.fetchone()["count"]
                cur.execute(
                    "SELECT count(*) FROM allegations WHERE case_id = %s",
                    (case_id,),
                )
                allegation_count = cur.fetchone()["count"]
                return {
                    "parties_extracted": party_count,
                    "allegations_extracted": allegation_count,
                }
        finally:
            conn.close()

        return {"parties_extracted": 0, "allegations_extracted": 0}
    finally:
        await client.disconnect()


def synthesize_case(case_id: int) -> dict:
    """Synchronous wrapper — called by the background worker."""
    return asyncio.run(_run_synthesis(case_id))
