# Solicitation Pipeline — Ingestion → Triage → Vendor Matching

> **Purpose:** Onboard developers/agents to the fully unattended federal solicitation pipeline — from SAM.gov intake through vendor matching and outreach drafting.
> **Last Updated:** 2026-07-21

---

## 1. Business Overview

### What This Domain Does

A federal solicitation created with `source_type='federal'` runs through three chained background jobs with **no human checkpoints**, provided each stage's conditional gate passes: fetch SAM.gov metadata/documents → classify + quick-kill + extract 5 partner-facing artifacts → build a candidate vendor pool + LLM-rank the top 25 + draft one outreach email. State/local solicitations skip Stage 1 (no `sam_fetch` job) and must be triaged manually via the "Run Triage" button; from Stage 2 onward the chain is identical.

### Key Business Rules (Gates)

| Gate | Location | Condition | If it fails |
|---|---|---|---|
| **Triage gate** | `worker.py: process_sam_fetch_job` (end) | `has_missing_docs == False` | `solicitation_triage` is NOT enqueued — solicitation sits with `ingestion_status='complete'`; user must click "Run Triage" manually |
| **Matching gate** | `solicitation_triage.py: run_solicitation_triage` (end) | None — matching always runs | `vendor_matching` is always auto-enqueued after artifact extraction. `quick_kill` is informational only and does NOT block the pipeline. **Artifacts are always extracted and matching always runs regardless of quick-kill status.** |
| **NAICS gate** | `vendor_matching.py: run_vendor_matching_pipeline` | `solicitations.naics_code` is non-null | `matching_status='failed'`, no agent call |
| **Empty-pool short-circuit** | same | `build_candidate_pool()` returns `[]` | `matching_status='complete'` with 0 matches — a legitimate outcome, not a failure. No LLM call (cost-saving). |

So: **"one-shot, ingestion → vendor matching" is true if and only if** the SAM.gov fetch retrieves all documents cleanly, triage doesn't quick-kill the notice, and the notice has a NAICS code. Any of those breaking the chain is a deliberate product decision (per-stage manual re-trigger endpoints exist for recovery), not a bug.

### User Stories This Supports

- As a BD analyst, I paste a SAM.gov URL and — without touching anything else — get back a ranked shortlist of subcontracting partners and a ready-to-send outreach email.
- As a BD analyst, if the auto-chain stalls (missing docs, quick-kill, no NAICS), I can manually re-trigger triage or vendor matching from the UI once I've fixed the underlying issue.

---

## 2. Pipeline Flow

```
POST /api/solicitations {source_type: "federal", url}
  → SolicitationManager.create()            [cases row + solicitations row]
  → enqueue(job_type="sam_fetch")
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 1 — sam_fetch  (worker.py: process_sam_fetch_job)      │
│  fetch_notice() → metadata_updates → mgr.update(solicitation)│
│  download_resource_link() per attachment → ingest_file()     │
│    → enqueue(job_type="enrich") per document (classification)│
│  ingestion_status = 'complete', has_missing_docs = T/F       │
│  IF has_missing_docs == False:                                │
│      enqueue(job_type="solicitation_triage")  ──────────────┐│
└────────────────────────────────────────────────────────────┼┘
                                                                │
        ┌───────────────────────────────────────────────────────┘
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 2 — solicitation_triage                                │
│  (worker.py: process_solicitation_triage_job                 │
│   → solicitation_triage.py: run_solicitation_triage)          │
│  Phase 1: TRIAGE_SYSTEM_PROMPT agent (read tools) classifies  │
│    notice_type + quick_kill (+ reason)                        │
│  Phase 2: 5 extractor agents run concurrently (asyncio.gather) │
│    regardless of quick_kill result — artifacts are always     │
│    generated for full solicitation understanding.             │
│    Each writes its own artifact_* column + mirrors an HTML    │
│    draft into the workspace (drafts table, folder='artifacts')│
│  triage_status='complete', has_partial_artifacts=T/F           │
│  IF NOT quick_kill: enqueue(job_type="vendor_matching") ──────┐│
└────────────────────────────────────────────────────────────┼┘
                                                                │
        ┌───────────────────────────────────────────────────────┘
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 3 — vendor_matching                                     │
│  (worker.py: process_vendor_matching_job                      │
│   → vendor_matching.py: run_vendor_matching_pipeline)          │
│  VendorMatchManager.build_candidate_pool(naics, set_aside)     │
│    tiered SQL: exact NAICS → 4-digit family → capabilities FTS │
│    (each tier gated by set-aside is_* column), capped at 300   │
│  IF pool empty: matching_status='complete', match_count=0, NO  │
│    LLM call                                                    │
│  ELSE: MATCHING_SYSTEM_PROMPT agent (no read tools — pool +    │
│    solicitation context embedded in the query) ranks top 25,   │
│    calls save_matches() then save_outreach_email()             │
│  matching_status='complete'                                    │
└─────────────────────────────────────────────────────────────┘
```

