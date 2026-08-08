# GovCon Engine

Master Business Blueprint · For Partners · v1.0 · August 2026

## The Business in One Paragraph

We are a **government contracting company** that wins federal construction contracts as the prime contractor and delivers the work through a network of  **specialized small-business subcontractors** .
 We bring the institutional presence, handle every piece of federal
compliance and paperwork, and pass the actual work to qualified trades.
To the government we look like a capable, established contractor. To
small businesses we are the door into federal work they can't navigate
alone.

## The Market We're Going After

The federal government spends hundreds of billions a year and is  **required by law to award a share to small businesses** .
 Yet most small contractors never bid — not because they can't do the
work, but because the process defeats them: registration, bonding,
proposal writing, compliance, invoicing.

At the same time, **large prime contractors are required to subcontract a portion of their work to small businesses** — but finding, vetting, and managing those subs is slow and manual.

Our wedge is the  **$100K–$150K+ small-business set-aside market** :
 big enough to build a real business on, small enough that the large
players don't compete hard. As of this week alone, there are **~250 active federal construction opportunities set aside for small business** — that's the pipeline we start from.

## The Model — Who Does What

| Role                                                                     | What they do                                                                                                              |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| **We (the Prime)**                                                 | Hold the contract, face the agency, own the compliance and the paperwork, manage the job to completion.                   |
| **Subcontractors**                                                 | The skilled trades who actually perform the work — general contractors, HVAC, electrical, plumbing, and more as we grow. |
| **The Engine**                                                     | Software that finds opportunities,                                                                                        |
| reads them, matches subs, collects pricing, drafts responses, and tracks |                                                                                                                           |
| the contract. This is what lets the whole thing scale.                   |                                                                                                                           |

## The Engine — How It Works

Six steps, in plain English. Each one replaces work that normally takes a small contractor weeks of paperwork:

1

**Find.** Our system
continuously scans federal portals for two things: contract
opportunities we can bid, and large primes who are looking for
small-business subcontractors.

2

**Read.** AI reads each
posting and summarizes it — what the work is, what trades are involved,
what's required, when it's due. Nothing slips through.

3

**Match.** It compares
each opportunity against our network of vetted subs by trade, location,
and capacity, and flags who could do the work.

4

**Price.** For bids that
 need pricing, we send each matched sub a simple, one-page request for
their portion. They send back a number. No jargon, no forms.

5

**Respond.** AI drafts the proposal or capability statement from what we already know. Our team reviews and submits before the deadline.

6

**Manage.** After we win, we track milestones, approvals, and payments through to completion — and make sure every sub gets paid on time.

## The Subcontractor Network

* We start with  **construction trades** : general contractors, HVAC, electrical, plumbing — the backbone of most federal facility work.
* Subs register  **once** , provide their licenses, insurance, and bonding, and from then on receive a  **steady pipeline of federal work without the federal headache** .
* We vet them once and keep their credentials on file, so every bid doesn't start from zero.

## Revenue & Economics

* We earn the full contract value as prime. Our margin is the difference between the price we win and the prices our subs quote.
* **Scale comes from software and network, not headcount.** Adding a thousand subs or a hundred opportunities doesn't require a hundred employees.
* Low capital intensity: no equipment, no crews, no payroll on the
  bench. We coordinate, manage, and get paid on contract milestones.

## The Roadmap

| Stage                 | What we build                                                      | Outcome                                        |
| --------------------- | ------------------------------------------------------------------ | ---------------------------------------------- |
| **1 · Launch** | Sourcing, AI triage, vendor matching, automated responses          | Win our first construction set-aside contracts |
| **2 · Growth** | Subcontractor portal, credential management, award tracking        | More subs, more bids, repeat wins              |
| **3 · Scale**  | Finance automation, milestone tracking, new markets (IT, services) | A self-running contracting business            |

## What Success Looks Like

At any moment, our partner dashboard shows the whole business at a glance: **how
 many opportunities we're evaluating, how many are matched to subs, how
many quotes are in, how many proposals went out, how much we've won, and
 how much has been paid to our subcontractors.** The numbers move with almost no manual effort — that's the point.

## Why This Wins

The government **wants** to buy from small business. The only real
 barrier is process. We remove the process. Subcontractors do what
they're great at; we do what they're not. That's the whole business in
one sentence.

GovCon Engine · Master Business Blueprint · v1.0 · Prepared for partner review, August 2026

# Vision — Global Context

> **Load order:** Priority 1. Read before any code is written.
> **Project root:** `scripts/Vision/`

