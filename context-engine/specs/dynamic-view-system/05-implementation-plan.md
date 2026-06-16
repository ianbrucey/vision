# Dynamic View System — Implementation Plan

> **Version:** 1.0 | **Status:** Draft | **Depends on:** `00-Brief.md` (APPROVED), `01-view-envelope-schema.json`, `04-ui-specs.md`

---

## Sequencing Strategy

**Backend-out:** Backend validation → Agent skill → Frontend components. The database schema already supports `json_view` — no migration needed.

**Atomic tickets:** Each ticket is independently completable and testable. A ticket is not "done" until its Verdict passes.

---

## Ticket Summary

| # | Ticket | Layer | Depends On | Est. Complexity |
|---|--------|-------|------------|-----------------|
| T01 | Envelope validation in API | Backend | None | Small |
| T02 | Agent skill: `dynamic-views` | Agent Config | T01 | Medium |
| T03 | `useInlineEdit` hook | Frontend | None | Medium |
| T04 | `DynamicCards` component | Frontend | T03 | Small |
| T05 | `DynamicTable` component | Frontend | T03 | Medium |
| T06 | `DynamicList` component | Frontend | T03 | Medium |
| T07 | `ViewSwitcher` component | Frontend | T04, T05 | Small |
| T08 | `ViewComposer` + `JsonViewRenderer` | Frontend | T04, T05, T06, T07 | Medium |
| T09 | WorkspaceTab integration | Frontend | T08 | Small |
| T10 | End-to-end verification | All | T01-T09 | Small |

---

## T01 — Envelope Validation in API

**File:** `backend/api/routes/workspace.py`
**New file:** `backend/schemas/view_envelope.py` (Python validation using `jsonschema` library)

**Work:**
1. Add `jsonschema` to `backend/requirements.txt` if not present
2. Create `backend/schemas/view_envelope.py`:
   - Load `01-view-envelope-schema.json` from the specs directory
   - Export `validate_view_envelope(content: dict) -> tuple[bool, str | None]` — returns (valid, error_message)
3. **Fix Pydantic content type:** In `backend/api/routes/workspace.py`:
   - Change `UpdateWorkspaceItemRequest.content: list | None` → `content: list | dict | None`
   - Change `CreateWorkspaceItemRequest.content: list = []` → `content: list | dict = []`
   - Reason: `json_view` content is a dict (`{documentMetadata, views}`), not an array. Existing file types send lists — this is backward-compatible.
4. In `create_workspace_item_endpoint` and `update_workspace_item_endpoint`:
   - If `file_type == "json_view"`, validate `body.content` against the envelope schema
   - Reject with 422 and the schema violation message if invalid
5. Write a Python test that validates the fixture file, then mutates it to invalid and confirms rejection

**Verdict:**
- [ ] Valid fixture envelope passes validation (returns True)
- [ ] Envelope missing `documentMetadata` returns False with descriptive error
- [ ] Envelope with unknown `viewType` returns False with descriptive error
- [ ] Envelope with table missing `headers` returns False with descriptive error
- [ ] `POST /api/workspace` with `file_type: "json_view"` and invalid content returns 422
- [ ] `PATCH /api/workspace/{id}` with `file_type: "json_view"` and invalid content returns 422

**Files touched:** `backend/api/routes/workspace.py` (~25 lines changed: Pydantic types + validation calls), new `backend/schemas/view_envelope.py` (~40 lines)

---

## T02 — Agent Skill: `dynamic-views`

**File:** `.claude/skills/dynamic-views/SKILL.md`

**Work:**
Create the skill file that teaches agents how to produce `json_view` workspace items. Must include:
1. What the Dynamic View System is and when to use it
2. The view envelope schema (referencing `01-view-envelope-schema.json`)
3. When to choose each `viewType`:
   - `table`: Data has consistent columns across multiple entities (accounts, transactions, line items)
   - `list`: Sequential steps, action items, chronological entries, checklists
   - `cards`: Summary metrics, key-value overviews, dashboard stats
