# Calendar System — Implementation Plan

> **Phase:** State 3 — Planning (The Foreman)
> **Date:** 2026-06-17
> **Principle:** Backend-Out Sequencing (DB → API → Agent Tools → Frontend)
> **Ticket Standard:** Each ticket is atomic, completable in isolation, and has a binary acceptance test.

---

## Ticket Dependency Graph

```
T01 (DB Migration)
 └─ T02 (DB Functions)
     ├─ T03 (API Routes)
     │   ├─ T04 (Router Registration)
     │   └─ T06 (Frontend API Client)
     │       └─ T07 (CalendarTab)
     │           ├─ T08 (Forms)
     │           ├─ T09 (Side Panel)
     │           └─ T10 (TabNav Integration)
     ├─ T05 (Agent Tools)
     └─ T11 (Reminder Polling)
         └─ T12 (RBC CSS Overrides)
             └─ T13 (Integration Verification)
```

---

## T01 — Database Migration

**Dependencies:** None
**Type:** Backend — Schema
**Estimated effort:** Small

### Files to Create
- `backend/schemas/006_calendar.sql` — Full migration from [01-schema.sql](01-schema.sql)

### Acceptance Criteria
- [ ] `calendar_events` table created with all columns, CHECK constraints, and indexes
- [ ] `reminders` table created with all columns, CHECK constraints (including partial index on pending reminders), and cascade FK
- [ ] `schema_migrations` insert is version 15 with `ON CONFLICT DO NOTHING`
- [ ] Migration runs idempotently (`CREATE TABLE IF NOT EXISTS` on all statements)
- [ ] Expression index on `(case_id, (start_time::DATE))` exists for date-range queries
- [ ] `created_by` uses `TEXT CHECK (IN ('user', 'agent'))` — no UUID dependency
- [ ] `workspace_id` is nullable FK — deferred but schema-supported
- [ ] `event_id` FK has `ON DELETE CASCADE` with documented behavior in comments

**Verification:**
```bash
psql -c "INSERT INTO schema_migrations (version, name) VALUES (15, 'add_calendar_tables');"
# Expect: no error, tables exist, indexes exist
psql -c "\d calendar_events"
psql -c "\d reminders"
```

**Maps to Brief:** CLAIM-03, CLAIM-04, CLAIM-05 (data storage)

---

## T02 — Backend DB Functions

**Dependencies:** T01 (tables must exist)
**Type:** Backend — Data Layer
**Estimated effort:** Medium

### Files to Modify
- `backend/core/db.py` — Add 10 functions

### Functions to Add

| Function | Signature | Purpose |
|----------|-----------|---------|
| `insert_calendar_event` | `(conn, case_id, title, start_time, **kwargs) → int` | Create event, return ID |
| `list_calendar_events` | `(conn, case_id, start_date?, end_date?, category?, limit?) → list[dict]` | List with filters |
| `get_calendar_event` | `(conn, event_id) → dict | None` | Single event with attached reminders |
| `update_calendar_event` | `(conn, event_id, **kwargs) → dict | None` | Partial update |
| `delete_calendar_event` | `(conn, event_id) → bool` | Delete (cascades to reminders) |
| `insert_reminder` | `(conn, case_id, title, remind_at, **kwargs) → int` | Create reminder, return ID |
| `list_reminders` | `(conn, case_id, status?, category?, event_id?, limit?) → list[dict]` | List with filters |
| `get_reminder` | `(conn, reminder_id) → dict | None` | Single reminder |
| `update_reminder` | `(conn, reminder_id, **kwargs) → dict | None` | Partial update (including status transitions) |
| `delete_reminder` | `(conn, reminder_id) → bool` | Delete |

### Patterns to Follow
- Existing `insert_task` / `list_tasks` / `get_task` / `update_task` / `delete_task` in `core/db.py`
- Use `tx()` context manager for writes, `connect()` for reads
- Return dictionaries with column names as keys (matching existing pattern)
- `update_*` functions accept `**kwargs` and only SET provided fields (matching `update_task`)

