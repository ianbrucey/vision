ta gi

# Reports Feature — Design Document

> **Status:** Draft for discussion
> **Date:** July 22, 2026

---

## The Problem

You have three data sources (forecasts, SAM notices, SAM.gov API) and a clear set of criteria for what you want to pursue. But there's no way to save those criteria as a named report that you can revisit, share with the agent, or refine over time.

Currently you ask the agent to run queries. The agent can do it — `query_forecast_opportunities`, `query_sam_notices`, `summarize_forecasts` — but every query is ad-hoc. There's no persistence. No "IT Projects Under $150K" report you can click on next week and see updated results.

## What You Asked For

From the attack plan:

1. **IT projects** — all of them, ascending by value (forecasts + SAM)
2. **Total Small Business set-asides** — ascending by value (forecasts)
3. **Unrestricted under $500K** — ascending by value (forecasts)
4. **Small-value verticals** — under $150K, specific industries (IT, office supplies, cleaning, medical, lab equipment, small vehicles, appliances)
5. **Same categories for SAM notices** — but no value filter available, so use NAICS/text search
6. **Ability to have MULTIPLE reports** per tab, not just one at a time

## Proposed Architecture

### Data Model

New table: `saved_reports`

```sql
CREATE TABLE saved_reports (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id),
    name            TEXT NOT NULL,              -- "IT Projects Under $150K"
    data_source     TEXT NOT NULL,              -- 'forecasts' | 'sam_notices'
    query_filters   JSONB NOT NULL,             -- the filter criteria
    sort_by         TEXT,                       -- 'estimated_value_low' | 'created_date'
    sort_dir        TEXT DEFAULT 'ASC',
    created_by      TEXT DEFAULT 'agent',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

The `query_filters` JSONB stores the exact filter object passed to `query_forecast_opportunities` or `query_sam_notices`. This makes reports trivially executable — just pass the stored filters to the existing query tool.

### UI Concept

Each data tab (Sam Notices, Forecasts) gets a **reports sidebar** on the left:

```
┌──────────────────────────────────────────────────┐
│  Reports                    │  Results           │
│                              │                    │
│  📋 IT Projects (150)       │  [table of results]│
│  📋 SB Set-Asides (795)     │                    │
│  📋 Unrestricted <$500K (16)│                    │
│  📋 Medical Supplies (45)   │                    │
│  📋 Office Supplies (23)    │                    │
│  📋 Lab Equipment (67)      │                    │
│  ─────────────────────────  │                    │
│  [+ New Report]             │                    │
│                              │                    │
└──────────────────────────────────────────────────┘
```

Each report shows its name and a live count of matching results. Click a report → results load in the main panel. The count badge updates whenever you refresh.

### Creating a Report

Two paths:

**Path A: From the filter panel** — Set your filters in the existing UI, then click "Save as Report" → give it a name. The current filter state becomes the report definition.

**Path B: Via the agent** — Tell the agent "Create a report called 'IT Projects Under $150K' showing all forecast IT opportunities under $150K." The agent uses the existing tools to determine the right filters, then calls `create_report`.

### Agent Tools

| Tool               | Purpose                                                 |
| ------------------ | ------------------------------------------------------- |
| `list_reports`   | List saved reports for the current case                 |
| `get_report`     | Get a report's definition + execute it (return results) |
| `create_report`  | Save a new report with name + filters                   |
| `update_report`  | Modify a report's filters or name                       |
| `delete_report`  | Remove a report                                         |
| `execute_report` | Run a report and return paginated results               |

The agent can also use the existing query/summarize tools directly — reports are a convenience, not a gate.

### Key Design Decisions

**1. Reports are just saved filter presets, not materialized views.**
Every time you open a report, it runs the query live against the current data. This means counts change as you upload new data — you're always seeing the latest.

**2. Multiple reports coexist.**
The sidebar shows all reports. Clicking one loads its results. No limit on how many reports you can have.

**3. Reports are shareable with the agent.**
The agent can read a report's filters to understand what you're targeting. "Execute the 'SB Set-Asides' report and tell me which ones have approaching deadlines."

**4. SAM.gov API integration for gap detection.**
A report can optionally include a flag `include_live_sam: true`. When executed, it runs the same filters against the live SAM.gov API (via `search_sam_opportunities`) and flags opportunities that exist in the live API but NOT in your local database. This closes the gap between your CSV export and real-time SAM.gov.

### What You'd Say to the Agent

```
"Create a report called 'IT Under 150K' for forecasts —
 IT-related NAICS codes, under $150K value, ascending order."

"Run the 'SB Set-Asides' report and show me anything due in the next 14 days."

"Check the live SAM.gov API for any new IT opportunities
 I don't already have in my database."

"Create reports for each of my target verticals:
 IT, medical supplies, office supplies, cleaning supplies,
 lab equipment, small vehicles, appliances."
```

### Implementation Priority

| Priority | What                                                                | Why                                        |
| -------- | ------------------------------------------------------------------- | ------------------------------------------ |
| P0       | `saved_reports` table + CRUD endpoints                            | Foundation                                 |
| P0       | Agent tools:`create_report`, `list_reports`, `execute_report` | Agent can build reports for you            |
| P1       | Reports sidebar in Forecasts tab                                    | Immediate value for the attack plan        |
| P1       | Reports sidebar in Sam Notices tab                                  | Same pattern, different data source        |
| P2       | Live SAM.gov API gap detection                                      | Closes the data freshness gap              |
| P2       | Report scheduling (daily refresh + notification)                    | "Tell me when new IT opportunities appear" |

### What We DON'T Need

- **No cross-source reports** (yet) — forecasts and SAM notices stay separate because their schemas differ. A unified view can come later.
- **No charts/dashboards** in the report viewer — the existing summarize tools already give you aggregate data. Reports are about seeing individual opportunities.
- **No export beyond what the browser provides** — the table is already copy-pasteable. PDF/CSV export can come later.

---

## Open Questions

1. **Should reports be case-scoped or global?** Leaning case-scoped (each case has its own reports) since different cases may target different agencies/verticals.
2. **Should the agent proactively suggest reports?** E.g., "I notice you have 1,413 opportunities under $150K. Want me to create a report for that?" Could be useful but needs a trigger mechanism.
3. **Should reports auto-refresh on a schedule?** The data only changes when you upload new CSVs/HTML. Auto-refresh is low-value until we have live API integration.
