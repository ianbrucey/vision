# Drafting System (MVP) — Strategic Brief

## 1. Strategic Intent

**Goal:** Give the agent the ability to create, update, and iterate on structured documents (drafts) that the user can review, edit, and export — without leaving the case workspace.

**Success Verdict:**
- [ ] Agent can create a draft with 3+ block types via a database tool
- [ ] User sees the draft rendered as a formatted document in the Drafts tab
- [ ] User can click any block to edit it inline (desktop) or full-screen (mobile)
- [ ] Agent and user can iterate on the same draft — agent writes, user edits, both persist
- [ ] Draft survives page refresh (stored in DB, not component state)
- [ ] Floating chat button is visible on Overview and Documents tabs, opening a slide-out chat scoped to the current context

## 2. The Claims

| Claim ID | Description | Verdict |
|----------|-------------|---------|
| CLAIM-01 | `drafts` table exists with block array stored as JSONB | `SELECT * FROM drafts WHERE case_id = X` returns rows |
| CLAIM-02 | Agent has `create_draft` tool — writes a new draft row | Agent says "create a draft about X" → row appears in drafts table |
| CLAIM-03 | Agent has `update_draft` tool — modifies blocks in existing draft | Agent says "add a section to draft 3" → blocks array updated |
| CLAIM-04 | DraftsTab renders draft list + preview panel | Open Drafts tab → see list, click draft → see formatted preview |
| CLAIM-05 | 4 block types render correctly: section_heading, numbered_paragraph, list_item, signature | Each block type visually distinct, numbering auto-computed |
| CLAIM-06 | Inline editing: click block → textarea → save → block content updates | Click paragraph, edit text, save, preview reflects change |
| CLAIM-07 | Floating chat button on Overview and Documents tabs | 💬 button visible, tap opens slide-out chat panel |
| CLAIM-08 | All draft tools are case-scoped (closure pattern, no contextvars) | Agent cannot access drafts from another case |

## 3. The Elements

| Element | Purpose | Belongs To |
|---------|---------|------------|
| `drafts` table (SQL) | Store draft metadata + block array | CLAIM-01 |
| `create_draft` tool | Agent writes a new draft | CLAIM-02 |
| `update_draft` tool | Agent modifies blocks | CLAIM-03 |
| `replace_draft` tool | Agent rewrites entire draft content | CLAIM-03 |
| DraftsTab component | Draft list + preview layout | CLAIM-04 |
| DraftPreview component | Block renderer with inline edit | CLAIM-05, CLAIM-06 |
| FloatingChat component | 💬 button + slide-out panel | CLAIM-07 |
| Draft API endpoints | CRUD for drafts (list, get, create, update, delete) | CLAIM-04 |
| Draft server factory | `create_draft_server(case_id)` — same closure pattern as vision/enricher/synthesizer | CLAIM-02, CLAIM-03, CLAIM-08 |

## 4. The Evidence

**Tech Stack:** Python FastAPI + PostgreSQL + Next.js 16 + React 19 + TypeScript + Tailwind 4

**External APIs:** None. Drafts are self-contained in the Vision database.

**Sample Data:** See mockup at `frontend/drafting-mockup.html` — 3 sample drafts with 4 block types.

**Block types (MVP):**

```json
[
  { "type": "section_heading", "content": "COMPANY PROFILE" },
  { "type": "numbered_paragraph", "content": "Vision Technologies is a..." },
  { "type": "list_item", "content": "Delivered production systems for..." },
  { "type": "signature", "content": "Ian Bruce\nPrincipal" }
]
```

**Document types (MVP):** `letter`, `pleading`, `contract`, `memo`, `other`

**Draft statuses:** `draft`, `review`, `final`

---

## 5. Existing Infrastructure

### Related Existing Tables
| Table | Relationship | Location |
|-------|-------------|----------|
| `cases` | FK: `drafts.case_id → cases.id` | `schemas/001_core.sql` |
| `documents` | Drafts may reference evidence blocks | `schemas/001_core.sql` |

### Related Existing Endpoints
| Endpoint | What It Does | Reuse or Extend? |
|----------|--------------|------------------|
| `POST /api/cases/{id}/synthesize` | Enqueues agent job | Reuse pattern for draft creation |
| `GET /api/cases/{id}` | Returns case with parties/allegations/documents | Extend to include drafts |

### Related Existing Components
| Component | Purpose | Location |
|-----------|---------|----------|
| `ChatTab` | Full chat sessions | `tabs/ChatTab.tsx` — extract FloatingChat from here |
| `OverviewTab` | Narrative + synthesis results | `tabs/OverviewTab.tsx` — pattern for button → action → result |
| `DocumentsTab` | Document list + upload | `tabs/DocumentsTab.tsx` — pattern for list + preview modal |

### Known Constraints
- [x] Must use existing closure-based tool pattern (`create_vision_server` style)
- [x] Must use existing job queue pattern if async agent work is needed
- [x] Must use existing design tokens (surface-0, border, brand, etc.)
- [x] Floating chat must not break existing ChatTab functionality

## 6. Pre-Mortem

**What could break?**
- JSONB block array gets corrupted by concurrent edits (agent + user editing same block simultaneously)
- Mobile reflow CSS doesn't handle all block types gracefully
- Floating chat on multiple tabs causes duplicate session creation

**What assumptions are we making?**
- Agent writes to drafts via tools, user edits via REST API — last-write-wins is acceptable for MVP
- Block array is small enough to fit in a single JSONB column (< 1MB)
- 4 block types are sufficient for initial document types

**What do we NOT know yet?**
- Whether users want the floating chat to share sessions with the Chat tab
- Optimal print/export CSS for the reflow mode
- Whether 4 block types will suffice for the first real protocol (RFP response)

## 7. Approval Gate

**Status:** [ ] DRAFT  [ ] APPROVED

**Approved By:** 

**Date:** 

---