### Acceptance Criteria
- [ ] All 10 functions exist and follow the same signature pattern as task equivalents
- [ ] `insert_calendar_event` handles `all_day=true` by setting `start_time` appropriately
- [ ] `list_calendar_events` supports `start_date`/`end_date` filters using the expression index
- [ ] `get_calendar_event` returns attached reminders (nested query on `reminders WHERE event_id = $1`)
- [ ] `list_reminders` supports `status`, `category`, and `event_id` filters
- [ ] All functions imported and callable

**Verification:**
```python
from core.db import connect, insert_calendar_event, list_calendar_events, get_calendar_event
conn = connect()
event_id = insert_calendar_event(conn, case_id=1, title="Test", start_time="2026-07-01T09:00:00Z")
events = list_calendar_events(conn, case_id=1)
event = get_calendar_event(conn, event_id)
assert event["title"] == "Test"
```

**Maps to Brief:** CLAIM-03, CLAIM-04, CLAIM-10, CLAIM-11 (data access)

---

## T03 — Backend API Routes

**Dependencies:** T02 (DB functions must exist)
**Type:** Backend — REST API
**Estimated effort:** Medium

### Files to Create
- `backend/api/routes/calendar.py` — Full router from [02-api-contract.json](02-api-contract.json)

### Endpoints (10 total)

| Method | Path | Maps to |
|--------|------|---------|
| `GET` | `/cases/{case_id}/calendar/events` | `list_calendar_events` |
| `POST` | `/cases/{case_id}/calendar/events` | `insert_calendar_event` |
| `GET` | `/calendar/events/{event_id}` | `get_calendar_event` |
| `PATCH` | `/calendar/events/{event_id}` | `update_calendar_event` |
| `DELETE` | `/calendar/events/{event_id}` | `delete_calendar_event` |
| `GET` | `/cases/{case_id}/calendar/reminders` | `list_reminders` |
| `POST` | `/cases/{case_id}/calendar/reminders` | `insert_reminder` |
| `GET` | `/calendar/reminders/{reminder_id}` | `get_reminder` |
| `PATCH` | `/calendar/reminders/{reminder_id}` | `update_reminder` |
| `DELETE` | `/calendar/reminders/{reminder_id}` | `delete_reminder` |

### Patterns to Follow
- [tasks.py](backend/api/routes/tasks.py) — exact structural copy
- Pydantic `BaseModel` request classes (CreateCalendarEvent, UpdateCalendarEvent, CreateReminder, UpdateReminder)
- `APIRouter(prefix="/api", tags=["calendar"])`
- `Depends(get_current_user)` on every endpoint
- `HTTPException(status_code=404)` for not-found
- `tx()` context manager for writes, `connect()` for reads
- Response shape: `{"events": [...], "count": N}` for lists, `{"event": {...}}` for singles

### Acceptance Criteria
- [ ] All 10 endpoints registered and reachable
- [ ] `POST` endpoints validate required fields via Pydantic
- [ ] `PATCH` endpoints reject empty bodies with 400
- [ ] `GET` endpoints support query param filters matching the API contract
- [ ] `DELETE` returns `{"deleted": true}`
- [ ] 404 returned for non-existent IDs
- [ ] All endpoints require authentication (401 without token)

**Verification:**
```bash
curl -X POST http://localhost:8000/api/cases/1/calendar/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Hearing","start_time":"2026-07-01T09:00:00-04:00","category":"hearing"}'
# Expect: 201 with {"event": {...}}
```

**Maps to Brief:** CLAIM-10, CLAIM-11 (API access)

---

## T04 — Router Registration

**Dependencies:** T03 (router must exist)
**Type:** Backend — Integration
**Estimated effort:** Trivial

### Files to Modify
- `backend/api/main.py` — Add `from api.routes.calendar import router as calendar_router` and `app.include_router(calendar_router)`

### Acceptance Criteria
- [ ] Calendar endpoints accessible through the running FastAPI app
- [ ] OpenAPI docs show calendar endpoints under "calendar" tag
- [ ] Existing routes unaffected

**Verification:**
```bash
curl http://localhost:8000/api/openapi.json | jq '.paths | keys' | grep calendar
# Expect: calendar endpoints appear in OpenAPI spec
```

**Maps to Brief:** CLAIM-10, CLAIM-11 (API availability)

---

## T05 — Agent Tools

