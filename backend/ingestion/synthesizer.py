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

SYNTHESIZER_SYSTEM_PROMPT = """You are a case analyst. Your job is to read a case
narrative and extract structured data from it. The case could be about anything —
medical malpractice, contract dispute, RFP response, tax audit, employment claim,
regulatory investigation, or any other legal or business matter.

You have two tools:
  read_narrative   — Returns the full case narrative text. Call this first.
  save_extraction  — Writes extracted parties and allegations to the database.
                     Call this after thorough analysis.

EXTRACTION GUIDELINES

CRITICAL: You MUST extract parties AND issues. Do not skip parties just
because the narrative uses structured headers like "RESPONDENT" or
"COMPLAINANT." Labeled sections are not a substitute — the database needs
every party as a row. If you can see a person or organization name with
a role in the matter, extract it.

Parties — every person or organization mentioned in the narrative who plays a
role in the matter. For each:
  - name: Full name as it appears in the narrative.
  - party_kind: "individual" or "organization". Facilities like hospitals
                or office locations are organizations; list the facility
                name, not just the parent entity.
  - roles: Array of role tags that describe this party's position. Choose from:
           plaintiff, defendant, respondent, claimant, petitioner,
           witness, expert, counsel, opposing_counsel,
           employer, employee, contractor, subcontractor,
           government_agency, regulatory_body, insurer,
           medical_provider, hospital, physician, nurse,
           vendor, supplier, client, customer,
           interested_party, other.
           A party can have multiple roles. Pick the most specific ones.
           Look for implicit roles — a "patient" is likely the claimant,
           a "respondent" in a complaint form is the defendant.
  - notes: Brief context about this party's involvement. 1-2 sentences.

Allegations — every claim, accusation, issue, or theory mentioned. This could
be a legal claim, a regulatory violation, a contractual breach, a factual
dispute, a compliance gap, or anything the attorney is investigating. For each:
  - allegation_id: "A01", "A02", "A03"... in order of appearance or importance.
  - text: Clear, concise statement. One sentence.
  - category: Best-fit label. Choose from:
              Medical: failure_to_diagnose, failure_to_treat, surgical_error,
                medication_error, diagnostic_delay, post_op_management,
                informed_consent, documentation, communication
              Contract/Business: breach_of_contract, breach_of_warranty,
                non_performance, non_payment, misrepresentation, fraud
              Employment: discrimination, retaliation, wrongful_termination,
                harassment, wage_dispute
              Regulatory: compliance_violation, licensing, data_privacy
              Tax: underreporting, audit_finding, penalty_dispute
              General: negligence, strict_liability, defamation,
                professional_misconduct, other
  - extraction_focus: Array of specific phrases to search for in the evidence.
                      Be concrete about what documents, dates, people, or
                      keywords would prove or disprove this allegation.
                      Examples by case type:
                      Medical: "operative report May 2024", "nursing notes
                        post-op day 1-3", "informed consent form"
                      Contract: "statement of work section 3.2", "delivery
                        receipts Q2 2025", "email chain about deadline change"
                      Tax: "2024 1099 forms", "correspondence with IRS",
                        "expense categorization for contractor payments"
                      Employment: "performance reviews 2024", "HR complaint
                        filed March 2025", "termination letter"
                      These guide document searches — be as specific as the
                      narrative allows.

Be thorough. Extract EVERY party and EVERY allegation the narrative mentions.
Do not invent or assume facts not in the narrative. If the narrative is vague
about something, note that. The case type determines what's relevant — do not
default to medical unless the narrative is clearly about medical care."""


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
                    "minItems": 1,
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
                    "description": "Every person or organization in the case. At least one required.",
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
