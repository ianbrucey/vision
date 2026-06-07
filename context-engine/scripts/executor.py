#!/usr/bin/env python3
"""
Zero Ambiguity Executor - State 4: Execution

Deploys sub-agents to execute tickets from the Implementation Plan.

Usage:
    python scripts/executor.py                    # Execute all pending tickets
    python scripts/executor.py --ticket 1         # Execute specific ticket
    python scripts/executor.py --status           # Check status of all jobs
    python scripts/executor.py --agent gemini     # Use specific agent (default: gemini)

Workflow:
    1. Reads 05-implementation-plan.md
    2. Parses tickets (marked with ## Ticket format)
    3. For each ticket, spawns a sub-agent with:
       - Ticket description
       - Relevant specs (schema, API contract)
       - Relevant standards
       - Domain contexts
    4. Tracks job completion in subagent_runs/

IMPORTANT: Sub-agents are STATELESS
- Instructions must be COMPLETE and SELF-CONTAINED
- All context is injected automatically from specs/standards

See guides/executor-workflow.md for detailed explanation.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# --- CONFIGURATION ---
ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "subagent_runs"

DIRS = {
    "SPECS": ROOT / "context-engine" / "specs",
    "STANDARDS": ROOT / "context-engine" / "standards",
    "DOMAIN_CONTEXTS": ROOT / "context-engine" / "domain-contexts",
}

FILES = {
    "PLAN": DIRS["SPECS"] / "05-implementation-plan.md",
    "SCHEMA": DIRS["SPECS"] / "01-schema.sql",
    "API": DIRS["SPECS"] / "02-api-contract.json",
    "INFRA": DIRS["SPECS"] / "00.5-existing-infrastructure.md",
    "EXECUTION_STATUS": DIRS["SPECS"] / "06-execution-status.json",
}

# Supported agents
AGENTS = {
    "gemini": {
        "cmd": ["gemini", "-p", "{prompt}", "-m", "gemini-2.5-flash", "-y"],
        "timeout": 320,
    },
    "auggie": {
        "cmd": ["auggie", "-p", "{prompt}"],
        "timeout": 300,
    },
}

DEFAULT_AGENT = "gemini"


# --- UTILITY FUNCTIONS ---

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def read_file(path: Path) -> str | None:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_json(path: Path) -> dict | None:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# --- PLAN PARSING ---

def parse_tickets(plan_content: str) -> list[dict]:
    """
    Parse tickets from the Implementation Plan.

    Expected format:
    ## Ticket 1: [Title]
    **Priority:** [High/Medium/Low]
    **Type:** [Migration/Model/Controller/etc.]
    **File:** [path/to/file.py]
    **Description:**
    [Multi-line description]

    **Acceptance Criteria:**
    - [ ] Criterion 1
    - [ ] Criterion 2
    """
    tickets = []

    # Split by ticket headers
    ticket_pattern = r'## Ticket (\d+): (.+?)(?=## Ticket \d+:|$)'
    matches = re.findall(ticket_pattern, plan_content, re.DOTALL)

    for ticket_num, ticket_content in matches:
        ticket = {
            "id": int(ticket_num),
            "raw_content": ticket_content.strip(),
        }

        # Extract title (first line after the header match)
        title_match = re.match(r'^(.+?)(?:\n|$)', ticket_content.strip())
        ticket["title"] = title_match.group(1).strip() if title_match else f"Ticket {ticket_num}"

        # Extract priority
        priority_match = re.search(r'\*\*Priority:\*\*\s*(\w+)', ticket_content)
        ticket["priority"] = priority_match.group(1) if priority_match else "Medium"

        # Extract type
        type_match = re.search(r'\*\*Type:\*\*\s*(.+?)(?:\n|$)', ticket_content)
        ticket["type"] = type_match.group(1).strip() if type_match else "Unknown"

        # Extract file path
        file_match = re.search(r'\*\*File:\*\*\s*`?([^`\n]+)`?', ticket_content)
        ticket["file"] = file_match.group(1).strip() if file_match else None

        # Extract description
        desc_match = re.search(r'\*\*Description:\*\*\s*(.+?)(?=\*\*Acceptance Criteria:\*\*|$)',
                               ticket_content, re.DOTALL)
        ticket["description"] = desc_match.group(1).strip() if desc_match else ticket_content

        # Extract acceptance criteria
        criteria_match = re.search(r'\*\*Acceptance Criteria:\*\*\s*(.+?)$', ticket_content, re.DOTALL)
        if criteria_match:
            criteria_text = criteria_match.group(1)
            ticket["acceptance_criteria"] = re.findall(r'- \[ \] (.+?)(?:\n|$)', criteria_text)
        else:
            ticket["acceptance_criteria"] = []

        tickets.append(ticket)

    return tickets


# --- CONTEXT BUILDING ---

def load_standards() -> str:
    """Load coding standards for the sub-agent."""
    standards_dir = DIRS["STANDARDS"]
    if not standards_dir.exists():
        return ""

    standards = []
    for file in standards_dir.glob("*.md"):
        content = read_file(file)
        if content:
            standards.append(f"### {file.name}\n{content}")

    return "\n\n".join(standards) if standards else ""


def load_domain_contexts() -> str:
    """Load domain contexts for business rules and code navigation."""
    contexts_dir = DIRS["DOMAIN_CONTEXTS"]
    if not contexts_dir.exists():
        return ""

    contexts = []
    for file in contexts_dir.glob("*.md"):
        # Skip README
        if file.name == "README.md":
            continue
        content = read_file(file)
        if content and "[Date]" not in content:  # Skip templates
            contexts.append(f"### {file.name}\n{content}")

    return "\n\n".join(contexts) if contexts else ""


def build_ticket_context(ticket: dict) -> str:
    """Build the full context for a ticket execution."""
    context_parts = []

    # Add schema if relevant
    if ticket.get("type") in ["Migration", "Model", "Database"]:
        schema = read_file(FILES["SCHEMA"])
        if schema:
            context_parts.append(f"## Database Schema\n```sql\n{schema}\n```")

    # Add API contract if relevant
    if ticket.get("type") in ["Controller", "API", "Endpoint", "Route"]:
        api = read_file(FILES["API"])
        if api:
            context_parts.append(f"## API Contract\n```json\n{api}\n```")

    # Add infrastructure analysis
    infra = read_file(FILES["INFRA"])
    if infra:
        context_parts.append(f"## Existing Infrastructure\n{infra}")

    # Add domain contexts (always include for business rules)
    domain = load_domain_contexts()
    if domain:
        context_parts.append(f"## Domain Contexts (Business Rules & Code Navigation)\n{domain}")

    # Add standards (always include)
    standards = load_standards()
    if standards:
        context_parts.append(f"## Coding Standards\n{standards}")

    return "\n\n---\n\n".join(context_parts)


def build_prompt(ticket: dict, context: str) -> str:
    """Build the complete prompt for the sub-agent."""
    return f"""# EXECUTION TASK

