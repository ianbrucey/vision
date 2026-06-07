# The Council Workflow Guide

> **Purpose:** This document explains the "Relay Race" automation that powers the Zero Ambiguity Architecture phase.

---

## What is the Council Script?

The Council Orchestrator (`scripts/orchestrator.py`) is a **Relay Race automation**. It takes the output of one agent and forces it to become the input for the next agent.

This ensures:
- No context is dropped between phases
- No steps are skipped
- Each artifact builds on the previous one

It replaces the need to manually copy-paste prompts between different agent sessions.

---

## The Logic Flow (The "Relay Race")

### PHASE 0: The Archaeologist (Infrastructure Discovery)

| Attribute | Value |
|-----------|-------|
| **Agent** | Auggie (High Intelligence) |
| **Role** | Infrastructure Archaeologist |
| **Input** | `00-Brief.md` + Scanned existing code |
| **Output** | `00.5-existing-infrastructure.md` |
| **Prompt** | "Analyze existing code. Identify what exists, what to extend, what is net-new." |

**Why This Phase Exists:**
Without understanding existing infrastructure, the Council will:
- Create duplicate tables
- Define conflicting API endpoints
- Break existing functionality

**What It Scans:**
- `app/Models/` or `src/models/` (database models)
- `database/migrations/` (existing schema)
- `app/Http/Controllers/` or `src/controllers/` (existing endpoints)
- `routes/` (existing API routes)
- `resources/views/components/` or `src/components/` (existing UI)

**Greenfield Projects:**
If no existing code is found, this phase creates a minimal file indicating "greenfield" status.

---

### PHASE A: The Vault Master (Database Architecture)

| Attribute | Value |
|-----------|-------|
| **Agent** | Auggie (High Intelligence) |
| **Role** | Database Architect |
| **Input** | `00-Brief.md` + `00.5-existing-infrastructure.md` |
| **Output** | `01-schema.sql` |
| **Prompt** | "Read the Brief and Infrastructure. Output SQL for NET NEW and ALTER statements for EXTENSIONS." |

**Critical Rules for Brownfield:**
- Do NOT recreate tables that already exist
- Output `ALTER TABLE` for extending existing tables
- Output `CREATE TABLE` only for net-new tables
- Reference the Infrastructure Analysis for existing column names

### PHASE B: The Gatekeeper (API Architecture)

| Attribute | Value |
|-----------|-------|
| **Agent** | Auggie (High Intelligence) |
| **Role** | API Architect |
| **Input** | `00-Brief.md` + `00.5-existing-infrastructure.md` + `01-schema.sql` |
| **Output** | `02-api-contract.json` |
| **Prompt** | "Read the Brief, Infrastructure, and Schema. Define only NET NEW endpoints." |

**Critical Rules for Brownfield:**
- Do NOT define endpoints that already exist
- Mark existing endpoints as `"existing": true` in the contract
- Only define net-new endpoints in detail
- All fields must come from the Schema

### PHASE C: The Witness (Evidence Generation)

| Attribute | Value |
|-----------|-------|
| **Agent** | Gemini (High Speed) |
| **Role** | Data Specialist |
| **Input** | `02-api-contract.json` |
| **Output** | `03-fixtures.json` |
| **Prompt** | "Read the API Contract. Generate realistic mock data." |

This creates the "Evidence" that proves the API contract is viable. Fixtures enable testing without hitting live APIs.

### PHASE D: The Foreman (Project Planning)

| Attribute | Value |
|-----------|-------|
| **Agent** | Auggie (High Intelligence) |
| **Role** | Project Manager |
| **Input** | ALL previous artifacts |
| **Output** | `05-implementation-plan.md` |
| **Prompt** | "Read all specs. Sequence work into atomic tickets." |

The Foreman sees everything and breaks it into executable units.

---

## Agent Assignment Strategy

The script uses different models based on the task:

| Agent | Used For | Characteristics |
|-------|----------|-----------------|
| **Auggie** | Strategy, Schema, API, Planning | High intelligence, higher cost |
| **Gemini** | Fixtures, Code Implementation | High speed, lower cost |

---

## How to Recognize Your Role

When the orchestrator calls you, it prefixes with a role indicator:

- `[Role: Database Architect]` → You're in Phase A. Output SQL only.
- `[Role: API Architect]` → You're in Phase B. Output JSON only.
- `[Role: Data Specialist]` → You're in Phase C. Output fixture JSON.
- `[Role: Project Manager]` → You're in Phase D. Output the plan.

**Rule:** When assigned a role, ignore all other concerns. A Database Architect does not comment on UI design.

---

## Running the Orchestrator

```bash
# From project root
python scripts/orchestrator.py
```

### Prerequisites

1. A `00-Brief.md` must exist in `context-engine/specs/`
2. You must implement `run_agent_command()` with your actual CLI tool

### Implementing the Agent Call

Edit `scripts/orchestrator.py` and replace the mock in `run_agent_command()`:

```python
# Example: Using 'llm' CLI
process = subprocess.run(
    ["llm", "-m", "gpt-4", "-s", system_role, prompt],
    input=context_content,
    capture_output=True,
    text=True
)
return process.stdout
```

---

## What This Achieves

Running one command simulates 30 minutes of manual copy-pasting between agent sessions. The relay race ensures:

1. **Consistency** - Each phase inherits verified context
2. **Traceability** - Artifacts chain together
3. **Enforcement** - You can't skip phases

---

## Related Files

- `scripts/orchestrator.py` - The automation script
- `context-engine/templates/specs/` - Artifact templates
- `AGENTS.md` - The Master Context Engine (the "brain")

