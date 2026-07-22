# Vendor Matching — Implementation Plan

> **Phase:** State 3 — Planning (The Foreman)
> **Date:** 2026-07-21
> **Principle:** Backend-Out Sequencing (DB → Data Layer → Pipeline → Worker → API → Frontend)
> **Ticket Standard:** Each ticket is atomic, completable in isolation, binary acceptance test.

## Ticket Dependency Graph

```
T01 (DB Migration v19)
 └─ T02 (VendorMatchManager + candidate-pool query)
     └─ T03 (vendor_matching.py pipeline)
         └─ T04 (Worker handler + auto-trigger hook)
             ├─ T05 (API Routes: trigger + list)
             │   └─ T06 (Frontend API Client)
             │       └─ T07 (VendorMatchesTab.tsx + nav wiring)
             └─ T08 (Integration Verification)
```

---

## T01 — Database Migration v19

**Dependencies:** None | **Type:** Backend — Schema | **Effort:** Small

### Files to Create
- `backend/schemas/010_vendor_matching.sql` — copy of [01-schema.sql](01-schema.sql) verbatim

### Files to Modify
- `backend/core/db.py` — add `ensure_vendor_matching_schema()` (mirrors `ensure_solicitation_triage_schema()`, reads `010_vendor_matching.sql`), add to `__all__`
- `backend/api/main.py` — import + call `ensure_vendor_matching_schema()` in `_apply_schemas()`, after `ensure_vendors_schema()`
- `backend/init_db.py` — import + call `ensure_vendor_matching_schema()` alongside the other `ensure_*` calls; add `vendor_matches` to the `expected` table set

### Acceptance Criteria
- [ ] `vendor_matches` table created with all columns, CHECK constraints, `UNIQUE(solicitation_id, vendor_id)`, both indexes, trigger
- [ ] `solicitations` gains `matching_status`/`matching_error`/`outreach_email_subject`/`outreach_email_body`
- [ ] `jobs.job_type` CHECK includes `'vendor_matching'` (full list carried forward per Brief §5 constraint)
- [ ] `schema_migrations` version 19 inserted, `ON CONFLICT DO NOTHING`
- [ ] Migration idempotent — safe to re-run
- [ ] `\d vendor_matches` and `\d solicitations` show expected shape

**Verification:**
```bash
psql -c "\d vendor_matches"
psql -c "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='jobs_job_type_check';"
```

**Maps to Brief:** CLAIM-01, CLAIM-02

---

## T02 — VendorMatchManager + Candidate-Pool Query

**Dependencies:** T01 | **Type:** Backend — Data Layer | **Effort:** Medium

### Files to Create
- `backend/core/vendor_match.py` — new module, sibling to `core/solicitation.py`

### Class: `VendorMatchManager`
| Method | Signature | Purpose |
|--------|-----------|---------|
| `build_candidate_pool` | `(naics_code: str, set_aside_type: str \| None, cap: int = 300) -> list[dict]` | Tiered SQL: (1) exact NAICS match on `naics_code_primary`, tagged `naics_match_type='exact'`; (2) if pool < `cap`, UNION in NAICS-family (first 4 digits, `naics_code_primary LIKE 'xxxx%'`) tagged `'family'`; (3) if still < `cap`, UNION in capabilities FTS (`plainto_tsquery` against a synthesized query built from the NAICS code's description — deferred to prompt/agent context, not SQL-guessed) tagged `'capability_only'`. Set-aside hard gate applied as a `WHERE` clause on the relevant `is_*` column at every tier per CLAIM-04 (map `set_aside_type` string → column, e.g. contains "SDVOSB" → `is_sdvosb=TRUE`; unrecognized/None → no gate). Excludes vendors whose `contact_email` equals the sentinel string only at read time (§ below), not from the pool (email absence doesn't disqualify a match). Returns raw vendor rows capped at `cap`, deduplicated across tiers. |
| `save_matches` | `(solicitation_id: int, matches: list[dict]) -> None` | Delete-then-insert pattern (mirrors `_save_artifact_impl`): `DELETE FROM vendor_matches WHERE solicitation_id=%s` then bulk `INSERT` the ≤25 ranked rows (CLAIM-08) |
| `list_for_solicitation` | `(solicitation_id: int) -> list[dict]` | `SELECT` `vendor_matches` JOIN `vendors` on the `VendorMatch` schema's fields, `ORDER BY rank`. Replaces sentinel-string `contact_email` with `NULL` in the query (`CASE WHEN contact_email = '<sentinel>' THEN NULL ELSE contact_email END`) |

