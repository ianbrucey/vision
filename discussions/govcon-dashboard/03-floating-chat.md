# Floating Chat Improvements

**Status:** Straightforward

## What it is

A `FloatingChat` component already exists and is used in OverviewTab. The
brainstorm wants to extend it so the chat floats across ALL tabs, can be resized
(full screen, 1/3 width, etc.), and changes made by the agent are visible
immediately without switching tabs.

## Existing infrastructure

- `frontend/src/components/FloatingChat.tsx` — a floating chat panel with
  `FloatingChatButton` trigger. Already imported in OverviewTab.
- Chat logic is duplicated between `FloatingChat` and `ChatTab` — both have
  their own session/message/streaming state.

## What needs to be built

### 1. Unify chat logic into a shared hook

Extract session management, message loading, and SSE streaming from both
`ChatTab.tsx` and `FloatingChat.tsx` into a shared hook:

```
frontend/src/hooks/useChatSession.ts
```

Returns: `{ sessions, activeSessionId, messages, streaming, input, send, ... }`

Both `ChatTab` and `FloatingChat` consume this hook. This eliminates the
duplication and ensures the same session is accessible from both places.

### 2. Make FloatingChat available globally

Move `FloatingChat` + `FloatingChatButton` from `OverviewTab` into the case
dashboard layout (`page.tsx`). The floating button appears on every tab, and
clicking it opens the chat overlay regardless of which tab is active.

### 3. Resize / position controls

Add three modes to `FloatingChat`:
- **Minimized** — just the floating button (current default)
- **Side panel** — slides in from the right, ~380px wide (1/3 of screen)
- **Full screen** — covers the entire viewport

Persist the user's preferred mode in localStorage.

### 4. Real-time UI updates

When the agent makes changes (creates a task, updates correspondence, etc.),
the relevant tab should reflect those changes immediately. Options:
- **WebSocket/SSE events** — the agent stream includes `tool_result` events
  already; we can dispatch custom events that tabs listen to
- **Optimistic + refetch** — after the agent completes a turn, tabs refetch
  their data (simpler, matches current polling patterns)

Option 2 is simpler and sufficient for now. After each agent turn, emit a
`case:updated` event that tabs subscribe to for refetching.

## Files to modify / create

- `frontend/src/hooks/useChatSession.ts` ✨ — shared chat hook (~200 lines extracted)
- `frontend/src/components/FloatingChat.tsx` — consume hook, add resize modes
- `frontend/src/app/cases/[id]/tabs/ChatTab.tsx` — consume hook instead of inline logic
- `frontend/src/app/cases/[id]/page.tsx` — add FloatingChat + button globally
- `frontend/src/app/globals.css` — add resize transition animations

## Open question

Should the ChatTab remain as a tab when FloatingChat is available everywhere?
Probably yes — some users prefer a full dedicated chat view. The FloatingChat
is an overlay convenience, not a replacement.

## Estimated effort

~3-4 hours. Most of the work is extracting the shared hook and refactoring
existing code without breaking anything.
