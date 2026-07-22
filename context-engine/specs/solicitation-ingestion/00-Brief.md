# Solicitation Ingestion — Strategic Brief

## 1. Strategic Intent

**go**

**Goal:** Let a user enter a solicitation (federal SAM.gov URL, or state/local URL) and have Vision create a `solicitations` row backed by a `cases` row, auto-fetching metadata + documents for federal sources, and accepting manual title + document upload for state/local sources.

**Success Verdict:**

- [ ] User pastes a SAM.gov opportunity URL, selects source type `federal` (default) → a `solicitations` row + backing `cases` row are created immediately, and a background job fetches full metadata (agency, NAICS, PSC, set-aside, POC, deadline, place of performance) and downloads all `resourceLinks` attachments into the evidence store
- [ ] User can watch fetch progress via job polling (existing `GET /api/jobs/{job_id}` pattern) and see the solicitation's `ingestion_status` move `pending → fetching → complete` (or `failed`/`partial` if SAM.gov fails or omits documents)
- [ ] User selects source type `state` or `local`, provides URL + title, uploads one or more documents → `solicitations` row + `cases` row created synchronously, documents ingested via the existing `ingest_file` pipeline; no SAM.gov calls attempted
- [ ] A solicitation with missing/failed document fetch is flagged (`has_missing_docs = true`) and visible in a list view without blocking on the flag
- [ ] All solicitation documents are visible/searchable via the existing `documents`/`sections`/`blocks` evidence store scoped to the backing `case_id` — no duplicate document engine
- [ ] `GET /api/solicitations` and `GET /api/solicitations/{id}` return the solicitation with its nested `case_id`-derived documents

## 2. The Claims

| Claim ID | Description                                                                                                                                                                                                                                                                      | Verdict (Test)                                                                                                           |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| CLAIM-01 | `solicitations` table exists with `SERIAL id` + `external_id UUID`, FK to `cases(id)`, `source_type` enum (`federal`/`state`/`local`), `ingestion_status` enum                                                                                                 | Migration applies cleanly on top of v16; table visible in`\d solicitations`                                            |
| CLAIM-02 | `POST /api/solicitations` with `{source_type: "federal", url, title}` creates `cases` row + `solicitations` row synchronously, enqueues a `sam_fetch` job, returns `{solicitation, job_id}`                                                                          | Call endpoint → 201 with solicitation + job_id; row exists in DB immediately                                            |
| CLAIM-03 | `POST /api/solicitations` with `{source_type: "state"\|"local", url, title}` creates `cases` + `solicitations` synchronously with no job enqueued; documents attached via existing `POST /api/cases/{case_id}/ingest`                                                   | Call endpoint → 201; then upload doc via existing ingest endpoint → document appears under case                        |
| CLAIM-04 | New`sam_fetch` job type: worker extracts `noticeId` from the stored URL, calls SAM.gov v2 opportunities API (`noticeid=` param), upserts metadata onto the `solicitations` row, downloads each `resourceLinks` URL into MinIO, then calls `ingest_file` per document | Enqueue job manually → solicitation row populated with agency/NAICS/PSC/set-aside/deadline; documents appear under case |
| CLAIM-05 | If SAM.gov returns zero`resourceLinks` or a download fails, `solicitations.has_missing_docs = true` and job still completes (not failed)                                                                                                                                     | Simulate empty`resourceLinks` → job status `complete`, `has_missing_docs = true`                                  |
| CLAIM-06 | If the SAM.gov API call itself fails (bad URL, invalid noticeId, API error), job is marked`failed` and `solicitations.ingestion_status = 'failed'` with error surfaced                                                                                                       | Call with bad URL → job`failed`; solicitation shows `ingestion_status = 'failed'`                                   |
| CLAIM-07 | `GET /api/solicitations` lists all solicitations with filters by `source_type` and `ingestion_status`                                                                                                                                                                      | Call endpoint → paginated list, filterable                                                                              |
| CLAIM-08 | `GET /api/solicitations/{id}` returns the solicitation plus its case's documents (reuse `CaseManager._list_documents`)                                                                                                                                                       | Call endpoint → solicitation dict includes`documents: [...]`                                                          |
| CLAIM-09 | `solicitations.notice_id` has a unique constraint (federal only); resubmitting the same `noticeId` via `POST /api/solicitations` returns 409 Conflict instead of creating a duplicate case                                                                                 | Submit same SAM.gov URL twice → second call returns 409 with the existing solicitation's`external_id`                 |

