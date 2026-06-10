"""
Vision — Solicitation Pipeline Runner.

Runs the full solicitation assembly line for a case. Orchestrates sub-agents
through: Triage → Deep Read (parallel) → Synthesize → Assess → Draft → Quality.

Sub-agents are loaded from .claude/agents/*.md. They use MCP tools scoped to
the case's "vision" server for reading documents, writing workspace artifacts,
and accessing the company profile.

Usage:
    cd backend && python -m scripts.solicitation_pipeline --case-id 5
    cd backend && python -m scripts.solicitation_pipeline --case-id 5 --profile-id 1
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import yaml

# Project root is three levels up from this file:
#   backend/scripts/solicitation_pipeline.py → backend → vision/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Agent loader — reads .claude/agents/*.md → AgentDefinition
# ---------------------------------------------------------------------------


def _parse_agent_md(file_path: Path) -> dict:
    """Parse a .claude/agents/*.md file into {name, description, prompt, tools, model}."""
    raw = file_path.read_text()
    parts = raw.split("---")
    if len(parts) < 3:
        raise ValueError(f"Invalid agent frontmatter in {file_path}")
    meta = yaml.safe_load(parts[1])
    body = parts[2].strip()
    return {
        "name": meta["name"],
        "description": meta.get("description", ""),
        "prompt": body,
        "tools": meta.get("tools"),
        "model": meta.get("model", "inherit"),
    }


def load_agents() -> dict[str, dict]:
    """Load all solicitation agent definitions from .claude/agents/."""
    agents_dir = PROJECT_ROOT / ".claude" / "agents"
    if not agents_dir.is_dir():
        print(f"Warning: No agents directory at {agents_dir}")
        return {}
    agents = {}
    for md_file in sorted(agents_dir.glob("*.md")):
        agent = _parse_agent_md(md_file)
        agents[agent["name"]] = agent
    return agents


# ---------------------------------------------------------------------------
# SDK tool adaptation — injected into each sub-agent's system prompt
# ---------------------------------------------------------------------------

SDK_TOOL_PREAMBLE = """## Tools Available (Vision Agent SDK)

You are running inside the Vision platform with direct database access.
There is NO filesystem — use the tools below exclusively.

**Reading solicitation documents:**
- get_case — Full case overview including parties, documents, events, strategies
- list_documents — All documents in the case, filterable by document_type
- get_document_structure — Section outline (table of contents) for a document
- search_blocks — Full-text keyword search using PostgreSQL ts_rank/ts_headline
- semantic_search — Concept/meaning search via pgvector embeddings
- search_hybrid — Combined keyword + semantic with merge/ranking
- search_sections — Find sections by fuzzy title matching (trigram similarity)
- get_block_context — Read a block with surrounding pages for context
- get_blocks_in_section — Read all blocks within a section, optional block_type filter

**Reading/writing workspace artifacts:**
- list_workspace_items — List existing items, filterable by folder
- get_workspace_item — Read an item's full content
- create_workspace_item — Create a new workspace item
- update_workspace_item — Modify an existing workspace item

**Company profile:**
- get_case_profile — Get the company profile attached to this case
- list_company_profiles — List all profiles (metadata only)
- get_company_profile — Get full data for a specific profile by ID
"""

# Injected AFTER the agent's original prompt — the last thing it reads.
# This overrides any filesystem-oriented language in the original prompt.
MANDATORY_WRITE_INSTRUCTION = """
## ⛔ MANDATORY — READ THIS LAST ⛔

You MUST write your artifact via create_workspace_item BEFORE responding.
This is NOT optional. If you respond without writing the artifact, your
work is discarded and the pipeline fails.

To write your artifact:
```
create_workspace_item(
    name="TRIAGE - Case N",     # use the correct artifact name
    file_type="markdown",
    folder="artifacts",
    document_type="other",
    content={"markdown": "# Title\\n\\nYour full markdown artifact here..."}
)
```

1. Do ALL your reading and analysis first
2. Compose the COMPLETE artifact as a markdown string
3. Call create_workspace_item with the full artifact
4. Verify you get a success response with an item_id
5. ONLY THEN respond with a brief summary

Do NOT respond with your findings as text. Findings go in the artifact.
Your text response should only confirm the artifact was written successfully.
"""


# ---------------------------------------------------------------------------
# Agent-specific tool lists
# ---------------------------------------------------------------------------

# Read + document search + write-one-artifact (Phase 2-3 extraction agents)
EXTRACTOR_TOOLS = [
    "mcp__vision__get_case",
    "mcp__vision__list_documents",
    "mcp__vision__get_document_structure",
    "mcp__vision__search_blocks",
    "mcp__vision__semantic_search",
    "mcp__vision__search_hybrid",
    "mcp__vision__search_sections",
    "mcp__vision__get_block_context",
    "mcp__vision__get_blocks_in_section",
    "mcp__vision__list_workspace_items",
    "mcp__vision__get_workspace_item",
    "mcp__vision__create_workspace_item",
]

# Workspace read + write (synthesis agents: brief-writer, assessor)
SYNTHESIS_TOOLS = [
    "mcp__vision__list_workspace_items",
    "mcp__vision__get_workspace_item",
    "mcp__vision__create_workspace_item",
]

# Workspace read + write + profile access (response drafter)
DRAFTER_TOOLS = [
    "mcp__vision__list_workspace_items",
    "mcp__vision__get_workspace_item",
    "mcp__vision__create_workspace_item",
    "mcp__vision__update_workspace_item",
    "mcp__vision__get_case_profile",
    "mcp__vision__get_company_profile",
    "mcp__vision__list_company_profiles",
]

# Workspace read + write + document verification (quality checker)
QUALITY_TOOLS = [
    "mcp__vision__list_workspace_items",
    "mcp__vision__get_workspace_item",
    "mcp__vision__create_workspace_item",
    "mcp__vision__get_case",
    "mcp__vision__list_documents",
    "mcp__vision__get_document_structure",
    "mcp__vision__search_blocks",
    "mcp__vision__get_block_context",
]

# Which tool set each agent gets
AGENT_TOOL_MAP: dict[str, list[str]] = {
    "solicitation-triage": EXTRACTOR_TOOLS,
    "scope-extractor": EXTRACTOR_TOOLS,
    "compliance-extractor": EXTRACTOR_TOOLS,
    "submission-extractor": EXTRACTOR_TOOLS,
    "opportunity-brief-writer": SYNTHESIS_TOOLS,
    "go-no-go-assessor": SYNTHESIS_TOOLS,
    "response-drafter": DRAFTER_TOOLS,
    "quality-gate-checker": QUALITY_TOOLS,
}


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


async def run_pipeline(
    case_id: int,
    profile_id: int | None = None,
) -> None:
    """Run the full solicitation pipeline for a case."""

    from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition
    from chat.tools import create_vision_server

    # ---- Attach profile to case if specified ----
    if profile_id is not None:
        from core.db import connect as _db_connect
        conn = _db_connect()
        try:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "UPDATE cases SET profile_id = %s WHERE id = %s RETURNING id, name",
                    (profile_id, case_id),
                )
                updated = cur.fetchone()
            conn.commit()
            if updated:
                print(f"Attached profile {profile_id} to case {case_id} ({updated['name']})")
            else:
                print(f"Warning: case {case_id} not found — continuing anyway")
        finally:
            conn.close()

    # ---- Create the MCP server ----
    vision_server = create_vision_server(case_id)

    # ---- Load and adapt agent definitions ----
    raw_agents = load_agents()
    if not raw_agents:
        print("No solicitation agents found in .claude/agents/")
        sys.exit(1)

    agents: dict[str, AgentDefinition] = {}
    for name, raw in raw_agents.items():
        tool_list = AGENT_TOOL_MAP.get(name, ["mcp__vision__*"])
        # Preamble first (tool awareness), original prompt (process + output format),
        # mandatory write instruction LAST — overrides any filesystem language
        adapted_prompt = (
            SDK_TOOL_PREAMBLE
            + "\n---\n\n"
            + raw["prompt"]
            + "\n---\n\n"
            + MANDATORY_WRITE_INSTRUCTION
        )

        agents[name] = AgentDefinition(
            description=raw["description"],
            prompt=adapted_prompt,
            tools=tool_list,
            model=raw.get("model", "sonnet") if raw.get("model") != "inherit" else None,
        )

    # ---- Load orchestrator protocol ----
    skill_path = PROJECT_ROOT / ".claude" / "skills" / "solicitation-pipeline" / "SKILL.md"
    if skill_path.is_file():
        skill_content = skill_path.read_text()
        # Strip frontmatter, keep the body
        parts = skill_content.split("---")
        protocol = parts[2].strip() if len(parts) >= 3 else skill_content
    else:
        protocol = "Follow the solicitation pipeline protocol."
        print(f"Warning: Skill not found at {skill_path}")

    profile_note = ""
    if profile_id:
        profile_note = (
            f"\nCompany profile {profile_id} is attached to this case. "
            "Tell the response-drafter to call get_case_profile for firm details.\n"
        )

    # ---- Build the orchestrator prompt ----
    orchestrator_prompt = f"""Run the full solicitation assembly line for case {case_id}.

You are the PIPELINE ORCHESTRATOR. You delegate EVERY task to sub-agents.
You never extract, analyze, or draft anything yourself. Your job is to:
1. Invoke the right sub-agent for each phase
2. Run Phase 3 agents IN PARALLEL (invoke all three, then wait for results)
3. Pause at each human checkpoint and present findings
4. Pass clear task descriptions to each sub-agent

{profile_note}
## Available Sub-Agents

- **solicitation-triage** (Phase 2): Classify notice type, extract header block, run quick-kill. Writes TRIAGE to workspace.
- **scope-extractor** (Phase 3, parallel): Extract scope of work, background, requirements. Writes SCOPE to workspace.
- **compliance-extractor** (Phase 3, parallel): Extract NAICS, clearance, evaluation criteria, contract type. Writes COMPLIANCE to workspace.
- **submission-extractor** (Phase 3, parallel): Extract due date, POC, page limits, format, submission method. Writes SUBMISSION to workspace.
- **opportunity-brief-writer** (Phase 3b): Synthesize the three extractions into a one-page brief. Reads SCOPE/COMPLIANCE/SUBMISSION from workspace, writes BRIEF.
- **go-no-go-assessor** (Phase 4): Score the decision matrix against the brief. Reads BRIEF, writes DECISION.
- **response-drafter** (Phase 5): Draft the full response using the appropriate template. Reads all previous artifacts. MUST call get_case_profile for company info. Writes RESPONSE.
- **quality-gate-checker** (Phase 6): Run the quality checklist against the response. Reads RESPONSE, writes QUALITY.

## Pipeline Protocol

{protocol}

## CRITICAL RULES

1. **Delegate everything.** You are the orchestrator — invoke sub-agents, don't do the work.
2. **Phase 3 MUST run in parallel.** Invoke scope-extractor, compliance-extractor, AND submission-extractor all at once. Do not run them sequentially.
3. **Artifacts go to workspace folder 'artifacts' as markdown.** Tell each sub-agent: "Write [NAME] to workspace folder 'artifacts' as markdown."
4. **Company profile is critical.** The response-drafter MUST call get_case_profile before writing anything. No invented company info.
5. **Sub-agents can read previous artifacts** via list_workspace_items and get_workspace_item. Tell them the exact names to look for.
6. **AUTO-PROCEED — no checkpoints.** This is a non-interactive pipeline run. Check which artifacts already exist (list_workspace_items), skip completed phases, and run ALL remaining phases through Phase 6 WITHOUT STOPPING. Do not ask for permission. Do not pause. Just go.

Start by listing workspace items to see what exists. Skip completed phases. Run every remaining phase through Phase 6 (Quality Gate) in a single continuous execution.
"""

    print(f"╔══════════════════════════════════════════════════════════╗")
    print(f"║  SOLICITATION PIPELINE — Case {case_id:<44}║")
    print(f"║  Sub-agents loaded: {len(agents):<38}║")
    print(f"╠══════════════════════════════════════════════════════════╣")
    print(f"║  Phase 2: Triage        → solicitation-triage           ║")
    print(f"║  Phase 3: Deep Read     → 3 agents IN PARALLEL          ║")
    print(f"║  Phase 3b: Synthesize   → opportunity-brief-writer       ║")
    print(f"║  Phase 4: Assess        → go-no-go-assessor              ║")
    print(f"║  Phase 5: Draft         → response-drafter               ║")
    print(f"║  Phase 6: Quality Gate  → quality-gate-checker           ║")
    print(f"╚══════════════════════════════════════════════════════════╝")
    print()

    # ---- Run the pipeline ----
    turn = 0
    async for message in query(
        prompt=orchestrator_prompt,
        options=ClaudeAgentOptions(
            system_prompt=(
                "You are a federal procurement pipeline orchestrator. "
                "You coordinate sub-agents through a fixed assembly line. "
                "You never do the extraction, analysis, or drafting yourself — "
                "you delegate every task to specialized sub-agents. "
                "You enforce the checkpoint protocol: pause at each gate "
                "for human review. Be terse and professional."
            ),
            mcp_servers={"vision": vision_server},
            agents=agents,
            allowed_tools=["mcp__vision__*", "Agent"],
            setting_sources=["project"],
            cwd=str(PROJECT_ROOT),
            permission_mode="bypassPermissions",
            max_turns=40,
        ),
    ):
        turn += 1
        # Stream text output
        if hasattr(message, "content"):
            for block in (message.content or []):
                if hasattr(block, "text") and block.text:
                    print(block.text, end="", flush=True)
                elif hasattr(block, "name") and hasattr(block, "input"):
                    # Tool use block — sub-agent invocation
                    name = block.name
                    inp = block.input or {}
                    agent_name = inp.get("subagent_type", "") or inp.get("type", "") or ""
                    if name in ("Agent", "Task"):
                        desc = inp.get("description", "") or inp.get("prompt", "") or ""
                        desc_short = desc[:120] + "..." if len(desc) > 120 else desc
                        print(f"\n  ╭─ Sub-agent: {agent_name} ─────────────────")
                        print(f"  │ {desc_short}")
                    else:
                        tool_desc = inp.get("description", "") or str(inp)[:120]
                        print(f"\n  ╭─ Tool: {name}")
                        print(f"  │ {tool_desc}")
        if hasattr(message, "result"):
            subtype = getattr(message, "subtype", "")
            cost = getattr(message, "total_cost_usd", None)
            print(f"\n\nPipeline complete ({subtype})", end="")
            if cost:
                print(f" — cost: ${cost:.4f}")
            else:
                print()
            if hasattr(message, "result"):
                print(f"Result: {message.result}")
            # Use os._exit to avoid async generator cleanup race
            # (aclose() collides with SDK's internal generator).
            import os as _os
            _os._exit(0)

    print("\nPipeline finished (max turns reached).")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Run the solicitation pipeline for a case",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m scripts.solicitation_pipeline --case-id 5\n"
            "  python -m scripts.solicitation_pipeline --case-id 5 --profile-id 1\n"
            "\n"
            "The pipeline runs 6 phases, writing artifacts to the workspace.\n"
            "Human checkpoints pause at each gate for review."
        ),
    )
    parser.add_argument(
        "--case-id", type=int, required=True,
        help="Case ID containing the solicitation documents"
    )
    parser.add_argument(
        "--profile-id", type=int,
        help="Company profile ID to attach to the case (if not already attached)"
    )
    args = parser.parse_args()

    asyncio.run(run_pipeline(case_id=args.case_id, profile_id=args.profile_id))


if __name__ == "__main__":
    main()
