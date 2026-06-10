# Markdown Ingestion — Design

> **Status:** DRAFT
> **Opened:** 2026-06-10

## Why

The agent needs markdown files as searchable, citable context — not just as workspace scratch paper. A `.md` file uploaded to a case should go through the same ingestion pipeline as any other document: sections → blocks → embeddings → full-text index. The agent then finds it via `search_blocks`, `semantic_search`, `search_hybrid`, and cites it by block ID.

## Current Pipeline (for reference)

```
Upload → MinIO → enqueue job → worker picks up → ingest_file() dispatches by extension:

  .pdf / .jpg / .png  → DataLab API (Mistral OCR)  → _normalize_datalab_json()
  .docx               → python-docx                 → _normalize_docx()
  .csv                → csv parser                  → _normalize_csv()
  .xlsx               → openpyxl                    → _normalize_xlsx()
  .m4a / .mp3 / .wav  → transcription API           → _normalize_audio()
  
                      ↓
              sections + blocks + block_headings
                      ↓
              embeddings (bg, enricher)
                      ↓
              tsvector index (generated column)
```

The dispatcher is `ingest_file()` in `backend/ingestion/dispatcher.py:771`.

## What We Add — `.md` Path

```
  .md → markdown splitter → _normalize_markdown()
```

### The Splitter

A new function `_normalize_markdown(conn, md_path, document_id)` in `dispatcher.py`:

1. **Read** the raw markdown file
2. **Parse headings** — each `# Heading` creates a section:
   - `# Title` → heading_level=1
   - `## Section` → heading_level=2
   - `### Subsection` → heading_level=3
   - Sections inherit parent section IDs for hierarchy
3. **Split into blocks** — content between headings becomes blocks:
   - Paragraphs → `block_type: paragraph`
   - List items (`- ` or `1. `) → `block_type: list_item`
   - Code blocks (```) → `block_type: code_block`
   - Blockquotes (`>`) → `block_type: blockquote`
   - Horizontal rules (`---`) → `block_type: divider`
   - The heading text itself → `block_type: heading`
4. **Insert** sections and blocks using the existing `insert_section` / `insert_block` / `insert_block_heading` helpers
5. **Mark document** as `ocr_status: complete`, `ocr_provider: markdown-splitter`

### Block content format

Each block stores both `html_content` (rendered markdown → HTML) and `text_content` (plain text). For markdown, the "HTML" is just the raw markdown rendered through Python's `markdown` library. The text is the plain text extracted from the markdown.

### No OCR, No External API

This is entirely native Python. No DataLab. No Mistral. The file IS the text — we just need to parse its structure.

## Changes Required

### 1. `backend/ingestion/dispatcher.py`

- Add `_MD_EXTENSIONS = {".md", ".markdown"}`
- Add `_normalize_markdown(conn, md_path, document_id)` function
- Add dispatch branch in `ingest_file()`:
  ```python
  if suffix in _MD_EXTENSIONS:
      print(f"Ingest (Markdown): {document_name}")
      with tx() as conn:
          doc_id = insert_document(conn, case_id=case_id, name=document_name,
                                   page_count=1, source="user_upload")
          with conn.cursor() as cur:
              cur.execute("UPDATE documents SET ocr_status='complete', ocr_provider='markdown-splitter' WHERE id=%s", (doc_id,))
      with tx() as conn:
          _normalize_markdown(conn, file_path, doc_id)
      # ... count sections/blocks, return result
  ```

### 2. `backend/ingestion/worker.py`

- No changes needed — the worker already calls `ingest_file()` which dispatches by extension
- `.md` files uploaded via the existing upload endpoint flow through the same job queue

### 3. Upload endpoint

- No changes needed — `POST /api/cases/{case_id}/ingest` already accepts any file type
- The worker picks up the job and calls `ingest_file()` which handles `.md`

### 4. Dependencies

- Python's `markdown` library (or `mistune` for speed) to convert markdown to HTML for `html_content`
- Both are lightweight, no API keys needed

## Section Splitting Logic

The splitter needs to handle markdown structure correctly:

```
# Case Background          ← section (heading_level=1)
This is a paragraph...     ← block (paragraph)
More text here...          ← block (paragraph)

## Timeline                ← section (heading_level=2, parent=Case Background)
- Jan 2024: Event A        ← block (list_item)
- Mar 2024: Event B        ← block (list_item)

### Key Events              ← section (heading_level=3, parent=Timeline)
1. First event             ← block (list_item, ordered)
2. Second event            ← block (list_item, ordered)
```

The heading chain for each block is built the same way as the DataLab path — `_extract_heading_chain` already handles this. We just need to produce sections with the right `heading_level` and `parent_id` relationships.

## What Stays the Same

- **Embedding** — the existing enrichment worker (`enricher.py`) picks up un-embedded blocks and generates vectors. No changes needed.
- **Full-text search** — `text_tsv` is a generated column on `blocks`. Text content is auto-indexed.
- **Agent search tools** — `search_blocks`, `semantic_search`, `search_hybrid`, `get_block_context` all work against the same tables.
- **Citation** — blocks get `id` values. The agent cites them the same way it cites PDF blocks.
- **Document preview** — the existing `GET /api/documents/{id}/preview` endpoint works for any stored document.

## Edge Cases — Resolved

### Frontmatter → `documents.metadata`
YAML frontmatter (`---\ntitle: ...\n---`) is stripped from the content and stored in `documents.metadata` as JSONB. The agent accesses it via `get_case` or `list_documents`. This gives the agent structured access to title, date, author, and tags without requiring it to parse YAML from raw text.

### Nested Lists → Flattened with metadata
Indented sub-lists are flattened to a single level. Each list item stores `list_level` (1-based depth) and `list_marker` (`-`, `*`, `1.`, `a.`, etc.) in block metadata. The agent sees every list item as a searchable, citable block. Section hierarchy handles major structure; list nesting is detail.

### Code Blocks → Searchable
Code blocks store the raw code as `text_content` (makes it searchable via tsvector) and a `<pre><code>` wrapper as `html_content`. The language tag (e.g., `python`) goes into block metadata. Semantic search won't surface code blocks well, but full-text search will.

### Inline HTML → Pass through
Raw HTML in markdown is preserved in `html_content` and stripped for `text_content` (using the existing `strip_html` helper).

### Very Large Files → Line-by-line streaming
The splitter reads line-by-line — no loading the entire file into memory. Handles files of any size.

## Open Questions — Resolved

1. **Frontmatter:** Strip → `documents.metadata` JSONB ✓
2. **Nested lists:** Flatten with `list_level` + `list_marker` in metadata ✓
3. **Code blocks:** Searchable. `text_content` = raw code, `html_content` = `<pre><code>` ✓
4. **Print/export:** Out of scope. MinIO serves the raw `.md` file via the existing preview endpoint ✓
