# SAM.gov Databank Notices

> **Purpose:** Searchable local copy of SAM.gov databank CSV exports for offline opportunity research
> **Last Updated:** 2026-07-22

---

## 1. Business Overview

### What This Domain Does

The Sam Notices tab lets users upload CSV exports from the SAM.gov databank (e.g., `Contract_Notice_Details.csv`) and search them with full-text and structured filters. The data is available to both the UI and the agent for opportunity research — finding active solicitations, identifying agency buying patterns, and matching NAICS/set-aside criteria.

### Why It Exists

The SAM.gov API returns only ~100 results per call and requires date range filters. Bulk CSV exports contain thousands of rows spanning months of data. Having this data locally means the agent can query across all notices instantly — no API rate limits, no date range constraints.

### Data Source

SAM.gov databank CSV export. Contains ~4,500 rows with 27 recognized columns including: notice ID (solicitation number), opportunity title, type, description, NAICS, PSC, set-aside, agency hierarchy, place of performance, POC info, dates, and attachment counts.

---

## 2. Data Model

### Table: `sam_notices` (migration v26)

```sql
sam_notices
├── id                    SERIAL PK
├── external_id           UUID UNIQUE
├── notice_id             TEXT (solicitation number — unique index where NOT NULL)
├── opportunity_title     TEXT NOT NULL
├── contract_opportunity_type TEXT
├── description           TEXT
├── status                TEXT
├── naics_code            TEXT (indexed)
├── naics_description     TEXT
├── psc_code              TEXT
├── current_set_aside     TEXT
├── current_set_aside_code TEXT (indexed)
├── sub_tier_name         TEXT (agency — indexed)
├── contracting_office    TEXT
├── pop_city/state/country TEXT
├── poc_name/email        TEXT
├── awardee_name/uei      TEXT
├── attachment_count      INTEGER
├── ivl_enabled           BOOLEAN
├── search_vector         TSVECTOR (GIN index — auto-updated via trigger)
├── upload_batch_id       UUID
├── source_csv            TEXT
└── created_at            TIMESTAMPTZ
```

**Key indexes:** `notice_id` (UNIQUE WHERE NOT NULL), `naics_code`, `set_aside_code`, `sub_tier_name`, `status`, `search_vector` (GIN).

**Dedup:** `UNIQUE (notice_id) WHERE notice_id IS NOT NULL` — re-uploading the same CSV won't create duplicates.

**Search trigger:** Auto-updates `search_vector` on INSERT/UPDATE using `setweight` for title (A), description (B), NAICS/agency (C/D).

---

## 3. Code Navigation

| File | Purpose |
|---|---|
| `backend/schemas/017_sam_notices.sql` | Schema — table, indexes, search trigger |
| `backend/api/routes/sam_notices.py` | Upload (POST CSV → COPY), query (POST filters), batch management, solicitation URL lookup |
| `backend/chat/tools.py` | Agent tool: `query_sam_notices` (Layer 14) |
| `frontend/src/lib/api.ts` | Types: `SamNotice`, `SamNoticesQuery`, functions: `querySamNotices`, `uploadSamNoticesCsv`, `lookupSolicitationUrl`, CRUD |
| `frontend/src/app/cases/[id]/tabs/SamNoticesTab.tsx` | Full tab — upload, search bar, filter panel, expandable table, pagination, delete |
| `frontend/src/app/cases/[id]/TabNav.tsx` | Tab definition: `sam_notices` with Database icon |
| `frontend/src/app/cases/[id]/page.tsx` | Tab routing |

### Upload Flow
```
User clicks "Upload CSV" → POST /api/sam-notices/upload (multipart)
  → CSV parsed with utf-8-sig encoding
  → Rows streamed into PostgreSQL COPY for speed (~1s for 4.5K rows)
  → Returns {batch_id, rows_inserted, source}
  → Frontend refreshes table
```

