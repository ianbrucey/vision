# Vision Database — External Agent Quick Reference

Connect locally. No password. Read what you need.

## Connection

```
Host:     127.0.0.1
Port:     5432
Database: vision
User:     ianbruce
Password: (none)
```

```python
import psycopg2, psycopg2.extras
conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="vision", user="ianbruce")
conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SET search_path TO vision, agent_work, public")
```

```bash
psql -h 127.0.0.1 -p 5432 -d vision -U ianbruce
```

## How to Understand a Matter

A "matter" is a row in `cases`. Everything else hangs off it. To orient yourself in a case:

```
1. SELECT * FROM cases WHERE id = <n>          — what kind of matter is this?
2. SELECT * FROM documents WHERE case_id = <n> — what evidence/files do we have?
3. SELECT * FROM drafts WHERE case_id = <n>    — what's been written so far?
4. SELECT * FROM tasks WHERE case_id = <n>     — what needs doing?
5. SELECT * FROM strategies WHERE case_id = <n> — any legal strategy trees?
6. SELECT * FROM company_profiles cp JOIN cases c ON c.profile_id = cp.id WHERE c.id = <n> — who's the client?
```

The case's `case_type` column signals what kind of matter it is: `rfp_response` means a GovCon solicitation, `civil_litigation` means a lawsuit, `other` is a catch-all (used for system cases like FAR and Knowledge Base). The `profile_id` links to a `company_profiles` row if a GovCon firm is attached.

## Tables — What They Are and When to Use Them

### `cases` — Every matter, solicitation, or reference corpus
The top-level container. Every document, draft, task, and strategy belongs to a case. The `name` is human-readable. Look up by name since IDs drift: `SELECT id FROM cases WHERE name ILIKE '%keyword%'`.

### `documents` — Ingested files (PDFs, DOCX, HTML, images, audio)
Raw source material. Each document is decomposed into `sections` (its table of contents) and `blocks` (individual paragraphs). The `document_type` column signals what kind of file it is (`medical_record`, `complaint`, `contract`, `capability_statement`, `other`). The `ocr_status` tells you whether the text has been extracted (`pending`, `processing`, `complete`, `failed`).

### `sections` — The structural hierarchy inside a document
Think of this as the document's outline. Sections form a tree via `parent_id`. `heading_level` is 1 for top-level, 2 for sub-sections, etc. `search_text` is a concatenation of title + all child block text, used for full-text search and embedding. `embedding` is a 1024-dim pgvector for semantic search. `metadata` is JSONB — for FAR documents it holds `far_number`; for other documents it can hold arbitrary annotations.

### `blocks` — Individual paragraphs, the atomic unit of text
Every paragraph, list item, table cell, or heading from the source document. `block_type` is usually `Text`. `text_content` is the plain text. Full-text search runs against this column. Every block belongs to a section via `section_id`.

### `drafts` — Workspace items, knowledge base entries, and written artifacts
This table serves double duty. In a case context (folder = `freestyle`, `research`, `artifacts`), drafts are the workspace items visible in the file explorer. In the Knowledge Base case (case 14), they're tagged, searchable knowledge entries. `content` is JSONB — for `file_type = 'markdown'` it's `[{"markdown": "..."}]`; for `structured_draft` it's a block array. `metadata` holds tags, knowledge_type, and source URLs.

### `company_profiles` — GovCon firm identity and qualifications
One row per company. `content` is a JSONB object holding everything a proposal needs: `company_name`, `cage_code`, `uei`, `naics_codes`, `certifications`, `past_performance`, `key_personnel`, `contact`. The `field_status` sub-object tracks whether each field was `agent_filled`, `uncertain`, or `needs_input`. A case links to its profile via `cases.profile_id`.

### `strategies` — Legal claim trees with adversarial dialectics
Each strategy is a root node in a tree of propositions (stored in the `propositions` table via `strategy_id`). `strategy_type` signals the kind of analysis. `posture` is `offensive` or `defensive`. Propositions form parent-child chains representing legal reasoning.

### `tasks` — Action items and follow-ups
Scoped to a case. `title` is the task name, `status` tracks progress (`pending`, `in_progress`, `completed`), `priority` is `low`/`medium`/`high`/`urgent`, `deadline` is optional. Agents create tasks during analysis to track what needs follow-up.

### `chat_sessions` — Agent conversation transcripts
One row per conversation with an agent. `status` is `active` or `archived`. Messages are in `chat_messages` keyed by `session_id`. The `sdk_session_id` links to the SDK's internal session store.

### `correspondence_threads` / `correspondence_items` — Logged communications
Tracks emails, calls, and messages with parties. Threads group related items. Items carry `direction` (inbound/outbound), `parties` involved, and attached `documents`.

### `embedding_cache` — Mistral embed deduplication
Maps `content_hash` (SHA-256 of section text) to `embedding` (1024-dim vector). When re-ingesting or re-embedding, identical text is cached instead of re-embedding, saving API calls.

