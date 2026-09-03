# Architectural Brief: Smart Ingestion & Direct Document Package Ingest

> **Domain:** Solicitation Ingestion & Intake Architecture  
> **Status:** Active / Production  
> **Last Updated:** 2026-09-03  
> **Target Files:**
> - Frontend: `frontend/src/app/solicitations/page.tsx`, `frontend/src/lib/api.ts`
> - Backend API: `backend/api/routes/solicitations.py`
> - Backend Worker: `backend/ingestion/worker.py`
> - Diagnostics & Ops: `backend/scripts/diagnose_triage.py`, `docs/sops/SOP-06-Triage-Pipeline-Failures-and-Recovery.md`

---

## 1. Executive Summary & Problem Statement

### The Bottleneck
Previously, federal solicitation ingestion relied entirely on server-side fetching from SAM.gov via `process_sam_fetch_job`. For solicitations with multiple large attachments (SOW, PWS, technical exhibits, wage determinations, drawings), SAM.gov API endpoints consistently triggered:
1. **Aggressive rate-limiting / 429 & 403 throttles**, causing attachment downloads to stall or fail.
2. **Missing documents flags (`has_missing_docs = True`)**, which historically blocked the automated transition into triage.
3. **Queue backlogs**, where a batch of 5–10 concurrent solicitations would exhaust worker throughput waiting on high-latency attachment streams.

### The Architectural Solution ("Smart Ingest")
Shift document transport from fragile server-to-SAM downloads to a client-assisted, high-throughput ingest pipeline:
- **SAM.gov API is used only for metadata**: Lightweight JSON query (title, agency, NAICS, set-aside, response deadline, description).
- **Documents are provided directly**: The user downloads the single `.zip` "Download All" package (or individual files) from SAM.gov and drops it into the intake form.
- **Multipart unpack & MinIO streaming**: The backend extracts zip archives safely in-memory/stream, uploads all files to MinIO, records document rows in PostgreSQL, and immediately initiates the triage pipeline.

---

## 2. Component Architecture & Changes

### A. Frontend Intake UI (`frontend/src/app/solicitations/page.tsx`)

1. **Collapsible Intake Card:**
   - Defaults to collapsed on page load to preserve viewport real estate for the solicitation queue.
   - Expandable/collapsible via clean toggle header with chevron indicator.
   - Automatically collapses and resets upon successful package submission.

2. **Clean Inputs & No Blocking Inline SAM Calls:**
   - Removed `onBlur` fetch and inline spinner that previously stalled the UI for 15–30 seconds.
   - **SAM.gov Opportunity URL / Notice ID (OPTIONAL):** User can paste a link without any blocking call occurring.
   - **Title (OPTIONAL):** Custom title can be supplied; otherwise derived from SAM in the background.
   - **Description (OPTIONAL):** Custom description can be supplied; otherwise auto-populated from SAM in the background.
   - **Solicitation Documents (REQUIRED):** Accepts `.zip`, `.pdf`, `.docx`, `.doc`, `.xlsx`, `.csv`, `.txt`, `.md`.

3. **In-Place Creation UX:**
   - On submission, the form clears and collapses, and the page refreshes in place.
   - The newly created row immediately appears with `ingestion_status = 'pending'`.
   - The existing 3-second polling hook tracks transitions through `fetching`, `complete`, and `solicitation_triage` in real time.

---

### B. Backend API Endpoint (`backend/api/routes/solicitations.py`)

**`POST /api/solicitations/ingest-package`**
- **Form Fields:** `files` (multipart, required), `url` (optional), `notice_id` (optional), `title` (optional), `description` (optional), `source_type` (optional, defaults to `"federal"`).
- **Execution Flow (Synchronous, <500ms):**
  1. Creates case and solicitation database records with `ingestion_status = 'pending'`.
  2. Stages raw uploaded files/zips directly to MinIO under `staging/{sol_id}/{uuid}_{filename}`.
  3. Enqueues a `smart_ingest` background job in the PostgreSQL `jobs` queue.
  4. Returns `{ solicitation, document_count, job_id }` immediately (`201 Created`).

---

### C. Worker Pipeline (`backend/ingestion/worker.py`)

**`process_smart_ingest_job`**
- Claims the `smart_ingest` job via transactional `SKIP LOCKED`.
- **Background SAM Enrichment:** If a SAM `notice_id` was derived or provided, queries `fetch_notice()` and `fetch_description()` in the background (preserving any custom title or description entered by the user).
- **Staged File Unpack:** Downloads staged files from MinIO, extracts `.zip` archives (filtering out macOS resource forks like `__MACOSX`, `._*`), and streams individual documents into permanent MinIO storage and PostgreSQL `documents` rows.
- **Cleanup & Transition:** Deletes staging files from MinIO, marks `ingestion_status = 'complete'`, and enqueues `solicitation_triage`.

---

## 3. Data Flow Diagram

```
User (Browser)
  │
  ├─ 1. [Optional] Enters SAM URL ────────► GET /api/solicitations/preview-sam
  │                                           │ (Fetches notice JSON only)
  │  ◄─ Populates Title, Agency, Deadline ────┘
  │
  ├─ 2. Drops Attachments (.ZIP / PDFs)
  │
  └─ 3. Clicks "Create & Start Triage" ───► POST /api/solicitations/ingest-package
                                              │
                                              ├─ Create Case & Solicitation
                                              ├─ Unpack Zip & Stream to MinIO
                                              ├─ Create `documents` rows
                                              └─ Enqueue job: `solicitation_triage`
                                                      │
                                                      ▼
                                              Worker Pool (SKIP LOCKED)
                                                      │
                                                      ▼
                                              5 Concurrent Extractors:
                                                - Scope of Work
                                                - Deliverables & Milestones
                                                - Evaluation Criteria
                                                - Technical Requirements
                                                - Submission Checklist
```

---

## 4. Operational & Diagnostic Tools

- **CLI Diagnostic Script:** `backend/scripts/diagnose_triage.py`
  - Inspects triage column statuses (`artifact_scope_of_work`, `artifact_technical_requirements`, etc.).
  - Inspects document extraction counts and error logs.
  - Supports `--retry` to re-enqueue failed or stalled triage runs without re-uploading documents.
- **Operational SOP:** `docs/sops/SOP-06-Triage-Pipeline-Failures-and-Recovery.md`
  - Defines escalation, triage recovery, and manual intake protocols for operations and BD teams.
