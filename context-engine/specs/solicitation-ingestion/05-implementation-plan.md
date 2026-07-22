# Solicitation Ingestion — Implementation Plan

> **Phase:** State 3 — Planning (The Foreman)
> **Date:** 2026-07-21
> **Principle:** Backend-Out Sequencing (DB → sam_client → API → Worker → Frontend)
> **Ticket Standard:** Each ticket is atomic, completable in isolation, binary acceptance test.

## Ticket Dependency Graph

```
T01 (DB Migration)
 └─ T02 (SolicitationManager CRUD)
     ├─ T03 (sam_client.py)
     │   └─ T04 (Worker sam_fetch handler)
     ├─ T05 (API Routes)
     │   └─ T06 (Router Registration)
     │       └─ T07 (Frontend API Client)
     │           └─ T08 (SolicitationsPage)
     │               └─ T09 (Nav Link)
     └─ T10 (Integration Verification)
```

---

## T01 — Database Migration

**Dependencies:** None | **Type:** Backend — Schema | **Effort:** Small

### Files to Create
- `backend/schemas/007_solicitations.sql` — full migration from [01-schema.sql](01-schema.sql)

### Files to Modify
- `backend/core/db.py` — add `ensure_solicitations_schema()` (mirrors `ensure_folders_schema()`), add to `__all__`
- `backend/api/main.py` — import + call `ensure_solicitations_schema()` in `_apply_schemas()`
- `backend/init_db.py` — call `ensure_solicitations_schema()` alongside the other `ensure_*` calls

### Acceptance Criteria
- [ ] `solicitations` table created with all columns, CHECK constraints, indexes, `UNIQUE(notice_id)`
- [ ] `jobs.job_type` CHECK includes `'sam_fetch'`
- [ ] `documents.source` CHECK includes `'sam_gov'`
- [ ] `schema_migrations` version 17 inserted, `ON CONFLICT DO NOTHING`
- [ ] Migration idempotent — safe to re-run
- [ ] `\d solicitations` shows expected shape

**Verification:**
```bash
psql -c "\d solicitations"
psql -c "SELECT conname FROM pg_constraint WHERE conname='jobs_job_type_check';"
```

**Maps to Brief:** CLAIM-01, CLAIM-09

---

## T02 — SolicitationManager CRUD

**Dependencies:** T01 | **Type:** Backend — Data Layer | **Effort:** Medium

### Files to Create
- `backend/core/solicitation.py` — `SolicitationManager` class, mirrors `CaseManager` in `backend/core/case.py`

### Methods
| Method | Signature | Purpose |
|--------|-----------|---------|
| `create` | `(source_type, url, title=None, notice_id=None) -> dict` | Creates `cases` row (`case_type='rfp_response'`) + `solicitations` row in one transaction. Raises `DuplicateNoticeError` if `notice_id` already exists (caught by route → 409). |
| `get` | `(solicitation_id) -> dict \| None` | Row + `documents` via `CaseManager()._list_documents(case_id)` |
| `list` | `(source_type=None, ingestion_status=None, limit=50, offset=0) -> list[dict]` | Filtered list |
| `update` | `(solicitation_id, **kwargs) -> dict \| None` | Partial update — used by worker to set metadata/status; allowed fields: `title, ingestion_status, has_missing_docs, error_message, agency, naics_code, psc_code, set_aside_type, set_aside_description, point_of_contact, place_of_performance, response_deadline, posted_date` |
| `get_by_notice_id` | `(notice_id) -> dict \| None` | Idempotency check before insert |

### Patterns to Follow
- `CaseManager` in `backend/core/case.py` — `tx()`/`connect()` usage, `RealDictCursor`, `self._j()` for JSONB
- `create()` composes `CaseManager().create_case(name=title or placeholder, case_type='rfp_response')` inside the same `tx()` as the `solicitations` INSERT (single transaction, single commit)
- Federal title placeholder: `"Untitled SAM.gov Opportunity (fetching...)"` when `title` is omitted (per 02-api-contract.json)

### Acceptance Criteria
- [ ] `create()` for federal (no title) creates case + solicitation with placeholder title, `notice_id` set, `ingestion_status='pending'`
- [ ] `create()` for state/local requires `title`; raises `ValueError` if missing (caught by route → 400)
- [ ] `create()` with a duplicate `notice_id` raises before creating a new case (no orphan case row)
- [ ] `get()` returns solicitation dict with nested `documents` list
- [ ] `list()` filters correctly by `source_type` and `ingestion_status`
- [ ] `update()` only sets provided kwargs; always sets `updated_at = now()`

