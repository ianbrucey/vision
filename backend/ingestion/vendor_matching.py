"""
Vision — Vendor Matching Pipeline (Unattended).

Runs after a solicitation's triage completes (automatically or on-demand
via the manual trigger). quick_kill is informational only and does NOT
block matching. Builds a deterministic SQL candidate
pool (NAICS exact -> NAICS family -> capabilities FTS, set-aside
hard-gated, capped ~300 rows) via VendorMatchManager, then runs a single
LLM agent that ranks/selects the top 25 candidates and drafts one
reusable outreach email template.

Flow:
  run_solicitation_triage() completes (quick_kill=false) -> enqueue
  job(type='vendor_matching') -> worker claims -> run_vendor_matching_pipeline
  -> build_candidate_pool() (no LLM) -> if non-empty, one ranking/drafting
  agent call -> writes vendor_matches rows + outreach_email_subject/body
  -> solicitations.matching_status = 'complete'

Fully unattended — no human checkpoints. Unlike solicitation_triage.py's
agents, this pipeline's agent has NO read tools: the candidate pool and
solicitation context are embedded directly in the query message as JSON,
since everything it needs is already known deterministically.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

MATCHING_SYSTEM_PROMPT = """You are a federal subcontracting business-development specialist. You will be
given a candidate pool of vendors (as JSON) and a solicitation's NAICS
code, set-aside type, scope of work, technical requirements, and place of
performance, all embedded directly in the user message. You have NO tools
to read documents — everything you need is already provided.

RANK the candidate pool by:
  1. NAICS specificity — exact matches outrank family matches, which
     outrank capability-only matches.
  2. Capability-narrative relevance — how well the vendor's profile
     (capabilities, vendor_name) aligns with the solicitation's scope of
     work and technical requirements text.
  3. State proximity to the solicitation's place of performance — this is
     ONE advisory signal among several, not a hard filter. A far-away
     vendor with strong capability relevance can still outrank a
     nearby one with weak relevance.

SELECT the top candidates, up to 25 (fewer is fine if the pool is small
or weak). For each selected vendor, assign:
  - match_score: integer 0-100, your overall confidence this vendor is a
    strong subcontracting match.
  - match_rationale: 1-2 sentences citing the SPECIFIC overlap (e.g. exact
    NAICS code, named capability, relevant location) — never generic
    filler like "good fit for this opportunity".
  - rank: integer 1-25, 1 = strongest match.
  - vendor_id and naics_match_type: copy directly from the candidate pool
    entry you selected.

Then DRAFT ONE outreach email (not per-vendor). This is a cold outreach to a
potential subcontractor, supplier, or teaming partner. The goal is to start a
real conversation — write like a person who knows the space, not a template.

SUBJECT — 8 words max, no NAICS code:
  Format: "[Product/need] — [Agency] [solicitation #]"
  Examples:
    RFQ:  "Snowmobile supply — USDA Forest Service RFQ 12444526Q0056"
    RFP:  "IT modernization — Dept of Labor RFP 1605C5-25-R-0003"
    SSN:  "Capability statements — DHS Sources Sought 70RTAC25SS00003"
  The solicitation number tells them it's real. The product summary tells
  them whether to keep reading.

BODY — write naturally. A real person should be able to read it and think
"a human wrote this." Structure:

  1. Opening — "Hi [company name]," or "Hello,". No "Dear X team."

  2. The opportunity — 2-4 sentences describing what's being procured,
     for whom, key specs (the 3-4 that gate), quantity, delivery, and
     contract type. State the facts. Use the solicitation number. If it's
     set-aside, mention it. If it's brand-name-or-equal, mention it.
     This paragraph tells them what they need to know to decide if they
     can do the work.

  3. What we're looking for — 1-2 sentences. Be specific: supplier?
     teaming partner? someone to handle a specific workstream? This
     signals that we're serious and know what we need.

  4. Why them — 1-2 conversational sentences. Write the LITERAL
     placeholder {{match_reason}} as a natural observation, not a
     citation. Imagine you're pointing at their website and telling a
     colleague why they're interesting. Examples of the tone:
       Good: "Powersports dealer in Alaska — a prime snowmobile market.
       Name directly signals snowmobile retail capability, and Alaska
       dealers routinely supply mountain-class machines meeting
       deep-powder specs. Exact NAICS match."
       Good: "Your firm's experience with the VA's VistA imaging
       modernization maps directly to the PACS replacement described in
       the SOW, and you're already in the VA's ecosystem."
       Bad: "Your firm was identified as a match because of your
       capabilities in [X] which align with the solicitation's scope."
     Never use the word "match" or "identified" in this paragraph. Just
     state what they do and why it's relevant. If the connection is
     thin, acknowledge it honestly rather than forcing it.

  5. Call to action — two options, email first:
       "If you can provide a quote, reply to this email and we'll send
       the full technical specs / scope of work."
       "If a call is easier, let us know what time works and we'll set
       it up."
     If there's a deadline, mention it here: "The response deadline is
     [date], so we'd want to connect before then."

  6. Closing — "Thanks," or "Best," followed by "Ian Bruce, Justice
     Quest LLC".

