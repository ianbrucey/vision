# Workspace Feature Regression — Remote vs Local Diff

**Date:** 2026-07-22
**Finding:** The local codebase (`/Users/ianbruce/code/vision`, branch `talentlynk`)
has regressed on multiple workspace features that exist on the remote server
(`/root/vision`, the old deployment). The remote has more advanced folder
management, a tabbed file interface, and CSS fixes that were lost or reverted
locally.

**Root cause:** Remote changes were made directly on the server (rsync deploy,
not git) and never pushed back to the GitHub repo. The local branch diverged
without those changes.

---

## Summary of Regressions

| # | Feature | Remote (`/root/vision`) | Local (`talentlynk`) | Status |
|---|---------|------------------------|----------------------|--------|
| 1 | Folder deletion (UI + API + DB) | Full | Missing | **REGRESSED** |
| 2 | `folder_id` on draft CRUD | Integrated | Missing | **REGRESSED** |
| 3 | Tabbed file interface | Multi-tab w/ localStorage | Single active item | **REGRESSED** |
| 4 | Context menu (right-click) | Delete file/folder, add-to-folder | Missing | **REGRESSED** |
| 5 | Agent background update listener | `vision_workspace_updated` event | Missing | **REGRESSED** |
| 6 | New-file dropdown opacity fix | `bg-surface-1` opaque, `z-50` | `bg-[--surface-4]`, `z-20` (partially opaque) | **REGRESSED** |
| 7 | Expanded-folder persistence | localStorage per case/workspace | Not persisted | **REGRESSED** |
| 8 | File-type icon colors | Color-coded by type | All same color | **REGRESSED** |
| 9 | Tree indentation lines | Vertical border-l guides | Missing | **REGRESSED** |
| 10 | Agent `list_folders`/`create_folder` tools | Present (both) | Present (both) | OK |
| 11 | Agent `folder_id` param on workspace tools | Integrated | Uses old `folder` string | **REGRESSED** |
| 12 | Default folder | `artifacts` | `freestyle` | **CHANGED** |
| 13 | `006_folders.sql` schema | Identical | Identical | OK |
| 14 | `list_folders` sentinel behavior | `-1` = all, `0`/null = root | `0` = root only (no "all") | **REGRESSED** |

---

## Detailed Findings by File

### 1. `backend/core/db.py` — MISSING FUNCTIONS

**Local is missing 3 functions** that exist on the remote:

- `get_folder(conn, folder_id)` — fetch a single folder by ID
- `update_folder(conn, folder_id, name, parent_id)` — rename/move a folder
- `delete_folder(conn, folder_id)` — cascade delete folder + all subfolders + all drafts inside (recursive CTE)

**Local `list_folders` is simpler** — no `-1` sentinel for "fetch all folders":
- Remote: `parent_id=-1` → returns ALL folders; `parent_id=0`/`null` → root only
- Local: `parent_id=0` → root only; no "fetch all" path

**Local `list_drafts` / `create_draft` / `update_draft` missing `folder_id`:**
- Remote `list_drafts` accepts `folder_id` param, filters by it, returns `folder_id` in SELECT
- Remote `create_draft` accepts `folder_id`, inserts it
- Remote `update_draft` accepts `folder_id`, updates it
- Local versions: **zero references to `folder_id`** — still uses old `folder` TEXT column only

### 2. `backend/api/routes/workspace.py` — MISSING ENDPOINT + FOLDER_ID

**Local is missing `DELETE /folders/{folder_id}` endpoint** (remote lines 288-305):
```python
@router.delete("/folders/{folder_id}")
def delete_folder_endpoint(folder_id, user=...):
    from core.db import delete_folder as _delete_folder
    ok = _delete_folder(conn, folder_id)
    ...
```

**Local `CreateItemRequest` missing `folder_id` field** — remote has `folder_id: int | None = None`
on both the request model and the create-item handler (line 169: `folder_id=body.folder_id`).

**Local `list_folders_endpoint` sentinel mismatch** — remote uses `-1` for "all",
local uses `0`.

**Default folder changed:** remote `folder: str = "artifacts"`, local `folder: str = "freestyle"`.

### 3. `frontend/src/components/FileExplorer.tsx` — MAJOR REGRESSION

Remote: 356 lines. Local: 257 lines. **~100 lines of functionality lost.**

**Missing from local:**
- `deleteFolder`, `deleteWorkspaceItem` imports from `@/lib/api`
- `Trash2` icon import
- `handleDeleteFolder()` — confirm + delete + refresh + dispatch update event
- `handleDeleteFile()` — confirm + delete + dispatch update event
- `handleContextMenu()` — right-click context menu state
- Context menu click-outside listener (`useEffect`)
- **Expanded folder persistence** to localStorage (`vision_explorer_expanded_{caseId}_{workspaceId}`)
- **File-type icon colors** (`FILE_TYPE_ICON_COLOR` map: markdown=info, draft=brand, html=warning, json=success)
- **Tree indentation lines** (vertical `border-l` guides)
- **Context menu UI** (right-click → "Add to folder" / "Delete folder" / "Delete file")
- **Delete buttons** on folder rows (hover-to-reveal trash icon)
- `onContextMenu` handlers on folder + file rows

