# Dynamic View System — Strategic Brief

## 1. Strategic Intent

**Goal:** Give the agent the ability to produce structured, interactive, editable views (tables, lists, cards) from ingested documents — and give the user the ability to edit those views inline and switch between view types on demand. This is the "Jarvis hologram": the agent scans the data and renders it in the most appropriate format.

**Success Verdict:**
- [ ] Agent can create a `json_view` workspace item with a valid view envelope containing 1+ views
- [ ] Table view renders with sortable headers, inline-editable cells, and row striping
- [ ] List view renders with the specified list style (checkbox, ordered, bullet) and inline-editable items
- [ ] Cards view renders key-value pairs in a responsive card grid
- [ ] User can click any cell/list item/card value to edit it inline; edits persist via `PATCH /api/workspace/{id}`
- [ ] User can switch between compatible view types client-side without agent re-invocation (table ↔ cards)
- [ ] User can request a structural view change via chat ("show as a chart instead") and the agent re-generates the view
- [ ] Multiple views compose into a single scrollable workspace item (summary cards + detail table + action checklist)
- [ ] Source blocks are never modified by view edits

## 2. The Claims

| Claim ID | Description | Verdict |
|----------|-------------|---------|
| CLAIM-01 | `json_view` content envelope contract is defined and documented | Agent produces JSON that validates against the schema; invalid envelopes are rejected by the API |
| CLAIM-02 | `json_view` renderer exists in the Workspace — dispatched when `file_type === "json_view"` | Open a `json_view` workspace item → see rendered views instead of raw JSON |
| CLAIM-03 | Table view renders `{headers, rows}` with inline-editable cells | Click cell → input appears → edit → save → cell updates in DB |
| CLAIM-04 | List view renders `{listStyle, items}` with inline-editable items | Click item → input appears → edit → save → item text updates in DB |
| CLAIM-05 | Cards view renders `{pairs}` as key-value cards | Click value → input appears → edit → save → value updates in DB |
| CLAIM-06 | Client-side view switching: user can toggle between compatible view types without agent call | Click "View as Cards" on a table → same data payload, different renderer |
| CLAIM-07 | Agent can produce composite views (array of views in one envelope) | Agent says "analyze this credit report" → single workspace item with cards + table + list |
| CLAIM-08 | Agent has tool instructions for when and how to produce `json_view` items | Agent chooses appropriate viewType(s) based on data structure without being explicitly told which view type to use |
| CLAIM-09 | View edits do not touch source blocks | Edit a cell value → source block text is unchanged; only `drafts.content` is modified |

## 3. The Elements

| Element | Purpose | Belongs To |
|---------|---------|------------|
| View Envelope Schema (TypeScript + Python) | Validate `{views: [{viewType, title, data}]}` structure | CLAIM-01 |
| `JsonViewRenderer` component | Dispatcher: reads `viewType` → renders correct sub-component | CLAIM-02 |
| `DynamicTable` component | Renders `viewType: "table"` with sortable headers + inline edit | CLAIM-03 |
| `DynamicList` component | Renders `viewType: "list"` with checkbox/ordered/bullet styles + inline edit | CLAIM-04 |
| `DynamicCards` component | Renders `viewType: "cards"` as key-value card grid + inline edit | CLAIM-05 |
| `ViewSwitcher` component | Dropdown/toggle to switch between compatible view types client-side | CLAIM-06 |
| `ViewComposer` component | Renders array of views as sections in a scrollable viewport | CLAIM-07 |
| Agent skill: `dynamic-views` | Prompt instructions for the agent on producing view envelopes | CLAIM-08 |
| Updated `create_workspace_item` validation | Reject `json_view` items with invalid envelopes | CLAIM-01 |
| `useInlineEdit` hook | Shared inline editing logic (click-to-edit, save on blur/Enter, debounced PATCH) | CLAIM-03, CLAIM-04, CLAIM-05 |

## 4. The Evidence

**Tech Stack:** Python FastAPI + PostgreSQL + Next.js 16 + React 19 + TypeScript + Tailwind CSS 4

**External APIs:** None. Views are self-contained in the Vision database.

**View Envelope Contract (v1):**