**Dependencies:** T02 (DB functions must exist)
**Type:** Backend — MCP Tools
**Estimated effort:** Medium

### Files to Modify
- `backend/chat/tools.py` — Register 6 tools inside `create_vision_server()`

### Tools to Add

| Tool Name | Type | Required Args | Maps to |
|-----------|------|--------------|---------|
| `create_calendar_event` | Write | `title`, `start_time` | `insert_calendar_event` |
| `list_calendar_events` | Read | none | `list_calendar_events` |
| `get_calendar_event` | Read | `event_id` | `get_calendar_event` |
| `create_reminder` | Write | `title`, `remind_at` | `insert_reminder` |
| `list_reminders` | Read | none | `list_reminders` |
| `get_reminder` | Read | `reminder_id` | `get_reminder` |

### Tool Input Schemas (JSON Schema format, per existing pattern)

```python
@tool(
    "create_calendar_event",
    "Create a calendar event in the case. Use this to schedule hearings, "
    "depositions, deadlines, meetings, or other events. The event appears "
    "on the case calendar and can have reminders attached.",
    {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Event title. Be specific (e.g., 'Deposition — Jane Smith' not 'Meeting').",
            },
            "start_time": {
                "type": "string",
                "description": "Event start time in ISO 8601 format with timezone "
                "(e.g., '2026-07-15T09:00:00-04:00'). Use the user's local timezone.",
            },
            "end_time": {
                "type": "string",
                "description": "Event end time (optional). ISO 8601 with timezone.",
            },
            "all_day": {
                "type": "boolean",
                "description": "Set true for all-day events like filing deadlines. "
                "When true, start_time should be set to midnight of the event date.",
            },
            "category": {
                "type": "string",
                "enum": ["hearing", "deposition", "deadline", "meeting", "other"],
                "description": "Event category. Choose based on the type of event.",
            },
            "description": {
                "type": "string",
                "description": "Detailed notes — purpose, preparation needed, attendees, etc.",
            },
            "location": {
                "type": "string",
                "description": "Physical address, courtroom number, or virtual meeting link.",
            },
        },
        "required": ["title", "start_time"],
    },
)
async def create_calendar_event(args: dict[str, Any]) -> dict[str, Any]:
    ...
```

### Key Design Decisions
- `case_id` is captured in closure — agent never provides it (existing pattern)
- Agent computes absolute `remind_at` from natural language intervals ("remind me 48 hours before" → agent calculates the absolute time)
- All tools follow lazy import pattern (`from core.db import ...` inside handler)
- Read tools annotated with `ToolAnnotations(readOnlyHint=True)`
- Return shape: `{"event_id": ..., "title": ...}` on success; `{"error": "..."}` on failure

### Acceptance Criteria
- [ ] 6 tools registered and callable from chat sessions scoped to a case
- [ ] Agent can say "Add a hearing on June 25 at 2pm" → `create_calendar_event` called with correct args → event appears in DB
- [ ] Agent can say "Remind me to file the motion 48 hours before the hearing" → agent computes absolute time → `create_reminder` called → reminder appears in DB
- [ ] Agent can list events: "What's on the calendar this week?" → `list_calendar_events` returns correct results
- [ ] Agent can list reminders: "What reminders are pending?" → `list_reminders` returns correct results
- [ ] Tool error messages are descriptive enough for the agent to self-correct
- [ ] Existing tools unaffected

**Verification:**
```python
# In a chat session scoped to case_id=42:
# User: "Schedule a deposition for Jane Smith on July 15, 2026 at 9am Eastern, 4 hours"
# Agent calls: create_calendar_event(title="Deposition — Jane Smith", start_time="2026-07-15T09:00:00-04:00", end_time="2026-07-15T13:00:00-04:00", category="deposition")
# Expect: event_id returned, event appears in list_calendar_events
```

**Maps to Brief:** CLAIM-06, CLAIM-07 (agent tools)

---

## T06 — Frontend API Client

**Dependencies:** T03 (API routes must exist)
**Type:** Frontend — Data Layer
**Estimated effort:** Small

### Files to Modify
- `frontend/src/lib/api.ts` — Add types + functions

### Types to Add

