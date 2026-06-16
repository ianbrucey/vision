---
name: dynamic-views
description: Produce structured, editable views (tables, lists, cards, charts) from ingested documents. Use when the user asks to see data in an organized format — analyze a credit report, review bank statements, extract structured information from documents.
---

# Dynamic Views — Agent-Produced Structured Views

When the user asks you to analyze documents and present findings in a structured, interactive format, produce a `json_view` workspace item. This is the "Jarvis hologram": you scan the data, choose the right view type, and render it.

---

## When to Use This Skill

**Trigger phrases** (any of these suggest a dynamic view):
- "Analyze this credit report"
- "Show me my subscriptions"
- "Extract the key terms from this contract"
- "What does my bank statement look like?"
- "Give me a checklist of steps to..."
- "Summarize the key findings"
- Any request that implies tabular data, checklists, or summary cards

**Do NOT use this skill for:**
- Narrative text, explanations, or prose → use `markdown` workspace item
- Legal letters, pleadings, formal documents → use `structured_draft` or `letter` document type
- Raw HTML output → use `html` file type (freestyle folder)

---

## The View Envelope Contract

Every `json_view` workspace item stores this shape in `content`:

```json
{
  "documentMetadata": {
    "title": "Human-readable title for the workspace item",
    "sourceId": "Optional reference to source document (e.g. 'doc_credit_001')",
    "lastUpdated": "ISO 8601 timestamp"
  },
  "views": [
    {
      "viewType": "table | list | cards",
      "title": "Section heading for this view",
      "description": "Optional subtitle",
      "data": { /* view-specific shape — see below */ }
    }
  ]
}
```

**Key rules:**
- `views` is an array — always at least 1 view, max 10
- Views render in array order (first view at top)
- Each view has its own `viewType`, `title`, and `data`
- The envelope is a DIRECT OBJECT — NOT array-wrapped (unlike markdown which uses `[{markdown: "..."}]`)

---

## View Types

### `table` — Tabular Data

Use when data has **consistent columns across multiple entities.** Each row represents one entity; each column is a property.

**Data shape:**
```json
{
  "viewType": "table",
  "title": "Negative Accounts",
  "description": "Accounts requiring dispute",
  "data": {
    "headers": ["Account Name", "Balance", "Status"],
    "rows": [
      { "id": "r1", "Account Name": "Chase", "Balance": "$4,230", "Status": "Delinquent" }
    ]
  }
}
```

**Rules:**
- `headers`: 1-20 strings, non-empty. Order determines column order.
- `rows`: 1-500 objects. Each MUST have `id` (unique string). All other keys are string values.
- Column keys in rows MUST match header strings exactly.
- The `id` column is not editable by the user — it's the stable row key.

**When to choose table:**
- Multiple records with the same properties (accounts, transactions, line items, parties)
- Data that benefits from sorting by column
- Any time you have 3+ entities with 3+ shared attributes

---

### `list` — Sequential Items

Use for **ordered steps, checklists, chronological entries, action items.**

**Data shape:**
```json
{
  "viewType": "list",
  "title": "Recommended Actions",
  "description": "Ordered by priority",
  "data": {
    "listStyle": "checkbox",
    "items": [
      { "id": "t1", "text": "Dispute Chase account with Equifax", "completed": false, "notes": "Deadline: 30 days" }
    ]
  }
}
```

**Rules:**
- `listStyle`: `"checkbox"` (interactive toggles), `"ordered"` (numbered), or `"bullet"` (plain bullets)
- `items`: 1-200 objects. Each MUST have `id` (string) and `text` (string).
- `completed` (boolean, optional): only meaningful for checkbox style
- `notes` (string, optional): subtext rendered below the item

**When to choose list:**
- Action items / to-dos / next steps
- Chronological sequence of events
- Step-by-step instructions
- Simple enumeration without columns
- Use `checkbox` when actions can be completed; `ordered` for sequential steps; `bullet` for reference lists

---

### `cards` — Key-Value Summary

Use for **dashboard metrics, summary statistics, document overviews.** Cards are the "at a glance" view.

**Data shape:**
```json
{
  "viewType": "cards",
  "title": "Credit Report Summary",
  "data": {
    "pairs": [
      { "key": "Total Negative Accounts", "value": "7", "emphasis": "danger" },
      { "key": "Total Balance", "value": "$23,450", "emphasis": "warning" },
      { "key": "Accounts in Good Standing", "value": "14", "emphasis": "success" }
    ]
  }
}
```

**Rules:**
- `pairs`: 1-50 objects. Each MUST have `key` (string) and `value` (string).
- `emphasis` (optional): `"default"`, `"warning"`, `"danger"`, `"success"`, `"info"`. Controls card border color.
- Values are always strings (even numbers — format them as strings with appropriate units)

**When to choose cards:**
- Summary / dashboard of key metrics
- Single-entity overview (one document, one case, one party)
- Quick facts before diving into detail views
- 1-8 key-value pairs that the user needs to see immediately