**CSS regression — New-file dropdown:**
- Remote: `bg-surface-1 border border-border rounded-lg shadow-xl z-50` (fully opaque, high z-index)
- Local: `bg-[--surface-4] border border-[--border] rounded-lg shadow-lg z-20` (surface-4 is less opaque, z-20 can be overlapped)

**CSS regression — class syntax:**
- Remote uses semantic tokens: `text-text-disabled`, `bg-surface-1`, `text-brand`
- Local uses raw CSS var syntax: `text-[--text-disabled]`, `bg-[--surface-2]` (older pattern, pre-design-system)

### 4. `frontend/src/app/cases/[id]/tabs/WorkspaceTab.tsx` — MAJOR REGRESSION

Remote: 715 lines. Local: 575 lines. **~140 lines of functionality lost.**

**Missing from local:**
- **Multi-tab file interface** — remote has `openTabIds[]` array, `activeTabId`, `openItemsData` map, `closeTab()` function, tab bar UI with per-tab close buttons, localStorage persistence (`vision_workspace_tabs_{caseId}`)
- Local reverted to single `activeItem` (one file open at a time)
- **Agent background update listener** — remote listens for `vision_workspace_updated` custom event to auto-refresh file list + active file content; local doesn't
- **`folder_id` on item creation** — remote passes `folder_id: folderId` to create API; local doesn't
- **`explorerRefreshKey`** — remote increments to force FileExplorer re-render after creates/deletes; local passes static `0`
- **`key` props on renderers** — remote uses `key={activeItem.id}` on Markdown/HTML/JSON renderers (forces remount on tab switch); local doesn't (stale state risk)

**Local-only addition (not in remote):**
- `PdfRenderer` component for `case "pdf"` file type — this is a local improvement that should be preserved

### 5. `frontend/src/lib/api.ts` — MISSING FUNCTION

**Local is missing `deleteFolder`:**
```typescript
// REMOTE has this, LOCAL does not:
export const deleteFolder = (folderId: number): Promise<{ deleted: boolean }> =>
  api(`/api/workspace/folders/${folderId}`, { method: "DELETE" });
```

Local has `listFolders`, `createFolder`, `deleteWorkspaceItem` — only `deleteFolder` is missing.

### 6. `backend/chat/tools.py` — FOLDER_ID NOT INTEGRATED

Remote: 4530 lines. Local: 4282 lines.

**Both have** `list_folders` and `create_folder` agent tools (Layer 6.6) — these are present locally.

**Remote uses `folder_id`** (integer FK) in workspace item tools:
- `list_workspace_items`: filters by `folder_id` (int)
- `create_workspace_item`: accepts `folder_id` (int), passes to `create_draft`
- `update_workspace_item`: accepts `folder_id` to move items between folders

**Local uses `folder`** (string: "freestyle"/"research"/"artifacts"):
- `list_workspace_items`: filters by `folder` (string)
- `create_workspace_item`: requires `folder` string, passes to `create_draft`
- `update_workspace_item`: accepts `folder` string

This is the old flat-folder model. The remote migrated to `folder_id` (hierarchical) but local never got that migration in the CRUD layer.

### 7. `backend/chat/prompt.py` — IDENTICAL

Both remote and local reference `folder` in the agent prompt. No diff.

### 8. `.claude/skills/workspace/SKILL.md` — IDENTICAL

No diff between remote and local.

### 9. `backend/schemas/006_folders.sql` — IDENTICAL

Both have the same schema creating the `folders` table + `folder_id` column on `drafts`.

### 10. `backend/init_db.py` — IDENTICAL (re: folders)

Both call `ensure_folders_schema()` during migration.

---

## What Needs to Be Restored

To bring local up to remote parity for workspace features, without touching
the new solicitation/vendor/mailgun work:

### Backend (minimal, folder-focused only):
1. **`db.py`**: Add `get_folder`, `update_folder`, `delete_folder` functions; add `folder_id` param to `list_drafts`, `create_draft`, `update_draft`; add `-1` sentinel to `list_folders`
2. **`workspace.py`**: Add `DELETE /folders/{folder_id}` endpoint; add `folder_id` to `CreateItemRequest` + create handler; fix `list_folders` sentinel to `-1`
3. **`chat/tools.py`**: Migrate workspace item tools from `folder` (string) to `folder_id` (int) — `list_workspace_items`, `create_workspace_item`, `update_workspace_item`

### Frontend:
4. **`api.ts`**: Add `deleteFolder` function
5. **`FileExplorer.tsx`**: Restore from remote version — folder deletion, context menu, expanded persistence, icon colors, tree lines, CSS fix (opaque dropdown, `z-50`, semantic tokens)
6. **`WorkspaceTab.tsx`**: Restore multi-tab interface + agent update listener + `folder_id` on create + `explorerRefreshKey` + `key` props. **Preserve local `PdfRenderer` addition.**

### NOT changing:
- No solicitation/vendor/mailgun code
- No new schemas (006 already exists locally)
- `SKILL.md`, `prompt.md`, `init_db.py` — already identical