---

## 1. What Vision Is

Vision is a **legal intelligence operating system** with two halves sharing one database:

| Half                      | Role                                                                                                                                    | Metaphor                                                    |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **Evidence Agent**  | Ingests unstructured documents, makes them queryable down to the text block, answers factual questions with citation-backed conclusions | Jarvis — sees through the data                             |
| **Strategy Engine** | Models legal claims as computational trees, maps facts to elements, runs adversarial dialectics, computes the disposition before filing | Doctor Strange's Time Stone — simulates 14 million futures |

**The through-line:** Legal claims have discoverable anatomy. That anatomy can be modeled. That model can be computed. The computation finds the optimal path.

Every factual claim anchors to a source block. Every legal proposition links to verified authority. The database is the source of truth — files are export artifacts.

**Source docs:** `docs/Destination.md` (Evidence Agent), `docs/strategy-destination.md` (Strategy Engine)

---

## 2. System Architecture

```
┌────────────────────────────────────────────────────┐
│                    VISION SYSTEM                     │
│                                                     │
│  ┌──────────────────┐   ┌──────────────────────┐   │
│  │  EVIDENCE AGENT   │   │   STRATEGY ENGINE    │   │
│  │                   │   │                      │   │
│  │  Ingest → Store → │   │  Doctrine Tree →     │   │
│  │  Query → Reason → │   │  Fact Map →          │   │
│  │  Audit → Output   │   │  Adversarial Walk →  │   │
│  │                   │   │  Gate Walk →         │   │
│  │  Layers 1-6       │   │  Gauntlet            │   │
│  │                   │   │  Layers 7-X          │   │
│  └────────┬──────────┘   └──────────┬───────────┘   │
│           │                         │               │
│           └─────────┬───────────────┘               │
│                     │                               │
│         ┌───────────▼───────────┐                   │
│         │   PostgreSQL +        │                   │
│         │   pgvector + FTS      │                   │
│         └───────────┬───────────┘                   │
│                     │                               │
│     ┌───────────────┼───────────────┐               │
│     │               │               │               │
│  ┌──▼──────┐   ┌────▼─────┐   ┌────▼──────┐        │
│  │ Next.js │   │  Python  │   │  MCP      │        │
│  │ Frontend│   │  Backend │   │  Server   │        │
│  │ React 19│   │  FastAPI │   │ legal-hub │        │
│  └─────────┘   └──────────┘   └───────────┘        │
└────────────────────────────────────────────────────┘
```

### The Evidence Agent (Layers 1-6)

1. **Ingestion:** PDF → DataLab API → structured JSON → normalize → Evidence Store
2. **Evidence Store:** PostgreSQL — `documents`, `sections`, `blocks`. Each block indexed 3 ways: full-text (`tsvector`), semantic (`pgvector`), structural (section hierarchy).
3. **Case Core:** Structured case model — parties (role-tagged, not typed), allegations, events, citations. Populated by the agent as it works.
4. **Query Interface:** Composed search chain — structural → keyword → analytical → contextual → extractive → verify. No single-pass retrieval. See `docs/Destination.md` §Layer 4.
5. **Agent Workspace:** Session-scoped temporary tables for intermediate work.
6. **Output:** Citation-anchored reports, legal documents, timelines, indices.

### The Strategy Engine (Layers 7-X)

1. **Doctrine Tree:** Recursive legal claim model with AND/OR gates. Jurisdiction-scoped. Citation-verified. Reusable across cases.
2. **Fact Inventory:** Interpretive characterizations of raw events. Separate from case-core events to enable the permutation engine.
3. **Element-Fact Mapping:** Every connection has a rhetorical move, directionality, and rationale.
4. **Adversarial Walk:** T1→T2→T3→T4 dialectic per element. Adversary agent sees only the element and doctrine — never our strategy. Terminates: CLOSED, CONTESTED, or OPEN.
5. **Gate Walk:** Deterministic AND/OR propagation. Produces SPOF map, pressure rankings, missing evidence impact.
6. **Gauntlet:** Systematic cross-claim screening — 8 attack surfaces (Standing, Licensing, Preclusion, Timing, Pleading, Evidence, Remedies, Party-Specific). Catches what element analysis misses.
7. **Permutation Engine (Future):** Re-characterize facts, swap authority emphasis, reorder claims. Find the one path that wins.

---

## 3. Tech Stack

