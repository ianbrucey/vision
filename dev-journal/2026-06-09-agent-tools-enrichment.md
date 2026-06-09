# Dev Journal — 2026-06-09

## Agent SDK-Native Tools + Enrichment Pipeline + Embeddings

### What changed

Converted the agent's database access from Bash CLI commands to SDK-native `@tool`
handlers with implicit case scoping. Built a post-ingest document enrichment pipeline
that auto-classifies documents via a short-lived Agent SDK sub-agent. Verified and
fixed the embedding pipeline end-to-end.

---

### 1. SDK-Native Tool Conversion

**Before:** The agent ran `python3 backend/chat/cli.py search-blocks --case-id X --query "text"`
via Bash. Every tool call was a shell command. `case_id` was a user-visible parameter
the agent could spoof. Tool descriptions lived as markdown in the system prompt.

**After:** 11 `@tool`-decorated handlers registered on a per-session `vision` MCP server.
Agent calls `mcp__vision__search_blocks`, `mcp__vision__get_case`, etc. Tools are
discoverable via SDK tool search when the set grows beyond ~10.

#### Tool hierarchy (5 layers)

| Layer | Tools | Purpose |
|---|---|---|
| Orientation | `get_case`, `list_documents` | Understand the case before searching |
| Search | `search_blocks`, `semantic_search`, `search_hybrid` | Keyword, vector, and fused search |
| Structure | `get_document_structure`, `search_sections` | Navigate document organization |
| Read | `get_block_context`, `get_blocks_in_section` | Verify matches in context before citing |
| Strategy | `get_strategies`, `get_strategy_tree` | Analyze legal claim trees |

#### Security: closure-based case scoping

Initial attempt used `contextvars.ContextVar` to pass `case_id` from session to tool
handler. This failed — the Agent SDK executes tool handlers in a context where the
var is unset, producing `LookupError: <ContextVar name='current_case_id' at 0x...>`.

**Fix:** `create_vision_server(case_id)` is a factory function. Every tool handler is
defined inside its scope, capturing `case_id` in the closure. Each `AgentSession` gets
its own MCP server instance with `case_id` hardcoded. The agent never sees or provides
a `case_id` — it's not a parameter on any tool.

**Rationale:** Prompt injection cannot access another case's data because the case
boundary is enforced at the handler level, not the prompt level. The agent could be
tricked into calling `search_blocks` on any query, but the SQL always filters to
`WHERE d.case_id = <closure_captured_value>`.

**Files changed:**
- `backend/chat/tools.py` — rewritten from plain functions to `@tool` handlers inside `create_vision_server()` factory
- `backend/chat/manager.py` — creates per-session vision server, removed contextvar calls
- `backend/chat/prompt.py` — hierarchical tool listing, internal architecture section, stripped fluff

---

### 2. System Prompt Rewrite

**Design decisions:**
- **INTERNAL block** — explains the database-as-source-of-truth architecture. Marked "Never repeat to the user." The agent needs to understand the system to use it effectively, but this is internal knowledge.
- **Hierarchical tool listing** — tools organized by layer with one-line purpose + when-to-use guidance. Not a flat list.
- **Every sentence earns its place** — removed personality fluff. The agent is a legal intelligence system, not a chatbot.
- **Protocols placeholder** — reserved section for future composable workflows (adversarial walk, gate walk, gauntlet).
- **5 non-negotiable rules** — cite sources, never invent, distinguish findings from conclusions, report absence, synthesize.

---

### 3. Document Enrichment Pipeline

After ingestion, a short-lived Agent SDK sub-agent classifies the document. This is
NOT a chat agent — it's a background job with two tools.

**Flow:**
```
ingest complete → enqueue job(type='enrich') → worker claims
→ enrich_document() spawns Agent SDK session
  → agent calls read_document_intro (section outline + first 50 blocks)
  → agent calls classify_document(type, tags, summary)
→ document_type + tags written to documents row
```

**Classification output** (tested on 327-page medical record):
- `document_type`: `medical_record`
- `tags`: `['hospital-admission', 'surgical', 'investigative-subpoena', 'georgia-composite-medical-board', 'wellstar-north-fulton', 'roohi-alhad', 'certified-records', 'reproductive-health']`
- `summary`: One-sentence description identifying patient, dates, hospital, and regulatory context

