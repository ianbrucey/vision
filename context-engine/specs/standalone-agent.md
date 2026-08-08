# Standalone System Agent — Spec

> **Status:** Draft  
> **Date:** 2026-07-23  

---

## 1. Problem

Currently, the AI chat agent is only accessible inside a case (`/cases/{id}?tab=chat`).
There's no way to ask system-wide questions like:

- "What SAM.gov solicitations are pending triage?"
- "Do I have any unread vendor replies?"
- "What jobs are currently queued or failed?"
- "Create a solicitation from this SAM.gov URL"
- "What's the status of case 60?"

The agent needs to be accessible from the main dashboard (`/solicitations`) with
visibility into the entire system — all cases, all solicitations, all jobs, all
vendor replies, all SAM notices, all forecasts.

---

## 2. Requirements

### R1 — Persistent floating chat button on `/solicitations`

A chat bubble/FAB in the bottom-right corner of the solicitations page. Same
visual pattern as the existing `FloatingChat` component used on case pages.
Clicking it opens a chat panel.

### R2 — System-wide agent context

The agent gets ALL read tools available across cases — every case, every
document, every solicitation. No `case_id` scoping. It can also write:
- Create solicitation from a SAM.gov URL
- Create/delete cases
- Check job queue status
- Check unread vendor replies
- Query SAM notices and forecast data

### R3 — Own page at `/agent`

A full-page version accessible via a nav link or the chat panel's expand button.
Same as the case chat tab but with system-wide scope.

### R4 — Agent awareness of the operator

The agent knows who's logged in (from JWT) and can reference the operator by name.

---

## 3. Implementation

### T1 — Frontend: Floating chat on `/solicitations` (15 min)

Add `<FloatingChat>` (or a new `<SystemFloatingChat>` variant) to the
solicitations page. Reuse the existing `FloatingChat` component pattern.

### T2 — Frontend: Full page at `/agent` (10 min)

A thin page wrapper:
```
/app/agent/page.tsx
  → renders <SystemChatPanel /> with full viewport height
```

### T3 — Backend: System-wide MCP server (20 min)

Create a new endpoint that creates an MCP server with system-wide tools,
not scoped to a single case. Reuse `chat/tools.py`'s `create_vision_server`
but call it with `case_id=None` to signal "all cases" mode.

Tools available:
- All existing read tools (list cases, get case, search documents, etc.)
- `list_solicitations` — all solicitations with status
- `get_jobs` — job queue status (queued/processing/failed counts)
- `get_unread_replies` — vendor replies needing attention  
- `create_solicitation` — from SAM.gov URL
- `query_sam_notices` — search the 4,357 SAM notices
- `query_forecasts` — search the 7,398 forecast opportunities

### T4 — Backend: Agent endpoint (5 min)

`POST /api/agent` — same pattern as `POST /api/cases/{id}/chat` but with
system-wide scope. Uses the system MCP server.

### T5 — Navigation link (5 min)

Add "Agent" to the solicitations page header or as a link in the chat panel header.
Also accessible directly at `/agent`.

---

## 4. Total: ~55 minutes