```typescript
export interface CalendarEvent {
  id: number;
  case_id: number;
  workspace_id: number | null;
  title: string;
  description: string | null;
  start_time: string;
  end_time: string | null;
  all_day: boolean;
  category: "hearing" | "deposition" | "deadline" | "meeting" | "other";
  location: string | null;
  created_by: "user" | "agent";
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Reminder {
  id: number;
  case_id: number;
  event_id: number | null;
  title: string;
  description: string | null;
  remind_at: string;
  category: "hearing" | "deposition" | "deadline" | "meeting" | "other";
  status: "pending" | "fired" | "dismissed";
  created_by: "user" | "agent";
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}
```

### Functions to Add (10 total)

```typescript
export const api = {
  // ... existing ...
  calendar: {
    events: {
      list: (caseId: number, params?: { start_date?: string; end_date?: string; category?: string; limit?: number }) =>
        request<{ count: number; events: CalendarEvent[] }>(`/api/cases/${caseId}/calendar/events${toQuery(params)}`),
      get: (eventId: number) =>
        request<{ event: CalendarEvent; reminders: Reminder[] }>(`/api/calendar/events/${eventId}`),
      create: (caseId: number, data: CreateCalendarEvent) =>
        request<{ event: CalendarEvent }>(`/api/cases/${caseId}/calendar/events`, { method: "POST", body: JSON.stringify(data) }),
      update: (eventId: number, data: Partial<CreateCalendarEvent>) =>
        request<{ event: CalendarEvent }>(`/api/calendar/events/${eventId}`, { method: "PATCH", body: JSON.stringify(data) }),
      delete: (eventId: number) =>
        request<{ deleted: boolean }>(`/api/calendar/events/${eventId}`, { method: "DELETE" }),
    },
    reminders: {
      list: (caseId: number, params?: { status?: string; category?: string; event_id?: number; limit?: number }) =>
        request<{ count: number; reminders: Reminder[] }>(`/api/cases/${caseId}/calendar/reminders${toQuery(params)}`),
      get: (reminderId: number) =>
        request<{ reminder: Reminder }>(`/api/calendar/reminders/${reminderId}`),
      create: (caseId: number, data: CreateReminder) =>
        request<{ reminder: Reminder }>(`/api/cases/${caseId}/calendar/reminders`, { method: "POST", body: JSON.stringify(data) }),
      update: (reminderId: number, data: Partial<CreateReminder & { status: string }>) =>
        request<{ reminder: Reminder }>(`/api/calendar/reminders/${reminderId}`, { method: "PATCH", body: JSON.stringify(data) }),
      delete: (reminderId: number) =>
        request<{ deleted: boolean }>(`/api/calendar/reminders/${reminderId}`, { method: "DELETE" }),
    },
  },
};
```

### Patterns to Follow
- Existing `api.tasks.*` functions — exact structural copy
- `ApiError` class for error handling (already exists)
- `request<T>()` generic wrapper (already exists)

### Acceptance Criteria
- [ ] All 10 functions exist and compile without TypeScript errors
- [ ] Types match the API contract exactly (no extra/missing fields)
- [ ] `list` functions accept query param objects matching API contract
- [ ] `create`/`update` functions accept typed request bodies
- [ ] Existing API functions unaffected

**Verification:**
```typescript
// In browser console or test:
const { events } = await api.calendar.events.list(42, { start_date: "2026-07-01", end_date: "2026-07-31" });
expect(Array.isArray(events)).toBe(true);
```

**Maps to Brief:** CLAIM-10, CLAIM-11 (client access)

---

## T07 — CalendarTab Component

**Dependencies:** T06 (API client must exist)
**Type:** Frontend — Page Component
**Estimated effort:** Large

### Files to Create
- `frontend/src/app/cases/[id]/tabs/CalendarTab.tsx` — Main wrapper

### Sub-components (created inline or as separate files in T08/T09)
- `CalendarTab` orchestrates: data fetching, state management, layout

### What It Does
1. Fetches events + reminders on mount and when `caseId` changes
2. Renders `CalendarGrid` (RBC wrapper) + `SidePanel` in responsive layout
3. Manages state per [04-ui-specs.md §11](04-ui-specs.md)
4. Handles event click → shows EventDetail in side panel
5. Handles "New Event" / "New Reminder" button clicks → opens forms
6. Refreshes data after any mutation (create/edit/delete)

