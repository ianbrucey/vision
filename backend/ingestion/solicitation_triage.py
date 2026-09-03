"""
Vision — Solicitation Triage Pipeline (Unattended).

Runs after a federal solicitation's documents finish fetching (or on-demand
via the manual trigger). Classifies the notice type, runs the quick-kill
checklist, and always extracts 5 partner-facing HTML artifacts in parallel
(regardless of quick-kill outcome — quick-kill only gates the vendor_matching
auto-enqueue). Each artifact is written directly to its `solicitations` column
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
  - Restricted contract vehicle (e.g. "must be JWCC awardee")
  - Due in under 5 days with no prior relationship

If any apply, quick_kill=true and quick_kill_reason must quote the specific
language that triggered it. If none apply, quick_kill=false and
quick_kill_reason should be null.

IMPORTANT: quick_kill only blocks automatic vendor matching — your
classification and the 5 artifact extractors will still run regardless.
Set quick_kill honestly based on the checklist above; don't avoid flagging
just because you want artifact extraction to proceed (it will either way).

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
# Helpers — export + agent invocation
# ---------------------------------------------------------------------------


# Keywords for detecting solicitation type from document text.
# Ordered — first match wins (e.g. "Combined Synopsis/Solicitation" before
# the more general "Solicitation").
_TYPE_DETECTION = [
    ("combined_synopsis_solicitation", [
        "Combined Synopsis/Solicitation", "Combined Synopsis / Solicitation",
    ]),
    ("sources_sought", ["Sources Sought", "Source Sought"]),
    ("rfp", ["Request for Proposal", "RFP"]),
    ("rfq", ["Request for Quote", "Request for Quotation", "RFQ"]),
    ("rfi", ["Request for Information", "RFI"]),
    ("presolicitation", ["Presolicitation", "Pre-Solicitation"]),
]


def _detect_notice_type(all_text: str) -> str:
    """Detect the solicitation notice type from document text.

    Returns one of: combined_synopsis_solicitation, sources_sought, rfp,
    rfq, rfi, presolicitation, or solicitation (default).
    """
    text_lower = all_text.lower()
    for label, keywords in _TYPE_DETECTION:
        for kw in keywords:
            if kw.lower() in text_lower:
                return label
    return "solicitation"


def _export_documents_to_folder(case_id: int, work_dir: Path) -> dict:
    """Export all document text for a case to work_dir as markdown.

    Uses blocks (which carry 0-based page numbers from datalab OCR) when
    available; falls back to sections when a document has no blocks.
    Page numbers are converted to 1-based in the output and included as
    `[page N]` markers so agents can cite their sources.

    Returns {'doc_count': int, 'total_chars': int, 'notice_type': str}.
    """
    from core.db import connect

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name FROM documents WHERE case_id = %s ORDER BY id",
                (case_id,),
            )
            docs = cur.fetchall()

            total_chars = 0
            all_text_parts = []
            for i, (doc_id, doc_name) in enumerate(docs):
                safe_name = doc_name.replace("/", "_").replace(" ", "_")[:80]
                out_path = work_dir / f"{i+1:02d}_{safe_name}.md"

                # Prefer blocks — they carry 0-based page numbers.
                cur.execute(
                    """SELECT page, text_content
                       FROM blocks
                       WHERE document_id = %s
                       ORDER BY id""",
                    (doc_id,),
                )
                blocks = cur.fetchall()

                if blocks:
                    lines = []
                    current_page = None
                    for page, text in blocks:
                        if text and text.strip():
                            # page is 0-based from datalab OCR → 1-based display
                            page_1 = int(page) + 1 if page is not None else None
                            if page_1 is not None and page_1 != current_page:
                                current_page = page_1
                                lines.append(f"\n[page {current_page}]\n")
                            lines.append(text.strip() + "\n")
                            all_text_parts.append(text)
                else:
                    # Fallback to sections (may not have page numbers).
                    cur.execute(
                        """SELECT heading_level, title, search_text,
                                  page_start, page_end
                           FROM sections
                           WHERE document_id = %s
                           ORDER BY id""",
                        (doc_id,),
                    )
                    sections = cur.fetchall()

                    lines = []
                    current_page = None
                    for level, title, text, page_start, page_end in sections:
                        # page_start is also 0-based when present
                        if page_start is not None:
                            page_1 = int(page_start) + 1
                            if page_1 != current_page:
                                current_page = page_1
                                lines.append(f"\n[page {current_page}]\n")
                        if title and title.strip():
                            h = "#" * min(int(level or 0) + 1, 4)
                            lines.append(f"\n{h} {title.strip()}\n")
                        if text and text.strip():
                            lines.append(text.strip() + "\n")
                            all_text_parts.append(text)

                content = "\n".join(lines)
                out_path.write_text(content)
                total_chars += len(content)

            notice_type = _detect_notice_type(" ".join(all_text_parts))

        return {
            "doc_count": len(docs),
            "total_chars": total_chars,
            "notice_type": notice_type,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Template-based artifact specs
# ---------------------------------------------------------------------------

_TEMPLATE_SPECS: list[dict] = [
    {
        "key": "sow_technical",
        "template": "sow_technical.html",
        "output": "sow_technical_requirements.html",
        "label": "Scope of Work & Technical Requirements",
    },
    {
        "key": "submission",
        "template": "submission_requirements.html",
        "output": "submission_requirements.html",
        "label": "Submission Requirements & Instructions",
    },
    {
        "key": "sourcing",
        "template": "sourcing_script.html",
        "output": "sourcing_script.html",
        "label": "Sourcing Script",
    },
]

# Maps template keys → solicitations.artifact_* columns and draft labels.
_ARTIFACT_PERSIST: dict[str, dict] = {
    "sow_technical": {
        "column": "artifact_scope_of_work",
        "label": "Scope of Work & Technical Requirements",
    },
    "submission": {
        "column": "artifact_submission_checklist",
        "label": "Submission Requirements & Instructions",
    },
    "sourcing": {
        "column": "artifact_evaluation_criteria",
        "label": "Sourcing Script",
    },
}


def _persist_artifacts(
    solicitation_id: int, case_id: int, work_dir: Path
) -> dict:
    """Read produced HTML files and write them to the solicitations row
    AND the case's workspace (drafts table, folder='artifacts').

    Returns {'count': int, 'errors': list[str]}.
    """
    from core.db import tx, insert_draft
    from core.solicitation import SolicitationManager

    mgr = SolicitationManager()
    errors: list[str] = []
    count = 0

    for spec in _TEMPLATE_SPECS:
        key = spec["key"]
        persist = _ARTIFACT_PERSIST.get(key)
        if not persist:
            continue

        html_path = work_dir / spec["output"]
        if not html_path.exists():
            errors.append(f"{key}: file not found")
            continue

        html = html_path.read_text()
        if len(html) < 100:
            errors.append(f"{key}: output too small ({len(html)} chars)")
            continue

        column = persist["column"]
        label = persist["label"]

        # 1. Write to solicitations.artifact_* column → Triage tab
        mgr.update(solicitation_id, **{column: html})
        # If the solicitation doesn't exist, mgr.update returns None
        # but that shouldn't happen here — we just created it.

        # 2. Write to drafts table → Workspace (Artifacts folder)
        draft_name = f"TRIAGE — {label}"
        with tx() as conn:
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

        count += 1

    return {"count": count, "errors": errors}

_EXTRACTION_RULES = """\
RULES (follow exactly):
1. Every placeholder looks like [EXTRACT: description]. Replace each one
   with the relevant content from the documents.