## 3. The Elements

| Element                                                                                                             | Purpose                                                                                                      | Belongs To Claim     |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | -------------------- |
| `solicitations` table (migration `007_solicitations.sql`, schema v17)                                           | Core domain entity                                                                                           | CLAIM-01             |
| `SolicitationManager` (`backend/core/solicitation.py`)                                                          | CRUD: create, get (with documents), list, update                                                             | CLAIM-02, 03, 07, 08 |
| `backend/ingestion/sam_client.py`                                                                                 | Net-new: extract`noticeId` from URL, call SAM.gov v2 single-notice search, parse `resourceLinks`         | CLAIM-04, 05, 06     |
| `jobs.job_type` CHECK extended with `'sam_fetch'`                                                               | New async job type                                                                                           | CLAIM-04             |
| `process_sam_fetch_job()` in `backend/ingestion/worker.py`                                                      | Worker handler: calls`sam_client`, downloads attachments via `storage.py`, calls `ingest_file` per doc | CLAIM-04, 05, 06     |
| `documents.source` CHECK extended with `'sam_gov'`                                                              | Tag SAM-fetched docs distinctly from user uploads                                                            | CLAIM-04             |
| `POST /api/solicitations`, `GET /api/solicitations`, `GET /api/solicitations/{id}` in `backend/api/main.py` | REST surface                                                                                                 | CLAIM-02, 03, 07, 08 |

## 4. The Evidence

**Tech Stack:** Python 3.12 / FastAPI / PostgreSQL (raw SQL, no ORM) / MinIO for blob storage / existing `SKIP LOCKED` job queue.

**External APIs:** SAM.gov Opportunities API v2 — `GET https://api.sam.gov/opportunities/v2/search?noticeid={id}&api_key={key}`. Response includes `title`, `fullParentPathName` (agency path), `naicsCode`, `classificationCode` (PSC), `typeOfSetAside`/`typeOfSetAsideDescription`, `pointOfContact[]`, `placeOfPerformance`, `responseDeadLine`, and `resourceLinks[]` (direct attachment URLs, authenticated via `api_key` query param appended per link). Reference: https://open.gsa.gov/api/get-opportunities-public-api/

**Sample Data:** None captured yet — fixtures phase (03) must pull one real SAM.gov notice response (sanitized) and one `resourceLinks` download to serve as `fixtures.json`. Commandment III blocks coding the `sam_client` parser without this.

## 5. Existing Infrastructure

### Related Existing Tables

| Table         | Relationship                                                                                                   | Location                         |
| ------------- | -------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| `cases`     | `solicitations.case_id → cases.id`; case created with `case_type='rfp_response'` as the backing container | `schemas/001_core.sql:49-83`   |
| `documents` | Unchanged; solicitation docs are ordinary rows keyed by`case_id`, `source` gets new `'sam_gov'` value    | `schemas/001_core.sql:159-181` |
| `jobs`      | Reused as-is;`job_type` CHECK extended with `'sam_fetch'`                                                  | `schemas/001_core.sql:437-458` |

### Related Existing Endpoints

| Endpoint                                          | What It Does                   | Reuse or Extend?                                                                                                                       |
| ------------------------------------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| `POST /api/cases/{case_id}/ingest`              | Upload + enqueue`ingest` job | **Reuse as-is** — state/local doc uploads and SAM-fetched attachments both funnel through `ingest_file`, not a duplicate path |
| `GET /api/jobs/{job_id}` / `GET /api/jobs`    | Poll job status                | **Reuse as-is** — dashboard polls `sam_fetch` jobs the same way                                                               |
| `POST /api/cases` (`CaseManager.create_case`) | Create backing case            | **Reuse internally** — called by `SolicitationManager.create()`, not exposed as a separate user step                          |

### Related Existing Components