```json
{
  "documentMetadata": {
    "title": "Credit Report Analysis",
    "sourceId": "doc_credit_001",
    "lastUpdated": "2026-06-16T12:00:00Z"
  },
  "views": [
    {
      "viewType": "cards",
      "title": "Summary",
      "data": {
        "pairs": [
          { "key": "Total Negative Accounts", "value": "7" },
          { "key": "Total Balance Owed", "value": "$23,450" }
        ]
      }
    },
    {
      "viewType": "table",
      "title": "Negative Accounts Detail",
      "data": {
        "headers": ["Account Name", "Balance", "Status", "Dispute Status"],
        "rows": [
          { "id": "1", "Account Name": "Chase Bank", "Balance": "$4,230", "Status": "Delinquent", "Dispute Status": "Unresolved" },
          { "id": "2", "Account Name": "Wells Fargo", "Balance": "$1,150", "Status": "Charge-Off", "Dispute Status": "In Progress" }
        ]
      }
    },
    {
      "viewType": "list",
      "title": "Recommended Actions",
      "data": {
        "listStyle": "checkbox",
        "items": [
          { "id": "t1", "text": "Dispute Chase Bank account with Equifax", "completed": false },
          { "id": "t2", "text": "Request debt validation from Wells Fargo", "completed": false },
          { "id": "t3", "text": "File FCRA complaint for unresolved disputes", "completed": false }
        ]
      }
    }
  ]
}
```

**V1 View Types:**

| viewType | Data Shape | Compatible With | Description |
|----------|-----------|-----------------|-------------|
| `table` | `{headers: string[], rows: {id, ...}[]}` | cards, (future: chart, spreadsheet) | Sortable, filterable data table |
| `list` | `{listStyle: "checkbox"\|"ordered"\|"bullet", items: {id, text, completed?}[]}` | (none — structural) | Checklist, steps, or bullet points |
| `cards` | `{pairs: {key, value}[]}` | table (if tabular data) | Key-value summary in card grid |

**Compatible view type transitions (client-side, no agent call):**
- `table` ↔ `cards` (when table rows have clear key-value pairs)
- Future: `table` ↔ `chart` ↔ `spreadsheet`

**Structural view type transitions (agent re-generation required):**
- `table` → `list` (data structure fundamentally changes)
- `list` → `letter` (narrative generation needed)
- Any → composite (agent decides which views to add/remove)

**Fixture Data:** The envelope above is the fixture. It covers all three v1 view types in a composite layout.

## 5. Existing Infrastructure

### Related Existing Tables
| Table | Relationship | Location |
|-------|-------------|----------|
| `drafts` | Views are stored as rows with `file_type = "json_view"` | `schemas/001_core.sql:522-546` |
| `documents` / `sections` / `blocks` | Source data the agent reads to produce views | `schemas/001_core.sql:159-263` |
| `cases` | FK: `drafts.case_id → cases.id` | `schemas/001_core.sql:49-83` |

### Related Existing Endpoints
| Endpoint | What It Does | Reuse or Extend? |
|----------|--------------|------------------|
| `GET /api/cases/{case_id}/workspace` | List workspace items, supports `?folder=` and `?file_type=` | **Reuse** — `json_view` items appear in listings automatically |
| `GET /api/workspace/{item_id}` | Get full workspace item with content | **Reuse** — no changes needed |
| `POST /api/workspace` | Create workspace item | **Extend** — add envelope validation for `file_type: "json_view"` |
| `PATCH /api/workspace/{item_id}` | Update workspace item (name, content, folder, etc.) | **Reuse** — handles inline edit saves |
| `PATCH /api/workspace/{item_id}/blocks/{block_id}` | Update single block within structured_draft | **Not used** — inline edits on views go through full-content PATCH, not block-level |

### Related Existing Components
| Component | Purpose | Location | Action |
|-----------|---------|----------|--------|
| `WorkspaceTab` | File explorer + viewport with renderer dispatch | `frontend/src/app/tabs/WorkspaceTab.tsx` | **Extend** — add `json_view` case to renderer dispatch |
| `FileExplorer` | Folder tree + item list | `frontend/src/app/components/FileExplorer.tsx` | **Reuse** — no changes needed |
| `DraftPreview` | Block-type-aware document with inline editing | `frontend/src/app/components/DraftPreview.tsx` | **Reference** — borrow inline edit pattern, don't extend |
| `MarkdownRenderer` | Rendered markdown + source editor | `frontend/src/app/components/MarkdownRenderer.tsx` | **Reference** — edit toggle pattern |