**Verification:**
```python
from core.solicitation import SolicitationManager, DuplicateNoticeError
mgr = SolicitationManager()
sol = mgr.create(source_type="federal", url="https://sam.gov/...", notice_id="abc123")
assert sol["ingestion_status"] == "pending"
try:
    mgr.create(source_type="federal", url="...", notice_id="abc123")
    assert False
except DuplicateNoticeError:
    pass
```

**Maps to Brief:** CLAIM-02, CLAIM-03, CLAIM-07, CLAIM-08, CLAIM-09

---

## T03 — sam_client.py

**Dependencies:** None (parallel with T01/T02) | **Type:** Backend — External Integration | **Effort:** Medium

### Files to Create
- `backend/ingestion/sam_client.py`

### Functions
| Function | Signature | Purpose |
|----------|-----------|---------|
| `extract_notice_id` | `(url: str) -> str \| None` | Regex-extract `noticeId` from a SAM.gov opportunity URL (pattern: `/opp/{id}/view` or `noticeid={id}`) |
| `fetch_notice` | `(notice_id: str) -> dict` | `GET https://api.sam.gov/opportunities/v2/search?noticeid={id}&api_key=...&postedFrom=...&postedTo=...` (1-year lookback window per API's mandatory date-range param). Raises `SamFetchError` if `totalRecords == 0` or non-200. Returns the single `opportunitiesData[0]` dict. |
| `download_resource_link` | `(url: str, dest_path: Path) -> dict` | `GET {url}?api_key=...`, parses `Content-Disposition` header for filename (fallback: `attachment_{hash}.bin`), writes bytes to `dest_path`. Returns `{"filename": str, "path": Path}`. Raises on non-200. |

### Patterns to Follow
- `httpx` sync client (worker context is sync, unlike the async `chat/external_tools.py` tools) — use `httpx.get(..., timeout=30)` not `AsyncClient`
- Reuse `SAM_GOV_API_KEY` env var (same name as `chat/external_tools.py`'s `_SAM_API_KEY`)
- Defensive `.get()` parsing throughout — per fixtures, `pointOfContact`/`placeOfPerformance`/`resourceLinks` can all be `null`

### Acceptance Criteria
- [ ] `extract_notice_id` correctly parses both `https://sam.gov/opp/{id}/view` and `https://sam.gov/workspace/contract/opp/{id}/view` URL shapes
- [ ] `fetch_notice` against the real fixture notice_id in [03-fixtures.json](03-fixtures.json) returns the expected fields
- [ ] `fetch_notice` raises `SamFetchError` for a nonexistent notice_id (0 results)
- [ ] `download_resource_link` against a real resourceLink URL returns the correct filename from `Content-Disposition` (per fixture: `Sol_140G0326Q0165.pdf`)
- [ ] Null `resourceLinks`/`pointOfContact` handled without exceptions

**Verification:**
```python
from ingestion.sam_client import extract_notice_id, fetch_notice
nid = extract_notice_id("https://sam.gov/workspace/contract/opp/fcdeac21a751483d9546f97d28fa27c5/view")
assert nid == "fcdeac21a751483d9546f97d28fa27c5"
notice = fetch_notice(nid)
assert notice["naicsCode"] == "541511"
```

**Maps to Brief:** CLAIM-04, CLAIM-05, CLAIM-06

---

## T04 — Worker sam_fetch Handler

**Dependencies:** T02, T03 | **Type:** Backend — Job Processing | **Effort:** Medium

### Files to Modify
- `backend/ingestion/worker.py` — add `process_sam_fetch_job(job: dict)`, add `elif job["job_type"] == "sam_fetch":` branch in `main()`

### Behavior
1. Set `solicitations.ingestion_status = 'fetching'` (via `SolicitationManager().update()`)
2. `notice = fetch_notice(notice_id)` — on `SamFetchError`: `mark_failed(job_id, str(e))` + `update(ingestion_status='failed', error_message=str(e))`, return (CLAIM-06)
3. Map fields → `SolicitationManager().update(agency=notice.get("fullParentPathName"), naics_code=notice.get("naicsCode"), psc_code=notice.get("classificationCode"), set_aside_type=notice.get("typeOfSetAside"), set_aside_description=notice.get("typeOfSetAsideDescription"), point_of_contact=notice.get("pointOfContact"), place_of_performance=notice.get("placeOfPerformance"), response_deadline=notice.get("responseDeadLine"), posted_date=notice.get("postedDate"))`. Also set `title=notice["title"]` when SAM.gov returns a non-empty title, replacing the `FEDERAL_TITLE_PLACEHOLDER` (per `solicitation_row_after_sam_fetch` in [03-fixtures.json](03-fixtures.json)) — `title` is `NOT NULL`, so never pass `title=None`/empty.
4. `resource_links = notice.get("resourceLinks") or []`; if empty → `has_missing_docs=True`, skip to step 6
5. For each link: `download_resource_link()` → `upload_file()` to MinIO → `ingest_file(case_id, local_path, document_name=filename)` with `source='sam_gov'` (requires passing `source` through `ingest_file`/`insert_document` call chain — confirm existing `ingest_file` signature supports an explicit `source` override, or set it via a follow-up `UPDATE documents SET source='sam_gov'` after ingest if not). On any single download/ingest failure: log, continue to next link, set `has_missing_docs=True` (CLAIM-05) — do not fail the whole job.
6. `update_progress(job_id, 100)`; `SolicitationManager().update(ingestion_status='complete')`; `mark_complete(job_id)`

### Acceptance Criteria
- [ ] Enqueuing a `sam_fetch` job for the fixture notice_id results in `ingestion_status='complete'`, metadata populated, 3 documents ingested with `source='sam_gov'`
- [ ] Empty/null `resourceLinks` → job completes, `has_missing_docs=True`
- [ ] One failing download among several → job still completes, `has_missing_docs=True`, other documents ingested
- [ ] Invalid/nonexistent notice_id → job `failed`, solicitation `ingestion_status='failed'` with `error_message` set

**Verification:** Manual enqueue + poll, per [03-fixtures.json](03-fixtures.json) `sam_fetch_failure_example` / `sam_fetch_missing_docs_example`.

**Maps to Brief:** CLAIM-04, CLAIM-05, CLAIM-06

---

## T05 — API Routes

**Dependencies:** T02 | **Type:** Backend — REST API | **Effort:** Small

### Files to Create
- `backend/api/routes/solicitations.py` — per [02-api-contract.json](02-api-contract.json), structural copy of `tasks.py`

### Endpoints
| Method | Path | Maps to |
|--------|------|---------|
| `POST` | `/api/solicitations` | `SolicitationManager.create()` + `_enqueue_job(job_type="sam_fetch")` for federal |
| `GET` | `/api/solicitations` | `SolicitationManager.list()` |
| `GET` | `/api/solicitations/{id}` | `SolicitationManager.get()` |

### Acceptance Criteria
- [ ] `POST` with `source_type='federal'` → 201, `job_id` set, row visible immediately (pending)
- [ ] `POST` with `source_type='state'|'local'` and no title → 400
- [ ] `POST` with duplicate `notice_id` → 409 with `existing_external_id`
- [ ] `GET /api/solicitations?source_type=federal` filters correctly
- [ ] `GET /api/solicitations/{id}` returns `documents` array
- [ ] 404 for nonexistent id
- [ ] All endpoints require `Depends(get_current_user)`

**Maps to Brief:** CLAIM-02, CLAIM-03, CLAIM-07, CLAIM-08, CLAIM-09

---

## T06 — Router Registration

**Dependencies:** T05 | **Type:** Backend — Integration | **Effort:** Trivial

### Files to Modify
- `backend/api/main.py` — `from api.routes.solicitations import router as solicitations_router`; `app.include_router(solicitations_router)`

### Acceptance Criteria
- [ ] Endpoints appear in `/api/openapi.json` under `solicitations` tag
- [ ] Existing routes unaffected

**Maps to Brief:** CLAIM-02, CLAIM-07, CLAIM-08

---

## T07 — Frontend API Client

**Dependencies:** T06 | **Type:** Frontend — Data Layer | **Effort:** Small

### Files to Modify
- `frontend/src/lib/api.ts` — add `listSolicitations`, `createSolicitation`, `getSolicitation` per [04-ui-specs.md §9](04-ui-specs.md)

### Acceptance Criteria
- [ ] Functions compile, follow existing `listCases`/`createCase` pattern exactly (same `fetchAPI` wrapper, same param/query handling)
- [ ] Types match `02-api-contract.json` schemas

**Maps to Brief:** CLAIM-02, CLAIM-03, CLAIM-07, CLAIM-08

---

## T08 — SolicitationsPage (new landing page) + Cases route move

**Dependencies:** T07 | **Type:** Frontend — Page | **Effort:** Medium

> Per user decision: Solicitations becomes the landing page (`/`). The existing Cases dashboard moves to `/cases`, unchanged in behavior.

### Files to Create
- `frontend/src/app/cases/page.tsx` — move the **current** contents of `frontend/src/app/page.tsx` here verbatim (no functional changes)

### Files to Modify (rewrite)
- `frontend/src/app/page.tsx` — replaced with the new `SolicitationsPage` per [04-ui-specs.md](04-ui-specs.md) §§1–8

### Acceptance Criteria
- [ ] `/cases` renders the exact same Cases dashboard as before (byte-identical behavior, just moved)
- [ ] `/` renders the new Solicitations list + create panel per UI spec
- [ ] Source type selector toggles required/optional title field correctly
- [ ] Create → 201 → row appears; 409 → inline error shown; 400 → inline error shown
- [ ] Polling refreshes rows while any is `pending`/`fetching`, stops otherwise
- [ ] Empty state shown when list is empty
- [ ] Status/source-type badges match color maps in UI spec §6.1

**Maps to Brief:** Success Verdict (list view), CLAIM-02, CLAIM-03

---

## T09 — Nav Links (cross-links between `/` and `/cases`)

**Dependencies:** T08 | **Type:** Frontend — Integration | **Effort:** Trivial

### Files to Modify
- `frontend/src/app/page.tsx` (Solicitations) — add "Cases" link in header, per [04-ui-specs.md §2](04-ui-specs.md)
- `frontend/src/app/cases/page.tsx` (Cases) — add "Solicitations" link in header pointing to `/`
- `frontend/src/app/cases/[id]/page.tsx` — both `router.push("/")` "Back to cases" buttons (error state and header) → `router.push("/cases")`

### Acceptance Criteria
- [ ] Link visible in Solicitations header, navigates to `/cases`
- [ ] Link visible in Cases header, navigates to `/`
- [ ] "Back to cases" from a case detail page navigates to `/cases`, not `/`
- [ ] Existing header elements (Profile, API status, user/logout) unaffected on both pages
- [ ] `profile/page.tsx`'s back button (→ `/`) is left unchanged — lands on the new Solicitations landing page, which is acceptable general "home" behavior

**Maps to Brief:** Success Verdict (list view)

---

## T10 — Integration Verification (The Verdict)

**Dependencies:** All (T01–T09) | **Type:** QA | **Effort:** Small

Run against real fixture data ([03-fixtures.json](03-fixtures.json)):

```
CLAIM-01: psql \d solicitations — table + constraints exist
CLAIM-02: POST federal → 201 + job_id → poll job → solicitation reaches 'complete', metadata populated
CLAIM-03: POST state/local → 201, no job → POST /api/cases/{id}/ingest → document appears
CLAIM-04: sam_fetch job populates agency/naics/psc/set-aside/deadline + downloads resourceLinks
CLAIM-05: null/failed resourceLinks → job completes, has_missing_docs=true
CLAIM-06: bad notice_id → job failed, solicitation ingestion_status='failed'
CLAIM-07: GET /api/solicitations?source_type=&ingestion_status= filters correctly
CLAIM-08: GET /api/solicitations/{id} includes documents[]
CLAIM-09: duplicate notice_id → 409 with existing_external_id, no duplicate case created
UI: list view shows solicitations, create flow works end-to-end for both federal and state/local
```

### Acceptance Criteria
- [ ] All 9 claims pass against live SAM.gov API (not mocked) at least once
- [ ] 0 regressions on existing `/api/cases`, `/api/jobs`, `/api/cases/{id}/ingest` endpoints
- [ ] 0 TypeScript compilation errors

**Status:** [ ] DRAFT  [ ] APPROVED