### Layout Structure
```
CalendarTab
├── CalendarHeader (date navigator, view switcher, action buttons)
├── CalendarLayout (responsive: row on desktop, column on mobile)
│   ├── CalendarGrid (RBC Calendar component)
│   └── SidePanel (EventDetail or ReminderList or EmptyState)
├── CalendarEventForm (modal, conditionally rendered)
└── ReminderForm (modal, conditionally rendered)
```

### Acceptance Criteria
- [ ] Component renders without errors in a case context
- [ ] Events fetched and displayed on calendar grid
- [ ] Clicking an event shows EventDetail in side panel
- [ ] "+ New Event" opens CalendarEventForm modal
- [ ] "+ Reminder" opens ReminderForm modal
- [ ] After form submission, calendar refreshes with new data
- [ ] Desktop layout: calendar grid + side panel side by side
- [ ] Mobile layout (<1024px): full-width calendar, side panel as bottom sheet
- [ ] Mobile default view is "agenda" (not month)
- [ ] Loading state: skeleton (per component-patterns §5.3)
- [ ] Empty state: "No calendar events" with create button (per §12)
- [ ] Error state: error message with retry button

**Verification:**
```bash
# Navigate to a case → click Calendar tab → see calendar grid
# Create an event via the form → event appears on calendar
# Click the event → side panel shows details
# Resize to 320px → agenda view, bottom sheet side panel
```

**Maps to Brief:** CLAIM-01, CLAIM-02 (calendar tab + rendering)

---

## T08 — CalendarEventForm + ReminderForm

**Dependencies:** T07 (parent component must exist)
**Type:** Frontend — Modal Components
**Estimated effort:** Medium

### Files to Create
- `frontend/src/components/calendar/CalendarEventForm.tsx`
- `frontend/src/components/calendar/ReminderForm.tsx`

### CalendarEventForm Fields
Per [04-ui-specs.md §7](04-ui-specs.md): Title (required), Description, Start Date (required), Start Time, End Date, End Time, All Day checkbox, Category select, Location

### ReminderForm Fields
Per [04-ui-specs.md §8](04-ui-specs.md): Title (required), Description, Date (required), Time (required), Category select, Event select (optional — "Standalone reminder" default)

### Patterns to Follow
- Modal component pattern per component-patterns.md §2
- Form layout per component-patterns.md §1
- Inline create form pattern from TasksTab
- Mobile: bottom sheet on <640px per §2.2

### Acceptance Criteria
- [ ] CalendarEventForm opens as modal on desktop, bottom sheet on mobile
- [ ] Required fields validated before submit (title, start date)
- [ ] All Day checkbox hides time inputs when checked
- [ ] Submit button disabled while saving, shows "Saving..."
- [ ] On success: modal closes, parent refreshes
- [ ] On error: error displayed near submit button, form values preserved
- [ ] ReminderForm supports optional event attachment (dropdown of existing events)
- [ ] ReminderForm validates title + date/time
- [ ] Both forms match "Command" design system (colors, spacing, typography)
- [ ] Touch targets ≥44px on mobile

**Verification:**
```
Click "+ New Event" → form opens → fill fields → submit → event appears on calendar
Click "+ Reminder" → form opens → select event → set date/time → submit → reminder appears in side panel
```

**Maps to Brief:** CLAIM-03, CLAIM-04, CLAIM-05 (create events + reminders)

---

## T09 — EventDetail + ReminderList (Side Panel)

**Dependencies:** T07 (parent component must exist)
**Type:** Frontend — Side Panel Components
**Estimated effort:** Medium

### Files to Create
- `frontend/src/components/calendar/EventDetail.tsx`
- `frontend/src/components/calendar/ReminderList.tsx`

### EventDetail
Per [04-ui-specs.md §6](04-ui-specs.md): Category badge, title, time/date display, location (clickable if URL), description (with expand/collapse if >200 chars), attached reminders list with "Add reminder" button, created-by metadata, Edit/Delete action buttons.

