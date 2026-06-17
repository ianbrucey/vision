# Calendar System — Strategic Brief

## 1. Strategic Intent

**Goal:** Add a per-case calendar system with events and reminders, accessible via a new Calendar tab in the case detail view, with agent-accessible tools for creating and managing both.

**Success Verdict:**
- [ ] User navigates to Calendar tab and sees a month grid rendered with React Big Calendar
- [ ] User creates a calendar event with date, time range (start/end), title, description, and category
- [ ] User creates a standalone reminder (not attached to any event)
- [ ] User creates an event-attached reminder (e.g., "1 hour before the hearing")
- [ ] Agent creates a calendar event via chat ("Add a hearing on June 25 at 2pm")
- [ ] Agent creates a reminder via chat ("Remind me to file the motion 48 hours before the hearing")
- [ ] Agent lists/reads calendar events and reminders via chat tools
- [ ] Reminders fire as in-app toasts at the scheduled time while the app is open
- [ ] Browser notifications fire for reminders when the app tab is open (Notification API)
- [ ] Calendar renders correctly on mobile (320px viewport) and desktop (1024px+)
- [ ] Calendar tab is accessible from both desktop sidebar and mobile bottom tab bar

## 2. The Claims

| Claim ID | Description | Verdict |
|----------|-------------|---------|
| CLAIM-01 | Calendar tab is registered in `TabNav` and navigable on desktop sidebar + mobile bottom bar | Click Calendar tab → Calendar view renders |
| CLAIM-02 | Month, week, and day views rendered via React Big Calendar, responsive across breakpoints | Switch views; calendar re-renders correctly at 320px and 1024px |
| CLAIM-03 | User can create a calendar event with `{title, description, start_time, end_time, all_day, category}` | Fill form → submit → event appears on calendar |
| CLAIM-04 | User can create a standalone reminder with `{title, description, remind_at, category}` | Fill form → submit → reminder scheduled; appears in reminder list |
| CLAIM-05 | User can create an event-attached reminder with `{event_id, remind_at}` (absolute time; agent computes from natural language intervals like "48 hours before") | Create reminder on event → linked reminder shows in event detail |
| CLAIM-06 | Agent can create/read calendar events via chat tools (`create_calendar_event`, `list_calendar_events`, `get_calendar_event`) | Agent says "Add hearing June 25" → event appears on calendar |
| CLAIM-07 | Agent can create/read reminders via chat tools (`create_reminder`, `list_reminders`, `get_reminder`) | Agent says "Remind me 24h before deadline" → reminder is scheduled |
| CLAIM-08 | In-app toast notification fires at scheduled reminder time while app is open | Reminder time arrives → toast appears (per existing toast pattern) |
| CLAIM-09 | Browser notification fires for reminders when tab is open (Notification API with permission request) | Reminder time arrives → browser notification appears if permitted |
| CLAIM-10 | Calendar events are queryable via API (`GET /api/cases/{case_id}/calendar/events`) | API returns paginated event list with filters by date range and category |
| CLAIM-11 | Reminders are queryable via API (`GET /api/cases/{case_id}/calendar/reminders`) | API returns reminder list with filters by status (pending/fired/dismissed) |
| CLAIM-12 | Events and reminders survive page refresh and are restored on tab re-entry | Create event → refresh browser → event still visible on calendar |

## 3. The Elements

| Element | Purpose | Belongs To |
|---------|---------|------------|
| `calendar_events` table | Store event rows: `{id, case_id, title, description, start_time, end_time, all_day, category, location, created_by, created_at, updated_at}` | CLAIM-03, CLAIM-06 |
| `reminders` table | Store reminder rows: `{id, case_id, event_id?, title, description, remind_at, category, status, created_by, created_at, updated_at}` | CLAIM-04, CLAIM-05, CLAIM-07 |
| Schema migration `006_calendar.sql` | Add both tables + indexes to PostgreSQL | CLAIM-03, CLAIM-04 |
| `CalendarTab` component | Main calendar tab wrapper: renders React Big Calendar + event/reminder side panel | CLAIM-01, CLAIM-02 |
| `CalendarEventForm` component | Modal form for creating/editing calendar events | CLAIM-03 |
| `ReminderForm` component | Modal form for creating/editing reminders (standalone or event-attached) | CLAIM-04, CLAIM-05 |
| `EventDetail` component | Click event → detail panel with title, description, time, attached reminders | CLAIM-05 |
| `ReminderList` component | Sidebar list of pending/fired reminders with status pills | CLAIM-04 |
| Calendar API routes (`backend/api/routes/calendar.py`) | CRUD endpoints for events and reminders | CLAIM-10, CLAIM-11 |
| Agent tools in `backend/chat/tools.py` | `create_calendar_event`, `list_calendar_events`, `get_calendar_event`, `create_reminder`, `list_reminders`, `get_reminder` | CLAIM-06, CLAIM-07 |
| `ReminderService` (frontend hook) | Polls for due reminders, fires toasts + browser notifications | CLAIM-08, CLAIM-09 |
| Updated `TabNav.tsx` | Add `Calendar` tab with `CalendarDays` icon to `TABS` array | CLAIM-01 |
| Updated `page.tsx` | Import `CalendarTab`, wire to `activeTab === "calendar"` | CLAIM-01 |
| `date-fns` dependency | Date math library for React Big Calendar (peer dep) | CLAIM-02 |
| `react-big-calendar` dependency | Calendar UI component | CLAIM-02 |

