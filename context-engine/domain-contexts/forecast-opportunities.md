# Acquisition Gateway Forecast Opportunities

> **Purpose:** Searchable database of federal procurement forecasts scraped from the Acquisition Gateway forecast tool
> **Last Updated:** 2026-07-22

---

## 1. Business Overview

### What This Domain Does

The Forecasts tab stores future procurement projections from federal agencies — what they plan to buy, estimated values, timelines, and set-aside strategies. These are pre-solicitation forecasts that give vendors 12-18 months of advance notice before opportunities hit SAM.gov.

### Why It Exists

The Acquisition Gateway forecast tool (acquisitiongateway.gov) is an Angular SPA with no CSV export. The only way to get the data is to view the rendered page in a browser and extract the HTML. This feature automates the extraction: upload the rendered HTML, and all 12 fields per row are parsed into a queryable database.

### Data Source

Rendered HTML from `https://acquisitiongateway.gov/forecast` (adjust range parameter to capture all results). Currently ~7,400 rows across 8 agencies: Department of the Interior (3,101), Department of Agriculture (2,317), Department of Veterans Affairs (697), Department of Transportation (628), Department of Labor (210), General Services Administration (324), Nuclear Regulatory Commission (89), National Science Foundation (32).

---

## 2. Data Model

### Table: `forecast_opportunities` (migration v28)

```sql
forecast_opportunities
├── id                    SERIAL PK
├── external_id           UUID UNIQUE
├── title                 TEXT NOT NULL
├── description           TEXT
├── source_url            TEXT (e.g., /forecast/resources/47778%3Fnid%3D47778)
├── source_id             TEXT UNIQUE (nid extracted from source_url — dedup key)
├── agency                TEXT (indexed)
├── office                TEXT
├── naics_code            TEXT (indexed)
├── naics_description     TEXT
├── set_aside             TEXT (indexed)
├── place_of_performance  TEXT
├── period_of_performance TEXT
├── estimated_value_text  TEXT (original range label, e.g. "$250K - $499K")
├── estimated_value_low   NUMERIC (parsed lower bound)
├── estimated_value_high  NUMERIC (parsed upper bound)
├── fiscal_year           TEXT (indexed)
├── created_date          TEXT
├── last_updated_date     TEXT
├── search_vector         TSVECTOR (GIN index — auto-updated via trigger)
├── upload_batch_id       UUID
└── created_at            TIMESTAMPTZ
```

**Key indexes:** `source_id` (UNIQUE), `naics_code`, `agency`, `fiscal_year`, `set_aside`, `search_vector` (GIN).

**Dedup:** `UNIQUE (source_id)` — the `nid` (node ID) extracted from each forecast's detail URL serves as the dedup key. Re-uploading the same HTML won't duplicate rows.

**Value normalization:** The `estimated_value_text` column stores the original range string. Two derived numeric columns enable numeric queries:
- `estimated_value_low` — parsed lower bound (0 for "Below $X", exact number for ranges)
- `estimated_value_high` — parsed upper bound (NULL for "Over $X" and "To Be Determined")

### Value Range Mapping

| Text | Low | High |
|---|---|---|
| Below $150K | 0 | 150,000 |
| $150K - $249K | 150,000 | 249,000 |
| $250K - $499K | 250,000 | 499,000 |
| ... | ... | ... |
| $1B - $1.9B | 1,000,000,000 | 1,900,000,000 |
| Over $5B | 5,000,000,000 | NULL |
| To Be Determined | NULL | NULL |

---

## 3. Code Navigation

| File | Purpose |
|---|---|
| `backend/schemas/019_forecast_opportunities.sql` | Schema — table, indexes, search trigger |
| `backend/api/routes/forecasts.py` | Upload (POST HTML → BeautifulSoup parse → COPY), query (POST filters), delete |
| `backend/chat/tools.py` | Agent tool: `query_forecast_opportunities` (Layer 15) |
| `frontend/src/lib/api.ts` | Types: `ForecastOpportunity`, `ForecastQuery`, functions: `queryForecasts`, `uploadForecastHtml`, CRUD |
| `frontend/src/app/cases/[id]/tabs/ForecastsTab.tsx` | Full tab — upload, search bar, filter panel, expandable table, pagination |
| `frontend/src/app/cases/[id]/TabNav.tsx` | Tab definition: `forecasts` with TrendingUp icon |
| `frontend/src/app/cases/[id]/page.tsx` | Tab routing |