4. The composite pattern: summary cards first, then detail table, then action list
5. How to create a view: use `create_workspace_item` with `file_type: "json_view"` and `folder: "artifacts"`
6. Examples: credit report analysis, bank statement review
7. Anti-patterns: don't use json_view for narrative text (use markdown), don't invent viewTypes, don't put 5000 rows in a table
8. Source citation: when extracting data from blocks, include `sourceId` in `documentMetadata` referencing the document

**Verdict:**
- [ ] Agent given "analyze this credit report" produces a valid `json_view` envelope
- [ ] Agent chooses appropriate viewType(s) without being told which one
- [ ] Agent includes source document reference in `documentMetadata.sourceId`
- [ ] Agent does not produce `viewType: "chart"` or other undefined types

**Files touched:** `.claude/skills/dynamic-views/SKILL.md` (new, ~120 lines)

---

## T03 — `useInlineEdit` Hook

**File:** `frontend/src/hooks/useInlineEdit.ts`

**Work:**
1. Implement the hook as specified in `04-ui-specs.md` §8
2. Key behaviors:
   - `startEdit(cellKey, currentValue)` → sets editing state
   - `commitEdit()` → deep clones, updates value at path, calls `PATCH /api/workspace/{itemId}`
   - `cancelEdit()` → reverts
   - Auto-save on blur
   - Debounced saves (no API call per keystroke)
