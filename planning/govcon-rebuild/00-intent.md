# What We're Building — Rebuild Intent (My Understanding)

> Purpose: state, in my own words, what I believe this rebuild is trying to
> accomplish, before any architecture or code work starts. This is a
> checkpoint document — correct it where I'm wrong.

## 1. The Shift

Vision was built as a **legal intelligence OS**: ingest case documents, make
them queryable to the block level, and run a "Strategy Engine" that models
legal claims as doctrine trees and computes their strength. That system
(Evidence Agent + Strategy Engine) is not being thrown away — its ingestion
pipeline, evidence store, drafting system, and agent-tool infrastructure are
the substrate this rebuild sits on.

The rebuild's purpose is to turn Vision into a **government contracting (GovCon)
automation platform**: the tool that carries a business through the federal
solicitation lifecycle — ingest a solicitation, decide whether to pursue it,
extract everything relevant, draft a compliant response, and (eventually)
manage what happens after award. Legal case work becomes one tenant of the
underlying evidence/reasoning engine; GovCon becomes the primary one.

## 2. Two Different Workflows Are Being Described — This Needs Resolving

Reading the source material closely, there are **two distinct business
models** in play, and they imply different data models and different UIs:

**Workflow A — Respondent tool ("we bid on our own behalf").**
A single company (ours) tracks solicitations relevant to *itself*, builds
one company profile (CAGE/UEI/NAICS/certs/past performance), runs each
solicitation through the assembly line (triage → deep read → brief →
go/no-go → draft → quality gate), and produces a response *we* submit.
This is what `solicitation_pipeline.py`, `profile_synth.py`,
`company_profiles`, and the `govcon-dashboard.md` brainstorm all describe.
**This already has a working backend implementation** (CLI-driven, sub-agent
based) plus a partial DB schema.

**Workflow B — Prime/aggregator marketplace ("TalentNyk").**
We become the **prime**, win contracts, and route execution to a network of
subcontracted partners (small businesses, individual specialists, domestic
manufacturers). This requires a partner/vendor database, a matching engine,
teaming-agreement generation, wage-determination-driven pricing, digital
sign-off routing, and post-award payment splitting. This is what
`scratch.md` (the outreach/email-queue workflow) and the TalentLynk brief
describe. **None of this exists yet** — it is a much bigger build (its own
frontend, its own vendor-facing auth, external integrations like SAM.gov
UEI lookup and DocuSign).

These are not the same product. Workflow A is "help us win our own bids."
Workflow B is "become a matchmaking prime that wins bids for a network of
others." TalentLynk's brief explicitly frames itself as sitting *on top of*
Vision as a separate app — which is consistent with treating B as a later,
larger, separately-scoped effort rather than part of this rebuild.

**My assumption, to be confirmed:** this rebuild targets **Workflow A** —
making the assembly line and company-profile system into a real
dashboard-driven product instead of a CLI script. Workflow B / TalentLynk is
the long-term destination but is out of scope for the immediate rebuild.

## 3. What Already Exists and Is Reusable

- **Ingestion pipeline** — PDF/DOCX/XLSX/image → OCR (DataLab) → sections →
  blocks → embeddings → FTS. Domain-agnostic. ZIP support is planned but not
  yet built (needed for solicitation packages).
- **Solicitation assembly line** — `backend/scripts/solicitation_pipeline.py`
  orchestrates 8 sub-agents (`.claude/agents/*.md`) through Triage → Deep
  Read (parallel) → Brief → Go/No-Go → Draft → Quality Gate, using an
  MCP tool server scoped per-case. A full run's output exists
  (`case-7-artifacts/`) proving the pipeline works end-to-end.
- **Company profile system** — `company_profiles` table + `profile_synth.py`
  agent that reads uploaded docs and extracts CAGE/UEI/NAICS/certs/past
  performance/personnel into a JSONB profile, with per-field status
  (`verified` / `agent_filled` / `uncertain` / `needs_input`) so agent
  re-synthesis never clobbers user-confirmed data.
- **Case infrastructure** — `cases` table already has `case_type =
  'rfp_response'` and a `solicitation JSONB` column plus `profile_id` FK.
  Drafts, tasks, workspace items, and correspondence all attach to cases
  already.
- **Agent tool pattern** — MCP closure-per-case (`create_vision_server`) is
  the established way to give sub-agents scoped read/write tools.

## 4. What's Explicitly Undecided

- **Case vs. Matter naming** — discussed, recommendation exists (do a
  user-facing-text-only rename, leave DB/API alone), not yet decided/applied.
- **Company profile architecture** — three options written up
  (structured form / agent-synthesized / hybrid). Hybrid is recommended and
  partially built (`profile_synth.py` already implements it), but whether
  the profile is account-level, per-case, or workspace-scoped is still open.
- **Solicitation as an entity** — three options written up (solicitation =
  case with `case_type=rfp_response` / solicitation = workspace under a
  company case / solicitation = new top-level entity). Recommendation is
  Option A (reuse cases), which is also what the *existing* pipeline script
  already assumes. Not formally decided.
- **The dashboard itself** — no GovCon-specific UI exists yet. Today's
  frontend is a generic case list/detail (`/cases`, `/cases/[id]`) built for
  litigation; the assembly line currently only runs from a CLI script, with
  no way to trigger it, watch it, or review its checkpoints from the browser.
- **Multi-tenancy** — is this single-tenant (our own contracting business)
  or does it need to support multiple companies/accounts from day one? The
  `company_profiles` schema has no `account_id`/`owner` scoping yet.
- **SAM.gov integration, partner database, email outreach** — all Workflow B
  concerns, not built, likely out of scope for now per §2.

## 5. What I Think "Done" Looks Like for This Rebuild (First Cut)

A user can: maintain one company profile (agent-assisted, human-verified);
drop a solicitation package (files or, later, a SAM.gov URL) into the app;
watch it move through triage → deep read → brief → go/no-go → draft →
quality gate inside the UI, with human checkpoints at go/no-go and before
final draft; and end up with a compliant response document tied back to the
company profile and the source solicitation — all without touching a CLI.

## 6. Open Questions for You

1. Confirm: is Workflow A (respond to our own solicitations) the correct
   scope for this rebuild, with Workflow B/TalentLynk deferred?
2. Is this single-tenant (just us) for now, or must it support multiple
   companies/accounts from the start?
3. Do we lock in Option A for solicitations (case with
   `case_type=rfp_response`), or do you want to reconsider given a clean
   rebuild is on the table?
4. Do we do the Case→Matter rename as part of this rebuild, or leave it?
5. Should the existing `solicitation_pipeline.py` sub-agent architecture be
   ported as-is into a UI-triggered flow, or rebuilt against new standards?