2. Do NOT change ANYTHING else — no new CSS, no new HTML elements, no
   rewording of headings, no changing colors or layout. Only replace the
   placeholders.
3. Use exact text from the documents where possible. Quote dates, email
   addresses, and form numbers verbatim.
4. CITE PAGE NUMBERS: Source documents have [page N] markers (1-based).
   After every extracted fact, append the page reference in parentheses:
   "(p. 3)" or "(pp. 3-4)". Example: "Response deadline is Aug 28, 2026
   at 10:00 AM JST (p. 1)." If multiple pages discuss the same fact,
   list them: "(pp. 2, 5, 12)".
5. When information is genuinely NOT found in the documents, use
   <span class="not-specified">Not specified</span> or the appropriate
   "not found" text already indicated in the placeholder description.
6. Delete unused <li> items only when the placeholder description
   explicitly says "delete this line if none" or "delete unused lines."
   Otherwise keep the structure intact.
7. NEVER use an em dash (—) anywhere in extracted content. Use a comma,
   period, colon, or parentheses instead.
8. When you are done, call save_artifact with the complete HTML."""

# Type-specific guidance appended to the system prompt per notice type.
_TYPE_GUIDANCE: dict[str, str] = {
    "combined_synopsis_solicitation": """\
This is a Combined Synopsis/Solicitation — the most common federal
opportunity type. All sections typically apply. It may use SF-1449.
Look for CLIN structures in the pricing/B Schedule.""",

    "sources_sought": """\