3. Handle edge cases:
   - Concurrent edits (user edits cell A, then cell B, while A's save is in-flight)
   - Network error (show error, revert on failure)
   - Rapid blur-then-focus (user blurs one cell, immediately clicks another)
4. Export the hook and its return type

**Verdict:**
- [ ] `startEdit` sets editing state correctly
- [ ] `commitEdit` sends correct PATCH with updated envelope
- [ ] `cancelEdit` restores original value
- [ ] Blur triggers auto-save
- [ ] Network error reverts and shows error
- [ ] Rapid edit sequences don't corrupt state

**Files touched:** `frontend/src/hooks/useInlineEdit.ts` (new, ~100 lines)

---

## T04 — `DynamicCards` Component

**File:** `frontend/src/components/views/DynamicCards.tsx`

**Work:**
1. Implement the card grid as specified in `04-ui-specs.md` §6
2. Render `pairs[]` in a responsive grid
3. Apply emphasis styling based on `pair.emphasis`
4. Integrate `useInlineEdit` for value editing on click
5. Handle empty state
6. Use existing design tokens exclusively

**Verdict:**
- [ ] Renders 4 pairs in a 2-col grid on mobile, 4-col on desktop
- [ ] Emphasis colors apply correct left border and text color
- [ ] Click value → input appears → edit → save persists to DB
- [ ] Key labels are not editable
- [ ] Empty pairs array shows "No data" state

**Files touched:** `frontend/src/components/views/DynamicCards.tsx` (new, ~80 lines)

---

## T05 — `DynamicTable` Component

**File:** `frontend/src/components/views/DynamicTable.tsx`

**Work:**
1. Implement the table as specified in `04-ui-specs.md` §4
2. Render headers + rows with alternating stripes
3. Implement client-side sort (click header → asc → desc → off)
4. Integrate `useInlineEdit` for cell editing
5. `id` column: read-only, muted styling
6. Mobile: card stack layout (< 768px)
7. Handle empty rows array

**Verdict:**
- [ ] Renders table with correct headers and row count
- [ ] Click header → rows sort ascending by that column
- [ ] Click same header again → rows sort descending
- [ ] Click cell → input appears → edit → save persists to DB
- [ ] `id` column cells are not editable
- [ ] Mobile viewport (< 768px) renders as card stack
- [ ] Empty rows shows "No data available"

**Files touched:** `frontend/src/components/views/DynamicTable.tsx` (new, ~180 lines)

---

## T06 — `DynamicList` Component

**File:** `frontend/src/components/views/DynamicList.tsx`

**Work:**
1. Implement the list as specified in `04-ui-specs.md` §5
2. Support all three `listStyle` variants: checkbox, ordered, bullet
3. Checkbox style: toggle completion on click → immediate save
4. Integrate `useInlineEdit` for item text editing (double-click)
5. Render item `notes` when present
6. Handle empty items array

**Verdict:**
- [ ] Checkbox list renders with checkboxes, completed items get line-through
- [ ] Click checkbox → toggles completed → saves immediately
- [ ] Ordered list renders with auto-numbering
- [ ] Bullet list renders with bullets
- [ ] Double-click item text → textarea → edit → save persists to DB
- [ ] Item notes render below item text when present

**Files touched:** `frontend/src/components/views/DynamicList.tsx` (new, ~140 lines)

---

## T07 — `ViewSwitcher` Component

**File:** `frontend/src/components/views/ViewSwitcher.tsx`

**Work:**
1. Implement the view switcher as specified in `04-ui-specs.md` §7
2. Implement compatibility matrix (table ↔ cards; list has no alternatives)
3. Implement transformation logic:
   - Table → Cards: convert rows to pairs
   - Cards → Table: convert pairs to 2-column table rows
4. Render dropdown with compatible view type options
5. On switch: transform data, immediately save via PATCH
6. Don't show switcher when no compatible alternatives exist

**Verdict:**
- [ ] Table view shows "View as Cards" option in dropdown
- [ ] Clicking "View as Cards" transforms data and saves — viewType changes
- [ ] Cards view shows "View as Table" option
- [ ] Clicking "View as Table" transforms data and saves — viewType changes
- [ ] List view does NOT show ViewSwitcher (no compatible alternatives)
- [ ] Transformed data preserves title and description

**Files touched:** `frontend/src/components/views/ViewSwitcher.tsx` (new, ~80 lines)

---

## T08 — `ViewComposer` + `JsonViewRenderer`

**Files:**
- `frontend/src/components/views/JsonViewRenderer.tsx`
- `frontend/src/components/views/ViewComposer.tsx`

**Work:**
1. `JsonViewRenderer`:
   - Validate content envelope on mount
   - Error state for invalid envelopes
   - Single view: render directly without composer chrome
   - Multi-view: delegate to ViewComposer
2. `ViewComposer`:
   - Render each view as a section with header (title + description + ViewSwitcher)
   - Render appropriate view component (DynamicTable / DynamicList / DynamicCards)
   - Handle view-level error boundaries (one view fails, others still render)

**Verdict:**
- [ ] Valid single-view envelope renders the view directly
- [ ] Valid multi-view envelope renders sections with headers
- [ ] Each section has title, description (if present), and ViewSwitcher (if compatible)
- [ ] Invalid envelope shows error card with violation details
- [ ] Empty views array shows "No views" state
- [ ] One view error doesn't crash other views

**Files touched:**
- `frontend/src/components/views/JsonViewRenderer.tsx` (new, ~60 lines)
- `frontend/src/components/views/ViewComposer.tsx` (new, ~50 lines)

---

## T09 — WorkspaceTab Integration

**File:** `frontend/src/app/cases/[id]/tabs/WorkspaceTab.tsx`

**Work:**
1. Add `json_view` case to the renderer dispatch
2. Ensure `isEditing` defaults to `true` for `json_view` items
3. Wire up the content prop from `drafts.content` to `JsonViewRenderer`
4. No changes to FileExplorer, toolbar, or API layer

**Verdict:**
- [ ] Click a `json_view` workspace item → JsonViewRenderer renders
- [ ] Other file types (markdown, structured_draft) still render correctly
- [ ] Edit toggle in toolbar works for json_view (edit mode = cells clickable, view mode = read-only)

**Files touched:** `frontend/src/app/cases/[id]/tabs/WorkspaceTab.tsx` (~10 lines added)

---

## T10 — End-to-End Verification

**Work:**
1. Run the full loop using the fixtures:
   - Create a case with credit report documents
   - Agent analyzes the documents → produces `json_view` workspace item
   - User opens the workspace item → sees composite view (cards + table + list)
   - User edits a cell → save persists
   - User switches view type → data transforms
   - User asks agent to update the view → agent regenerates
2. Verify all 9 Brief Success Verdict checkboxes
3. Verify all ticket-level verdicts

**Verdict:**
- [ ] All 9 Brief Success Verdicts pass
- [ ] All T01-T09 ticket verdicts pass
- [ ] No console errors in browser
- [ ] No 500 errors in API logs
- [ ] Existing workspace functionality (markdown, structured_draft) is not broken
