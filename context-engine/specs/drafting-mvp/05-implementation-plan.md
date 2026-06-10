# Drafting System (MVP) — Implementation Plan

> **Generated From:** `00-Brief.md`, `01-schema.sql`, `02-api-contract.json`, `04-ui-specs.md`

---

## Sequencing (Backend-Out)

| Ticket | Layer | What | Depends On |
|--------|-------|------|------------|
| T1 | DB | Apply `01-schema.sql` — `drafts` table + indexes + migration v4 | — |
| T2 | DB | Add `insert_draft`, `update_draft`, `get_draft`, `list_drafts` helpers to `core/db.py` | T1 |
| T3 | Agent | Add `create_draft`, `update_draft`, `replace_draft`, `list_drafts`, `get_draft` tools to `create_vision_server()` in `chat/tools.py` | T2 |
| T4 | API | `GET /api/cases/{id}/drafts`, `GET /api/drafts/{id}`, `POST /api/drafts`, `PATCH /api/drafts/{id}`, `PATCH /api/drafts/{id}/blocks/{block_id}`, `DELETE /api/drafts/{id}` | T2 |
| T5 | Frontend | Update `api.ts` — add all draft API functions | T4 |
| T6 | Frontend | `DraftPreview` component — block renderer with desktop inline edit + mobile full-screen edit | T5 |
| T7 | Frontend | `DraftsTab` component — draft list + preview panel layout (desktop 2-column, mobile sequential) | T6 |
| T8 | Frontend | `FloatingChatButton` + `FloatingChatPanel` components | T5 |
| T9 | Frontend | Wire FloatingChat into OverviewTab and DocumentsTab | T8 |
| T10 | Prompt | Update `WAR_ROOM_SYSTEM_PROMPT` to include draft tools | T3 |
| T11 | Verify | Create a draft via chat → edit in DraftsTab → agent updates via chat → verify iteration loop | T1–T10 |

---

## Ticket Details

### T1 — Schema (10 min)
- Add `drafts` table to `schemas/001_core.sql`
- Add migration v4 block
- Apply via `ensure_schema()`

### T2 — DB Helpers (15 min)
- `insert_draft(conn, case_id, name, document_type, content, created_by)` → int
- `update_draft(conn, draft_id, **kwargs)` → dict
- `get_draft(conn, draft_id)` → dict | None
- `list_drafts(conn, case_id)` → list[dict]
- `delete_draft(conn, draft_id)` → bool
- `update_block(conn, draft_id, block_id, content)` → dict

### T3 — Agent Tools (20 min)
- Add 5 tools to `create_vision_server()` in `chat/tools.py`
- All closure-scoped to `case_id`
- `create_draft` — writes new row, returns draft_id
- `update_draft` — modifies existing draft metadata/blocks
- `replace_draft` — full content replacement
- `list_drafts` — returns list for the case
- `get_draft` — returns full draft with content (use before editing)

### T4 — API Endpoints (30 min)
- Add draft routes to `api/routes/drafts.py`
- Include in `api/main.py` via `app.include_router`
- Standard CRUD + block-level PATCH
- Case-scope verification on all endpoints

### T5 — API Client (10 min)
- `listDrafts(caseId)`, `getDraft(id)`, `createDraft(data)`, `updateDraft(id, data)`, `updateBlock(draftId, blockId, content)`, `deleteDraft(id)`

### T6 — DraftPreview Component (45 min)
- Props: `blocks`, `editMode`, `onBlockUpdate`, `mobile`
- Render loop: switch on `block.type` → styled output
- Desktop edit: click → inline textarea → Save/Cancel
- Mobile edit: tap → full-screen overlay with textarea
- Live numbering computation

### T7 — DraftsTab Component (40 min)
- Desktop: `flex` layout — 280px sidebar + flex-1 preview
- Mobile: state machine — `list` | `preview`, sequential views with back button
- Fetch drafts on mount, auto-select first
- Edit mode toggle in toolbar
- Wire block edit → `updateBlock` API → optimistic update

### T8 — FloatingChatButton + Panel (35 min)
- Reusable pair: button (fixed, bottom-right) + panel (slide-out)
- Uses existing `ChatManager` session API
- Passes `context` string to agent via system prompt append
- Mobile: bottom sheet with 80vh max-height

### T9 — Wire into Tabs (15 min)
- Add `<FloatingChatButton>` to OverviewTab and DocumentsTab
- Context strings: `"overview"` → parties/issues summary, `"documents"` → document count

### T10 — Prompt Update (5 min)
- Add "DRAFTING TOOLS" section to `WAR_ROOM_SYSTEM_PROMPT` in `chat/prompt.py`
- Hierarchical placement: after Strategy, before Protocols

### T11 — End-to-End Verify (15 min)
- Create draft via chat agent
- Verify appears in DraftsTab
- Edit block inline, verify persists
- Agent updates draft, verify preview refreshes
- Floating chat opens on Overview and Documents tabs

---

## Estimated Total: ~4 hours
