# FAR Database Access — Raw SQL Guide

> **For:** Outside agents (CLI agents, scripts, external services) that need to query the FAR directly via PostgreSQL.
> **Last Updated:** 2026-08-12

---

## Where the FAR Lives

The FAR is a single case in the `cases` table, ingested into the standard evidence-store tables:

| Table | Role | FAR Count |
|-------|------|-----------|
| `cases` | Case container | 1 row — name `'FAR — Federal Acquisition Regulation'` |
| `documents` | One row per FAR Part | 51 rows (Parts 1–53, minus reserved 20/21) |
| `sections` | Structural hierarchy — subparts, sections, subsections | 3,815 rows |
| `blocks` | Actual regulatory text (paragraphs) | 30,351 rows |

Everything follows the standard schema: `documents.case_id → cases.id`, `sections.document_id → documents.id`, `blocks.section_id → sections.id`. No special tables — just a case like any other.

---

## Connection

```
Host:     127.0.0.1
Port:     5433 (DBngin local; check VISION_DB_PORT)
Database: vision
User:     vision
Password: vision_dev
Schema:   vision
```

```sql
SET search_path TO vision, public;
```

---

## The Core Queries

### 1. Find the FAR case ID

```sql
SELECT id FROM cases WHERE name = 'FAR — Federal Acquisition Regulation';
-- → 13
```

### 2. List all Parts (documents)

```sql
SELECT id, name, metadata->>'part' AS part
FROM documents
WHERE case_id = 13
ORDER BY (metadata->>'part')::int;
```

### 3. Look up an exact citation (e.g., FAR 15.101)

The key trick: sections carry a normalized citation in `sections.metadata->>'far_number'`.

```sql
SELECT s.id, s.title, s.search_text, d.name AS part_name
FROM sections s
JOIN documents d ON d.id = s.document_id
WHERE d.case_id = 13
  AND s.metadata->>'far_number' = '15.101';
```

### 4. Read the text of a section

```sql
SELECT b.page, b.block_type, b.text_content
FROM blocks b
WHERE b.section_id = (SELECT id FROM sections WHERE metadata->>'far_number' = '15.101'
                      AND document_id IN (SELECT id FROM documents WHERE case_id = 13)
                      LIMIT 1)
ORDER BY b.page, b.id;
```

Or get the section's full text in one shot — `search_text` holds concatenated block text:

```sql
SELECT search_text FROM sections WHERE metadata->>'far_number' = '15.101'
  AND document_id IN (SELECT id FROM documents WHERE case_id = 13);
```

### 5. Clause lookup with dash (e.g., FAR 52.212-1)

```sql
SELECT s.id, s.title
FROM sections s
JOIN documents d ON d.id = s.document_id
WHERE d.case_id = 13
  AND (s.metadata->>'far_number' = '52.212-1'
       OR s.metadata->>'far_number' LIKE '52.212-1%');
```

### 6. Keyword search across all FAR text

Full-text search via tsvector on blocks:

```sql
SELECT b.id, b.text_content, s.title, d.name AS part
FROM blocks b
JOIN sections s ON s.id = b.section_id
JOIN documents d ON d.id = b.document_id
WHERE d.case_id = 13
  AND b.text_tsv @@ plainto_tsquery('english', 'best value tradeoff')
LIMIT 20;
```

Semantic search via pgvector:

```sql
SELECT b.id, b.text_content,
       1 - (b.embedding <=> query_vec.embedding) AS similarity
FROM blocks b
JOIN documents d ON d.id = b.document_id,
LATERAL (SELECT embedding FROM blocks WHERE id = :example_block_id) query_vec
WHERE d.case_id = 13
ORDER BY b.embedding <=> query_vec.embedding
LIMIT 20;
```

---

## Citation Formats

`sections.metadata->>'far_number'` holds normalized citations:

| Input | Stored far_number |
|-------|-------------------|
| `15.101` | `15.101` |
| `52.212-1` | `52.212-1` |
| `52.212-1(b)` | parentheticals stripped — match on `52.212-1` and filter blocks |

---

## Data Quality Notes

- **Parts 20 and 21 are reserved** — no content, no rows.
- **Part 52 is the largest** — ~37% of all blocks. Clause lookups there should use `LIKE '52.xxx-%'` prefix matching.
- Cross-references between sections are preserved as HTML links inside `blocks.html_content`. Follow them by extracting the citation from the href and re-querying `far_number`.
- The authoritative lookup tool used by the in-app agent is `far_lookup` in `backend/chat/tools.py` — if SQL semantics are unclear, mirror its 4-tier strategy: exact match → partial (drop `-(x)` suffix) → title search → full-text.
