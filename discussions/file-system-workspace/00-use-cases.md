# File System Workspace — Use Cases & Refactor Plan

> **Status:** DISCOVERY — Updated 2026-06-10
> **Decisions made:** 2
> **Open questions:** 3

---

## Decisions Made

### D-1: `file_type` and `document_type` are separate dimensions
- `file_type` → determines renderer/editor (html | markdown | structured_draft | json_view)
- `document_type` → legal classification (letter | pleading | contract | memo | other)
- They coexist. file_type is the new addition; document_type is preserved from drafting-mvp.

### D-2: Editing model is determined by file_type
- **HTML (freestyle):** Agent-only canvas. Never edited by humans. Agent controls all styling. Primary purpose: print-formatted output on 8.5×11.
- **Markdown:** Human-editable. Used for artifacts, scratch paper, informal notes. Rendered preview + source editor toggle.
- **Structured Draft:** Human-editable at block level. Agent writes JSON blocks, user makes inline edits through formatted UI.
- **Formatted JSON:** Read-only view of agent-produced structured data. For non-technical users.

---

## The Four Use Cases

### UC-1: HTML Documents — "Freestyle"
**Agent role:** Writes complete HTML documents with embedded styling.
**User role:** Views rendered output in-browser. Prints to 8.5×11. Does NOT edit source.
**Storage:** Database row — `file_type: html`, full HTML string in content column.
**Renderer:** Sandboxed iframe. Print CSS is the agent's responsibility.
**User creates?** No.
**User edits?** No.

### UC-2: Markdown Documents
**Agent role:** Writes Markdown prose. Summaries, analysis, notes.
**User role:** Views rendered Markdown. Toggles to source editor to make changes. Casual editing.
**Storage:** Database row — `file_type: markdown`, raw Markdown string in content column.
**Renderer:** Markdown→HTML rendered view. Toggle to monospace textarea for source editing.
**User creates?** Yes — "New scratch note."
**User edits?** Yes — source editor.

### UC-3: Structured Legal Drafts — JSON → Formatted HTML
**Agent role:** Writes typed JSON blocks (section_heading, numbered_paragraph, list_item, signature).
**User role:** Views professionally formatted document. Edits individual blocks inline through the UI (not raw JSON).
**Storage:** Database row — `file_type: structured_draft`, JSONB array of typed blocks in content column.
**Renderer:** Block-type-aware HTML renderer. Print CSS for 8.5×11. Auto-numbering at render time.
**User creates?** Yes — "New letter/memo/pleading."
**User edits?** Yes — block-level inline editing.

### UC-4: Formatted JSON Viewer
**Agent role:** Produces structured JSON data (timelines, matrices, party lists).
**User role:** Views data in formatted tables/cards. No raw JSON visible.
**Storage:** Database row — `file_type: json_view`, JSONB in content column.
**Renderer:** Structure-aware layout (tables for arrays of objects, cards for key-value, lists for arrays of primitives).
**User creates?** No.
**User edits?** No.

---

## The Workspace Metaphor

The previous app operated like a **Legal IDE** — VS Code's file explorer, but backed by database rows instead of filesystem files.

- **File explorer sidebar:** List of workspace items with type-specific icons
- **Main viewport:** The active item, rendered with the appropriate renderer/editor for its `file_type`
- **Print:** A first-class action, not an afterthought — especially for HTML and Structured Drafts

---

## Open Questions

### Q-1: User file creation model
Should users be able to create files directly, or does the file explorer only track agent-created content?

**Current thinking:** It depends on file_type (see table above). Markdown and Structured Drafts allow user creation. HTML and JSON View are agent-only. But the UX for "New File" needs design:
- Option A: "New File" button → user picks from types they're allowed to create → blank editor opens
- Option B: "New File" button → opens a chat prompt: "What should the agent create?"
- Option C: Both — a split button (New Blank File / Ask Agent)

### Q-2: Folders / grouping
The previous app had a "freestyle folder." Was this a literal grouping/folder in the file explorer, or just a naming convention for HTML-type files? Do we need folders/groups as a first-class concept?

### Q-3: What else existed in the previous app?
Are there other file types, workspace features, or interaction patterns we haven't captured?

---

## Proposed Phases

### Phase 1: The Workspace Shell
- New `WorkspaceTab` component (sits alongside existing tabs)
- File explorer sidebar with type-specific icons
- Main viewport that loads the appropriate renderer based on `file_type`
- Schema: add `file_type` column to `drafts` table (or new `workspace_items` table)
- **This phase delivers:** the container. Clicking an item shows a placeholder/stub for each type.

### Phase 2: Markdown Renderer
- First complete renderer/editor — lowest risk
- Rendered view (markdown → HTML) + toggle to source editor
- Agent tools: `create_workspace_item`, `update_workspace_item` with file_type=markdown
- User can create a blank markdown file
- User can edit source

### Phase 3: HTML Freestyle Renderer
- Sandboxed iframe renderer
- Agent tools extended for HTML content
- Print action
- User cannot create or edit — view + print only

### Phase 4: Structured Drafts (Migrate from drafting-mvp)
- Port the block-type renderer from the current DraftsTab
- Add print CSS
- Migrate existing drafting-mvp data if schema changes
- User can create blank structured drafts

### Phase 5: Formatted JSON Viewer
- Structure-aware JSON renderer (tables, cards, lists)
- Read-only
- Agent tools for producing JSON view content

---

## Schema Sketch

```sql
-- Option: extend existing drafts table
ALTER TABLE drafts ADD COLUMN file_type TEXT NOT NULL DEFAULT 'structured_draft'
    CHECK (file_type IN ('html', 'markdown', 'structured_draft', 'json_view'));

-- Or: new table for cleaner separation
CREATE TABLE workspace_items (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    name            TEXT NOT NULL,
    file_type       TEXT NOT NULL CHECK (file_type IN ('html', 'markdown', 'structured_draft', 'json_view')),
    document_type   TEXT CHECK (document_type IN ('letter', 'pleading', 'contract', 'memo', 'other')),
    content         JSONB NOT NULL DEFAULT '{}',  -- structure varies by file_type
    created_by      TEXT NOT NULL DEFAULT 'agent' CHECK (created_by IN ('agent', 'user')),
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'final')),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## Discussion Needed

- Does this capture the distinction between the four use cases correctly?
- Phase order: is Markdown the right first renderer to build?
- Should we extend the `drafts` table or create a new `workspace_items` table?
- What am I missing from the previous app?
