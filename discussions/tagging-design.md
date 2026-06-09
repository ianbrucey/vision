# Document Tagging — Design Document

> **Status:** Decided, deferred. Return to this when tooling is ready.
> **Date:** 2026-06-09
> **Source transcript:** `discussions/tagging.md`

---

## 1. Problem

Vision ingests diverse documents — medical records, tax returns, resumes, contracts, capability statements, correspondence. Today, every document lands in the evidence store undifferentiated. The system has no way to answer: *"Find all documents relevant to building a company profile"* or *"Show me every tax-related document in this case."*

The user needs to:
- Classify documents by type and subject
- Filter the evidence store by those classifications
- Have the agent reason about which documents are relevant to a given task (company profile generation, tax analysis, RFP response)
- Do this **without** creating separate database tables or ingestion pipelines per feature

The through-line: **A "Company Profile" page is not a database table. It is a logical view over tagged documents + an agentic synthesis step.**

---

## 2. Design Decisions

### 2.1 Tag Granularity: Document-Level Only

Tags apply to entire documents, not individual sections or blocks.

**Rationale:**
- A 300-page medical record has one identity — it's a medical record
- If a specific section inside it becomes independently relevant, the agent cites it by block — but the *tag* describes what the document IS
- Section-level tagging on large documents would be resource-prohibitive and adds complexity with marginal ROI

**Open sub-question:** For large documents, how does the auto-tagger decide? Answer: it inspects the first 5-10 pages (via section outline + first N blocks) — sufficient to classify the document without scanning all 300 pages.

### 2.2 Tag Storage: TBD (Junction Table vs. Array Column)

Two approaches, deferred for implementation:

| | `tags TEXT[]` column on documents | Normalized `tags` + `document_tags` tables |
|---|---|---|
| Complexity | One column, one GIN index | Two tables, join queries |
| Tag metadata | None — just strings | Source (user/agent), confidence score, timestamp per assignment |
| User + agent coexistence | Agent could overwrite user tags silently | Each assignment is a separate row with provenance |
| Rename/merge tags | Update every document row | Update one tag row |
| Migration path | Array → junction table is a migration | Junction table is the end state |

**Default recommendation:** Junction table (normalized, auditable). But array column is acceptable as an MVP that can be migrated later.

### 2.3 Auto-Tagging: Post-Ingest LLM Subagent

Tags are generated asynchronously after ingestion completes. The subagent sees:

- The section outline (table of contents — structural, zero-cost)
- First ~10 pages of block text (representative sample)
- The document name

The subagent returns:

- `document_type` — constrained enum: `medical_record`, `tax_return`, `contract`, `resume`, `capability_statement`, `correspondence`, `pleading`, `transcript`, `spreadsheet`, `other`
- `tags` — 3-8 freeform strings relevant to the case domain
- `confidence` — 0.0-1.0 per tag

This fires as a new job type (`enrich` or `tag`), enqueued immediately after `ingest` completes:

```
ingest complete → enqueue job(type='enrich', document_id=X)
→ worker claims → reads first N blocks → calls LLM → writes tags
```

Keeping it async means:
- Upload response is not blocked
- LLM failures don't lose the document (it's already ingested)
- It's retryable

### 2.4 The `document_type` Column Already Exists

The schema has `document_type TEXT` on `documents` — it exists but is **never populated by any code path**. The auto-tagger will populate it. This gives us:

- **Coarse classification** (`document_type`) for routing and broad filtering
- **Fine-grained tags** for discovery and agent context

### 2.5 Feature Contexts: Tag-to-Task Registry

A configuration file maps "feature contexts" to the tags they require. Example:

```json
{
  "company_profile": {
    "label": "Company Profile Generation",
    "required_tags": ["resume", "capability-statement", "tax-document"],
    "helpful_tags": ["contract", "correspondence"],
    "description": "Synthesize corporate background and capabilities for RFPs."
  },
  "tax_matter": {
    "label": "Tax Analysis",
    "required_tags": ["tax-return", "w2", "1099", "irs-notice"],
    "description": "Analyze income tax liabilities and audit notices."
  },
  "medical_review": {
    "label": "Medical Record Review",
    "required_tags": ["medical-record", "lab-result", "imaging-report"],
    "description": "Chronological review of medical records for case analysis."
  }
}
```

This registry is fed into the agent's system prompt so it knows: *"I'm in the Company Profile context → I should search for documents tagged with resume, capability-statement, tax-document."*

**Storage:** A JSON file in the codebase (version-controlled, simple). Can be promoted to a database table later if runtime mutability is needed.

### 2.6 Tag-Aware Search

The query layer needs a metadata-filtered search function that the agent can call:

```
search_documents(case_id, tags: ["resume", "capability-statement"], query: "past performance")
→ returns blocks from documents matching those tags, ranked by relevance
```

This is the bridge between "tagged documents" and "agent can find the right evidence."

---

## 3. Architecture

### 3.1 New/Modified Components

```
┌─────────────────────────────────────────────────┐
│                 INGESTION FLOW                    │
│                                                   │
│  Upload → MinIO → Job:ingest → Normalize → Done  │
│                                          │        │
│                                          ▼        │
│                                    Job:enrich     │
│                                          │        │
│                              ┌───────────▼──────┐ │
│                              │  Tagging Agent    │ │
│                              │  - Reads outline  │ │
│                              │  - Reads first N  │ │
│                              │    blocks          │ │
│                              │  - Returns tags   │ │
│                              └───────────┬──────┘ │
│                                          │        │
│                                          ▼        │
│                              Write document_type  │
│                              + tags to DB         │
└─────────────────────────────────────────────────┘
```

### 3.2 Schema Changes

**New tables (if junction table approach):**

```sql
-- Tag definitions (shared across cases)
CREATE TABLE tags (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    color       TEXT,  -- hex color for UI
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Which tags apply to which documents
CREATE TABLE document_tags (
    id          SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    tag_id      INTEGER REFERENCES tags(id) ON DELETE CASCADE NOT NULL,
    source      TEXT NOT NULL CHECK (source IN ('user', 'agent')),
    confidence  REAL CHECK (confidence >= 0 AND confidence <= 1),
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (document_id, tag_id, source)
);
```

**New columns on `documents` (already exists — just start populating it):**
- `document_type TEXT` — populated by auto-tagger, not nullable after enrichment

**New job type:**
- `job_type` enum extended with `'enrich'` (or `'tag'`)

**New file:**
- `context-engine/tag-registry.json` — the feature context → tags mapping

### 3.3 Code Changes

| File | Change |
|---|---|
| `backend/schemas/001_core.sql` | Add `tags`, `document_tags` tables; extend `jobs.job_type` CHECK |
| `backend/ingestion/dispatcher.py` | After `ingest_file()` returns, enqueue an `enrich` job |
| `backend/ingestion/enricher.py` | **New file** — reads first N blocks, calls LLM, writes tags |
| `backend/ingestion/worker.py` | Handle `job_type = 'enrich'` |
| `backend/core/db.py` | Add `insert_tag()`, `assign_document_tag()`, `get_documents_by_tags()` |
| `context-engine/tag-registry.json` | **New file** — feature context definitions |
| `frontend/` | Tag display, tag filter UI, manual tag assignment |

---

## 4. Implementation Sequence

Following **Backend-Out Sequencing** (DB → API → UI):

| Ticket | Layer | What | Depends On |
|---|---|---|---|
| T1 | DB | Add `tags` + `document_tags` tables; extend `jobs.job_type` | — |
| T2 | DB | Add insert/query helpers in `core/db.py` | T1 |
| T3 | Ingestion | Enqueue `enrich` job after successful ingest | T1 |
| T4 | Ingestion | `enricher.py` — LLM subagent for auto-tagging | T2, T3 |
| T5 | Worker | Handle `enrich` job type in worker loop | T4 |
| T6 | API | Tag-aware search endpoint | T2 |
| T7 | Config | `tag-registry.json` + load into agent system prompt | — |
| T8 | Frontend | Tag display on document list, tag filter UI | T6 |
| T9 | Frontend | Manual tag add/remove | T6 |
| T10 | Frontend | Feature context pages (Company Profile, etc.) that use tag registry | T7, T6 |

---

## 5. Open Questions (Deferred)

1. **Junction table vs. array column** — decide at T1 implementation time
2. **Which LLM for auto-tagging?** — Needs to be fast and cheap (Haiku or Flash). The task is classification, not reasoning.
3. **Tag namespace** — global across all cases, or scoped per case? Leaning global (tags are reusable descriptors), but scoped avoids tag pollution across unrelated matters.
4. **Re-tagging** — if a user corrects a tag, does the agent re-tag? Probably not — agent tags are "suggestions" and user tags are "authoritative."
5. **Tag registry as file vs. DB** — start with file; promote to DB if runtime configuration becomes necessary.

---

## 6. References

- [discussions/tagging.md](tagging.md) — Raw design transcript
- [backend/ingestion/dispatcher.py](../backend/ingestion/dispatcher.py) — Current ingestion pipeline
- [backend/schemas/001_core.sql](../backend/schemas/001_core.sql) — Current schema
- [context-engine/global-context.md](../context-engine/global-context.md) — System architecture and design principles