## 4. The Evidence

**Tech Stack:**
- Frontend: Next.js 16 + React 19 + TypeScript + Tailwind CSS 4
- Backend: Python FastAPI + PostgreSQL 16+
- Calendar: React Big Calendar v1.x + date-fns v3.x
- Icons: Lucide React (`CalendarDays`, `Clock`, `Bell`, `BellRing`)
- Notifications: Browser Notification API (no external dep)

**External APIs:** None. Calendar is self-contained in Vision. No Google Calendar / Outlook integration in v1.

**Event Data Model:**
```json
{
  "id": 1,
  "case_id": 42,
  "title": "Deposition — Jane Smith",
  "description": "Remote deposition via Zoom. Prepare Exhibit A and Exhibit C.",
  "start_time": "2026-06-25T14:00:00Z",
  "end_time": "2026-06-25T16:30:00Z",
  "all_day": false,
  "category": "deposition",
  "location": "Zoom — link in case notes",
  "created_by": "agent",
  "created_at": "2026-06-17T12:00:00Z",
  "updated_at": "2026-06-17T12:00:00Z"
}
```

**Event Categories (v1):**
| Category | Description |
|----------|-------------|
| `hearing` | Court hearing, oral argument |
| `deposition` | Witness deposition |
| `deadline` | Filing deadline, statute of limitations |
| `meeting` | Client meeting, team sync |
| `other` | Uncategorized |

**Reminder Data Model:**
```json
{
  "id": 1,
  "case_id": 42,
  "event_id": null,
  "title": "File motion for summary judgment",
  "description": "Must be filed before 5pm EST",
  "remind_at": "2026-06-24T09:00:00Z",
  "category": "deadline",
  "status": "pending",
  "created_by": "agent",
  "created_at": "2026-06-17T12:00:00Z",
  "updated_at": "2026-06-17T12:00:00Z"
}
```

**Event-attached reminder (linked):**
```json
{
  "id": 2,
  "case_id": 42,
  "event_id": 1,
  "title": "Prep for Jane Smith deposition",
  "description": "Review exhibits A-C, prepare questions",
  "remind_at": "2026-06-24T14:00:00Z",
  "category": "deposition",
  "status": "pending",
  "created_by": "agent",
  "created_at": "2026-06-17T12:00:00Z",
  "updated_at": "2026-06-17T12:00:00Z"
}
```

**Reminder Statuses:**
| Status | Description |
|--------|-------------|
| `pending` | Scheduled, not yet fired |
| `fired` | Reminder time arrived, notification sent |
| `dismissed` | User dismissed manually |
| `snoozed` | User deferred (snooze support deferred to v2) |

**Fixture Data:** The three JSON objects above (event, standalone reminder, event-attached reminder) constitute the fixture set. See `03-fixtures.json` for the expanded set.

## 5. Existing Infrastructure

### Related Existing Tables
| Table | Relationship | Location |
|-------|-------------|----------|
| `cases` | FK: `calendar_events.case_id → cases.id` | `schemas/001_core.sql:49-83` |
| `tasks` | Reference pattern for scoped items with status, priority, deadline | `schemas/001_core.sql:551-567` |
| `users` | FK: `calendar_events.created_by → users.id` | `schemas/001_core.sql:410-426` |

### Related Existing Endpoints
| Endpoint | What It Does | Reuse or Extend? |
|----------|--------------|------------------|
| `GET /api/cases/{case_id}/tasks` | List scoped items with filters | **Reference pattern** — same structure for `/calendar/events` |
| `POST /api/tasks` | Create scoped item | **Reference pattern** — same structure for `/calendar/events` |
| `GET /api/cases/{case_id}` | Get case with nested data | **Reuse** — no changes needed |

### Related Existing Components
| Component | Purpose | Location | Action |
|-----------|---------|----------|--------|
| `TabNav` | Desktop sidebar + mobile bottom tab bar | `frontend/src/app/cases/[id]/TabNav.tsx` | **Extend** — add Calendar tab to `TABS` array + `TabId` type |
| `CaseDashboardInner` / `page.tsx` | Tab dispatch + layout | `frontend/src/app/cases/[id]/page.tsx` | **Extend** — import `CalendarTab`, add render branch |
| `Modal` | Form container per component-patterns §2 | N/A (pattern) | **Reuse** — event/reminder forms follow this pattern |
| `TasksTab` | Reference for tab structure with list + create flow | `frontend/src/app/cases/[id]/tabs/TasksTab.tsx` | **Reference** — similar sidebar + form pattern |