This is a Sources Sought / market research notice. There is NO formal
proposal submission and NO pricing request. The agency is surveying
the market to see what vendors exist.
- Submission: capability statements, not full proposals. Forms and
  certifications are usually NOT required at this stage.
- SOW: the agency may describe the work in general terms only.
- Sourcing: focus on finding subs who can strengthen a capability
  statement — relevant past performance, socio-economic status,
  technical capabilities that align with the stated need.""",

    "rfp": """\
This is a formal Request for Proposal (RFP). Evaluation criteria with
weights are expected (Section M). Proposals are typically voluminous.
All template sections apply — extract everything available.""",

    "rfq": """\
This is a Request for Quote (RFQ) — commercial items, price-focused.
- Look for CLIN/line-item structures with quantities and units.
- Evaluation is often LPTA (Lowest Price Technically Acceptable).
- Submission may be simpler — quote form instead of full proposal.
- Sourcing: focus on authorized resellers, competitive pricing,
  ability to meet exact specs with no substitutions.""",

    "rfi": """\
This is a Request for Information (RFI) — market research only.
No pricing, no formal submission, no contract award from this notice.
- Submission: industry feedback, white papers, capability summaries.
  No forms or certifications are typically required.
- SOW: may be high-level or conceptual — the government is still
  defining requirements.
- Sourcing: focus on finding subs with deep domain expertise who
  can contribute to a compelling RFI response that positions your
  company for the eventual RFP.""",

    "presolicitation": """\
This is a Presolicitation — a preview before the formal solicitation
drops. Not all details may be available yet.
- The synopsis may reference a future RFP/RFQ number and date.
- Extract what's available; note gaps clearly.""",

    "solicitation": """\
This is a federal solicitation. Standard sections (A-M) may apply.
Extract everything available from the documents.""",
}


_SOURCING_SCRIPT_EMAIL_GUIDANCE = """\
SAMPLE OUTREACH EMAIL: This artifact contains a ready-to-send email
(Subject + body) that a sourcing specialist copies and pastes directly
into an email client to contact a potential subcontractor — the same way
a technical recruiter emails candidates about a job opening.
- Write real, complete copy — not a description of what the email should
  contain. Use the actual solicitation number, agency, scope, and
  deadline you extracted elsewhere in this document.
- TONE: Write like a busy person emailing another busy person — short,
  plain, and direct. No corporate throat-clearing, no legalese, no
  restating the solicitation's formal language back at them. Get to the
  point in the first sentence. Prefer short sentences and everyday words
  over long compound sentences.
- ONLY ASK WHAT WE ACTUALLY NEED RIGHT NOW: at this stage we only need to
  know if they have the capacity and qualifications to do the work, and
  a rough price/lead time. Do NOT ask for UEI, CAGE code, SAM.gov
  registration status, Buy American / country-of-origin forms, bonding,
  insurance certificates, or any other compliance paperwork — that comes
  later once we know they can do the job. Do not reference the
  "Questions to Ask Subcontractors" list wholesale; pull only the 1-2
  questions from it that are about capability/capacity (e.g. relevant
  experience, ability to meet the deadline), not administrative/
  registration questions.
- Keep it to 3 short paragraphs: (1) one line on who we are and the
  opportunity (agency + solicitation #), (2) one line on the scope in
  plain English and what we need from them (can they do it, rough
  price/lead time), (3) the deadline to respond.
- BRAND: We are "Gov Services Connect" — refer to us by that name in the
  body of the email (e.g. "Gov Services Connect is pursuing..."). Do NOT
  use "Justice Quest LLC" in the body text.
- SIGNATURE: End with this exact literal signature block, on separate
  lines, with no other placeholders:
  "Ian Bruce"
  "Director"
  "Gov Services Connect (a Justice Quest LLC company)"
  "470-785-3007"
  "https://govservicesconnect.com"
  Do not include an email address in the signature — outreach is sent
  from a Gov Services Connect email address.
- The email body placeholder must contain real line breaks between
  paragraphs and no HTML tags — it will be pasted as-is into an email."""


