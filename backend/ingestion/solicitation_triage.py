"""
Vision — Solicitation Triage Pipeline (Unattended).

Runs after a federal solicitation's documents finish fetching (or on-demand
via the manual trigger). Classifies the notice type, runs the quick-kill
checklist, and — if it passes — extracts 5 partner-facing HTML artifacts in
parallel. Each artifact is written directly to its `solicitations` column
(matching the external govcon Laravel portal's column names, per
specs/vision-ai-brief.md) AND mirrored into the case's workspace (`drafts`
table, folder='artifacts', file_type='html') so it's viewable in Vision's
Triage tab.

Flow:
  sam_fetch job completes (docs OK) → enqueue job(type='solicitation_triage')
  → worker claims → run_solicitation_triage(case_id, solicitation_id)
  → triage agent classifies + quick-kill, writes directly to solicitations row
  → if PASS: 5 extractor agents run concurrently (asyncio.gather), each
    writes its own artifact_* column + a workspace item
  → solicitations.triage_status = 'complete'

Fully unattended — no human checkpoints. Per-extractor failures are caught
individually; the run still completes with has_partial_artifacts=true rather
than failing the whole pipeline over one bad extraction.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from core.db import tx, insert_draft

# ---------------------------------------------------------------------------
# Read tools — reused from the existing "vision" MCP server (chat/tools.py).
# Restricting allowed_tools to this subset keeps each agent read-only and
# scoped to document search/structure, mirroring the old EXTRACTOR_TOOLS
# list in scripts/solicitation_pipeline.py.
# ---------------------------------------------------------------------------

READ_TOOLS = [
    "mcp__vision__get_case",
    "mcp__vision__list_documents",
    "mcp__vision__get_document_structure",
    "mcp__vision__search_blocks",
    "mcp__vision__semantic_search",
    "mcp__vision__search_hybrid",
    "mcp__vision__search_sections",
    "mcp__vision__get_block_context",
    "mcp__vision__get_blocks_in_section",
]

ARTIFACT_CSS = """@page { size: letter; margin: 0.75in; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.6;
  color: #1f2937;
  max-width: 7in;
  margin: 0 auto;
  padding: 0.5in 0;
  background: #ffffff;
}
h2 {
  font-size: 17pt;
  font-weight: 700;
  color: #111827;
  border-bottom: 2px solid #2563eb;
  padding-bottom: 6px;
  margin: 0 0 16px 0;
}
h3 {
  font-size: 13pt;
  font-weight: 600;
  color: #1f2937;
  margin: 20px 0 8px 0;
}
p { margin: 0 0 10px 0; }
ul, ol { margin: 0 0 14px 0; padding-left: 1.4em; }
li { margin-bottom: 4px; }
table { width: 100%; border-collapse: collapse; margin: 12px 0 18px 0; font-size: 10pt; }
th, td { border: 1px solid #d1d5db; padding: 6px 10px; text-align: left; vertical-align: top; }
th { background: #f3f4f6; font-weight: 600; color: #111827; }
tr:nth-child(even) td { background: #fafafa; }
strong { font-weight: 600; color: #111827; }
em { font-style: italic; }
@media print {
  body { padding: 0; max-width: none; }
  table, tr { page-break-inside: avoid; }
  h2, h3 { page-break-after: avoid; }
}"""

HTML_FORMAT_RULES = f"""
FORMAT RULES (strict):
- Output a COMPLETE, self-contained HTML document — this is rendered
  standalone (its own page/iframe) and printed directly, so it must carry
  all of its own styling. Structure it exactly like this:

  <!DOCTYPE html>
  <html lang="en">
  <head>
  <meta charset="UTF-8">
  <style>
  {ARTIFACT_CSS}
  </style>
  </head>
  <body>
  <h2>[Artifact title, e.g. "Scope of Work"]</h2>
  ... your content ...
  </body>
  </html>

- Copy the <style> block above EXACTLY, character for character. Do not
  add, remove, or modify any rules in it.
- Inside <body>, use only clean, semantic HTML: <h2>, <h3>, <p>, <ul>/<ol>,
  <li>, <table>/<thead>/<tbody>/<tr>/<th>/<td>, <strong>, <em>. Start with a
  single <h2> naming this artifact section.
- Do NOT include <script>, <link>, <iframe>, <object>, <embed>, additional
  <style> tags, inline style attributes, or event handlers (onclick,
  onload, etc).
- If the information is genuinely absent from the solicitation, keep the
  <h2> title and output exactly:
  <p>This information was not found in the solicitation document.</p>
- Read using the available tools before writing. Do not invent facts not
  present in the documents.
- When you are confident in the complete HTML document, call save_artifact
  with it. Do not respond with the HTML as chat text — it must go through
  the tool.
"""


# ---------------------------------------------------------------------------
# Phase 1 — Triage: classify notice type + quick-kill
# ---------------------------------------------------------------------------

TRIAGE_SYSTEM_PROMPT = """You are a federal procurement intake specialist. Classify this solicitation
and run the quick-kill checklist. You do NOT read the full document — just
the first pages, cover letter, and submission instructions.

Use list_documents and get_document_structure to orient yourself, then
search_blocks / get_block_context to read the cover page and early sections.

CLASSIFY the notice type:
  rfi              — Request for Information / market research, no pricing ask
  sources_sought   — Sources Sought / capability statement request
  rfp              — Request for Proposal, evaluation criteria with weights
  rfq              — Request for Quote, commercial items, price-focused
  other            — Doesn't fit any of the above

RUN the quick-kill checklist. Answer true only if you find clear evidence:
  - Product buy: a specific COTS product by name, no "or Equal" clause
  - Facility clearance required that a typical small subcontractor won't hold
  - TS/SCI personnel clearance required for all key personnel
  - On-site military base with no remote option
  - Non-IT NAICS unrelated to professional/technical services
  - Brand Name Only with no "or Equal" clause
  - Restricted contract vehicle (e.g. "must be JWCC awardee")
  - Due in under 5 days with no prior relationship

If any apply, quick_kill=true and quick_kill_reason must quote the specific
language that triggered it. If none apply, quick_kill=false and
quick_kill_reason should be null.

When ready, call save_triage_result with your findings. Do not respond with
findings as chat text — they must go through the tool."""


def _save_triage_impl(
    solicitation_id: int,
    notice_type: str,
    quick_kill: bool,
    quick_kill_reason: str | None,
) -> dict:
    from core.solicitation import SolicitationManager

    mgr = SolicitationManager()
    updated = mgr.update(
        solicitation_id,
        notice_type=notice_type,
        quick_kill=quick_kill,
        quick_kill_reason=quick_kill_reason,
    )
    if updated is None:
        return {"error": f"Solicitation {solicitation_id} not found"}
    return {
        "saved": True,
        "notice_type": notice_type,
        "quick_kill": quick_kill,
        "quick_kill_reason": quick_kill_reason,
    }


async def _run_triage(case_id: int, solicitation_id: int) -> dict:
    """Run the triage agent. Returns the classification read back from the DB."""
    import json as _json

    from claude_agent_sdk import (
        ClaudeSDKClient, ClaudeAgentOptions, tool,
        create_sdk_mcp_server, ToolAnnotations,
    )
    from chat.tools import create_vision_server

    vision_server = create_vision_server(case_id)

    @tool(
        "save_triage_result",
        "Save your classification and quick-kill assessment. Call this once "
        "you're confident, after reading the cover page and early sections.",
        {
            "type": "object",
            "properties": {
                "notice_type": {
                    "type": "string",
                    "enum": ["rfi", "sources_sought", "rfp", "rfq", "other"],
                },
                "quick_kill": {"type": "boolean"},
                "quick_kill_reason": {
                    "type": "string",
                    "description": "Required if quick_kill=true — quote the "
                    "specific disqualifying language.",
                },
            },
            "required": ["notice_type", "quick_kill"],
        },
    )
    async def save_triage_result(args: dict[str, Any]) -> dict[str, Any]:
        try:
            result = _save_triage_impl(
                solicitation_id=solicitation_id,
                notice_type=args["notice_type"],
                quick_kill=args["quick_kill"],
                quick_kill_reason=args.get("quick_kill_reason"),
            )
            return {"content": [{"type": "text", "text": _json.dumps(result, default=str)}]}
        except Exception as exc:
            return {"content": [{"type": "text", "text": f"Failed: {exc}"}], "is_error": True}

    triage_server = create_sdk_mcp_server(
        name="triage", version="1.0.0", tools=[save_triage_result],
    )

    workdir = Path(os.environ.get("VISION_SDK_TMP", "/tmp/vision/sdk"))
    workdir.mkdir(parents=True, exist_ok=True)

    options = ClaudeAgentOptions(
        system_prompt=TRIAGE_SYSTEM_PROMPT,
        mcp_servers={"vision": vision_server, "triage": triage_server},
        allowed_tools=READ_TOOLS + ["mcp__triage__save_triage_result"],
        cwd=str(workdir),
        permission_mode="bypassPermissions",
        setting_sources=[],
    )

    client = ClaudeSDKClient(options=options)
    await client.connect()
    try:
        await client.query(
            f"Classify the solicitation in case {case_id} and run the "
            f"quick-kill checklist. Call save_triage_result when done."
        )
        from claude_agent_sdk.types import ResultMessage
        async for msg in client.receive_response():
            if isinstance(msg, ResultMessage):
                pass  # consume stream
    finally:
        await client.disconnect()

    from core.solicitation import SolicitationManager
    sol = SolicitationManager().get(solicitation_id)
    return {
        "notice_type": sol.get("notice_type") if sol else None,
        "quick_kill": sol.get("quick_kill") if sol else None,
        "quick_kill_reason": sol.get("quick_kill_reason") if sol else None,
    }


# ---------------------------------------------------------------------------
# Phase 2 — Deep Read: 5 single-purpose extractors, run concurrently
# ---------------------------------------------------------------------------

SCOPE_OF_WORK_PROMPT = """You are a federal procurement analyst. Extract the SCOPE OF WORK from this
solicitation — what the government is actually asking for.

Read the Performance Work Statement / Statement of Work (Section C or an
attachment labeled PWS/SOW), the Supplies/Services section (Section B), and
any background section.

Cover in your HTML:
- What is being asked for (services/products), in plain language
- Location / place of performance
- Contract type (FFP, IDIQ, T&M, etc.) if stated
- Any performance metrics or SLAs
- For RFQs: a table of CLINs/line items with quantities and units, if present
- Key requirements as a bulleted or numbered list, distinguishing mandatory
  (shall/must/will) from desirable (should/may) where the document does

Do NOT include compliance/eligibility info, evaluation criteria, or
submission logistics — those are handled elsewhere."""

TECHNICAL_REQUIREMENTS_PROMPT = """You are a federal procurement analyst. Extract the TECHNICAL REQUIREMENTS
from this solicitation — what certifications, qualifications, and specs a
subcontractor needs to have BEFORE bidding.

Read Section H (Special Contract Requirements), the PWS/SOW's personnel and
equipment sections, and any certification requirements.

Cover in your HTML:
- Personnel qualifications (years experience, certs, degrees) per role
- Security clearance requirements — facility and personnel (state "not
  mentioned" if silent; do not assume "none")
- Equipment specs or material standards required
- Safety requirements
- IT security standards if applicable (NIST 800-171, CMMC, FedRAMP, etc.)

Do NOT include scope of work, evaluation criteria, or submission logistics —
those are handled elsewhere."""

DELIVERABLES_TIMELINE_PROMPT = """You are a federal procurement analyst. Extract the DELIVERABLES AND TIMELINE
from this solicitation — when things are due and what the milestones are.

Read the Period of Performance section, delivery schedule, and any
milestone/reporting requirements in the PWS/SOW.

Cover in your HTML:
- Period of performance: base year + option years, with dates if stated
- Submission deadline: date, time, and timezone (triple-check — quote it
  verbatim if it appears in multiple places)
- Key milestones (mobilization, first article, phase-in/phase-out, recurring
  reports) as a table: milestone | due date/interval | notes
- Delivery schedule for any physical deliverables

Do NOT include evaluation criteria or the submission checklist (forms,
format, POC) — those are handled elsewhere."""

EVALUATION_CRITERIA_PROMPT = """You are a federal procurement analyst. Extract the EVALUATION CRITERIA from
this solicitation — how a bid will be judged.

Read Section M (Evaluation Criteria) for RFPs, or the equivalent
"how offers will be evaluated" language for RFQs/RFIs.

Cover in your HTML:
- Evaluation factors, in order of importance, as a table: rank | factor |
  weight (if stated) | subfactors
- Whether it is Best Value Trade-off or Lowest Price Technically Acceptable
  (LPTA) — state explicitly if unclear
- Any pass/fail or go/no-go gate factors
- Page limits tied to specific evaluation volumes, if stated

If this is an RFQ/RFI with no formal evaluation section, state that clearly
rather than inventing factors.

Do NOT include scope of work or submission logistics — those are handled
elsewhere."""

SUBMISSION_CHECKLIST_PROMPT = """You are a federal procurement analyst. Extract the SUBMISSION CHECKLIST from
this solicitation — every document, form, and step required to submit a
compliant response.

Read Section L (Instructions to Offerors) or the equivalent submission
instructions, plus the cover page for POC details.

Cover in your HTML as a checklist (<ul> of items, each a clear action):
- Every required form (by number, e.g. SF-1442, SF-33, SF-LLL) and
  certification
- Required volumes/sections and their page limits, if applicable
- File format requirements (PDF, Word, font, margins)
- Submission method: email address / portal name+URL / physical address
  (quote exactly — these must be copy-paste accurate)
- Subject line format, if specified
- Number of copies, if physical delivery
- Questions-due date, if different from the response due date

Do NOT include scope of work or evaluation criteria — those are handled
elsewhere."""


ARTIFACT_SPECS: list[dict[str, str]] = [
    {
        "key": "scope_of_work",
        "column": "artifact_scope_of_work",
        "label": "Scope of Work",
        "prompt": SCOPE_OF_WORK_PROMPT,
    },
    {
        "key": "technical_requirements",
        "column": "artifact_technical_requirements",
        "label": "Technical Requirements",
        "prompt": TECHNICAL_REQUIREMENTS_PROMPT,
    },
    {
        "key": "deliverables_timeline",
        "column": "artifact_deliverables_timeline",
        "label": "Deliverables & Timeline",
        "prompt": DELIVERABLES_TIMELINE_PROMPT,
    },
    {
        "key": "evaluation_criteria",
        "column": "artifact_evaluation_criteria",
        "label": "Evaluation Criteria",
        "prompt": EVALUATION_CRITERIA_PROMPT,
    },
    {
        "key": "submission_checklist",
        "column": "artifact_submission_checklist",
        "label": "Submission Checklist",
        "prompt": SUBMISSION_CHECKLIST_PROMPT,
    },
]


def _save_artifact_impl(
    solicitation_id: int,
    case_id: int,
    column: str,
    label: str,
    html: str,
) -> dict:
    """Write the artifact to its solicitations column AND mirror it into the
    case's workspace (drafts table, file_type='html', folder='artifacts') so
    it's viewable in Vision's Triage tab.
    """
    from core.solicitation import SolicitationManager

    mgr = SolicitationManager()
    updated = mgr.update(solicitation_id, **{column: html})
    if updated is None:
        return {"error": f"Solicitation {solicitation_id} not found"}

    draft_name = f"TRIAGE — {label}"

    with tx() as conn:
        # Re-running triage should replace the prior mirrored artifact, not
        # accumulate duplicates in the case's Artifacts folder.
        with conn.cursor() as cur:
            cur.execute(
                """DELETE FROM drafts
                   WHERE case_id = %s AND folder = 'artifacts' AND name = %s""",
                (case_id, draft_name),
            )
        insert_draft(
            conn,
            case_id=case_id,
            name=draft_name,
            document_type="other",
            content=[{"html": html}],
            created_by="agent",
            status="final",
            file_type="html",
            folder="artifacts",
        )

    return {"saved": True, "column": column, "length": len(html)}


async def _run_extractor(case_id: int, solicitation_id: int, spec: dict[str, str]) -> dict:
    """Run one extractor agent. Returns {'key', 'ok', 'error'?} — never raises,
    so one failing extractor doesn't take down the others in asyncio.gather.
    """
    import json as _json

    try:
        from claude_agent_sdk import (
            ClaudeSDKClient, ClaudeAgentOptions, tool,
            create_sdk_mcp_server, ToolAnnotations,
        )
        from chat.tools import create_vision_server

        vision_server = create_vision_server(case_id)

        @tool(
            "save_artifact",
            f"Save the completed {spec['label']} HTML artifact. Call this "
            f"once, with the full HTML, after you've read enough to be "
            f"confident. Do not call it multiple times.",
            {
                "type": "object",
                "properties": {
                    "html": {
                        "type": "string",
                        "description": "The complete, self-contained HTML document "
                        "(<!DOCTYPE html> through </html>) for this artifact, "
                        "including the required <style> block.",
                    },
                },
                "required": ["html"],
            },
        )
        async def save_artifact(args: dict[str, Any]) -> dict[str, Any]:
            try:
                result = _save_artifact_impl(
                    solicitation_id=solicitation_id,
                    case_id=case_id,
                    column=spec["column"],
                    label=spec["label"],
                    html=args["html"],
                )
                return {"content": [{"type": "text", "text": _json.dumps(result, default=str)}]}
            except Exception as exc:
                return {"content": [{"type": "text", "text": f"Failed: {exc}"}], "is_error": True}

        artifact_server = create_sdk_mcp_server(
            name=f"artifact_{spec['key']}", version="1.0.0", tools=[save_artifact],
        )

        workdir = Path(os.environ.get("VISION_SDK_TMP", "/tmp/vision/sdk"))
        workdir.mkdir(parents=True, exist_ok=True)

        options = ClaudeAgentOptions(
            system_prompt=spec["prompt"] + "\n\n" + HTML_FORMAT_RULES,
            mcp_servers={"vision": vision_server, "artifact": artifact_server},
            allowed_tools=READ_TOOLS + ["mcp__artifact__save_artifact"],
            cwd=str(workdir),
            permission_mode="bypassPermissions",
            setting_sources=[],
        )

        client = ClaudeSDKClient(options=options)
        await client.connect()
        try:
            await client.query(
                f"Extract the {spec['label']} artifact for the solicitation "
                f"in case {case_id}. Call save_artifact when the HTML is complete."
            )
            from claude_agent_sdk.types import ResultMessage
            async for msg in client.receive_response():
                if isinstance(msg, ResultMessage):
                    pass  # consume stream
        finally:
            await client.disconnect()

        # Verify the artifact was actually written — an agent that never
        # calls save_artifact should count as a failure, not a silent no-op.
        from core.solicitation import SolicitationManager
        sol = SolicitationManager().get(solicitation_id)
        if not sol or not sol.get(spec["column"]):
            return {"key": spec["key"], "ok": False, "error": "Agent did not save an artifact"}

        return {"key": spec["key"], "ok": True}
    except Exception as exc:
        return {"key": spec["key"], "ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def run_solicitation_triage(case_id: int, solicitation_id: int) -> dict:
    """Run the full unattended triage pipeline for one solicitation.

    Sets triage_status through 'running' -> 'complete'|'failed'. Quick-kill
    stops after Phase 1 with no artifacts generated. Otherwise runs all 5
    extractors concurrently; individual extractor failures are tolerated
    (has_partial_artifacts=true) rather than failing the whole run.
    """
    from core.solicitation import SolicitationManager

    mgr = SolicitationManager()
    mgr.update(solicitation_id, triage_status="running", triage_error=None)

    try:
        triage_result = await _run_triage(case_id, solicitation_id)
    except Exception as exc:
        mgr.update(solicitation_id, triage_status="failed", triage_error=str(exc))
        return {"error": str(exc)}

    if triage_result.get("notice_type") is None or triage_result.get("quick_kill") is None:
        err = "Triage agent did not produce a classification"
        mgr.update(solicitation_id, triage_status="failed", triage_error=err)
        return {"error": err}

    if triage_result["quick_kill"]:
        mgr.update(solicitation_id, triage_status="complete")
        return {
            "quick_kill": True,
            "notice_type": triage_result["notice_type"],
            "reason": triage_result.get("quick_kill_reason"),
        }

    results = await asyncio.gather(
        *[_run_extractor(case_id, solicitation_id, spec) for spec in ARTIFACT_SPECS]
    )

    errors = [
        f"{spec['label']}: {r.get('error')}"
        for spec, r in zip(ARTIFACT_SPECS, results)
        if not r.get("ok")
    ]
    has_partial = bool(errors)

    mgr.update(
        solicitation_id,
        triage_status="complete",
        has_partial_artifacts=has_partial,
        triage_error="; ".join(errors) if errors else None,
    )

    # Auto-trigger vendor matching — only reached on a non-quick-killed,
    # completed triage run (mirrors the sam_fetch -> solicitation_triage
    # chain in worker.py's process_sam_fetch_job).
    try:
        from ingestion.jobs import enqueue

        enqueue(
            case_id=case_id,
            job_type="vendor_matching",
            metadata={"solicitation_id": solicitation_id},
        )
    except Exception as e:
        print(f"Failed to enqueue vendor_matching for solicitation_id={solicitation_id}: {e}")

    return {
        "quick_kill": False,
        "notice_type": triage_result["notice_type"],
        "has_partial_artifacts": has_partial,
        "errors": errors,
    }


def run_solicitation_triage_pipeline(case_id: int, solicitation_id: int) -> dict:
    """Synchronous wrapper — called by the background worker."""
    return asyncio.run(run_solicitation_triage(case_id, solicitation_id))