TONE — conversational, confident, human. Read it out loud. If it sounds
like a government document or a marketing email, rewrite it. No em-dashes.
No exclamation points. No "we believe," "we feel," "esteemed," or
"valuable partner." Just a person who knows what they need and thinks your
company might be able to help.

PLACEHOLDERS — use {{vendor_name}} in the salutation only. Use
{{match_reason}} EXACTLY ONCE, in the "why them" paragraph. Do not use
either placeholder anywhere else.

When ready, call save_matches ONCE with the full ranked list, then call
save_outreach_email ONCE with the subject and body. Do not respond with
results as chat text — they must go through the tools."""


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

_VALID_NAICS_MATCH_TYPES = ("exact", "family", "capability_only")
_MAX_MATCHES = 25
_TEXT_TRUNCATE = 8000


def _save_matches_impl(solicitation_id: int, matches: list[dict]) -> dict:
    """Validate a ranked match list, truncate to 25, and persist it."""
    from core.vendor_match import VendorMatchManager

    if not matches:
        return {"error": "matches list is empty"}

    for i, m in enumerate(matches):
        for key in ("vendor_id", "rank", "match_score", "match_rationale", "naics_match_type"):
            if key not in m:
                return {"error": f"match at index {i} is missing required key '{key}'"}
        if not isinstance(m["rank"], int) or not (1 <= m["rank"] <= 25):
            return {"error": f"match at index {i} has invalid rank {m['rank']!r} (must be int 1-25)"}
        if not isinstance(m["match_score"], int) or not (0 <= m["match_score"] <= 100):
            return {"error": f"match at index {i} has invalid match_score {m['match_score']!r} (must be int 0-100)"}
        if not isinstance(m["match_rationale"], str) or not m["match_rationale"].strip():
            return {"error": f"match at index {i} has an empty match_rationale"}
        if m["naics_match_type"] not in _VALID_NAICS_MATCH_TYPES:
            return {"error": f"match at index {i} has invalid naics_match_type {m['naics_match_type']!r}"}

    truncated = matches[:_MAX_MATCHES]
    VendorMatchManager().save_matches(solicitation_id, truncated)
    return {"saved": True, "count": len(truncated)}


def _save_outreach_impl(solicitation_id: int, subject: str, body: str) -> dict:
    """Persist the single outreach email template onto the solicitation row."""
    from core.solicitation import SolicitationManager

    updated = SolicitationManager().update(
        solicitation_id,
        outreach_email_subject=subject,
        outreach_email_body=body,
    )
    if updated is None:
        return {"error": f"Solicitation {solicitation_id} not found"}
    return {"saved": True}


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


async def _run_matching_agent(
    case_id: int,
    solicitation_id: int,
    candidate_pool: list[dict],
    sol: dict,
) -> dict:
    """Run the ranking/outreach-drafting agent. Returns a DB-read-back summary."""
    import json as _json

    from claude_agent_sdk import (
        ClaudeSDKClient, ClaudeAgentOptions, tool, create_sdk_mcp_server,
    )

    @tool(
        "save_matches",
        "Save the ranked vendor matches (up to 25). Call this once, after "
        "ranking the full candidate pool.",
        {
            "type": "object",
            "properties": {
                "matches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "vendor_id": {"type": "integer"},
                            "rank": {"type": "integer"},
                            "match_score": {"type": "integer"},
                            "match_rationale": {"type": "string"},
                            "naics_match_type": {
                                "type": "string",
                                "enum": ["exact", "family", "capability_only"],
                            },
                        },
                        "required": [
                            "vendor_id", "rank", "match_score",
                            "match_rationale", "naics_match_type",
                        ],
                    },
                },
            },
            "required": ["matches"],
        },
    )
    async def save_matches(args: dict[str, Any]) -> dict[str, Any]:
        try:
            result = _save_matches_impl(
                solicitation_id=solicitation_id, matches=args["matches"],
            )
            return {"content": [{"type": "text", "text": _json.dumps(result, default=str)}]}
        except Exception as exc:
            return {"content": [{"type": "text", "text": f"Failed: {exc}"}], "is_error": True}

    @tool(
        "save_outreach_email",
        "Save the single outreach email template (subject + body). Call "
        "this once, after save_matches.",
        {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["subject", "body"],
        },
    )
    async def save_outreach_email(args: dict[str, Any]) -> dict[str, Any]:
        try:
            result = _save_outreach_impl(
                solicitation_id=solicitation_id,
                subject=args["subject"],
                body=args["body"],
            )
            return {"content": [{"type": "text", "text": _json.dumps(result, default=str)}]}
        except Exception as exc:
            return {"content": [{"type": "text", "text": f"Failed: {exc}"}], "is_error": True}

    matching_server = create_sdk_mcp_server(
        name="matching", version="1.0.0", tools=[save_matches, save_outreach_email],
    )

    workdir = Path(os.environ.get("VISION_SDK_TMP", "/tmp/vision/sdk"))
    workdir.mkdir(parents=True, exist_ok=True)

    options = ClaudeAgentOptions(
        system_prompt=MATCHING_SYSTEM_PROMPT,
        mcp_servers={"matching": matching_server},
        allowed_tools=["mcp__matching__save_matches", "mcp__matching__save_outreach_email"],
        cwd=str(workdir),
        permission_mode="bypassPermissions",
        setting_sources=[],
    )

    def _truncate(text: str | None) -> str:
        if not text:
            return ""
        return text[:_TEXT_TRUNCATE]

    query = (
        f"Candidate vendor pool (JSON array, {len(candidate_pool)} rows):\n"
        f"{_json.dumps(candidate_pool, default=str)}\n\n"
        f"Solicitation context:\n"
        f"- naics_code: {sol.get('naics_code')!r}\n"
        f"- set_aside_type: {sol.get('set_aside_type')!r}\n"
        f"- place_of_performance: {_json.dumps(sol.get('place_of_performance'), default=str)}\n"
        f"- artifact_scope_of_work (HTML, may be truncated):\n{_truncate(sol.get('artifact_scope_of_work'))}\n\n"
        f"- artifact_technical_requirements (HTML, may be truncated):\n{_truncate(sol.get('artifact_technical_requirements'))}\n\n"
        f"Rank the pool, select up to 25, and call save_matches. Then draft "
        f"and call save_outreach_email."
    )

    client = ClaudeSDKClient(options=options)
    await client.connect()
    try:
        await client.query(query)
        from claude_agent_sdk.types import ResultMessage
        async for msg in client.receive_response():
            if isinstance(msg, ResultMessage):
                pass  # consume stream
    finally:
        await client.disconnect()

    from core.solicitation import SolicitationManager
    from core.vendor_match import VendorMatchManager

    matches = VendorMatchManager().list_for_solicitation(solicitation_id)
    updated_sol = SolicitationManager().get(solicitation_id)
    outreach_saved = bool(
        updated_sol
        and updated_sol.get("outreach_email_subject")
        and updated_sol.get("outreach_email_body")
    )
    return {"match_count": len(matches), "outreach_saved": outreach_saved}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def run_vendor_matching_pipeline(case_id: int, solicitation_id: int) -> dict:
    """Run the full unattended vendor-matching pipeline for one solicitation.

    Sets matching_status through 'running' -> 'complete'|'failed'. No NAICS
    code -> immediate failure, no agent call. Empty candidate pool ->
    'complete' with 0 matches (legitimate outcome, not a failure), no
    agent call (cost-saving — nothing to rank).
    """
    from core.solicitation import SolicitationManager
    from core.vendor_match import VendorMatchManager

    mgr = SolicitationManager()
    mgr.update(solicitation_id, matching_status="running", matching_error=None)

    sol = mgr.get(solicitation_id)
    if not sol or not sol.get("naics_code"):
        err = "No NAICS code available for matching"
        mgr.update(solicitation_id, matching_status="failed", matching_error=err)
        return {"error": err}

    candidate_pool = VendorMatchManager().build_candidate_pool(
        naics_code=sol["naics_code"], set_aside_type=sol.get("set_aside_type"),
    )

    if not candidate_pool:
        mgr.update(solicitation_id, matching_status="complete")
        return {"match_count": 0}

    try:
        result = await _run_matching_agent(case_id, solicitation_id, candidate_pool, sol)
    except Exception as exc:
        mgr.update(solicitation_id, matching_status="failed", matching_error=str(exc))
        return {"error": str(exc)}

    mgr.update(solicitation_id, matching_status="complete")
    return result


def run_vendor_matching_pipeline_sync(case_id: int, solicitation_id: int) -> dict:
    """Synchronous wrapper — called by the background worker."""
    return asyncio.run(run_vendor_matching_pipeline(case_id, solicitation_id))