### Solicitation URL Lookup
```
User clicks notice_id link → GET /api/sam-notices/lookup?sol=36E79726R0017
  → Calls SAM.gov v2 API with solnum= parameter (exact solicitation number match)
  → Returns ui_link from SAM.gov response
  → Frontend opens direct SAM.gov page in new tab
  → Falls back to sam.gov/search URL if API call fails
```

---

## 4. API Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/sam-notices/upload` | Upload CSV file (multipart) — bulk insert via COPY |
| POST | `/api/sam-notices/query` | Query with dynamic filters (see SamNoticesQuery schema) |
| GET | `/api/sam-notices/lookup?sol=` | Resolve solicitation number → SAM.gov ui_link |
| GET | `/api/sam-notices/batches` | List upload batches with row counts |
| DELETE | `/api/sam-notices/batches/{id}` | Delete all rows from a batch |
| DELETE | `/api/sam-notices/all` | Delete all notices |
| DELETE | `/api/sam-notices/{id}` | Delete single notice |

### Query Filters (`SamNoticesQuery`)

| Filter | Type | Example |
|---|---|---|
| `q` | Full-text search | `"roofing repair"` |
| `naics_code` | Exact | `"238160"` |
| `naics_description` | ILIKE | `"roofing"` |
| `psc_code` | Exact | `"2330"` |
| `contract_opportunity_type` | Exact | `"Combined Synopsis/Solicitation"` |
| `current_set_aside` | ILIKE | `"Small Business"` |
| `current_set_aside_code` | Exact | `"SBA"` |
| `sub_tier_name` | ILIKE | `"DEPT OF THE ARMY"` |
| `pop_state` | Exact | `"VA"` |
| `status` | Exact | `"active"` |
| `response_date_from/to` | Date range | `"2026-07-01"` |
| `published_date_from/to` | Date range | |
| `has_attachments` | Boolean | `true` |
| `limit/offset` | Pagination | `limit=100` |
| `order_by/order_dir` | Sorting | `order_by=last_published_date` |

---

## 5. Agent Tool

### `query_sam_notices` (Layer 14, `vision` MCP server)

Same filters as the API. The agent uses this for:
- Finding opportunities matching a solicitation's NAICS and set-aside
- Researching agency buying patterns
- Identifying active solicitations with approaching deadlines
- Searching for specific notice IDs

**Example agent calls:**
```
query_sam_notices({naics_code: "541511", pop_state: "VA", status: "active"})
query_sam_notices({q: "roofing", current_set_aside_code: "SBA"})
query_sam_notices({sub_tier_name: "DEPT OF THE ARMY", response_date_from: "2026-07-22"})
```

---

## 6. Common Tasks

### Upload new CSV data
1. Go to SAM.gov databank → export CSV
2. In Vision, open a case → Sam Notices tab
3. Click "Upload CSV" → select file
4. Table refreshes with new data

### Search for opportunities
- Use the search bar for full-text queries
- Toggle "Filters" for structured filtering
- Combine multiple filters (e.g., NAICS + state + status)
- Click row to expand and see description, POC, location details
- Click notice_id to open the live SAM.gov page

### Clear and reload
- Click "Delete All" to wipe the table
- Re-upload fresh CSV

---

## 7. Known Limitations

- **CSV column mapping is fragile** — SAM.gov occasionally changes column headers. The `_CSV_COLUMN_MAP` in `sam_notices.py` maps 27 columns by exact name. Unrecognized columns are silently dropped.
- **Solicitation number ≠ SAM.gov notice ID** — The CSV's "Notice ID" is a solicitation number (e.g., `36E79726R0017`), not the SAM.gov UUID. The `/lookup` endpoint bridges this by calling the SAM.gov API.
- **No incremental updates** — Each upload replaces/merges all data. There's no delta/change detection.
- **Date parsing** — Tries 4 common formats. Unparseable dates become NULL.