### Set-Aside → Column Mapping
Reuse the exact map from `chat/tools.py`'s `search_vendors` (`small_business`→`is_small_business`, `woman_owned`→`is_woman_owned`, `veteran_owned`→`is_veteran_owned`, `sdvosb`→`is_sdvosb`, `hubzone`→`is_hubzone`, `8a`→`is_8a`). `solicitations.set_aside_type` is a free-text SAM.gov value (e.g. `"SDVOSB Set-Aside"`) — match case-insensitively by substring against known keywords (`SDVOSB`, `8(A)`/`8A`, `HUBZONE`, `WOSB`/`WOMEN`, `SB`/`SMALL BUSINESS`); no match → no gate applied (open pool), logged as informational, not an error.

### Acceptance Criteria
- [ ] `build_candidate_pool` on a real NAICS code (e.g. `541511`) returns exact matches only if pool ≥ some reasonable size, else backfills with family/capability tiers, capped at 300
- [ ] Set-aside gate: solicitation with `set_aside_type` containing `'SDVOSB'` → 0 non-SDVOSB vendors in the returned pool (CLAIM-04)
- [ ] `save_matches` called twice for the same `solicitation_id` → row count stays ≤25 (CLAIM-08)
- [ ] `list_for_solicitation` masks the sentinel email string as `null`
- [ ] `EXPLAIN ANALYZE` on the exact-NAICS tier query shows index usage (`idx_vendors_naics_primary`), not a sequential scan over 5.5M rows

**Verification:**
```python
from core.vendor_match import VendorMatchManager
mgr = VendorMatchManager()
pool = mgr.build_candidate_pool(naics_code="541511", set_aside_type="SDVOSB Set-Aside")
assert all(v["is_sdvosb"] for v in pool)
assert len(pool) <= 300
```

**Maps to Brief:** CLAIM-01, CLAIM-04, CLAIM-08

---

## T03 — vendor_matching.py Pipeline (SDK Agent)

**Dependencies:** T02 | **Type:** Backend — Agent Orchestration | **Effort:** Medium-Large

### Files to Create
- `backend/ingestion/vendor_matching.py` — structural sibling of `solicitation_triage.py`

### Functions
| Function | Purpose |
|----------|---------|
| `_save_matches_impl(solicitation_id, matches: list[dict]) -> dict` | Validates each match dict (`vendor_id`, `rank` 1-25, `match_score` 0-100, `match_rationale`, `naics_match_type`), truncates to 25, calls `VendorMatchManager().save_matches()` |
| `_save_outreach_impl(solicitation_id, subject, body) -> dict` | `SolicitationManager().update(solicitation_id, outreach_email_subject=subject, outreach_email_body=body)` |
| `_run_matching_agent(case_id, solicitation_id, candidate_pool, sol) -> dict` | One `ClaudeSDKClient` call. System prompt: rank the ≤300 candidate pool (passed as JSON in the user message, not re-fetched via tools — no read-tool access needed since the pool + `artifact_scope_of_work`/`artifact_technical_requirements` HTML are supplied directly), select top 25, assign `match_score`/`match_rationale` each, draft ONE outreach email (subject + body with `{{vendor_name}}`/`{{match_reason}}` placeholders). Two `@tool`s: `save_matches`, `save_outreach_email`. `allowed_tools` = only these two (no read tools — pipeline is fully data-driven, unlike triage) |
| `run_vendor_matching_pipeline(case_id, solicitation_id) -> dict` | Orchestrator: sets `matching_status='running'`; validates `naics_code` present (else `matching_status='failed'`, `matching_error='No NAICS code available for matching'`, return); calls `build_candidate_pool()`; if pool is empty → `matching_status='complete'` with 0 matches (legitimate per Brief §1, not a failure); else runs `_run_matching_agent()`; sets `matching_status='complete'`\|`'failed'` |
| `run_vendor_matching_pipeline_sync(case_id, solicitation_id) -> dict` | Sync wrapper (`asyncio.run`), called by worker — mirrors `run_solicitation_triage_pipeline` |

### Prompt Content (concrete, not deferred)
System prompt instructs: rank by NAICS specificity (exact > family > capability_only) + capability-narrative relevance to `artifact_scope_of_work`/`artifact_technical_requirements` + state proximity to `place_of_performance` (advisory only, per Brief §6) as one signal among several; `match_score` reflects overall confidence 0-100; `match_rationale` is 1-2 sentences citing the specific overlap. Outreach email: professional subcontracting-outreach tone, references the solicitation's NAICS/scope generically (no company name — Vision has no user-company profile requirement for this v1), uses `{{vendor_name}}` and `{{match_reason}}` placeholders exactly once each.