def _build_extraction_prompt(notice_type: str, artifact_label: str) -> str:
    """Build a type-aware system prompt for one extraction agent."""
    guidance = _TYPE_GUIDANCE.get(notice_type, _TYPE_GUIDANCE["solicitation"])
    extra = (
        f"\n\n{_SOURCING_SCRIPT_EMAIL_GUIDANCE}"
        if artifact_label == "Sourcing Script"
        else ""
    )
    return (
        f"You are a federal procurement analyst. Your job is to fill in "
        f"placeholders in an HTML template with content extracted from "
        f"the solicitation documents in your workspace.\n\n"
        f"AVAILABLE TOOLS:\n"
        f"- `list_documents`: Lists all files in the workspace with sizes and line counts.\n"
        f"- `search_documents(query)`: Search across documents for clauses, CLINs, SOW, wage rates, or keywords.\n"
        f"- `read_document(filename, start_line, max_lines)`: Read specific lines or sections from any file.\n"
        f"- `save_artifact(html)`: Call this with the complete populated HTML when all placeholders are filled.\n\n"
        f"WORKFLOW:\n"
        f"1. Use `search_documents` and `read_document` to inspect the relevant documents (e.g. SOW/PWS, instructions, pricing sheets).\n"
        f"2. Extract the exact facts, requirements, dates, and CLINs from the text.\n"
        f"3. Note source page numbers from the document [page N] markers and cite them as (p. N).\n"
        f"4. Replace every [EXTRACT: ...] placeholder in the template.\n"
        f"5. Call `save_artifact` with the complete, fully populated HTML.\n\n"
        f"NOTICE TYPE: {notice_type}\n{guidance}\n\n"
        f"This is the \"{artifact_label}\" artifact.\n\n"
        f"{_EXTRACTION_RULES}"
        f"{extra}"
    )


async def _invoke_triage_agent(
    case_id: int, work_dir: Path, notice_type: str
) -> str:
    """Invoke 3 agents in parallel — one per artifact template.

    Each agent inspects the exported documents in work_dir using dedicated
    document tools (list, read, search) and fills in the designated HTML template.
    Backend is selected via VISION_TRIAGE_BACKEND env var.
    """
    import os as _os

    backend = _os.environ.get("VISION_TRIAGE_BACKEND", "claude_sdk")
    templates_dir = Path(__file__).resolve().parent.parent / "test_triage" / "templates"

    # Build concise overview of files in work_dir for orientation
    doc_summary = []
    for md_file in sorted(work_dir.glob("*.md")):
        try:
          line_count = sum(1 for _ in md_file.open(encoding="utf-8"))
          size_kb = md_file.stat().st_size / 1024
          doc_summary.append(f"- `{md_file.name}` ({size_kb:.1f} KB, {line_count} lines)")
        except Exception:
          doc_summary.append(f"- `{md_file.name}`")
    docs_overview = "\n".join(doc_summary) if doc_summary else "No files found."

    # Run 3 parallel agents, one per template
    tasks = []
    for spec in _TEMPLATE_SPECS:
        template_path = templates_dir / spec["template"]
        if not template_path.exists():
            print(
                f"[solicitation_triage] WARNING: template not found: {template_path}"
            )
            continue
        template_html = template_path.read_text()

        system_prompt = _build_extraction_prompt(notice_type, spec["label"])

        if backend == "claude_sdk":
            tasks.append(
                _run_template_extractor(
                    spec=spec,
                    system_prompt=system_prompt,
                    template_html=template_html,
                    docs_overview=docs_overview,
                    work_dir=work_dir,
                    case_id=case_id,
                    notice_type=notice_type,
                )
            )
        else:
            raise ValueError(f"Unknown triage backend: {backend}")

    if not tasks:
        raise RuntimeError("No extraction tasks — templates missing?")

    results = await asyncio.gather(*tasks)

    # Report results
    ok = [r for r in results if r.get("ok")]
    failed = [r for r in results if not r.get("ok")]
    print(
        f"[solicitation_triage] case_id={case_id} — "
        f"{len(ok)}/{len(results)} artifacts extracted"
    )
    for f in failed:
        print(f"  FAILED: {f['key']} — {f.get('error')}")

    return f"{len(ok)} artifacts written to {work_dir}"


