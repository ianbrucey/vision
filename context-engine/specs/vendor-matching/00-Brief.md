scddddds sdssdsssddsggfovscid

# Vendor Matching — Strategic Brief

## 1. Strategic Intent

**Goal:** After solicitation triage completes (and doesn't quick-kill), automatically identify the top 25 candidate vendors from the 5.5M-row `vendors` registry, rank them with AI-generated rationale, and draft a single reusable outreach email template so the user can manually mail-merge and send to prospective subcontracting partners.

**Success Verdict:**

- [ ] When triage completes with `quick_kill=false`, a `vendor_matching` job auto-enqueues; on completion, `solicitations.matching_status` moves `pending → running → complete`
- [ ] User can also manually (re)trigger matching via a button, same UX pattern as "Run Triage" (disabled while `documents`/artifacts aren't ready)
- [ ] A new "Vendor Matches" tab shows up to 25 ranked vendor rows, each with a match score, rationale, and contact info, sorted by rank
- [ ] Vendors ineligible for the solicitation's set-aside type (e.g., an SDVOSB set-aside) are never surfaced as matches
- [ ] The same tab shows one AI-drafted outreach email (subject + body) with `{{vendor_name}}` / `{{match_reason}}` placeholders, and a per-vendor "Copy personalized email" action that substitutes the placeholders client-side
- [ ] Re-running matching replaces prior matches for that solicitation (no duplicate rows), same pattern as artifact re-runs

## 2. The Claims

| Claim ID | Description                                                                                                                                                                                                                                                                            | Verdict (Test)                                                                                                                            |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| CLAIM-01 | `vendor_matches` table exists: `SERIAL id` + `external_id UUID`, FK to `solicitations(id)` and `vendors(id)`, `match_score`, `match_rationale`, `naics_match_type`, `rank`, `UNIQUE(solicitation_id, vendor_id)`                                                   | Migration applies cleanly;`\d vendor_matches` shows expected shape                                                                      |
| CLAIM-02 | `solicitations` gains `matching_status` (`pending`\|`running`\|`complete`\|`failed`), `matching_error`, `outreach_email_subject`, `outreach_email_body` (TEXT, nullable, mail-merge placeholders)                                                                    | Columns present via`\d solicitations`; existing rows unaffected (nullable/defaulted)                                                    |
| CLAIM-03 | New`vendor_matching` job type; worker handler builds a deterministic SQL candidate pool (NAICS exact → NAICS family fallback → capability full-text-search union), gated by set-aside eligibility, then runs one LLM agent that ranks/select top 25 + drafts the outreach template | Enqueue job manually against a triaged solicitation →`vendor_matches` populated (≤25 rows), `outreach_email_subject/body` populated |
| CLAIM-04 | Set-aside eligibility is a hard gate, not a scoring boost: if`solicitations.set_aside_type` indicates SDVOSB/8(a)/HUBZone/WOSB, only vendors with the matching `is_*` flag enter the candidate pool at all                                                                         | Solicitation with`set_aside_type='SDVOSB'` → 0 non-SDVOSB vendors in `vendor_matches`                                                |
| CLAIM-05 | Triage pipeline auto-enqueues`vendor_matching` after `run_solicitation_triage` completes with `quick_kill=false` (mirrors the existing `sam_fetch` → `solicitation_triage` auto-chain in `worker.py`)                                                                     | Run triage on a real solicitation →`vendor_matching` job appears in `jobs` table without manual trigger                              |
| CLAIM-06 | `POST /api/solicitations/{id}/vendor-matching` manually (re)triggers matching; requires `triage_status='complete'` and `quick_kill=false`                                                                                                                                        | Call before triage completes → 400; call after → 202 + job_id                                                                           |
| CLAIM-07 | `GET /api/solicitations/{id}/vendor-matches` returns matches joined with vendor contact/capability fields, ordered by `rank`                                                                                                                                                       | Call endpoint → array of ≤25 objects with vendor_name, contact_email, match_score, match_rationale                                      |
| CLAIM-08 | Re-running matching deletes prior`vendor_matches` rows for that `solicitation_id` before inserting new ones (no accumulation)                                                                                                                                                      | Trigger twice → row count stays ≤25, not doubled                                                                                        |
| CLAIM-09 | New "Vendor Matches" tab (`vendor_matches` tab id — distinct from the existing global "Vendors" directory-search tab) renders the ranked list + outreach template panel, with the same status-badge/spinner/polling UX pattern as `TriageTab.tsx`                                 | Manual UI check: tab appears only for solicitation-backed cases, shows spinner while`running`, renders table when `complete`          |

## 3. The Elements

| Element                                                                                                                                     | Purpose                                                                                                                                                                    | Belongs To Claim |
| ------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| `backend/schemas/010_vendor_matching.sql` (schema v19)                                                                                    | `vendor_matches` table, `solicitations` matching/outreach columns, `jobs.job_type` CHECK += `'vendor_matching'`                                                    | CLAIM-01, 02, 03 |
| `ensure_vendor_matching_schema()` in `core/db.py` + call in `api/main.py` `_apply_schemas()`                                        | Idempotent schema application                                                                                                                                              | CLAIM-01, 02     |
| `backend/ingestion/vendor_matching.py` (new, mirrors `solicitation_triage.py`)                                                          | `_build_candidate_pool()` (deterministic SQL, no LLM), `run_vendor_matching_pipeline()` (SDK agent call), `save_vendor_matches`/`save_outreach_template` MCP tools | CLAIM-03, 04, 08 |
| `process_vendor_matching_job()` in `backend/ingestion/worker.py` + dispatch branch                                                      | Worker handler                                                                                                                                                             | CLAIM-03         |
| Auto-trigger hook in`run_solicitation_triage()` (`solicitation_triage.py`)                                                              | Enqueues`vendor_matching` after non-quick-kill triage completion                                                                                                         | CLAIM-05         |
| `POST /api/solicitations/{id}/vendor-matching`, `GET /api/solicitations/{id}/vendor-matches` in `backend/api/routes/solicitations.py` | REST surface                                                                                                                                                               | CLAIM-06, 07     |
| `frontend/src/app/cases/[id]/tabs/VendorMatchesTab.tsx` (new)                                                                             | Ranked list + outreach template UI                                                                                                                                         | CLAIM-09         |
| `TabNav.tsx` — add `vendor_matches` tab id                                                                                             | Nav wiring                                                                                                                                                                 | CLAIM-09         |
| `frontend/src/lib/api.ts` — `getVendorMatches`, `triggerVendorMatching`                                                              | API client functions                                                                                                                                                       | CLAIM-06, 07, 09 |

## 4. The Evidence

**Tech Stack:** Python 3.13 / FastAPI / PostgreSQL (raw SQL, no ORM) / `claude_agent_sdk` (same `ClaudeSDKClient` + `@tool`/`create_sdk_mcp_server` pattern as `solicitation_triage.py`) / Next.js/React/Tailwind frontend.

**Sample Data:** `vendors` table is live (5,545,335 rows, loaded 2026-07-21). Field coverage: `naics_code_primary` 99.9%, `state` 99.9%, `capabilities` 51% (2,832,163 rows), all rows have `contact_email` (though 137,698 share the sentinel string `"The business owner has hidden this information from public searches"` — must be treated as absent, not a real address).

**Known Data Gap (flag, not guess):** The `vendors` table has **no PSC/classification-code column**. `gsa_large_category`/`gsa_sub_category` are GSA Multiple Award Schedule categories, unrelated to federal PSC codes. PSC-based matching (mentioned as a "maybe" in the voice note) is **not implementable** without a new data source — out of scope for this Brief. Matching uses NAICS + capabilities text only.

## 5. Existing Infrastructure

### Related Existing Tables

| Table             | Relationship                                                                                                                                                             | Location                                                           |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `solicitations` | Gains`matching_status`, `matching_error`, `outreach_email_subject`, `outreach_email_body` columns (same ALTER-column pattern as `008_solicitation_triage.sql`) | `schemas/007_solicitations.sql`, `008_solicitation_triage.sql` |
| `vendors`       | Read-only source for candidate pool;`id BIGSERIAL` is the FK target (no `external_id` column exists on this table)                                                   | `schemas/009_vendors.sql`                                        |
| `jobs`          | Reused;`job_type` CHECK extended with `'vendor_matching'`                                                                                                            | `schemas/001_core.sql` (already touched 3x — 001/007/008)       |

### Related Existing Endpoints

| Endpoint                                | What It Does                                                | Reuse or Extend?                                                                                                                                                                        |
| --------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST /api/solicitations/{id}/triage` | Manual triage trigger                                       | **Pattern to mirror** — new `vendor-matching` trigger endpoint follows the same shape (enqueue + pending status)                                                               |
| `GET /api/vendors`                    | Global vendor directory search (existing`VendorsTab.tsx`) | **Not reused directly** — this feature needs solicitation-scoped ranked results with persisted rationale, not ad-hoc search. New endpoint is additive, does not modify this one. |

### Related Existing Components

| Component                                                                                                                                     | Purpose                                           | Location                                                      | Action                                                                                                                |
| --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `ingestion/jobs.py` (`enqueue`, `claim_next`, `mark_complete/failed`)                                                                 | Job queue                                         | `backend/ingestion/jobs.py`                                 | **Reuse as-is**                                                                                                 |
| `ingestion/worker.py` dispatch loop                                                                                                         | Job type routing                                  | `backend/ingestion/worker.py:607-631`                       | **Extend** — add `elif job["job_type"] == "vendor_matching":` branch                                         |
| `chat/tools.py` `search_vendors` MCP tool + `/api/vendors` SQL pattern                                                                  | Existing NAICS/state/set-aside filter query shape | `backend/chat/tools.py:3600+`, `backend/api/main.py:506+` | **Reference pattern, not reused directly** — candidate-pool query needs tiered fallback logic these don't have |
| `TriageTab.tsx` (status badges, spinner-while-running poll loop, `canTrigger` gating)                                                     | UI pattern                                        | `frontend/src/app/cases/[id]/tabs/TriageTab.tsx`            | **Reuse pattern** — `VendorMatchesTab.tsx` copies the same polling/status/trigger-button structure           |
| `solicitation_triage.py` SDK agent pattern (`ClaudeSDKClient`, `@tool`, `create_sdk_mcp_server`, `_save_*_impl` delete-then-insert) | Agent orchestration pattern                       | `backend/ingestion/solicitation_triage.py`                  | **Reuse pattern directly** — `vendor_matching.py` is structurally a sibling module                           |

### Known Constraints

- [X] Must use `SERIAL id` + `external_id UUID DEFAULT gen_random_uuid()` for `vendor_matches`, per `database-design.md`
- [X] No ORM — raw SQL, numbered migration file (`010_vendor_matching.sql`, `schema_migrations` version 19)
- [X] `jobs.job_type` CHECK constraint reset requires including **every** existing value (`ingest`, `ingest_pdf`, ..., `sam_fetch`, `solicitation_triage`, `'vendor_matching'`, `other`) — this bit us once already (the startup crash fixed earlier this session); the new migration file must carry the full list forward
- [X] Candidate-pool SQL query must run against 5.5M rows efficiently — reuse existing indexes (`idx_vendors_naics_primary`, `idx_vendors_naics_trgm`, `idx_vendors_fts`, `idx_vendors_state`); no new indexes anticipated but flag if `EXPLAIN ANALYZE` shows a seq scan during implementation
- [X] Email drafting is ONE LLM-authored template per solicitation (not per-vendor) — client-side placeholder substitution only, per user's explicit cost/complexity tradeoff decision

## 6. Pre-Mortem

**What could break?**

- Sparse `capabilities` field (49% NULL) means the FTS fallback tier silently returns nothing for half the registry — mitigated by NAICS being the primary/required signal; capabilities FTS is supplementary, not the sole path
- `contact_email` sentinel string (`"The business owner has hidden this information from public searches"`) must be filtered/treated as null in both the candidate pool and the outreach UI, or emails will look broken
- Large candidate pools before LLM ranking — mitigated by capping the deterministic SQL pre-filter output at a fixed ceiling (target ~300 rows) before it's ever handed to the agent, keeping token cost bounded regardless of how common a NAICS code is
- A solicitation with no `naics_code` (state/local sources never get one — see solicitation-ingestion Brief §5) has no matching path — `matching_status` should reflect a clear "no NAICS code available" failure state rather than silently returning zero matches with no explanation

**What assumptions are we making?**

- The already-extracted `artifact_scope_of_work` / `artifact_technical_requirements` HTML (from the triage pipeline) is sufficient context for the ranking agent — no need to re-read raw solicitation documents
- NAICS-family fallback (matching first 4 digits) is an acceptable "cast a wider net" heuristic when the exact-NAICS pool is thin; the LLM ranking step is the actual quality gate, not the SQL filter
- 25 is a fixed cap regardless of pool size (per user decision) — no dynamic "all above threshold" mode in v1

**What do we NOT know yet?**

- Exact system-prompt wording/tone for the outreach email draft — deferred to State 2 (Architecture) prompt-writing, not blocking the schema/API design
- Whether `place_of_performance` (JSONB, shape TBD per the solicitation-ingestion Brief) reliably contains a parseable state code for the location-boost scoring tier — must confirm against a live fixture during implementation; if absent, location becomes advisory-only in the LLM's rationale rather than a scoring input

## 7. Out of Scope (Explicit)

- PSC-code-based matching (no data source exists for it — see §4 Known Data Gap)
- Per-vendor personalized LLM email drafts (explicit user decision: shared template + client-side mail-merge instead)
- The future "Issue Communication" / outreach tracking resource (queuing sent emails, intercepting vendor responses, managing communication threads in-app) — explicitly deferred by the user to a separate future spec
- Geospatial distance scoring / PostGIS — state-level string match only for now; flagged as a possible future plugin if state-only proves too coarse
- Vendor-side portal, vendor self-registration, or vendor response intake — none of that exists yet and isn't part of this Brief

## 8. Approval Gate

**Status:** [ ] DRAFT  [ ] APPROVED

**Approved By:**

**Date:**

---

> ⚠️ **EXIT CONDITION:** This Brief is not approved until all Claims have defined Verdicts and the Tech Stack is explicit. No ambiguity allowed.