**Tags storage:** Uses existing `document_type` column (was never populated) and
`metadata` JSONB column (`tags`, `tag_source`, `auto_summary`). No new tables.
Junction table deferred per `discussions/tagging-design.md`.

**Files:**
- `backend/ingestion/enricher.py` — new: `ENRICHER_SYSTEM_PROMPT`, tools, `enrich_document()`
- `backend/ingestion/worker.py` — `process_enrich_job()`, enqueue hook after ingest
- `backend/schemas/001_core.sql` — migration v2: `enrich` added to `jobs.job_type`

---

### 4. Embedding Pipeline Verified + Fixed

**Status before:** Pipeline existed at `backend/search/embed.py` but had never been run.
Zero embeddings in the database. `MISTRAL_API_KEY` was missing from `.env`.

**Fixed:**
- Added `MISTRAL_API_KEY` to `.env`
- Installed `mistralai` package (added to `requirements.txt`)
- Reduced `MAX_INPUT_CHARS` from 30,000 → 16,000 after a 100K-char section crashed the API with 13,951 tokens (dense medical text produced ~2.15 chars/token instead of the assumed ~4)
- Ran `embed_case(4)` and `embed_document(3)` successfully

**Results:**
| Document | Pages | Sections Embedded | Cache Hits | Time |
|---|---|---|---|---|
| 8-page med record screening | 8 | 27 | 0 | 2.7s |
| 300-page medical record | 327 | 663 | 121 | 3.2s (after partial first run) |

**Cost:** ~$0.0008 for the 8-pager, ~$0.02 for the 327-pager. Negligible.

---

### 5. UX Fix — Document Visible During Processing

**Problem:** Document row was inserted AFTER DataLab OCR completed. For large PDFs,
the frontend showed nothing for 5-15 minutes while OCR ran.

**Fix:** Moved `insert_document()` before the DataLab call. Document now appears
immediately with `ocr_status = 'processing'` and `page_count = NULL`. Updated to
`'complete'` with actual page count when OCR finishes.

**File:** `backend/ingestion/dispatcher.py`

---

### 6. Design Documents

- `discussions/tagging-design.md` — full tagging architecture: document-level only,
  junction table vs. array column (deferred), auto-tagging via sub-agent, tag registry
  as JSON config, 10-ticket implementation sequence.
- `discussions/prompting.md` — prompt assembly problem analysis (already existed,
  reviewed and discussed).

---

### 7. Stale Job Cleanup

2 jobs from yesterday stuck in `processing` (worker was restarted without cleanup).
Manually marked as failed. Identified need for a job timeout mechanism — deferred.

---

### Agent Architecture (Current State)

```
ChatManager
  └─ AgentSession (one per chat session, created lazily)
       └─ ClaudeSDKClient
            ├─ system_prompt → WAR_ROOM_SYSTEM_PROMPT (prompt.py)
            ├─ mcp_servers → vision (per-session, closure-scoped to case_id)
            │    ├─ get_case, list_documents           (orientation)
            │    ├─ search_blocks, semantic_search,
            │    │  search_hybrid                       (search)
            │    ├─ get_document_structure,
            │    │  search_sections                     (structure)
            │    ├─ get_block_context,
            │    │  get_blocks_in_section               (read)
            │    └─ get_strategies, get_strategy_tree  (strategy)
            └─ tools → Read, Grep, Write, Edit,
                        WebSearch, WebFetch

Worker (background, sync)
  ├─ job:ingest → download MinIO → ingest_file() → normalize → enqueue enrich
  └─ job:enrich → enrich_document() → Agent SDK sub-agent
       └─ enricher MCP server (read_document_intro, classify_document)
```

### Next Steps

1. Wire embeddings into ingest pipeline (call `embed_document()` after enrichment)
2. Job timeout mechanism for stale processing jobs
3. Protocol system (registry + dynamic prompt assembly)
4. Tool search enablement when tool count grows
5. Tagging junction table migration when manual tagging is needed