### Related Agent Tools
| Tool | Purpose | Location | Action |
|------|---------|----------|--------|
| `create_workspace_item` | Agent creates workspace items | `backend/chat/tools.py` | **Extend** — add envelope validation; update prompt to include view schema |
| `update_workspace_item` | Agent modifies workspace items | `backend/chat/tools.py` | **Reuse** — no changes needed |
| `list_workspace_items` | Agent surveys existing items | `backend/chat/tools.py` | **Reuse** — no changes needed |
| `get_workspace_item` | Agent reads full content before editing | `backend/chat/tools.py` | **Reuse** — no changes needed |

### Known Constraints
- [x] Must use existing `drafts` table with `file_type = "json_view"` — no new tables
- [x] Must use existing workspace API endpoints — extend, don't replace
- [x] Must use existing design tokens (`--surface-*`, `--text-*`, `--brand`, `--border`, etc.)
- [x] Must use existing renderer dispatch pattern in `WorkspaceTab`
- [x] Must use existing agent tool closure pattern (`create_vision_server` style)
- [x] Must not break existing `markdown`, `structured_draft`, or `html` renderers
- [x] Inline editing must use the same `PATCH /api/workspace/{id}` endpoint as other file types
- [x] This will be registered as a skill (`dynamic-views`) so agents know the envelope contract

## 6. Pre-Mortem

**What could break?**
- Concurrent edits: agent regenerates a view while user is editing cells → last-write-wins could clobber user changes. Mitigation: agent should `get_workspace_item` before overwriting, and UI should warn if content has changed since load.
- Large datasets: a table with 5,000 rows in a JSONB column will be slow to render and painful to edit. Mitigation: v1 doesn't paginate (keep datasets small via agent prompting); v2 adds virtual scrolling + server-side pagination.
- Envelope validation divergence: TypeScript and Python validators get out of sync. Mitigation: single source of truth — JSON Schema — used by both.
- View switching data loss: user edits a cell, then switches view type before save. Mitigation: auto-save on blur before view switch executes.
- Agent produces invalid envelopes: the agent hallucinates a `viewType` that doesn't exist or a malformed `data` shape. Mitigation: strict server-side validation rejects invalid envelopes with a descriptive error the agent can self-correct.

**What assumptions are we making?**
- Agent can correctly classify data into table/list/cards shapes without explicit user instruction
- Users will interact with views primarily through inline editing, not raw JSON editing
- Three view types (table, list, cards) cover the v1 use cases sufficiently
- The `drafts.content` JSONB column can handle view payloads (< 1MB per item)
- Last-write-wins is acceptable for v1; no CRDT or OT needed

**What do we NOT know yet?**
- Whether the agent consistently chooses the right viewType for a given dataset
- How users will actually use view switching (client-side toggle vs. chat command)
- Whether three view types are sufficient for the first real use cases (credit report analysis, bank statement review)
- What the performance ceiling is for inline editing large JSONB payloads
- Whether the `html` escape hatch will see significant use or remain a safety valve

## 7. Out of Scope (Explicit)

- **Dynamic folder system** — Google Drive-like nesting is a separate feature with its own schema migration
- **Charts/graphs** — v2 view types (requires charting library evaluation)
- **Override tracking** — v1 uses mutable JSONB; source vs. override distinction is v2
- **Real-time collaboration** — single user per case; no CRDT or operational transform
- **Agent-invented HTML views** — the `html` file type exists as an escape hatch but is not part of the Dynamic View System
- **Spreadsheet view** — v2 view type (requires formula engine evaluation)
- **Timeline view** — v2 view type (requires chronological data model)

## 8. Approval Gate

**Status:** [ ] DRAFT  [x] APPROVED

**Approved By:** Ian Bruce

**Date:** 2026-06-16 

---

> ⚠️ **EXIT CONDITION:** This Brief is not approved until all Claims have defined Verdicts and the Tech Stack is explicit. No ambiguity allowed.
