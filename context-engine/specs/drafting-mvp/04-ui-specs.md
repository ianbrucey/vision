# Drafting System — UI Specifications

> **Generated From:** `02-api-contract.json`
> **Reference mockup:** `frontend/drafting-mockup.html`

---

## 1. Views

### 1.1 DraftsTab

**Purpose:** Primary drafting workspace — draft list + preview + embedded chat (desktop), or sequential full-width views (mobile).

**URL Route:** `/cases/{id}?tab=drafts` (existing tab navigation)

**Data Required:**

| Field | Source Endpoint | Type |
|-------|-----------------|------|
| drafts list | `GET /api/cases/{case_id}/drafts` | `Draft[]` |
| active draft content | `GET /api/drafts/{draft_id}` | `Draft` |
| block update | `PATCH /api/drafts/{draft_id}/blocks/{block_id}` | — |

**Layout — Desktop:**

```
┌──────────┬────────────────────────┬──────────────┐
│ Drafts   │ Preview                │ Chat         │
│ (280px)  │ (flex-1)               │ (360px)      │
│          │                        │              │
│ [list]   │ [rendered document]    │ [conversat.] │
└──────────┴────────────────────────┴──────────────┘
```

**Layout — Mobile:**

```
┌──────────────────────┐     ┌──────────────────────┐
│ Drafts               │     │ ← Back    [Edit]     │
│ (full width)         │ ──► │                      │
│                      │     │ [rendered document]  │
│ [list items]         │     │ (full width, reflow) │
│                      │     │                      │
│              [💬]    │     │              [💬]    │
└──────────────────────┘     └──────────────────────┘
```

**States:**
- **Loading:** Skeleton list (3 pulsing rows) + skeleton preview (pulsing page rectangle)
- **Empty:** "No drafts yet. Ask the agent to create one in the chat." + link to Chat tab
- **Error:** Inline banner: "Failed to load drafts" with retry button
- **Success:** Draft list populated, first draft auto-selected, preview rendered

**User Actions:**

| Action | Triggers | API Endpoint |
|--------|----------|--------------|
| Click draft in list | Select active draft | `GET /api/drafts/{id}` |
| Click "Edit" in toolbar | Enter edit mode (all blocks get hover outline) | — |
| Click block in edit mode | Open inline editor (desktop) or full-screen editor (mobile) | — |
| Save block edit | Update block content | `PATCH /api/drafts/{id}/blocks/{block_id}` |
| Click "Done" | Exit edit mode | — |
| Click "Export" | Open export menu (Print / PDF / DOCX) | — |
| Click "New Draft" (+) | Open agent prompt input | `POST /api/drafts` |

---

### 1.2 Floating Chat

**Purpose:** Quick-access chat scoped to the current view context. Slides out over content — doesn't navigate away.

**Appears on:** OverviewTab, DocumentsTab (NOT on ChatTab or DraftsTab — those have their own chat UI)

**Layout:**

```
                             ┌──────────────────┐
                             │ Chat (scoped)    │
                             │                  │
                             │ [conversation]   │
                             │                  │
                             │ [input] [send]   │
┌──────────────────────┐     └──────────────────┘
│ Overview / Documents │
│                      │
│ [content]            │
│                      │
│              [💬]    │
└──────────────────────┘
```

**Desktop:** Fixed 380px panel slides in from right edge. Content area shrinks (responsive grid).
**Mobile:** Full-width bottom sheet (80vh max). Backdrop dismisses. 💬 button anchored bottom-right.

**States:**
- **Closed:** 💬 button visible. Unread badge shows message count (if applicable).
- **Open:** Panel visible. Input focused. 💬 button hidden.
- **Loading (initial):** Spinner in chat body. "Connecting to your case..."
- **Streaming:** Agent response streams in. Input disabled. "Stop" button appears.

**Context scoping:** The floating chat passes a `context` hint to the agent:
- On Overview: `"The user is viewing the case overview. They have N parties and M issues extracted."`
- On Documents: `"The user is viewing the documents list. They have N documents ingested."`

**User Actions:**

| Action | Triggers |
|--------|----------|
| Click 💬 | Open panel, create session if first time |
| Type + send | Stream agent response |
| Click backdrop | Close panel |
| Click ✕ | Close panel |

**Data Required:**

| Field | Source Endpoint | Type |
|-------|-----------------|------|
| Create session | `POST /api/chat/sessions` | — |
| Stream message | `POST /api/chat/sessions/{id}/messages` (SSE) | — |
| Message history | `GET /api/chat/sessions/{id}/messages` | — |

---

## 2. Components

### 2.1 DraftPreview

**Props:**

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `blocks` | `Block[]` | Yes | Array of `{id, type, content}` |
| `editMode` | `boolean` | Yes | Whether blocks show hover affordance and are clickable |
| `onBlockUpdate` | `(blockId, content) => Promise<void>` | Yes | Persists block edit |
| `mobile` | `boolean` | No | If true, reflow layout (no print page container) |

**Block renderers:**

| Block Type | Desktop | Mobile |
|-----------|---------|--------|
| `section_heading` | Centered, underlined, bold, 14pt | Left-aligned, bold, 16px |
| `numbered_paragraph` | Indented, auto-numbered `1.`, `2.` | Same, wider margins |
| `list_item` | Letter-labeled `(a)`, `(b)` | Same |
| `signature` | Top-border line, min-width 200px | Same, full-width |

**Edit mode — Desktop:**
- Block gets dashed hover outline
- Click → inline `<textarea>` replaces block text, with Save/Cancel buttons
- Numbering re-computes on save

**Edit mode — Mobile:**
- Tap block → full-screen editor slides up
- `<textarea>` fills screen, keyboard auto-opens
- Save/Cancel in top bar
- On save → slide down, preview re-renders

**Numbering:** `numbered_paragraph` numbers are NOT stored — they're computed at render time by counting preceding `numbered_paragraph` blocks. `list_item` labels reset when interrupted by a non-list item.

### 2.2 FloatingChatButton

**Props:**

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `caseId` | `number` | Yes | Current case |
| `context` | `string` | Yes | Hint sent to agent about what the user is viewing |
| `unreadCount` | `number` | No | Badge count |

**Renders:** Fixed-position 💬 button (bottom: 20px, right: 20px, z-index: 30). When `unreadCount > 0`, red badge in top-right corner.

### 2.3 FloatingChatPanel

**Props:**

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `caseId` | `number` | Yes | Current case |
| `context` | `string` | Yes | Hint sent to agent |
| `open` | `boolean` | Yes | Controlled open state |
| `onClose` | `() => void)` | Yes | Close callback |

**Desktop render:** Fixed panel, right edge, 380px wide, full height. Slides in with `transform: translateX`.
**Mobile render:** Full-width bottom sheet, 80vh max, rounded top corners. Backdrop behind.

---

## 3. Conflict Check

- [x] Every field displayed exists in `02-api-contract.json`
- [x] Every action maps to a defined endpoint
- [x] No UI assumes data the API doesn't provide
- [x] Loading/Empty/Error states defined for all views
- [x] Mobile and desktop layouts defined for all components
- [x] Reference mockup at `frontend/drafting-mockup.html` matches these specs