# ---------------------------------------------------------------------------
# Single-template extractor (Claude Agent SDK)
# ---------------------------------------------------------------------------


async def _run_template_extractor(
    spec: dict,
    system_prompt: str,
    template_html: str,
    docs_overview: str,
    work_dir: Path,
    case_id: int,
    notice_type: str,
) -> dict:
    """Run one Claude Agent SDK agent to inspect files and fill an HTML template.

    The agent has access to `list_documents`, `read_document`, `search_documents`,
    and `save_artifact` to inspect files on-demand instead of receiving huge payloads.
    Returns {'key': str, 'ok': bool, 'error': str|None}.
    """
    import json as _json
    from datetime import datetime

    from claude_agent_sdk import (
        ClaudeSDKClient, ClaudeAgentOptions, tool,
        create_sdk_mcp_server,
    )

    output_path = work_dir / spec["output"]

    @tool(
        "list_documents",
        "List all available solicitation documents in the workspace with file sizes and line counts.",
        {"type": "object", "properties": {}},
    )
    async def list_documents(args: dict) -> dict:
        files_info = []
        for f in sorted(work_dir.glob("*.md")):
            try:
                lines = sum(1 for _ in f.open(encoding="utf-8"))
                files_info.append({
                    "filename": f.name,
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "lines": lines,
                })
            except Exception:
                files_info.append({"filename": f.name})
        return {"content": [{"type": "text", "text": _json.dumps(files_info, indent=2)}]}

    @tool(
        "read_document",
        "Read a range of lines from a specific solicitation document in the workspace.",
        {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The exact name of the file to read (e.g. '04_Solicitation.pdf.md').",
                },
                "start_line": {
                    "type": "integer",
                    "description": "1-based line number to start reading from.",
                    "default": 1,
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to return (default: 300, max: 600).",
                    "default": 300,
                },
            },
            "required": ["filename"],
        },
    )
    async def read_document(args: dict) -> dict:
        fname = Path(args["filename"]).name
        target = work_dir / fname
        if not target.exists() or not target.is_file():
            avail = [f.name for f in work_dir.glob("*.md")]
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: File '{fname}' not found. Available documents: {avail}",
                }],
                "is_error": True,
            }

        start_line = max(1, int(args.get("start_line") or 1))
        max_lines = min(600, max(1, int(args.get("max_lines") or 300)))

        try:
            with target.open("r", encoding="utf-8", errors="replace") as fp:
                all_lines = fp.readlines()
            total = len(all_lines)
            start_idx = start_line - 1
            end_idx = min(total, start_idx + max_lines)
            slice_lines = all_lines[start_idx:end_idx]
            numbered = [f"{i:4d}: {line.rstrip()}" for i, line in enumerate(slice_lines, start_line)]
            header = f"=== {fname} (lines {start_line}–{end_idx} of {total}) ===\n"
            return {"content": [{"type": "text", "text": header + "\n".join(numbered)}]}
        except Exception as exc:
            return {
                "content": [{"type": "text", "text": f"Error reading '{fname}': {exc}"}],
                "is_error": True,
            }

    @tool(
        "search_documents",
        "Search all solicitation documents in the workspace for keywords, clauses, CLINs, or phrases.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Case-insensitive search string (e.g. 'PWS', 'evaluation', 'CLIN', 'wage determination', 'deadline', 'bonding').",
                }
            },
            "required": ["query"],
        },
    )
    async def search_documents(args: dict) -> dict:
        query = str(args.get("query", "")).strip().lower()
        if not query:
            return {"content": [{"type": "text", "text": "Error: query cannot be empty"}]}

        matches = []
        for f in sorted(work_dir.glob("*.md")):
            try:
                with f.open("r", encoding="utf-8", errors="replace") as fp:
                    for line_no, line in enumerate(fp, 1):
                        if query in line.lower():
                            matches.append(f"[{f.name}:{line_no}] {line.strip()[:180]}")
                            if len(matches) >= 50:
                                break
            except Exception:
                pass
            if len(matches) >= 50:
                break

        if not matches:
            return {
                "content": [{
                    "type": "text",
                    "text": f"No occurrences of '{query}' found. Try broader terms or read the main solicitation/PWS file directly.",
                }]
            }
        return {"content": [{"type": "text", "text": f"Found {len(matches)} match(es):\n" + "\n".join(matches)}]}

    @tool(
        "save_artifact",
        f"Save the completed {spec['label']} HTML. Call this once with the "
        f"fully populated HTML — every [EXTRACT: ...] placeholder replaced.",
        {
            "type": "object",
            "properties": {
                "html": {
                    "type": "string",
                    "description": "The complete, self-contained HTML document "
                    "with all [EXTRACT: ...] placeholders replaced.",
                },
            },
            "required": ["html"],
        },
    )
    async def save_artifact(args: dict) -> dict:
        today = datetime.now().strftime("%B %d, %Y")
        html = args["html"].replace("[EXTRACT: date generated]", today)
        output_path.write_text(html, encoding="utf-8")
        return {"content": [{"type": "text", "text": f"{spec['label']} saved."}]}

    triage_server = create_sdk_mcp_server(
        name=f"triage_{spec['key']}",
        version="1.0.0",
        tools=[list_documents, read_document, search_documents, save_artifact],
    )

    user_message = (
        f"You are assigned to extract the \"{spec['label']}\" artifact for Case {case_id} "
        f"(Notice Type: {notice_type}).\n\n"
        f"=== SOLICITATION DOCUMENTS IN YOUR WORKSPACE ===\n"
        f"{docs_overview}\n\n"
        f"=== HTML TEMPLATE TO POPULATE ===\n"
        f"{template_html}\n"
        f"=== END TEMPLATE ===\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Use `search_documents` and `read_document` to inspect the documents in your workspace.\n"
        f"2. Note the page citations [page N] in the source files and cite them as (p. N).\n"
        f"3. Replace every [EXTRACT: ...] placeholder in the template above with your findings.\n"
        f"4. Call `save_artifact` with the complete HTML document when ready."
    )

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        mcp_servers={"tools": triage_server},
        allowed_tools=[
            "mcp__tools__list_documents",
            "mcp__tools__read_document",
            "mcp__tools__search_documents",
            "mcp__tools__save_artifact",
        ],
        cwd=str(work_dir),
        permission_mode="bypassPermissions",
        setting_sources=[],
    )

    client = ClaudeSDKClient(options=options)
    try:
        await client.connect()
        await client.query(user_message)
        from claude_agent_sdk.types import ResultMessage
        async for msg in client.receive_response():
            if isinstance(msg, ResultMessage):
                pass
    except Exception as exc:
        return {"key": spec["key"], "ok": False, "error": str(exc)}
    finally:
        await client.disconnect()

    # Verify the agent actually wrote the file
    if output_path.exists() and len(output_path.read_text()) > 100:
        return {"key": spec["key"], "ok": True, "error": None}
    return {
        "key": spec["key"],
        "ok": False,
        "error": "Agent did not save artifact (file missing or too small)",
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def run_solicitation_triage(case_id: int, solicitation_id: int) -> dict:
    """Run the full unattended triage pipeline for one solicitation.

    Sets triage_status through 'running' -> 'complete'|'failed'. Artifacts
    are ALWAYS extracted (even when quick_kill=true) — quick-kill only gates
    the vendor_matching auto-enqueue. All 5 extractors run concurrently;
    individual extractor failures are tolerated (has_partial_artifacts=true)
    rather than failing the whole run.
    """
    from core.solicitation import SolicitationManager

    mgr = SolicitationManager()
    mgr.update(solicitation_id, triage_status="running", triage_error=None)

    if True:
        # ---- New triage pipeline (WIP) ----
        from datetime import datetime
        from pathlib import Path
        from core.db import connect

        # ---- Step 1: Export document text from DB to case folder ----
        work_dir = Path(__file__).resolve().parent.parent / "test_triage" / f"case_{case_id}"
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            exported = _export_documents_to_folder(case_id, work_dir)
            notice_type = exported["notice_type"]
            print(
                f"[solicitation_triage] case_id={case_id} solicitation_id={solicitation_id} "
                f"— exported {exported['doc_count']} docs, {exported['total_chars']:,} chars, "
                f"type={notice_type}"
            )

            # ---- Step 2: Invoke 3 parallel agents to fill templates ----
            try:
                result = await _invoke_triage_agent(case_id, work_dir, notice_type)
                print(
                    f"[solicitation_triage] case_id={case_id} — "
                    f"agent completed: {result}"
                )
            except Exception as e:
                print(
                    f"[solicitation_triage] case_id={case_id} — "
                    f"agent FAILED: {e}"
                )
                mgr.update(solicitation_id, triage_status="failed", triage_error=str(e))
                return {"error": str(e)}

            # ---- Step 3: Persist artifacts to DB (solicitations + workspace) ----
            persisted = _persist_artifacts(solicitation_id, case_id, work_dir)
            print(
                f"[solicitation_triage] case_id={case_id} — "
                f"persisted {persisted['count']} artifacts to DB, "
                f"errors={persisted['errors']}"
            )

            mgr.update(
                solicitation_id,
                triage_status="complete",
                triage_error=None,
                has_partial_artifacts=bool(persisted["errors"]),
            )

            return {
                "quick_kill": False,
                "quick_kill_reason": None,
                "notice_type": "other",
                "has_partial_artifacts": False,
                "errors": [],
            }
        finally:
            # ---- Cleanup: always remove the per-case work directory when
            # triage finishes, whether it succeeded or failed. Only this
            # case_{id} subfolder is removed — test_triage/templates and
            # any other shared/unrelated content are left untouched.
            import shutil
            try:
                shutil.rmtree(work_dir, ignore_errors=True)
                print(f"[solicitation_triage] case_id={case_id} — cleaned up {work_dir}")
            except Exception as e:
                print(f"[solicitation_triage] case_id={case_id} — cleanup warning: {e}")
    else:
        # ---- Current triage + extractors (to be replaced) ----
        try:
            triage_result = await _run_triage(case_id, solicitation_id)
        except Exception as exc:
            mgr.update(solicitation_id, triage_status="failed", triage_error=str(exc))
            return {"error": str(exc)}

        if triage_result.get("notice_type") is None or triage_result.get("quick_kill") is None:
            err = "Triage agent did not produce a classification"
            mgr.update(solicitation_id, triage_status="failed", triage_error=err)
            return {"error": err}

        # Always run artifact extraction regardless of quick-kill status.
        # Quick-kill only gates the vendor_matching auto-enqueue below —
        # we still need the 5 artifacts to understand the solicitation fully.
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

        return {
            "quick_kill": triage_result["quick_kill"],
            "quick_kill_reason": triage_result.get("quick_kill_reason"),
            "notice_type": triage_result["notice_type"],
            "has_partial_artifacts": has_partial,
            "errors": errors,
        }


def run_solicitation_triage_pipeline(case_id: int, solicitation_id: int) -> dict:
    """Synchronous wrapper — called by the background worker."""
    return asyncio.run(run_solicitation_triage(case_id, solicitation_id))