| Component                                                                                          | Purpose                                                                      | Location                                     | Action                                                                                                                                                                                                                                                                       |
| -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ingestion/jobs.py` (`enqueue`, `claim_next`, `mark_complete/failed`, `update_progress`) | Postgres`SKIP LOCKED` queue                                                | `backend/ingestion/jobs.py`                | **Reuse as-is**                                                                                                                                                                                                                                                        |
| `ingestion/worker.py` main loop                                                                  | Dispatches by`job_type`                                                    | `backend/ingestion/worker.py:404-437`      | **Extend** — add `elif job["job_type"] == "sam_fetch"` branch                                                                                                                                                                                                       |
| `ingestion/storage.py` (`upload_file`, `download_file`)                                      | MinIO blob storage                                                           | `backend/ingestion/storage.py`             | **Reuse as-is** — SAM attachment bytes uploaded here before `ingest_file`                                                                                                                                                                                           |
| `ingestion/dispatcher.py` `ingest_file()`                                                      | OCR/chunk/embed pipeline                                                     | `backend/ingestion/dispatcher.py:1091`     | **Reuse as-is**                                                                                                                                                                                                                                                        |
| `chat/external_tools.py` `search_sam_opportunities` / `get_sam_opportunity_detail`           | Existing SAM.gov chat-agent tools (keyword search + HTML description scrape) | `backend/chat/external_tools.py:1199-1385` | **Not reused for this flow** — these are agent-facing search tools with no single-notice structured fetch or `resourceLinks` support; net-new `sam_client.py` is required (see Element table). Existing `_SAM_API_KEY` env var (`SAM_GOV_API_KEY`) is reused. |
| `core/case.py` `CaseManager`                                                                   | Case CRUD                                                                    | `backend/core/case.py`                     | **Reuse internally** — `SolicitationManager` composes it                                                                                                                                                                                                            |

### Known Constraints

- [X] Must use `SERIAL id` + `external_id UUID DEFAULT gen_random_uuid()` per `database-design.md`, not `UUID PRIMARY KEY`
- [X] No ORM — raw SQL via `psycopg2`, numbered migration file (`007_solicitations.sql`, schema_migrations version 17)
- [X] Federal fetch is async (job queue); state/local intake is fully synchronous (no job for metadata — only doc ingest jobs)
- [X] Must not duplicate the documents/sections/blocks/OCR engine — solicitation documents are ordinary `documents` rows under the backing case
- [X] `SAM_GOV_API_KEY` env var already exists and is reused; no new secret configuration needed

## 6. Pre-Mortem

**What could break?**

- SAM.gov v2 API shape drift (undocumented nulls, `resourceLinks: null` vs `[]`) — mitigation: defensive `.get()` parsing, `has_missing_docs` flag rather than hard failure, verified against real fixture in phase 3
- `resourceLinks` URLs require `api_key` appended as query param per-link, not just on the search call — must confirm during fixture capture, not assumed
- Large attachment sets (10+ PDFs) could make the `sam_fetch` job slow — mitigation: reuse existing `update_progress` pattern already proven for ZIP extraction in `worker.py`
- Duplicate `noticeId` re-submission — mitigation: `solicitations.notice_id` unique constraint (CLAIM-09); `POST /api/solicitations` checks for an existing row before creating a new `cases`/`solicitations` pair and returns 409 if found
- Rate limiting on SAM.gov API (public tier has daily caps) — mitigation: out of scope for v1, no retry/backoff strategy beyond existing `attempts` column on `jobs`

**What assumptions are we making?**

- One SAM.gov URL maps to exactly one `noticeId` extractable via existing regex pattern already used in `get_sam_opportunity_detail`
- `case_type = 'rfp_response'` (already in the `cases` CHECK constraint) is the correct backing case type for all solicitations regardless of source_type
- State/local sources never have a programmatic metadata API — title/agency/etc. are either manually entered or extracted later by a separate AI-triage module (out of scope here)

**What do we NOT know yet?**

- Exact SAM.gov v2 JSON field names for `pointOfContact` and `placeOfPerformance` sub-objects — must confirm via a live fixture capture before writing `01-schema.sql` column types
- Whether `resourceLinks` entries include a filename/label or only a bare URL (affects how `document_name` is derived in `ingest_file` calls)

## 7. Out of Scope (Explicit)

- AI triage/extraction of solicitation content (Module 2 — separate spec)
- Partner matching, email queueing (Module 3 — separate spec)
- Manual "flag and go get documents yourself" UI flow for missing federal docs — this Brief only sets `has_missing_docs`; the manual remediation UI is deferred
- Legacy `cases.solicitation JSONB` / `cases.profile_id` columns — untouched, will be deprecated in a later cleanup pass, not migrated here

## 8. Approval Gate

**Status:** [ ] DRAFT  [x] APPROVED

**Approved By:** ianbrucey

**Date:** 2026-07-21

---

> ⚠️ **EXIT CONDITION:** This Brief is not approved until all Claims have defined Verdicts and the Tech Stack is explicit. No ambiguity allowed.
