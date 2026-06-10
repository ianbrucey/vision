---
name: workspace
description: Reference for the Vision Workspace — the file explorer, content types, folder semantics, agent tools, API endpoints, and how the "Legal IDE" metaphor maps to database rows.
---

# Workspace — Legal IDE Architecture

The Workspace is a database-backed "file explorer" that replaces the legacy Drafts tab. It follows a **Legal IDE** metaphor — think VS Code's explorer panel, but every "file" is a row in the `drafts` table and every "folder" is a TEXT column value.

---

## Data Model — Single Table

Everything lives in the `drafts` table:

| Column | Type | Purpose |
|---|---|---|
| `id` | SERIAL PK | Item identifier |
| `case_id` | FK → cases | Scopes items to a case |
| `name` | TEXT | Display title in the file explorer |
| `file_type` | TEXT (CHECK) | Determines renderer and editor |
| `document_type` | TEXT (CHECK) | Legal classification (orthogonal to file_type) |
| `folder` | TEXT | Groups items into folders |
| `content` | JSONB | The actual content, structure varies by file_type |
| `status` | TEXT (CHECK) | draft / review / final |
| `created_by` | TEXT (CHECK) | agent / user |
| `metadata` | JSONB | Extensible metadata |

**There is no folders table.** Folders (`freestyle`, `research`, `artifacts`) are hardcoded in the FileExplorer component. Items are grouped by the `folder` column value.

---

## File Types

| file_type | Content Envelope | Renderer | User Edits? | Agent Creates? |
|---|---|---|---|---|
| `markdown` | `{"markdown": "string"}` | MarkdownRenderer | Yes (source) | Yes |
| `structured_draft` | `[{id, type, content}, ...]` | DraftPreview | Yes (inline blocks) | Yes |
| `html` | `{"html": "string"}` | Stub (Phase 2) | No | Yes |
| `json_view` | `{"data": {...}}` | Stub (Phase 3) | No | Yes |

**Content envelope detail:** The `content` JSONB column always stores an array. For markdown, this is `[{"markdown": "..."}]` — a single-element array wrapping the envelope object. For structured drafts, it's the block array directly: `[{"id":"b1","type":"section_heading","content":"TITLE"}, ...]`.

---

## Folder Semantics

| Folder | Intended Purpose | Default Contents |
|---|---|---|
| `freestyle` | Agent-owned HTML and print-formatted output. Not human-editable. | Empty in Phase 1 |
| `research` | Research notes, analysis, scratch paper. Markdown. Human-editable. | Empty in Phase 1 |
| `artifacts` | Structured legal drafts and formatted data. "Final product" folder. | Existing drafts (migrated) |

These three folders are always visible in the FileExplorer, even when empty. New files default to the folder the user clicked "+" in.

---

## API Endpoints