### Upload Flow
```
User clicks "Upload HTML" → POST /api/forecasts/upload (multipart)
  → HTML parsed with BeautifulSoup
  → Each .ag-item.ag-item--set row extracted
  → 12 fields per row: title, description, source_url, agency, office,
    NAICS (code + description split), set-aside, place of performance,
    period of performance, fiscal year, estimated value, created/updated dates
  → source_id extracted from URL (nid%3D pattern)
  → Rows streamed into temp table via PostgreSQL COPY
  → INSERT INTO real table ON CONFLICT (source_id) DO NOTHING (dedup)
  → Returns {batch_id, rows_imported, rows_inserted, rows_skipped, source}
  → Frontend refreshes table
```

### HTML Parsing Details
- Row selector: `.ag-item.ag-item--set`
- Title: `.ag-header__title a` (text + href)
- Description: `.ag-body__description`
- Key-value fields: `.ag-item-additional_content__display` → `.ag-body-additional_content__key` / `__value`
- Recognized field labels: Agency, NAICS Code, Organization/Contracting Office, Acquisition Strategy/Type of Set-Aside, Place of Performance, Period of Performance, Estimated Award FY, Created, Estimated Contract Value, Last Updated
- NAICS parsing: split on whitespace — first token is code if numeric, rest is description
- source_id regex: `nid%3D(\d+)` extracted from the source_url

---

## 4. API Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/forecasts/upload` | Upload rendered HTML file (multipart) |
| POST | `/api/forecasts/query` | Query with dynamic filters |
| DELETE | `/api/forecasts/all` | Delete all forecasts |
| DELETE | `/api/forecasts/{id}` | Delete single forecast |

### Query Filters (`ForecastQuery`)

| Filter | Type | Example |
|---|---|---|
| `q` | Full-text search | `"IT services"` |
| `agency` | ILIKE | `"Department of Labor"` |
| `naics_code` | Exact | `"541511"` |
| `set_aside` | ILIKE | `"Small Business"` |
| `fiscal_year` | Exact | `"2026"` |
| `estimated_value_text` | ILIKE | `"Below $150K"` |
| `value_under` | Numeric | `350000` (everything ≤ $350K) |
| `value_over` | Numeric | `1000000` (everything ≥ $1M) |
| `office` | ILIKE | `"OSHA"` |
| `place_of_performance` | ILIKE | `"Little Rock"` |
| `limit/offset` | Pagination | `limit=50` |
| `order_by/order_dir` | Sorting | `order_by=created_date` |

---

## 5. Agent Tool

### `query_forecast_opportunities` (Layer 15, `vision` MCP server)

Same filters as the API. The agent uses this for:
- Finding future opportunities before they hit SAM.gov
- Filtering by value range (e.g., everything under $350K SAT)
- Identifying agencies with active procurement forecasts in a NAICS
- Cross-referencing forecasts with vendor capabilities

**Example agent calls:**
```
query_forecast_opportunities({naics_code: "541511", fiscal_year: "2026"})
query_forecast_opportunities({q: "roofing", value_under: 350000})
query_forecast_opportunities({agency: "Department of Veterans Affairs", set_aside: "Small Business"})
```

---

## 6. Common Tasks

### Get new forecast data
1. Go to https://acquisitiongateway.gov/forecast
2. Set filters (agency, NAICS, etc.)
3. Change the `_a%5Eg_range` URL parameter to the total result count
4. View the fully rendered page → View Page Source → copy all HTML
5. Save as `.html` file
6. In Vision, open a case → Forecasts tab → Upload HTML
7. Repeat for each agency/query

### Query by value
- Use "Value ≤" to find everything under the Simplified Acquisition Threshold ($350,000)
- Use "Value ≥" to find larger opportunities
- Combine with set-aside filters for targeted searches

### Clear and reload
- Click "Delete All" to wipe the table
- Re-upload fresh HTML files

---

## 7. Known Limitations

- **No direct API integration** — The site is an Angular SPA; data is loaded client-side via JavaScript. The backend cannot fetch the data directly. Users must manually save rendered HTML.
- **HTML structure dependent** — If the Acquisition Gateway changes their CSS classes or HTML structure, the parser will break. The selectors (`.ag-item.ag-item--set`, `.ag-header__title a`, etc.) are hardcoded.
- **source_id extraction** — Relies on `nid%3D(\d+)` regex in the URL. If the URL format changes, dedup will fail silently (all source_ids become empty, no dedup).
- **NAICS parsing is basic** — Splits on whitespace, takes the first numeric token as the code. Multi-code fields or unusual formatting will produce incorrect results.
- **Value ranges are approximations** — "Below $150K" becomes 0–150,000. The actual award could be anywhere in that range.
