# FAR — Federal Acquisition Regulation Context

> **Purpose:** Onboard developers and agents to the FAR corpus — what it is, where it lives, how to query it, and how it feeds the solicitation pipeline.
> **Last Updated:** 2026-06-11
> **Maintained By:** Pipeline team

---

## 1. Business Overview

### What This Domain Does

The Federal Acquisition Regulation (FAR) is Title 48 of the Code of Federal Regulations. It is the primary rulebook for all federal procurement — every solicitation, contract, and procurement action references it. The FAR corpus lives in the Vision database as a fully searchable, semantically indexed reference that agents use to:

- Check compliance requirements against solicitation criteria
- Cross-reference clauses cited in RFPs, RFIs, and RFQs
- Draft responses that cite controlling procurement authority
- Verify NAICS applicability, set-aside eligibility, and evaluation standards

### Key Business Rules

- The FAR is authoritative. Agents must cite FAR references verbatim — never paraphrase a FAR clause from memory.
- The FAR updates via Federal Acquisition Circulars (FACs). The current version is **FAC 2026-01**, effective 03/13/2026. Re-ingest when a new FAC is published.
- FAR Parts 20 and 21 are **reserved** — they exist as placeholders with no content.
- FAR Part 52 (Solicitation Provisions and Contract Clauses) is the most frequently cited Part — it accounts for ~37% of all blocks.
- Cross-references between FAR sections are preserved as HTML links in block content. Agents should follow these to trace requirements chains.

### User Stories This Supports

- As a **solicitation analyst**, I can search "FAR 15.101 best value" and get the exact regulatory text with surrounding context.
- As a **compliance-extractor agent**, I can cross-reference a solicitation's cited FAR clauses against the authoritative text to verify accuracy.
- As a **response-drafter agent**, I can pull FAR definitions and standards into proposal language without leaving the database.
- As a **pipeline orchestrator**, I can re-ingest the entire FAR when a new FAC drops with one command.

---

## 2. Code Navigation Guide

> **Start here when working on FAR data**

### Entry Points

| If you want to... | Start at... | Then follow... |
|---|---|---|
| Re-ingest the FAR | `backend/scripts/far_ingest.py` | `_ingest_part()` → `_build_part_hierarchy()` → `_parse_section_html()` |
| Understand the data model | `backend/schemas/001_core.sql` | `documents`, `sections`, `blocks` tables |
| Query the FAR (agent) | `backend/chat/tools.py` → `search_blocks`, `semantic_search`, `get_block_context` | These are case-scoped — use case 12 for FAR |
| Query the FAR (API) | `backend/api/routes/workspace.py` | Workspace items are per-case; FAR is case 12 |
| Embed FAR sections | `backend/search/embed.py` → `embed_document()` | `embed_case(12)` to re-embed all |
| Download source | `https://www.acquisition.gov/sites/default/files/current/far/zip/html/FARHTML.zip` | FAC 2026-01, 3,893 HTML files, 6.5MB ZIP |

### Key Files

| File | Purpose | Key Functions/Classes |
|---|---|---|
| `backend/scripts/far_ingest.py` | FAR download, parse, ingest | `_TOCParser`, `_SectionParser`, `_build_part_hierarchy()`, `_ingest_part()`, `_ensure_far_case()` |
| `backend/search/embed.py` | Mistral embedding pipeline | `embed_document()`, `embed_case()`, `_fetch_cache_hits()`, `_write_cache()` |
| `backend/core/db.py` | Database CRUD | `insert_document()`, `insert_section()`, `insert_block()`, `connect()`, `tx()` |
| `backend/chat/tools.py` | Agent MCP tools for querying | `search_blocks`, `semantic_search`, `search_hybrid`, `get_block_context`, `get_blocks_in_section`, `get_document_structure` |
| `backend/schemas/001_core.sql` | Schema: documents/sections/blocks | `documents` table (line 153), `sections` (line 188), `blocks` (line 225) |

### File Relationships (How Data Flows)

```
acquisition.gov FARHTML.zip (6.5MB, 3,893 HTML files)
        │
        ▼
far_ingest.py ──download──→ /tmp/vision-far-ingest/FARHTML.zip
        │
        ▼
far_ingest.py ──extract──→ /tmp/vision-far-ingest/extracted/dita_html/
        │
        ├── Part_N.html  ──_TOCParser──→ TOC hierarchy (subparts, sections, subsections)
        │
        ├── N.NNN.html   ──_SectionParser──→ paragraphs (text blocks)
        │
        ▼
core/db.py insert_document() → 1 document per Part (51 docs, case_id=12)
        │
        ▼
core/db.py insert_section()  → 3-level hierarchy (subpart→section→subsection)
        │                       heading_level=1: Subpart
        │                       heading_level=2: Section
        │                       heading_level=3: Subsection
        │
        ▼
core/db.py insert_block()    → individual paragraphs (text_content)
        │
        ▼
search/embed.py embed_case() → Mistral embed (1024-dim) → sections.embedding
        │
        ▼
Agent tools ──search_blocks()──→ PostgreSQL full-text search
            ──semantic_search()──→ pgvector cosine similarity (<=>)
            ──get_block_context()──→ Read with surrounding context
```