### ReminderList
Per [04-ui-specs.md §5.3](04-ui-specs.md): Filtered list of reminders with status icons (Bell for pending, BellRing for fired, BellOff for dismissed), time display, category badge, dismiss button (pending only).

### Acceptance Criteria
- [ ] EventDetail shows all fields from the API response
- [ ] Time display handles: timed events, all-day events, events without end_time
- [ ] Location renders as clickable link if URL, plain text if address
- [ ] Attached reminders listed under event with status icons
- [ ] "Add reminder" button pre-fills event_id in ReminderForm
- [ ] Edit button opens CalendarEventForm in edit mode
- [ ] Delete button shows confirmation before deleting
- [ ] ReminderList shows pending reminders by default
- [ ] ReminderList supports status filter (pending/fired/dismissed)
- [ ] Dismiss button on pending reminders calls PATCH status → "dismissed"
- [ ] Empty state: "No upcoming reminders" when list is empty
- [ ] Both components match "Command" design system

**Verification:**
```
Click event on calendar → EventDetail shows in side panel with all fields
Dismiss a reminder → it moves to fired state, icon changes
Delete an event → event disappears from calendar, side panel closes
```

**Maps to Brief:** CLAIM-05, CLAIM-08 (event detail + reminder display)

---

## T10 — TabNav Integration

**Dependencies:** T07 (CalendarTab must exist)
**Type:** Frontend — Navigation Integration
**Estimated effort:** Trivial

### Files to Modify
- `frontend/src/app/cases/[id]/TabNav.tsx` — Add to `TabId` type and `TABS` array
- `frontend/src/app/cases/[id]/page.tsx` — Import `CalendarTab`, add render branch

### Changes

**TabNav.tsx:**
```typescript
import { CalendarDays } from "lucide-react";  // add to existing import

export type TabId = "..." | "calendar";  // add to union

const TABS: TabDef[] = [
  // ... existing 6 entries ...
  { id: "calendar", label: "Calendar", shortLabel: "Cal", icon: CalendarDays },
];
```

**page.tsx:**
```typescript
import CalendarTab from "./tabs/CalendarTab";  // add import

// Add to tabParam validation:
tabParam === "calendar" ? "calendar" : ...

// Add render branch:
{activeTab === "calendar" && <CalendarTab caseId={Number(id)} />}
```

### Acceptance Criteria
- [ ] Calendar tab visible in desktop sidebar (7th item)
- [ ] Calendar tab visible in mobile "More" menu (3rd secondary item)
- [ ] Clicking Calendar tab navigates to CalendarTab component
- [ ] URL reflects `?tab=calendar`
- [ ] Tab state survives page refresh (URL-based)
- [ ] Existing tabs unaffected
- [ ] Bottom tab bar "More" count: 3 items (Correspondence, Tasks, Calendar) — within design limits

**Verification:**
```
Navigate to case → see Calendar in desktop sidebar → click → calendar renders
Mobile: tap "More" → see Calendar in menu → tap → calendar renders
Refresh page → still on Calendar tab
```

**Maps to Brief:** CLAIM-01 (calendar tab accessible)

---

## T11 — useReminderPolling Hook

**Dependencies:** T06 (API client must exist)
**Type:** Frontend — Cross-Cutting
**Estimated effort:** Small

### Files to Create
- `frontend/src/lib/useReminderPolling.ts`

### Behavior per [04-ui-specs.md §9](04-ui-specs.md)
1. Fetch pending reminders on mount
2. Poll every 30 seconds
3. For each reminder where `remind_at <= now()`:
   - Fire in-app toast (existing toast pattern)
   - Fire browser notification (if permission granted)
   - PATCH reminder status → "fired"
4. Request notification permission once; store in localStorage
5. Clear interval on unmount
6. Pause polling when tab is hidden (`document.visibilitychange`)

### Acceptance Criteria
- [ ] Hook accepts `caseId` and optional `intervalMs` (default 30000)
- [ ] Polls `GET /api/cases/{caseId}/calendar/reminders?status=pending` every 30s
- [ ] Due reminders trigger in-app toast with title + category + time
- [ ] Due reminders trigger browser notification (if permission granted)
- [ ] Due reminders are PATCH-ed to status "fired" after notification
- [ ] Notification permission banner shown once (not a modal) on first mount
- [ ] Banner remembers dismissal in localStorage
- [ ] Polling stops when tab is backgrounded, resumes when visible
- [ ] Interval cleared on hook cleanup (no memory leaks)
- [ ] No duplicate notifications (tag-based dedup)

