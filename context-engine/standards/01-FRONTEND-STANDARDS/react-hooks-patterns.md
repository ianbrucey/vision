# React Hook & Data-Flow Patterns

> **Stack:** React 19, Next.js 16 App Router, no Redux/Zustand/SWR/React
> Query. This file replaces the old Livewire placeholder — there is no
> Livewire in this codebase; component behavior lives in custom hooks +
> plain `fetch`-based API client functions (`frontend/src/lib/api.ts`).
>
> **Companion to:** `component-patterns.md` (modals, forms, loading states)
> and `design-system.md` (visual tokens).

## 1. Custom Hook Structure

Every non-trivial stateful feature that's reused across components (or that
would otherwise bloat a component) gets its own hook in `frontend/src/hooks/`,
named `use<Feature>.ts`. Reference implementations:
`useChatSession.ts` (session + streaming state), `useInlineEdit.ts`
(generic edit-cell lifecycle), `useReminderPolling.ts` (polling +
notifications).

A hook file is organized top-to-bottom as:
1. `"use client";` directive (always — hooks use `useState`/`useEffect`).
2. Imports: React hooks, then `@/lib/api` functions + types.
3. Exported `interface`s for the hook's public state/options (e.g.
   `UIMessage`, `ReminderPollingOptions`).
4. The hook function itself, internally ordered: state → refs → derived
   callbacks → effects → return object.
5. The return value is a **flat object** of named fields and handlers —
   never a positional tuple beyond the trivial `useState`-style case.

## 2. State Ownership Rules

- **One hook owns one feature's state end-to-end** — `useChatSession` owns
  sessions, messages, and streaming; nothing else touches those `useState`
  calls directly. Components consuming the hook only call the returned
  handlers.
- **`useRef` for values that must not trigger re-renders but need to
  survive across callback closures** — in-flight guards (`sendingRef`,
  `savingRef`, `pollingRef`), abort controllers (`streamCtrlRef`), "have we
  already fired this" sets (`firedIdsRef`).
- **Persist cross-session state to `localStorage`**, not cookies or context,
  for client-only preferences/selection (active chat session id, notification
  permission choice) — keyed by a prefixed constant function:
  `const SESSION_KEY = (caseId: number) => \`vision_chat_active_session_${caseId}\`;`.

## 3. Data Fetching Pattern

No React Query / SWR. The standard shape for a fetch-on-mount hook or effect:

```tsx
const [items, setItems] = useState<Item[]>([]);
const [loading, setLoading] = useState(true);

const refresh = useCallback(async () => {
  try {
    const res = await listItems(id);
    setItems(res.items);
  } catch { /* silent — see §4 */ }
  setLoading(false);
}, [id]);

useEffect(() => { refresh(); }, [refresh]);
```

For fetches that must ignore stale responses (e.g. switching between
sessions/tabs quickly), use a `cancelled` flag closed over the effect (see
`useChatSession`'s message-loading effect) rather than an `AbortController`
unless the underlying call already supports cancellation (streaming does;
plain JSON fetches generally don't need it).

## 4. Error Handling in Hooks

- **Background/polling paths (silent failure, retry next cycle):** empty
  `catch {}` block with a comment — e.g. `useReminderPolling.checkReminders`:
  network errors are swallowed because the next poll retries.
- **User-initiated mutations (create/update/delete triggered by a click):**
  never swallow — surface via the returned `saveError`/error state field so
  the calling component can render it (see `useInlineEdit`'s `saveError`).
- **Streaming (`streamChatMessage`):** errors come through the `onError`
  callback and are pushed into the message list as a `role: "error"` entry
  — errors are shown in-line in the conversation, not as a separate toast.

## 5. Guarding Against Concurrent/Overlapping Operations

Every hook that can be triggered twice in quick succession (send message,
commit an edit, poll-and-fire a reminder) guards with a `useRef` boolean
checked at the top of the async function, set `true` immediately, and reset
in a `finally`:

```tsx
const savingRef = useRef(false);
const commit = useCallback(async (...) => {
  if (savingRef.current) return false;
  savingRef.current = true;
  try {
    // ... do the work
    return true;
  } finally {
    savingRef.current = false;
  }
}, [...]);
```

This is the pattern in `useInlineEdit.commitEdit` and
`useChatSession.handleSend` (`sendingRef`). Do not rely on disabling a
button alone to prevent double-submit — the ref guard is required in the
hook itself.

## 6. Cross-Component Communication

- **Parent owns modal open/close state**, passes `open`/`onClose` props down
  — no global modal manager (see `TaskListModalProps`).
- **Custom DOM events for decoupled, app-wide signals** — e.g.
  `window.dispatchEvent(new CustomEvent("vision:reminder-fired", {...}))`
  from `useReminderPolling`, listened to by a separate toast system. Use
  this only for truly cross-cutting concerns (notifications); prefer normal
  props/callbacks for anything with a clear parent-child relationship.
- **Browser Notification API** gated behind an explicit permission hook
  (`useNotificationPermission`) — never call `Notification.requestPermission()`
  eagerly on mount; defer and let the user opt in.

## 7. Polling

Standard polling hook shape (`useReminderPolling`):
1. Configurable `intervalMs` (default documented in the hook, e.g. 30s).
2. Pause when `document.visibilityState !== "visible"` via a
   `visibilitychange` listener + ref (don't poll hidden tabs).
3. `setInterval` started in a `useEffect`, cleared in the cleanup function.
4. An initial immediate check before the interval starts, so the user
   doesn't wait a full interval for the first result.
5. Expose a manual `checkNow` escape hatch in the return object for
   components that want to force a refresh (e.g. after an action that would
   change the polled data).