### Acceptance Criteria
- [ ] Running against a real triaged solicitation with a valid NAICS code populates `vendor_matches` (≤25 rows) and `outreach_email_subject`/`outreach_email_body`
- [ ] No `naics_code` → `matching_status='failed'`, `matching_error` set, no agent call made
- [ ] Empty candidate pool → `matching_status='complete'`, 0 matches, no agent call made (cost-saving — nothing to rank)
- [ ] Agent failure/exception → `matching_status='failed'`, `matching_error=str(exc)`
- [ ] `match_rationale` values are non-empty, plausible (spot-check 3 rows)

**Maps to Brief:** CLAIM-03, CLAIM-04

---

## T04 — Worker Handler + Auto-Trigger Hook

**Dependencies:** T03 | **Type:** Backend — Job Processing | **Effort:** Small

### Files to Modify
- `backend/ingestion/worker.py` — add `process_vendor_matching_job(job: dict)` (mirrors `process_solicitation_triage_job`), add `elif job["job_type"] == "vendor_matching":` branch in `main()`, add import `from ingestion.vendor_matching import run_vendor_matching_pipeline_sync`
- `backend/ingestion/solicitation_triage.py` — in `run_solicitation_triage()`, after the non-quick-kill success path (end of the function, after `mgr.update(..., triage_status="complete", ...)`), enqueue `job_type='vendor_matching'` with `metadata={"solicitation_id": solicitation_id}` (mirrors the `sam_fetch`→`solicitation_triage` chain in `worker.py`'s `process_sam_fetch_job`). Import `enqueue` from `ingestion.jobs` (deferred import inside the function, matching existing deferred-import style in this file)

### Acceptance Criteria
- [ ] Running triage on a real solicitation with `quick_kill=false` results in a `vendor_matching` job appearing in `jobs` automatically (CLAIM-05)
- [ ] Quick-killed triage does NOT auto-enqueue `vendor_matching`
- [ ] `process_vendor_matching_job` sets `mark_complete`/`mark_failed` correctly based on pipeline result
- [ ] Missing `solicitation_id` in job metadata → `mark_failed` with clear message

**Maps to Brief:** CLAIM-03, CLAIM-05

---

## T05 — API Routes: Trigger + List

**Dependencies:** T04 | **Type:** Backend — REST API | **Effort:** Small

### Files to Modify
- `backend/api/routes/solicitations.py` — add two endpoints per [02-api-contract.json](02-api-contract.json), placed after the existing triage trigger endpoint

### Endpoints
| Method | Path | Behavior |
|--------|------|----------|
| `POST` | `/api/solicitations/{id}/vendor-matching` | `mgr.get(id)` → 404 if none. Validate in order: `triage_status != 'complete'` → 400 `'Cannot run vendor matching — triage has not completed'`; `quick_kill` → 400 `'...quick-killed during triage'`; `not naics_code` → 400 `'...no NAICS code'`; `matching_status == 'running'` → 400 `'Vendor matching is already running'`. Else `mgr.update(id, matching_status='pending', matching_error=None)`, enqueue `job_type='vendor_matching'`, return `{"job_id": ..., "matching_status": "pending"}` |
| `GET` | `/api/solicitations/{id}/vendor-matches` | `mgr.get(id)` → 404 if none. `VendorMatchManager().list_for_solicitation(id)`. Return `{"matching_status", "matching_error", "outreach_email_subject", "outreach_email_body", "matches"}` per contract — 200 even when `matches=[]` and `matching_status='pending'` |

### Acceptance Criteria
- [ ] All 6 acceptance scenarios in [02-api-contract.json](02-api-contract.json) `vendor_matching_trigger`/`vendor_matches_list` pass
- [ ] Both endpoints require `Depends(get_current_user)`
- [ ] Response shapes match `VendorMatch` schema exactly (field names, types)

**Maps to Brief:** CLAIM-06, CLAIM-07

---

## T06 — Frontend API Client

**Dependencies:** T05 | **Type:** Frontend — Data Layer | **Effort:** Small

### Files to Modify
- `frontend/src/lib/api.ts` — add `VendorMatch`, `VendorMatchesResponse` interfaces, `getVendorMatches`, `triggerVendorMatching` functions per [04-ui-specs.md §9](04-ui-specs.md); extend the existing `Solicitation` interface with `matching_status`, `matching_error`, `outreach_email_subject`, `outreach_email_body`

### Acceptance Criteria
- [ ] Functions compile, follow the exact `fetchAPI` wrapper pattern as `triggerTriage`/`getSolicitationByCase`
- [ ] Types match `02-api-contract.json`'s `VendorMatch` schema field-for-field

**Maps to Brief:** CLAIM-06, CLAIM-07, CLAIM-09

---

## T07 — VendorMatchesTab.tsx + Nav Wiring

**Dependencies:** T06 | **Type:** Frontend — Page/Component | **Effort:** Medium

### Files to Create
- `frontend/src/app/cases/[id]/tabs/VendorMatchesTab.tsx` — per [04-ui-specs.md](04-ui-specs.md) in full (header, `canTrigger` gating, 5 body states, `OutreachEmailPanel`, `VendorMatchList`/`VendorMatchRow`/`ScoreBadge`/`NaicsMatchTypeBadge`/`SetAsideFlags`/`CopyEmailButton`, polling)

### Files to Modify
- `frontend/src/app/cases/[id]/TabNav.tsx` — add `"vendor_matches"` to `TabId` union; add `TabDef` entry (`icon: Users`, label "Vendor Matches", shortLabel "Matches") inserted after `"triage"` in `BASE_TABS`; add `showVendorMatches?: boolean` prop, filter `BASE_TABS` on it the same way `showTriage` filters `"triage"`
- `frontend/src/app/cases/[id]/page.tsx` — import `VendorMatchesTab`; add `"vendor_matches"` to the `tabParam ===` allow-list; add `{activeTab === "vendor_matches" && <VendorMatchesTab caseId={Number(id)} />}`; pass `showVendorMatches={hasSolicitation}` to `<TabNav>`

### Visual Polish Note
Per user direction, this is not a literal port of `mockups/vendor-matches-mockup.html` — apply reasonable visual polish beyond the bare mockup (spacing rhythm, icon choices, subtle hover/transition treatment) while staying within `design-system.md`/`component-patterns.md` tokens. No new colors, spacing scale, or components outside those standards.

### Acceptance Criteria
- [ ] Tab appears only when `hasSolicitation` is true, positioned right after Triage
- [ ] All 5 body states render correctly against real data (`pending`/`running`/`failed`/`complete+0`/`complete+N`)
- [ ] `canTrigger` client-side gating matches server 400 reasons exactly
- [ ] `CopyEmailButton` correctly substitutes `{{vendor_name}}`/`{{match_reason}}` and copies to clipboard, with "Copy"→"Copied" label swap
- [ ] Sentinel-masked email displays as italic "hidden", not the raw sentinel string
- [ ] Table wraps `overflow-x-auto` on desktop; mobile shows stacked cards; 44px touch targets on buttons
- [ ] 0 TypeScript compilation errors

**Maps to Brief:** CLAIM-09

---

## T08 — Integration Verification (The Verdict)

**Dependencies:** T01–T07 | **Type:** QA | **Effort:** Small

Run against real data:

```
CLAIM-01: psql \d vendor_matches — table + constraints exist
CLAIM-02: psql \d solicitations — 4 new columns present
CLAIM-03: Enqueue vendor_matching job manually → vendor_matches populated (≤25), outreach fields populated
CLAIM-04: Solicitation with set_aside_type='SDVOSB...' → 0 non-SDVOSB vendors in vendor_matches
CLAIM-05: Run triage end-to-end on a real solicitation → vendor_matching job auto-appears in jobs table
CLAIM-06: POST .../vendor-matching before triage complete → 400; after → 202 + job_id
CLAIM-07: GET .../vendor-matches → array of ≤25 objects, ordered by rank, vendor fields populated
CLAIM-08: Trigger matching twice on the same solicitation → row count stays ≤25
CLAIM-09: Manual UI check — tab appears, spinner while running, renders table when complete, Copy Email works
```

### Acceptance Criteria
- [ ] All 9 claims pass against live data (real `vendors` table, real LLM agent call — not mocked) at least once
- [ ] 0 regressions on existing `/api/solicitations`, `/api/vendors`, `/api/jobs` endpoints
- [ ] 0 TypeScript compilation errors on `npm run build` (or equivalent per `frontend/AGENTS.md`)

**Status:** [ ] DRAFT  [ ] APPROVED