| Layer                | Technology                                               |
| -------------------- | -------------------------------------------------------- |
| **Frontend**   | Next.js 16 + React 19 + TypeScript + Tailwind CSS 4      |
| **Fonts**      | Geist Sans + Geist Mono (via`next/font/google`)        |
| **Backend**    | Python FastAPI (see`backend/`)                         |
| **Database**   | PostgreSQL 16+ with pgvector + tsvector                  |
| **LLM**        | Claude Opus/Sonnet (reasoning), Gemini (vision for PDFs) |
| **OCR**        | DataLab API (Mistral)                                    |
| **Embeddings** | Mistral embed, 1024 dimensions                           |
| **Deployment** | Single-tenant, per-case isolation                        |

---

## 4. Non-Negotiable Design Principles

### Citation-Anchored Everything

No floating facts. Every claim links to a `block_id`. Every legal proposition links to a statute or case with an exact quotation. The citation chain is auditable.

### Doctrine First, Facts Second

The legal tree is built from doctrine alone. No facts enter until the tree is complete. The law defines what must be proved. Facts determine whether it can be.

### The Agent Has Eyes

The agent reads source blocks directly. It does not rely on summaries. When it makes a claim, it has seen the evidence.

### Deterministic Where It Matters

Ingestion and indexing are deterministic. Gate walk is deterministic math. LLMs handle classification and reasoning. The audit layer verifies all LLM output.

### Domain-Agnostic Evidence Layer

The ingestion pipeline doesn't know what a "medical record" is. It knows documents, pages, sections, and blocks. Domain understanding lives in prompts, schemas, and output templates.

### The Adversary Must Be Adversarial

The sub-agent generating opposing arguments sees only the element and doctrine — not our strategy. It is instructed to win.

### The Database Is the Source of Truth

No JSON files as primary storage in production. The database holds everything. Files are export artifacts.

---

## 5. Resolved Design Decisions

1. **Narrative-first input, not form-first.** Primary input is a text area with adaptive placeholder text. The agent extracts structure. Structured fields are optional shortcuts.
2. **No document summaries on ingest.** Structural indexing (section outline) is free and more useful. Agent discovers content by searching, not reading summaries.
3. **Multi-step composable search.** Structural → keyword → analytical → contextual → extractive → verify. Each step does what it does best.
4. **PostgreSQL as the single data store.** pgvector, tsvector, and relational data in one database. One query traces from claim → element → fact → event → block.
5. **Strategy facts ≠ case events.** Raw events (historical) and strategy facts (argumentative) are separate tables. Enables the permutation engine.
6. **Doctrine trees are reusable across cases.** "Negligence — Georgia" defined once, instantiated per case.
7. **Adversarial turns are structured rows, not JSONB.** Queryability over compactness.
8. **Workspaces are deferred; schema support is not.** `workspace_id` as nullable FK. Costs nothing now.
9. **No invented citations or facts.** Hard constraints. Violation = failure.

---

## 6. Project Structure

```
scripts/Vision/
├── CLAUDE.md              # Agent kernel (MCE state machine)
├── AGENTS.md / GEMINI.md / WARP.md  # Alternate agent entry points
├── context-engine/        # Global context + standards + specs + templates
├── docs/                  # Vision documents (Destination.md, strategy-destination.md)
├── frontend/              # Next.js 16 + React 19 + Tailwind 4
│   └── src/
│       ├── app/           # App router pages + layouts
│       ├── components/    # Shared UI components
│       └── lib/           # API client, auth, utilities
├── backend/               # Python FastAPI
├── sample_files/          # Test documents for development
├── discussions/           # Design discussions and open questions
├── execution/             # Execution flow documentation
├── planning/              # Implementation plans
└── dev-journal/           # Development log
```

---

## 7. Related Documents

| Document                                                                 | Purpose                                                                             |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| `docs/Destination.md`                                                  | Complete War Room Agent vision (all 8 layers)                                       |
| `docs/strategy-destination.md`                                         | Strategy Engine deep-dive (doctrine trees, adversarial walks, gate logic, gauntlet) |
| `CLAUDE.md`                                                            | MCE state machine, 5 commandments, context loading protocol                         |
| `context-engine/standards/01-FRONTEND-STANDARDS/design-system.md`      | UI design system: colors, typography, components, layout                            |
| `context-engine/standards/01-FRONTEND-STANDARDS/component-patterns.md` | Component behavior: modals, forms, buttons, data display                            |
| `context-engine/templates/specs/`                                      | Templates for Brief, Schema, API Contract, Fixtures, UI Specs, Plan                 |