---

## 3. Database Schema

### How the FAR Maps to Existing Tables

The FAR uses the **same three tables** as every other document in Vision — no special schema. The hierarchy is encoded in `sections.parent_id`.

```
documents (case_id=12)
  name: "Part 15 - Contracting by Negotiation"
  document_type: "other"
  source: "other"
  metadata: {"part": 15, "source_url": "https://..."}
    │
    └── sections (heading_level=1)
        title: "Subpart 15.1 - Source Selection Processes and Techniques"
        metadata: {"far_number": "15.1"}
        │
        └── sections (heading_level=2, parent=above)
            title: "15.101 Best value continuum."
            search_text: "15.101 Best value continuum.\n\n(a) The best value continuum..."
            embedding: VECTOR(1024)  ← Mistral embed
            metadata: {"far_number": "15.101"}
            │
            ├── blocks (section_id=above)
            │   block_type: "Text"
            │   text_content: "(a) The best value continuum is..."
            │
            ├── blocks
            │   text_content: "(b) The best value continuum includes..."
            │
            └── sections (heading_level=3, parent=above)  ← if subsection exists
                title: "15.101-1 Tradeoff process."
                │
                └── blocks...
```

### Case ID

The FAR lives in **case 12** (created by `_ensure_far_case()`). The case name is `"FAR — Federal Acquisition Regulation"` and `case_type` is `"other"`. The case is auto-created if it doesn't exist; re-running the ingest script on the same case name will reuse it.

### Important Constraints

- `documents.source` must be one of: `user_upload`, `discovery`, `data_lab`, `email`, `portal`, `api`, `other`. The ingest script uses `"other"`.
- `sections.search_text` is truncated to 16,000 chars before embedding (Mistral token limit).
- `sections.embedding` is 1024-dimensional (`mistral-embed` model).
- `ON CONFLICT (case_id, name)` on documents allows re-ingest without duplicates (upserts).
- Embedding cache (`embedding_cache` table) deduplicates identical text across re-ingests.

---

## 4. Agent Tool Access

### How Agents Query the FAR

All FAR access goes through the standard Vision MCP tools on the `"vision"` server. The FAR is just another case — agents use the same tools they use for solicitation documents.