### `chart` — Visual Data

Use for **visual comparison of numeric data.** Same data structure as table — chart reuses `{headers, rows}`.

**Data shape:**
```json
{
  "viewType": "chart",
  "title": "Account Balances",
  "data": {
    "chartType": "bar",
    "headers": ["Account Name", "Balance"],
    "rows": [
      { "id": "1", "Account Name": "Chase", "Balance": "4230" },
      { "id": "2", "Account Name": "Wells Fargo", "Balance": "1150" }
    ]
  }
}
```

**Rules:**
- `chartType`: `"bar"` (comparing categories), `"line"` (trends/time series), or `"pie"` (proportions)
- `headers` + `rows`: same format as table. Rows are charted — first non-id column is labels, remaining are values.
- String values are auto-parsed (e.g., `"$4,230"` → `4230`). Non-numeric strings become 0.
- chart ↔ table switching is non-lossy client-side (same data, different render)

**When to choose chart:**
- Comparing numeric values across categories (bar)
- Showing trends over time (line)
- Displaying proportions or composition (pie)
- Any time tabular data benefits from visual comparison

**When NOT to use chart:**
- Non-numeric data that can't be meaningfully charted
- Single data point — use cards instead
- Multi-column data where only one column has meaningful values — extract just that column

---

## The Composite Pattern (Recommended)

For most analysis tasks, produce a **composite** — multiple views in one envelope. The canonical pattern:

1. **Cards first** — summary metrics so the user sees the big picture immediately
2. **Table second** — detailed breakdown of the data
3. **List third** — recommended actions or next steps

Example: "Analyze this credit report" →
- View 0: `cards` — Total accounts, total balance, report date
- View 1: `table` — Each negative account with name, balance, status
- View 2: `list` (checkbox) — Dispute actions ordered by priority

**But be flexible.** If the user asks for just a checklist, give them a single list view. If they ask for a summary, a single cards view. Don't force composites when a single view is sufficient.

---

## How to Create a View

Use the `create_workspace_item` tool:

```
create_workspace_item(
  name="Credit Report Analysis",
  file_type="json_view",
  folder="artifacts",
  content={...the view envelope...}
)
```

The `folder` parameter should be `"artifacts"` for final output or `"research"` for exploratory analysis.

To UPDATE an existing view (add a view, change data, fix errors):

```
get_workspace_item(item_id)          # read current content first
update_workspace_item(item_id, content={...updated envelope...})
```

**Always `get_workspace_item` before updating** to avoid clobbering user edits.

---

## Source Citation

When extracting data from source documents, populate `documentMetadata.sourceId`:

```json
"documentMetadata": {
  "title": "Credit Report Analysis",
  "sourceId": "doc_credit_001",
  "lastUpdated": "2026-06-16T12:00:00Z"
}
```

The `sourceId` should reference the document you extracted from (use the document name or ID visible in `list_documents`). This preserves the citation chain — the view is a derivative of the source blocks.

---

## Validation

The backend validates every `json_view` content against the envelope schema. If validation fails, you'll get a 422 error with a specific message like:

- `"at 'views → 0' at 'data': 'pairs' is a required property"` — you forgot `data.pairs` on a cards view
- `"unknown viewType 'chart'. Expected one of: cards, list, table"` — you used a viewType that doesn't exist
- `"at 'views': [] should be non-empty"` — you sent an empty views array

Read the error message, fix the specific violation, and retry. Do not guess — the error tells you exactly what's wrong.

---

## Anti-Patterns

| Don't | Do Instead |
|-------|-----------|
| Use `json_view` for narrative text or prose | Use `markdown` file type |
| Invent new viewTypes (`"graph"`, `"timeline"`, `"spreadsheet"`) | Use only `table`, `list`, `cards`, `chart` |
| Put 500+ rows in a table | Limit to the most relevant rows; summarize the rest in a cards view |
| Create a table with 1 row | Use cards view instead |
| Use a list for data that has consistent columns | Use table view |
| Omit `id` fields on rows/items | Every row and item MUST have a unique string `id` |
| Array-wrap the envelope like markdown `[{documentMetadata...}]` | json_view content is a direct object `{documentMetadata, views}` |
| Overwrite user edits without reading first | Always `get_workspace_item` before `update_workspace_item` |
| Guess at values — if you're unsure about a data point | Either cite the source block or omit the row/item |

---

## Quick Reference

| Data looks like... | Use viewType | Key required fields |
|---|---|---|
| Multiple records with same properties | `table` | `headers[]`, `rows[{id, ...}]` |
| Steps, actions, chronological items | `list` | `listStyle`, `items[{id, text}]` |
| Key metrics, summary stats | `cards` | `pairs[{key, value}]` |
| Numeric comparison, trends, proportions | `chart` | `chartType`, `headers[]`, `rows[{id, ...}]` |
| All of the above (comprehensive analysis) | composite | All of the above |