You are a Builder agent executing a specific ticket from an implementation plan.

## Your Ticket
**ID:** {ticket['id']}
**Title:** {ticket['title']}
**Type:** {ticket['type']}
**File:** {ticket.get('file', 'To be determined')}
**Priority:** {ticket['priority']}

## Description
{ticket['description']}

## Acceptance Criteria
{chr(10).join(f"- [ ] {c}" for c in ticket['acceptance_criteria']) if ticket['acceptance_criteria'] else "- Complete the task as described"}

---

# CONTEXT

{context}

---

# INSTRUCTIONS

1. Read the context carefully - understand existing infrastructure before writing code
2. Follow the coding standards exactly
3. Reference domain contexts for business rules
4. Output ONLY the code for the specified file
5. If the file path is not specified, determine the appropriate path based on project conventions
6. Include all necessary imports
7. Add appropriate comments explaining complex logic
8. Ensure the code is complete and runnable

# OUTPUT FORMAT

Start with a comment indicating the file path:
```
// FILE: path/to/file.ext
```

Then output the complete file contents.
"""


# --- JOB MANAGEMENT ---

def init_job(ticket: dict, agent: str) -> tuple[str, Path]:
    """Initialize a job directory for a ticket."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    job_id = f"ticket{ticket['id']}_{ts}_{uuid.uuid4().hex[:6]}"
    job_dir = RUNS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Save the prompt
    context = build_ticket_context(ticket)
    prompt = build_prompt(ticket, context)
    (job_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    # Save ticket info
    write_json(job_dir / "ticket.json", ticket)

    # Initialize status
    status = {
        "job_id": job_id,
        "ticket_id": ticket["id"],
        "ticket_title": ticket["title"],
        "agent": agent,
        "started_at": now_iso(),
        "status": "running",
        "exit_code": None,
        "duration_ms": 0,
    }
    write_json(job_dir / "status.json", status)
    (job_dir / "output.jsonl").write_text('{"event":"start"}\n', encoding="utf-8")
    (job_dir / "run.log").write_text(f"[{now_iso()}] Job {job_id} started\n", encoding="utf-8")

    return job_id, job_dir


def spawn_worker(job_id: str, agent: str, job_dir: Path):
    """Spawn a detached worker subprocess."""
    log_f = open(job_dir / "run.log", "a", encoding="utf-8")
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--job-id", job_id,
        "--agent", agent,
        "--job-dir", str(job_dir),
    ]
    subprocess.Popen(
        cmd,
        stdout=log_f,
        stderr=log_f,
        stdin=subprocess.DEVNULL,
        cwd=str(ROOT),
        start_new_session=True,
        close_fds=True,
    )