| Task | Tool | Example |
|---|---|---|
| Full-text search for a FAR clause | `search_blocks` | `search_blocks(query="best value tradeoff", document_id=25)` (Part 15 doc) |
| Concept search (don't know exact wording) | `semantic_search` | `semantic_search(query="how to evaluate proposals", document_id=25)` |
| Combined search (important queries) | `search_hybrid` | For compliance checks where missing a result matters |
| Read a section in context | `get_block_context` | After finding a match, read surrounding paragraphs |
| Browse Part structure | `get_document_structure` | `get_document_structure(document_id=25)` — see all subparts/sections |
| Read an entire section | `get_blocks_in_section` | Read all paragraphs in FAR 15.101 |
| Find FAR case | `list_documents` | FAR documents are in case 12; filter by `case_id` or use `get_case` |

### Agent Workflow for FAR Research

```
1. mcp__vision__get_case(case_id=12)                    → list all 51 Part documents
2. mcp__vision__semantic_search(query, document_id=X)   → find relevant sections
3. mcp__vision__get_block_context(block_id)             → read in full context
4. Cite: "FAR 15.101(a): '[verbatim text from block]'"  → Authority established
```

### Company Profile Cross-Reference

When agents use the FAR to evaluate solicitation compliance, they should also call `get_case_profile` to cross-reference company NAICS codes, certifications, and past performance against FAR requirements.

---

## 5. Common Tasks (How-To)

### "I need to re-ingest the FAR after a new FAC"

```bash
cd backend && python -m scripts.far_ingest
```

The script will:
1. Download the latest `FARHTML.zip` from acquisition.gov
2. Extract and parse all 3,893 HTML files
3. Upsert documents (existing Parts are updated, new ones inserted)
4. Embed new sections via Mistral

This is safe to re-run — `ON CONFLICT` on documents prevents duplicates.

### "I need to search for a specific FAR clause"

From an agent session:
```
search_blocks(query="FAR 15.403-1", document_id=<Part_15_doc_id>)
```

Or across all FAR documents:
```
search_blocks(query="prohibition on contracting with inverted domestic corporations")
```

### "I need to verify a solicitation's FAR references are accurate"

1. Use `compliance-extractor` agent to pull all FAR citations from the solicitation
2. For each citation, search the FAR corpus for the exact text
3. Compare solicitation paraphrase against authoritative text
4. Flag discrepancies

### "I need to add FAR compliance checking to the solicitation pipeline"

The `compliance-extractor` agent already has `search_blocks` and `semantic_search` tools. Update its system prompt (`.claude/agents/compliance-extractor.md`) to include FAR cross-reference as a step:

```markdown
### Step N: Cross-Reference FAR Citations
1. Extract every FAR reference from the solicitation (e.g., "FAR 15.101", "52.212-1")
2. For each reference, search the FAR corpus (case 12) for the authoritative text
3. Verify the solicitation's paraphrase matches the FAR text
4. Flag any misrepresented or missing FAR requirements
```

### "I only want to ingest one Part for testing"

```bash
python -m scripts.far_ingest --part 15 --no-embed
```

---

## 6. Agent Tools & Scripting

### FAR Ingest Script CLI

```
usage: python -m scripts.far_ingest [-h] [--skip-download] [--no-embed] [--part PART] [--dry-run]

options:
  --skip-download  Use cached ZIP from temp dir
  --no-embed       Skip Mistral embedding (faster, embed separately)
  --part PART      Ingest a single Part by number (e.g., --part 15)
  --dry-run        Parse and count without inserting into DB
```

### FAR Statistics (FAC 2026-01)

| Metric | Count |
|---|---|
| Parts | 51 (excluding 20, 21 reserved) |
| Subparts | 453 |
| Sections + Subsections | 3,815 |
| Paragraph blocks | 30,351 |
| Embedding time | ~430s (7 min) for all 3,815 sections |
| ZIP size | 6.5 MB |
| DB size (est.) | ~30 MB text + ~16 MB vectors |

### FAR Part Reference (Frequently Used in GovCon)

| Part | Title | Doc ID (approx) | Key For |
|---|---|---|---|
| 1 | Federal Acquisition Regulations System | 25 | Definitions, conventions |
| 7 | Acquisition Planning | 31 | Requirements development |
| 8 | Required Sources of Supplies and Services | 32 | Competition requirements |
| 12 | Acquisition of Commercial Products and Commercial Services | 36 | Commercial items |
| 15 | Contracting by Negotiation | 39 | Evaluation, best value |
| 19 | Small Business Programs | 43 | Set-asides, certifications |
| 22 | Application of Labor Laws | 46 | Labor standards |
| 25 | Foreign Acquisition | 49 | Buy American, trade agreements |
| 52 | Solicitation Provisions and Contract Clauses | 76 | **Most cited Part** — clauses |

---

## 7. Known Issues & Technical Debt

- [ ] **Part 52 blocks are large** — Some Part 52 sections have very long paragraphs (500+ words each). Search may return large text chunks. Consider sub-block chunking for Part 52 specifically.
- [ ] **Tables not extracted** — FAR tables (e.g., OMB control numbers in 1.106) are parsed as `<p>` text but lose their tabular structure. The raw HTML is not preserved.
- [ ] **No automated FAC monitoring** — New FACs must be manually detected and re-ingested. A cron job or webhook to watch `acquisition.gov` for new FACs would keep the corpus current.
- [ ] **Cross-reference resolution** — FAR sections link to each other via `<a href="...">` tags, but these are rendered as plain text URLs. An agent that follows cross-references would need to parse the href and query the corresponding section.
- [ ] **Embedding cache not pre-warmed** — First ingest had 0 cache hits (naturally). Re-ingest after a FAC will benefit from cache on unchanged sections.
- [ ] **No FAR-specific search ranking** — The full-text search uses PostgreSQL `ts_rank`. A custom weighting that boosts Part/Section number matches over body text matches would improve precision.
- [ ] **FAR case_id is hardcoded** — The ingest script auto-creates case 12, but this ID could change if the case is deleted and re-created. A `case_type = 'far_reference'` or a lookup-by-name would be more robust.

---

## 8. Related Domains

| Domain | Relationship | Context File |
|---|---|---|
| Solicitation Pipeline | Uses FAR for compliance verification and response drafting | `.claude/skills/solicitation-pipeline/SKILL.md` |
| Company Profile | Cross-referenced against FAR requirements (NAICS, certifications) | `discussions/govcon-dashboard/04-company-profile.md` |
| Workspace | FAR artifacts could be workspace items if extracted for specific cases | `.claude/skills/workspace/SKILL.md` |
| Ingestion Pipeline | FAR uses same document→section→block pipeline as all documents | `backend/ingestion/` |

---

> ⚠️ **When working with FAR data:** Always search the FAR corpus (case 12) for the authoritative text before citing a FAR reference. Never paraphrase a FAR clause from memory. The agent tools `search_blocks` and `get_block_context` are the only valid paths to FAR text.