Every stage's job handler wraps its pipeline call in try/except and writes `*_status='failed'` + `*_error` on any exception — the job queue itself never silently drops a failure.

---

## 3. Code Navigation Guide

| If you want to... | Start at... | Then follow... |
|---|---|---|
| Trace the whole chain | `backend/ingestion/worker.py` `main()` | dispatches on `job['job_type']` to `process_*_job` |
| Change SAM.gov fetch logic | `backend/ingestion/sam_client.py` | `fetch_notice()`, `download_resource_link()`, `extract_notice_id()` |
| Change triage/quick-kill/artifact prompts | `backend/ingestion/solicitation_triage.py` | `TRIAGE_SYSTEM_PROMPT`, `ARTIFACT_SPECS`, `_run_extractor()` |
| Change candidate-pool SQL or set-aside gating | `backend/core/vendor_match.py` | `VendorMatchManager.build_candidate_pool()`, `_set_aside_column()`, `_SET_ASIDE_KEYWORDS` |
| Change ranking/outreach prompt | `backend/ingestion/vendor_matching.py` | `MATCHING_SYSTEM_PROMPT`, `_run_matching_agent()` |
| Add/inspect a manual re-trigger endpoint | `backend/api/routes/solicitations.py` | `trigger_triage_endpoint`, `trigger_vendor_matching_endpoint` |
| See/modify the job queue mechanics | `backend/ingestion/jobs.py` | `enqueue()`, `claim_next()` (SKIP LOCKED), `mark_complete/failed`, `update_progress` |
| Modify solicitation CRUD / status columns | `backend/core/solicitation.py` | `SolicitationManager.get/update` — `allowed` set in `update()` gates writable columns |
| Wire a new schema migration | `backend/core/db.py` | `ensure_*_schema()` functions, called from `backend/api/main.py` startup + `backend/init_db.py` |
| Modify the Vendor Matches UI | `frontend/src/app/cases/[id]/tabs/VendorMatchesTab.tsx` | polls `matching_status` every 3s while `'running'`; see `frontend/src/lib/api.ts` for `VendorMatch`/`VendorMatchesResponse` types |
| Modify the Triage UI | `frontend/src/app/cases/[id]/tabs/TriageTab.tsx` | same polling pattern against `triage_status` |

---

## 4. Database Schema

### `solicitations` (extended across 3 migrations — see `backend/schemas/007/008/010_*.sql`)

| Column group | Columns | Set by |
|---|---|---|
| Core | `id`, `case_id`, `source_type`, `title`, `url`, `notice_id` (federal-only, `UNIQUE`) | `SolicitationManager.create()` |
| Ingestion (007) | `ingestion_status` (`pending\|fetching\|complete\|failed`), `has_missing_docs`, `error_message`, `agency`, `naics_code`, `psc_code`, `set_aside_type`, `set_aside_description`, `point_of_contact` (JSONB), `place_of_performance` (JSONB), `response_deadline`, `posted_date` | Stage 1 (`process_sam_fetch_job`) |
| Triage (008) | `triage_status` (`pending\|running\|complete\|failed`), `triage_error`, `has_partial_artifacts`, `notice_type`, `quick_kill`, `quick_kill_reason`, `artifact_scope_of_work`, `artifact_technical_requirements`, `artifact_deliverables_timeline`, `artifact_evaluation_criteria`, `artifact_submission_checklist` | Stage 2 (`run_solicitation_triage`) |
| Matching (010) | `matching_status` (`pending\|running\|complete\|failed`), `matching_error`, `outreach_email_subject`, `outreach_email_body` | Stage 3 (`run_vendor_matching_pipeline`) |