def run_worker(job_id: str, agent: str, job_dir: Path) -> int:
    """Execute the agent call (run in worker subprocess)."""
    start = time.time()
    status_path = job_dir / "status.json"
    output_path = job_dir / "output.jsonl"
    report_path = job_dir / "report.md"
    prompt = (job_dir / "prompt.txt").read_text(encoding="utf-8")

    exit_code = 0
    err_msg = None

    try:
        agent_config = AGENTS.get(agent.lower())
        if not agent_config:
            raise ValueError(f"Unsupported agent: {agent}. Supported: {list(AGENTS.keys())}")

        # Build command with prompt
        cmd = [c.replace("{prompt}", prompt) if "{prompt}" in c else c for c in agent_config["cmd"]]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=agent_config["timeout"],
            cwd=str(ROOT),
        )

        if result.returncode != 0:
            raise Exception(f"{agent} CLI failed: {result.stderr}")

        # Save output
        text = result.stdout.strip()
        report_path.write_text(text, encoding="utf-8")

        with open(output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "final", "report": "report.md"}) + "\n")

    except Exception as e:
        exit_code = 1
        err_msg = str(e)
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "error", "message": err_msg}) + "\n")
        with open(job_dir / "run.log", "a", encoding="utf-8") as lf:
            lf.write(f"[{now_iso()}] ERROR: {e}\n")

    # Update status
    duration_ms = int((time.time() - start) * 1000)
    status = load_json(status_path)
    status.update({
        "status": "completed" if exit_code == 0 else "failed",
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "finished_at": now_iso(),
        **({"error": err_msg} if err_msg else {}),
    })
    write_json(status_path, status)

    return exit_code



# --- EXECUTION STATUS ---

def get_execution_status() -> dict:
    """Get status of all jobs."""
    if not RUNS_DIR.exists():
        return {"jobs": [], "summary": {"total": 0, "running": 0, "completed": 0, "failed": 0}}

    jobs = []
    for job_dir in sorted(RUNS_DIR.iterdir()):
        if job_dir.is_dir():
            status_file = job_dir / "status.json"
            if status_file.exists():
                jobs.append(load_json(status_file))

    summary = {
        "total": len(jobs),
        "running": sum(1 for j in jobs if j.get("status") == "running"),
        "completed": sum(1 for j in jobs if j.get("status") == "completed"),
        "failed": sum(1 for j in jobs if j.get("status") == "failed"),
    }

    return {"jobs": jobs, "summary": summary}