All endpoints are in `backend/api/routes/workspace.py`, registered in `api/main.py` via `app.include_router(workspace_router)`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/cases/{case_id}/workspace` | List items. Supports `?folder=` and `?file_type=` filters |
| GET | `/api/workspace/{item_id}` | Get full item with content |
| POST | `/api/workspace` | Create item |
| PATCH | `/api/workspace/{item_id}` | Update item (name, content, folder, status, file_type) |
| PATCH | `/api/workspace/{item_id}/blocks/{block_id}` | Update single block (structured_draft only) |
| DELETE | `/api/workspace/{item_id}` | Delete item |

All endpoints use the same auth pattern (`Depends(get_current_user)`). Reads use `connect()` + `try/finally`. Writes use `with tx() as conn:`.

The **legacy draft endpoints** (`/api/drafts/*`) are preserved and still functional — they were extended (not replaced) with `file_type` and `folder` support.

---

## Agent Tools

Four tools registered in `create_vision_server(case_id)` at `backend/chat/tools.py`:

| Tool | Type | Purpose |
|---|---|---|
| `list_workspace_items` | Read | List items with optional folder/file_type filters |
| `get_workspace_item` | Read | Get full content (use before editing) |
| `create_workspace_item` | Write | Create item with `file_type`, `folder`, and content envelope |
| `update_workspace_item` | Write | Modify name, content, folder, or status |

All tools are **closure-scoped** to `case_id` — the agent never provides or sees the case_id. The `folder` parameter on `create_workspace_item` is a required enum: `"freestyle" | "research" | "artifacts"`.

### Agent Workflow
```
1. list_workspace_items     → survey what exists
2. get_workspace_item       → read full content before editing
3. create_workspace_item    → write new item to a folder
4. update_workspace_item    → modify existing item
```

---

## DB Helpers

All workspace data flows through existing `core/db.py` functions, extended with `file_type` and `folder` params:

- `insert_draft(conn, case_id, name, ..., file_type="structured_draft", folder="artifacts")` → int
- `update_draft(conn, draft_id, ..., file_type=None, folder=None)` → dict | None
- `list_drafts(conn, case_id, folder=None)` → list[dict] (includes file_type and folder in SELECT)
- `get_draft(conn, draft_id)` → dict | None (SELECT * covers new columns)
- `delete_draft(conn, draft_id)` → bool
- `update_block(conn, draft_id, block_id, content)` → dict | None (surgical JSONB update)

---

## Frontend Component Tree

```
WorkspaceTab (tabs/WorkspaceTab.tsx)
├── FileExplorer (components/FileExplorer.tsx)
│   ├── Folder: freestyle  (always visible, even if empty)
│   ├── Folder: research   (always visible, even if empty)
│   └── Folder: artifacts  (always visible, even if empty)
│       └── items grouped by folder column
└── Main Viewport
    ├── Toolbar (name, status, edit toggle, delete)
    └── Renderer (dispatched by file_type)
        ├── MarkdownRenderer (components/MarkdownRenderer.tsx)
        │   ├── Rendered view: ReactMarkdown v10
        │   └── Source editor: textarea with Cmd+Enter save
        └── DraftPreview (components/DraftPreview.tsx, reused)
            └── Block-type-aware formatted document with inline editing
```

---

## URL State Persistence

Workspace tab state lives in URL search params to survive refresh:

```
/cases/{id}?tab=workspace&item=5&folder=research
```

- `tab=workspace` — managed by parent page.tsx
- `item=5` — the active item ID, managed by useWorkspaceUrl hook
- `folder=research` — the selected folder filter, managed by useWorkspaceUrl hook

On mount, the `useEffect` respects `item` param: if the item exists in the loaded list, it's selected; otherwise, falls back to the first item.

---

## Mobile Layout

Mobile uses sequential views (not split-panel):
- **List view:** Full-width FileExplorer
- **Preview view:** Full-width renderer with back button
- State machine controlled by `mobileView: "list" | "preview"`

---

## What's Preserved (Legacy Drafts)

The old Drafts system is fully preserved:
- `DraftsTab.tsx` — intact, accessible via `?tab=drafts`
- `DraftPreview.tsx` — intact, reused by WorkspaceTab for structured_draft
- All 6 `/api/drafts/*` endpoints — intact
- All 4 draft agent tools (`list_drafts`, `get_draft`, `create_draft`, `update_draft`) — intact

The `drafts` entry was removed from the `TABS` array in `TabNav.tsx` but `"drafts"` remains in the `TabId` type union for URL backward compatibility.

---

## Migration

Schema migration v11 in `backend/schemas/001_core.sql`:
```sql
ALTER TABLE drafts ADD COLUMN IF NOT EXISTS file_type TEXT NOT NULL DEFAULT 'structured_draft'
    CHECK (file_type IN ('markdown', 'structured_draft', 'html', 'json_view'));
ALTER TABLE drafts ADD COLUMN IF NOT EXISTS folder TEXT NOT NULL DEFAULT 'artifacts';
```

Existing drafts silently became `file_type: structured_draft, folder: artifacts` — no data migration needed.

---

## Phase Boundaries

**Phase 1 (current):** Workspace shell, FileExplorer, Markdown renderer/editor, structured_draft (reused), URL state persistence, auto-save on blur.

**Phase 2 (future):** HTML freestyle renderer (sandboxed iframe), print CSS for 8.5×11.

**Phase 3 (future):** Formatted JSON viewer (tables, cards, lists).

**Out of scope:** Folder CRUD (folders are static), drag-and-drop, markdown toolbar, item reordering.