### `vendor_matches` (010_vendor_matching.sql)

`id`, `external_id` (UUID), `solicitation_id` → `solicitations.id`, `vendor_id` → `vendors.id`, `rank` (1–25), `match_score` (0–100), `match_rationale`, `naics_match_type` (`exact\|family\|capability_only`), timestamps. `UNIQUE(solicitation_id, vendor_id)`; `VendorMatchManager.save_matches()` does delete-then-insert per solicitation on every run (re-run replaces, doesn't accumulate).

### `jobs.job_type` CHECK constraint

Must include `'sam_fetch'`, `'solicitation_triage'`, `'vendor_matching'`. **Gotcha:** `001_core.sql`, `007_solicitations.sql`, and `008_solicitation_triage.sql` each independently `DROP`+`ADD` this constraint on every `ensure_schema()` call (which runs on *every* MCP tool connection via `chat/tools.py::create_vision_server`, including mid-agent-run). All three now list every value including `vendor_matching` — if you add a new `job_type`, update the constraint list in **all** schema files that touch it, not just the newest one, or an older file re-running will silently strip it.

---

## 5. API Endpoints (`backend/api/routes/solicitations.py`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/solicitations` | Create solicitation; enqueues `sam_fetch` if `source_type='federal'` |
| GET | `/api/solicitations/{id}` | Full row + `documents` |
| GET | `/api/cases/{case_id}/solicitation` | Look up by backing case (used by tab components, which only know `case_id`) |
| POST | `/api/solicitations/{id}/triage` | Manual (re)trigger — 400 if no documents attached; 409 if already running |
| POST | `/api/solicitations/{id}/vendor-matching` | Manual (re)trigger — 400 if triage incomplete / quick-killed / no NAICS; 400 if already running |
| GET | `/api/solicitations/{id}/vendor-matches` | `{matching_status, matching_error, outreach_email_subject, outreach_email_body, matches[]}` — 200 with empty `matches` before first run, not 404 |

---

## 6. Frontend

Both `TriageTab.tsx` and `VendorMatchesTab.tsx` follow the same pattern: fetch the solicitation via `getSolicitationByCase(caseId)`, poll every 3s (`POLL_MS`) only while the relevant `*_status === 'running'`, and disable the manual trigger button while running. `TabNav.tsx` only shows the "Triage" and "Vendor Matches" tabs when `page.tsx`'s `getSolicitationByCase` probe succeeds (404 → tabs hidden, not an error).

`VendorMatchesTab.tsx` renders the shared outreach email template (`OutreachEmailPanel`) plus a ranked table (`VendorMatchList`) with score/match-type/set-aside badges and a per-row "Copy" button that substitutes `{{vendor_name}}`/`{{match_reason}}` into the template client-side.

---

## 7. Common Tasks

### "A solicitation didn't get vendor matches — why?"
1. `GET /api/solicitations/{id}` (or check the Triage/Vendor Matches tabs) — read `ingestion_status`, `has_missing_docs`, `triage_status`, `quick_kill`, `naics_code`, `matching_status`, `matching_error` in that order; the first gate that fails explains the stop point.
2. If `has_missing_docs=true` → click "Run Triage" manually once docs are fixed.
3. If `quick_kill=true` → by design, no vendor matching will ever auto-run; check `quick_kill_reason`.
4. If `matching_status='failed'` → read `matching_error` (usually "No NAICS code available for matching").

### "I need to change what counts as a set-aside match"
Edit `_SET_ASIDE_KEYWORDS` in `backend/core/vendor_match.py` (`vendors.is_*` boolean column list) — see the file's `_set_aside_column()` for the case-insensitive substring matching approach.

### "I need to re-run the whole chain from scratch for one solicitation"
There's no single "restart from ingestion" endpoint — call `/triage` then `/vendor-matching` manually in sequence once `ingestion_status='complete'`.

---

## 8. Related Domains

| Domain | Relationship | Context File |
|---|---|---|
| Agent Tool Building | `chat/tools.py`'s `create_vision_server`/`ensure_schema()` pattern reused by triage's read tools | `domain-contexts/agent-tool-building.md` |
| External Integrations | Sibling unattended-agent pattern (SDK, MCP servers, `@tool`) | `domain-contexts/external-integrations.md` |