**Verification:**
```
1. Create a reminder with remind_at = now + 2 minutes
2. Wait → toast appears at due time
3. Check browser notification (if permitted)
4. Reminder status changes to "fired" in DB
5. Reminder disappears from "pending" list
```

**Maps to Brief:** CLAIM-08, CLAIM-09 (reminder notification delivery)

---

## T12 — RBC CSS Overrides

**Dependencies:** T07 (CalendarGrid must exist to test against)
**Type:** Frontend — Styling
**Estimated effort:** Medium

### Files to Create
- `frontend/src/app/calendar-overrides.css` — ~200 lines, per [04-ui-specs.md §4.1](04-ui-specs.md)

### What It Does
Overrides ~60 React Big Calendar CSS classes to match the "Command" design system. Uses only CSS custom properties (`var(--color-*)`) — no `@apply`, no Tailwind directives (simpler and avoids PostCSS ordering issues with RBC's imported CSS).

### Import Order (Critical)
In `CalendarGrid.tsx` (or `CalendarTab.tsx`):
```tsx
import "react-big-calendar/lib/css/react-big-calendar.css";  // FIRST
import "@/app/calendar-overrides.css";                        // SECOND — wins via cascade
```

### Key Override Categories
1. Toolbar (hidden — we render our own)
2. Month view header row + grid cells
3. Events (category-colored pills via `data-category` attribute)
4. Time grid (week/day views)
5. Agenda view (mobile default)
6. Overlay/popup ("show more" in month view)
7. Buttons (RBC-generated button groups)
8. Loading state

### Acceptance Criteria
- [ ] Calendar renders with "Command" design colors (surface-1, text-primary, brand, border)
- [ ] Event pills use semantic category colors (danger=hearing, info=deposition, warning=deadline, success=meeting, surface-5=other)
- [ ] Today's date highlighted with `--color-brand-bg` (subtle amber)
- [ ] Typography matches design system: Geist Sans, 11-13px text scale
- [ ] Borders use `--color-border` / `--color-border-light`
- [ ] Border radius: `rounded-lg` (8px) on event pills, cells, and overlays
- [ ] Agenda view (mobile default) styled as card list with date headers
- [ ] Time grid (week/day) uses Geist Mono for time labels
- [ ] RBC toolbar hidden (our CalendarHeader replaces it)
- [ ] No Tailwind `@apply` in the override file (prevents PostCSS ordering bugs)
- [ ] No RBC blue (`#3174ad`) visible anywhere
- [ ] Override file is self-contained and commented

**Verification:**
```
Open calendar → visually inspect month view colors against design system
Switch to week/day views → verify time grid styling
Mobile: verify agenda view styling at 320px
Check for any RBC default colors bleeding through
```

**Maps to Brief:** CLAIM-02 (responsive calendar rendering with correct styling)

---

## T13 — Integration Verification (The Verdict)

**Dependencies:** All tickets (T01–T12)
**Type:** Quality Assurance
**Estimated effort:** Small

### What It Does
End-to-end verification of the complete calendar system against all 12 Brief claims using the fixture data in [03-fixtures.json](03-fixtures.json).

### Verification Script (Manual Checklist)

```
VERDICT CHECKLIST — Calendar System

CLAIM-01: Calendar tab navigable
  [ ] Desktop: Calendar appears in sidebar
  [ ] Mobile: Calendar appears in "More" menu
  [ ] Clicking navigates to CalendarTab

CLAIM-02: Month/week/day views, responsive
  [ ] Month view renders at 1024px+
  [ ] Week view renders at 1024px+
  [ ] Agenda view is default at 320px
  [ ] View switcher works on both desktop and mobile

CLAIM-03: User creates calendar event
  [ ] Fill CalendarEventForm → submit → event appears on calendar
  [ ] All-day event renders correctly (banner, no time label)
  [ ] Timed event shows time in pill

CLAIM-04: User creates standalone reminder
  [ ] Fill ReminderForm without event → submit → reminder appears in side panel
  [ ] Reminder shows Bell icon (pending state)

CLAIM-05: User creates event-attached reminder
  [ ] From EventDetail, "Add reminder" → form opens with event pre-selected
  [ ] Submit → reminder appears nested under event

CLAIM-06: Agent creates calendar event
  [ ] In chat: "Add a hearing on July 25 at 2pm" → event appears on calendar
  [ ] Event has created_by="agent"

CLAIM-07: Agent creates reminder
  [ ] In chat: "Remind me 48 hours before the MSJ hearing" → reminder appears
  [ ] reminder has correct remind_at (agent-computed absolute time)

CLAIM-08: In-app toast for due reminders
  [ ] Create reminder due in 2 min → wait → toast appears

CLAIM-09: Browser notification for due reminders
  [ ] Grant notification permission → reminder fires → browser notification appears
  [ ] Deny permission → toast still fires, no browser notification

CLAIM-10: Events queryable via API
  [ ] GET /api/cases/{id}/calendar/events → returns events
  [ ] Filter by date range works
  [ ] Filter by category works

CLAIM-11: Reminders queryable via API
  [ ] GET /api/cases/{id}/calendar/reminders → returns reminders
  [ ] Filter by status works
  [ ] Filter by event_id works

CLAIM-12: Events survive page refresh
  [ ] Create event → refresh browser → event still visible on calendar
  [ ] Reminders persist across refresh
```

### Acceptance Criteria
- [ ] All 12 claims pass
- [ ] 0 regressions on existing tabs (Overview, Chat, Documents, Workspace, Correspondence, Tasks)
- [ ] 0 TypeScript compilation errors
- [ ] 0 console errors in browser
- [ ] Mobile: all touch targets ≥44px
- [ ] Design system compliance (spot check against checklist in §14 of 04-ui-specs.md)

**Verification:** Run the checklist above. Every box checked.

**Maps to Brief:** ALL CLAIMS (system acceptance)

---

## Execution Order

Run tickets in strict numerical order. Each ticket is an independent unit of work that produces a verifiable output.

```
Phase 1 — Backend Foundation (T01–T04)
  T01 → T02 → T03 → T04

Phase 2 — Agent Tools (T05)
  (Can run in parallel with Phase 1 after T02)

Phase 3 — Frontend Data Layer (T06)
  (Can start after T03)

Phase 4 — Frontend Components (T07–T10)
  T06 → T07 → {T08, T09} → T10
  (T08 and T09 can run in parallel)

Phase 5 — Cross-Cutting (T11, T12)
  T06 → T11
  T07 → T12
  (T11 and T12 can run in parallel)

Phase 6 — Verification (T13)
  All preceding tickets must be complete
```

### Parallel Opportunities
- T08 + T09 can run in parallel (both depend on T07, neither depends on each other)
- T11 + T12 can run in parallel (no shared dependency beyond T06/T07)
- T05 can run in parallel with T03 + T04 (all depend only on T02)

### Critical Path
```
T01 → T02 → T03 → T06 → T07 → T10 → T13
```
Estimated: 10 sequential steps. With parallelization: 7 phases.

---

## Risk Register

| Risk | Likelihood | Impact | Tickets Affected | Mitigation |
|------|-----------|--------|------------------|------------|
| RBC CSS not fully overridable | Medium | Medium | T12 | CSS custom properties approach validated; fallback: fork RBC CSS into project |
| date-fns v3 incompatibility with RBC v1.x | Low | High | T07 | Pin exact versions; verify before `npm install` |
| Mobile month view unusable at 320px | High | Low | T07 | Default to agenda view on mobile |
| Reminder polling + existing job polling overload | Low | Medium | T11 | 30s interval is conservative; visibility API pauses polling when tab hidden |
| Tab count (7) exceeds comfortable mobile limit | Low | Low | T10 | 4 primary + 3 secondary is within design system bounds |

---

## Completion Criteria

All 12 Brief claims verified. No regressions. Ready for State 4 (Execution).

**Status:** [x] DRAFT  [ ] APPROVED