def print_status():
    """Print execution status to console."""
    status = get_execution_status()

    print("\n" + "=" * 60)
    print("📊 EXECUTION STATUS")
    print("=" * 60)

    s = status["summary"]
    print(f"\nTotal Jobs: {s['total']}")
    print(f"  ✅ Completed: {s['completed']}")
    print(f"  🔄 Running: {s['running']}")
    print(f"  ❌ Failed: {s['failed']}")

    if status["jobs"]:
        print("\n" + "-" * 60)
        print("Recent Jobs:")
        print("-" * 60)
        for job in status["jobs"][-10:]:  # Last 10 jobs
            icon = "✅" if job["status"] == "completed" else "🔄" if job["status"] == "running" else "❌"
            print(f"  {icon} {job['job_id']}: Ticket {job.get('ticket_id', '?')} - {job['status']}")


# --- MAIN EXECUTION ---

def execute_tickets(tickets: list[dict], agent: str, specific_ticket: int | None = None):
    """Execute tickets by spawning sub-agents."""
    if specific_ticket:
        tickets = [t for t in tickets if t["id"] == specific_ticket]
        if not tickets:
            print(f"❌ Ticket {specific_ticket} not found in plan")
            return

    print(f"\n🚀 Executing {len(tickets)} ticket(s) with {agent}...")

    job_ids = []
    for ticket in tickets:
        print(f"\n  📋 Ticket {ticket['id']}: {ticket['title']}")
        job_id, job_dir = init_job(ticket, agent)
        spawn_worker(job_id, agent, job_dir)
        print(f"     → Spawned job: {job_id}")
        job_ids.append(job_id)

    # Save execution status
    execution_status = {
        "started_at": now_iso(),
        "agent": agent,
        "tickets_spawned": len(job_ids),
        "job_ids": job_ids,
    }
    write_json(FILES["EXECUTION_STATUS"], execution_status)

    print(f"\n✅ Spawned {len(job_ids)} sub-agent job(s)")
    print(f"   Check status with: python scripts/executor.py --status")
    print(f"   Job outputs in: {RUNS_DIR}/")


def main():
    parser = argparse.ArgumentParser(
        description="Zero Ambiguity Executor - State 4: Execute Implementation Plan"
    )
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--job-id", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--job-dir", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--agent", default=DEFAULT_AGENT, help=f"Agent to use (default: {DEFAULT_AGENT})")
    parser.add_argument("--ticket", type=int, default=None, help="Execute specific ticket number")
    parser.add_argument("--status", action="store_true", help="Show execution status")
    parser.add_argument("--list", action="store_true", help="List tickets without executing")
    args = parser.parse_args()

    # Worker mode (called by spawn_worker)
    if args.worker:
        if not args.job_id or not args.job_dir or not args.agent:
            print("Missing worker args", file=sys.stderr)
            sys.exit(2)
        sys.exit(run_worker(args.job_id, args.agent, Path(args.job_dir)))

    # Status mode
    if args.status:
        print_status()
        return

    # Check for implementation plan
    plan_content = read_file(FILES["PLAN"])
    if not plan_content:
        print(f"❌ No Implementation Plan found at {FILES['PLAN']}")
        print("   Run the orchestrator first: python scripts/orchestrator.py")
        sys.exit(1)

    # Parse tickets
    tickets = parse_tickets(plan_content)
    if not tickets:
        print("❌ No tickets found in Implementation Plan")
        print("   Ensure tickets follow the format: ## Ticket N: Title")
        sys.exit(1)

    print(f"📋 Found {len(tickets)} ticket(s) in Implementation Plan")

    # List mode
    if args.list:
        print("\nTickets:")
        for t in tickets:
            print(f"  {t['id']}. [{t['priority']}] {t['title']} ({t['type']})")
        return

    # Execute
    execute_tickets(tickets, args.agent, args.ticket)


if __name__ == "__main__":
    main()