## Key Cases

| ID | Name | What's in it |
|---|---|---|
| 7 | digitization | RFI from Dept of War — EDMP/CEDMS Modernization. 1 solicitation document, 22 sections, 84 blocks. Company profile #1 attached. Pipeline artifacts (TRIAGE, SCOPE, COMPLIANCE, SUBMISSION, BRIEF, DECISION, RESPONSE, QUALITY) in workspace. |
| 13 | FAR — Federal Acquisition Regulation | Full FAR corpus (FAC 2026-01). 51 documents (one per Part), 3,815 sections (Subpart→Section→Subsection hierarchy), 30,351 paragraphs, all embedded via Mistral. |
| 14 | Knowledge Base — Cross-Case Reference | Agent knowledge store. Tagged markdown entries created via `create_knowledge_entry`. Cross-case — not scoped to any single matter. |

Case IDs drift when cases are deleted and recreated. Always resolve by name:
```sql
SELECT id FROM cases WHERE name ILIKE '%keyword%';
```

## Useful Queries

### Orient yourself in a case
```sql
-- What kind of matter?
SELECT id, name, case_type, profile_id, created_at FROM cases WHERE id = 7;

-- What documents do we have?
SELECT id, name, document_type, page_count, ocr_status FROM documents WHERE case_id = 7;

-- What's been written?
SELECT id, name, file_type, folder, status FROM drafts WHERE case_id = 7;

-- Who's the client?
SELECT cp.name, cp.content->>'company_name', cp.content->>'cage_code', cp.content->>'uei'
FROM company_profiles cp JOIN cases c ON c.profile_id = cp.id WHERE c.id = 7;
```

### Search within a case
```sql
-- Keyword search across all documents in a case
SELECT b.text_content, s.title, d.name AS doc_name
FROM blocks b JOIN sections s ON s.id = b.section_id
JOIN documents d ON d.id = b.document_id
WHERE d.case_id = 7
  AND to_tsvector('english', b.text_content) @@ plainto_tsquery('english', 'cloud platform')
ORDER BY ts_rank(to_tsvector('english', b.text_content), plainto_tsquery('english', 'cloud platform')) DESC
LIMIT 20;
```

### Look up a FAR citation
```sql
SELECT s.title, s.search_text
FROM sections s JOIN documents d ON d.id = s.document_id
JOIN cases c ON c.id = d.case_id
WHERE c.name = 'FAR — Federal Acquisition Regulation'
  AND s.metadata->>'far_number' = '15.101';
```

### Search the Knowledge Base
```sql
SELECT d.id, d.name, d.metadata->>'knowledge_type' AS type,
       d.metadata->>'tags' AS tags, d.content->0->>'markdown' AS body
FROM drafts d WHERE d.case_id = 14
  AND d.metadata->>'tags' ILIKE '%proposal%'
ORDER BY d.updated_at DESC;
```

### Read a workspace item's content
```sql
SELECT id, name, file_type, folder, content, metadata FROM drafts WHERE id = 38;
```
For markdown items the body is `content[0]->>'markdown'`. For structured drafts `content` is the block array directly.

## Content Envelope Formats

**Markdown (`drafts.content` when `file_type = 'markdown'`):**
```json
[{"markdown": "# Title\n\nBody text..."}]
```

**Structured draft (`drafts.content` when `file_type = 'structured_draft'`):**
```json
[{"id": "b1", "type": "section_heading", "content": "TITLE"}, {"id": "b2", "type": "numbered_paragraph", "content": "1. Text."}]
```

**Company profile (`company_profiles.content`):**
```json
{
  "company_name": "...", "cage_code": "...", "uei": "...",
  "naics_codes": ["541511"], "certifications": ["8(a)"],
  "past_performance": [{"client": "...", "contract_value": "..."}],
  "key_personnel": [{"name": "...", "title": "..."}],
  "contact": {"city": "...", "state": "...", "email": "..."},
  "field_status": {"company_name": "agent_filled", "cage_code": "needs_input"}
}
```

## Constraints

- `documents.source`: `user_upload`, `discovery`, `data_lab`, `email`, `portal`, `api`, `other`
- `drafts.document_type`: `letter`, `pleading`, `contract`, `memo`, `capability_statement`, `other`
- `drafts.folder`: `freestyle`, `research`, `artifacts`
- `drafts.file_type`: `markdown`, `structured_draft`, `html`, `json_view`
- Embeddings: Mistral `mistral-embed`, 1024-dim. Cosine distance via `sections.embedding <=> query_vector`.
- All write tools run with `autocommit = True`. No explicit COMMIT needed for agent-initiated writes.
- Schemas: `backend/schemas/001_core.sql` (core tables), `002_strategy.sql` (strategies), `003_chat.sql` (chat), `004_correspondence.sql` (correspondence).