### Related Agent Tools
| Tool | Purpose | Location | Action |
|------|---------|----------|--------|
| `create_task` / `list_tasks` | Agent creates/lists tasks | `backend/chat/tools.py:1506-1569` | **Reference pattern** — same structure for calendar tools |
| `create_vision_server` | Registers case-scoped MCP tools | `backend/chat/tools.py:120` | **Extend** — register new calendar tools |

### Known Constraints
- [x] Must integrate with existing case tab system (desktop sidebar + mobile "More" overflow)
- [x] Must use existing design tokens (`--surface-*`, `--text-*`, `--brand`, `--border`, etc.)
- [x] Must use existing Lucide icon library — no new icon package
- [x] React Big Calendar must be styled to match the "Command" design system (rounded-lg, surface-1 cards, Geist font, 4px spacing scale)
- [x] Mobile calendar must follow responsive design rules: single viewport, touch targets ≥44px, no hover-only interactions
- [x] Reminders must use existing toast pattern (component-patterns.md §3) + Browser Notification API
- [x] Agent tools must follow existing closure pattern in `create_vision_server`
- [x] Must not break existing tabs or their functionality
- [x] Calendar tab count (7th tab) means 4 primary + 3 secondary on mobile; decision on primary vs secondary slot deferred to UI spec phase
- [x] `react-big-calendar` imports its own CSS — must be scoped or overridden with Tailwind tokens

## 6. Pre-Mortem

**What could break?**
- React Big Calendar CSS bleed: the library ships its own stylesheet. Must be imported in a way that doesn't pollute global styles, or overridden with Tailwind tokens. Mitigation: wrap calendar in a scoped container and use CSS cascade to override library defaults.
- Timezone handling: events stored in UTC, displayed in user's local timezone. Server renders UTC, client converts. Mitigation: store all times as `TIMESTAMPTZ`, let PostgreSQL handle TZ; React Big Calendar + date-fns display in local TZ.
- Reminder polling: a polling interval that fires every second would hammer the API. Mitigation: poll every 30 seconds; check only for reminders due within the next polling window. Fired reminders are marked `fired` and never re-fire.
- Browser notification permission: users may deny. Mitigation: reminder toasts still fire in-app regardless of browser permission. Permission requested once, stored in localStorage.
- Concurrent event edits: two browser tabs open on same case. Last-write-wins. Mitigation: acceptable for v1 (same pattern as tasks and workspace items).
- Agent creates duplicate events: agent asked twice → two identical hearings. Mitigation: v1 accepts this; agent can list events before creating to check for duplicates. Dedup is a prompt concern.
- Mobile calendar usability: month view at 320px is tight. Mitigation: React Big Calendar supports responsive views — use month on desktop, agenda/list on mobile as default. User can switch.

**What assumptions are we making?**
- React Big Calendar can be styled to match the "Command" design system without extensive CSS overrides
- Per-case calendar scope is sufficient; no cross-case calendar view needed in v1
- Single-user per case (no multi-user scheduling conflicts)
- Browser Notification API is available in target browsers (Chrome, Firefox, Safari, Edge — all support it)
- Reminders don't need persistence across browser restarts beyond DB storage (polling resumes on page load)
- date-fns v3 is compatible with React Big Calendar v1.x
- No recurring events in v1 (deferred)
- No calendar sync with external providers (Google Calendar, Outlook) in v1 (deferred)
- No email reminders in v1 (deferred)

**What do we NOT know yet?**
- Whether React Big Calendar will style cleanly with Tailwind tokens or require invasive CSS overrides
- Whether 4 primary + 3 secondary tabs on mobile is too many for the "More" menu
- What the bundle size impact of react-big-calendar + date-fns will be
- Whether users will primarily use month, week, or agenda view
- How reminder polling interacts with the existing 5-second job polling in the dashboard

## 7. Out of Scope (Explicit)

- **Recurring events** — "Every Monday at 9am" patterns deferred to v2
- **Multi-user calendar** — no attendee management, no shared free/busy
- **External calendar sync** — no Google Calendar, Outlook, or iCal integration
- **Email reminders** — in-app toasts + browser notifications only
- **Cross-case calendar view** — calendar is scoped to a single case
- **Drag-and-drop event rescheduling** — events are edited via form, not drag
- **Snooze reminders** — reminders fire once or are dismissed; snooze deferred to v2
- **Reminder polling while tab is backgrounded** — browser may throttle; Service Worker-based reminders deferred to v2
- **Calendar print/export** — no PDF or iCal export in v1

## 8. Approval Gate

**Status:** [ ] DRAFT  [x] APPROVED

**Approved By:** Ian Bruce

**Date:** 2026-06-17

---

> ⚠️ **EXIT CONDITION:** This Brief is not approved until all Claims have defined Verdicts and the Tech Stack is explicit. No ambiguity allowed.
