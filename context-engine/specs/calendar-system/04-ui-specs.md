# Calendar System — UI Specifications

> **Purpose:** Define every component, layout, and interaction for the Calendar tab. AI agents reference this file — they do not invent layouts.

---

## 1. Component Tree

```
CalendarTab (page-level wrapper)
├── CalendarHeader (toolbar: view switcher, date navigator, "+ New" buttons)
├── CalendarLayout (responsive container)
│   ├── CalendarGrid (React Big Calendar — month/week/day/agenda)
│   │   └── CalendarEvent (RBC event component — custom styled)
│   └── SidePanel (desktop: right sidebar; mobile: bottom sheet)
│       ├── EventDetail (clicked event → detail card)
│       │   └── ReminderList (event-attached reminders)
│       ├── ReminderList (standalone reminders for the case)
│       └── EmptyState ("Select an event" or "No reminders")
├── CalendarEventForm (modal — create/edit event)
├── ReminderForm (modal — create/edit reminder)
└── useReminderPolling (hook — 30s poll for due reminders)
```

---

## 2. CalendarTab — Main Layout

### 2.1 Desktop Layout (≥1024px)

```
┌─────────────────────────────────────────────────────────┐
│ CalendarHeader                                          │
│ [< July 2026 >]  [Month|Week|Day|Agenda]  [+Event +Rem] │
├────────────────────────────┬────────────────────────────┤
│                            │  SidePanel                 │
│   CalendarGrid             │  ┌──────────────────────┐  │
│   (flex-1)                 │  │ EventDetail          │  │
│                            │  │ (if event selected)  │  │
│                            │  │                      │  │
│                            │  │ Reminders attached   │  │
│                            │  │ to this event        │  │
│                            │  └──────────────────────┘  │
│                            │  ┌──────────────────────┐  │
│                            │  │ Upcoming Reminders   │  │
│                            │  │ (filter: pending)    │  │
│                            │  └──────────────────────┘  │
└────────────────────────────┴────────────────────────────┘
```

- Calendar grid: `flex-1`, min 60% width
- Side panel: `w-[320px]`, border-l, overflow-y-auto
- Total height: fills viewport minus header (14px) and mobile bottom bar offset (14px on mobile only)

### 2.2 Mobile Layout (<1024px)

```
┌───────────────────────────┐
│ CalendarHeader (compact)  │
│ [< July 2026 >] [Agenda]  │
│ [+Event] [+Rem]           │
├───────────────────────────┤
│                           │
│ CalendarGrid              │
│ (full-width, flex-1)      │
│ — Agenda view by default  │
│ — Month view available    │
│   but cramped             │
│                           │
├───────────────────────────┤
│ Bottom Sheet (collapsed)  │
│ "Event Details" tap ↑     │
│ or slide up to reveal     │
└───────────────────────────┘
```

- On mobile, the side panel becomes a bottom sheet (per component-patterns §2.3)
- Calendar defaults to **Agenda view** on screens <640px (month grid is unusable at 320px)
- User can switch to Month/Week/Day but Month view is explicitly labeled "small screen — best in landscape"

### 2.3 React Big Calendar — View Configuration

| View | Desktop (<1024px) | Mobile (<640px) |
|------|-------------------|-----------------|
| **Month** | Default. Full 4×5 grid with event dots. | Available but not default. Accessible via view switcher. |
| **Week** | Available. 7-column time grid. | Hidden on mobile — not enough horizontal space. |
| **Day** | Available. Single-column time grid. | Available. Scrollable time slots. |
| **Agenda** | Available. List of upcoming events. | **Default.** Scrollable list, no horizontal overflow. |

**View switcher:** RBC's built-in toolbar buttons, styled to match secondary button pattern. Active view uses `bg-surface-2 text-brand`. Inactive: `text-text-secondary hover:text-text-primary`.

---

## 3. CalendarHeader

```
Desktop:
┌──────────────────────────────────────────────────────────┐
│ [<] July 2026 [>]     [Month] [Week] [Day] [Agenda]      │
│                                    [+ New Event] [+ Rem] │
└──────────────────────────────────────────────────────────┘

Mobile:
┌──────────────────────────────┐
│ [<] July 2026 [>] [v Agenda] │ ← view switcher is dropdown
│ [+ Event] [+ Reminder]       │
└──────────────────────────────┘
```

**Elements:**
- **Date navigator:** `<` and `>` buttons navigate by the current view unit (month for month view, week for week view, day for day view). Today button returns to current date.
- **View switcher (desktop):** Segmented button group. Follows secondary button style.
- **View switcher (mobile):** Native `<select>` dropdown — saves horizontal space, touch-friendly.
- **"+ New Event" button:** Primary button. Opens `CalendarEventForm` modal. Icon: `CalendarDays` (18px) + text.
- **"+ Reminder" button:** Secondary button. Opens `ReminderForm` modal. Icon: `Bell` (18px) + text.

**Styling:**
```html
<header class="shrink-0 bg-surface-1 border-b border-border px-4 py-2
                flex items-center justify-between gap-2 flex-wrap">
```

---

## 4. CalendarGrid — Styling React Big Calendar

### 4.1 Override Strategy — IMPLEMENTATION GUIDE

**⚠️ This is the hardest part of the frontend implementation.** React Big Calendar ships ~450 lines of hardcoded CSS (`react-big-calendar/lib/css/react-big-calendar.css`). It uses no CSS custom properties — every color, font, border, and pixel value is hardcoded. Our strategy must override all of them to match the "Command" design system.

#### 4.1.1 File Structure

```
frontend/src/
├── app/
│   └── calendar-overrides.css       ← RBC overrides (this file)
│   └── globals.css                  ← existing Tailwind + design tokens
├── components/
│   └── calendar/
│       └── CalendarGrid.tsx         ← imports RBC + overrides
```

#### 4.1.2 Import Order (Critical)

In `CalendarGrid.tsx`, the import order matters. RBC's CSS must load BEFORE our overrides:

```tsx
// CalendarGrid.tsx
import { Calendar, dateFnsLocalizer, type View } from "react-big-calendar";
import format from "date-fns/format";
import parse from "date-fns/parse";
import startOfWeek from "date-fns/startOfWeek";
import getDay from "date-fns/getDay";

// RBC's base CSS — loads FIRST
import "react-big-calendar/lib/css/react-big-calendar.css";

// Our overrides — loads SECOND, wins via cascade
import "@/app/calendar-overrides.css";
```

**Do NOT use a CSS module for RBC overrides.** RBC applies classes like `.rbc-event` directly to DOM elements it creates. CSS module scoping (`_hash_rbcevent`) won't match them. Use a plain `.css` file loaded after RBC's CSS.

#### 4.1.3 Override Technique

Use a `.calendar-wrapper` class on the container div that wraps `<Calendar>`. Every override rule is scoped under `.calendar-wrapper` to prevent bleed:

```tsx
// CalendarGrid.tsx
<div className="calendar-wrapper h-full">
  <Calendar
    localizer={localizer}
    events={events}
    ...
  />
</div>
```

All override CSS selectors are `.calendar-wrapper .rbc-*`. This ensures:
1. Higher specificity than RBC's bare `.rbc-*` selectors (scoped wins)
2. No bleed into other parts of the application
3. Clear ownership — every RBC override is in one file

#### 4.1.4 Complete Override File

File: `frontend/src/app/calendar-overrides.css`

This file targets ~60 RBC classes. It is organized into sections matching RBC's internal structure.

```css
/* =========================================================================
 * calendar-overrides.css
 * React Big Calendar → "Command" Design System mapping
 *
 * Load order: RBC base CSS → this file.
 * Scoped to .calendar-wrapper to prevent cascade bleed.
 * NO Tailwind @apply — use CSS custom properties from globals.css.
 * ========================================================================= */

/* -------------------------------------------------------------------------
 * 1. TOOLBAR (hidden — we render our own CalendarHeader)
 * ------------------------------------------------------------------------- */
.calendar-wrapper .rbc-toolbar {
  display: none;
}

/* -------------------------------------------------------------------------
 * 2. MONTH VIEW — Header Row (Sun Mon Tue ...)
 * ------------------------------------------------------------------------- */
.calendar-wrapper .rbc-month-header {
  background: var(--color-surface-1);
  border-bottom: 1px solid var(--color-border);
}
.calendar-wrapper .rbc-header {
  padding: 8px 0;
  font-size: 11px;
  font-weight: 500;
  font-family: var(--font-sans);
  color: var(--color-text-secondary);
  border: none;
}

/* -------------------------------------------------------------------------
 * 3. MONTH VIEW — Grid Cells
 * ------------------------------------------------------------------------- */
.calendar-wrapper .rbc-month-row {
  border-bottom: 1px solid var(--color-border);
  overflow: hidden;
}
.calendar-wrapper .rbc-month-row:last-child {
  border-bottom: none;
}
.calendar-wrapper .rbc-day-bg {
  border-right: 1px solid var(--color-border-light);
}
.calendar-wrapper .rbc-day-bg:last-child {
  border-right: none;
}

/* Days outside current month */
.calendar-wrapper .rbc-off-range-bg {
  background: var(--color-surface-0);
}
.calendar-wrapper .rbc-off-range {
  color: var(--color-text-disabled);
}

/* Today highlight */
.calendar-wrapper .rbc-today {
  background: var(--color-brand-bg); /* #FFF7EB — very subtle amber */
}

/* Date number in cell */
.calendar-wrapper .rbc-date-cell {
  padding: 4px 8px 0;
  font-size: 12px;
  font-weight: 500;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  text-align: right;
}
.calendar-wrapper .rbc-off-range .rbc-date-cell {
  color: var(--color-text-disabled);
}
.calendar-wrapper .rbc-now .rbc-date-cell {
  font-weight: 600;
}

/* "Show more" link when events overflow a cell */
.calendar-wrapper .rbc-show-more {
  font-size: 10px;
  font-weight: 500;
  font-family: var(--font-sans);
  color: var(--color-brand);
  background: transparent;
}
.calendar-wrapper .rbc-show-more:hover {
  color: var(--color-brand-hover);
  text-decoration: underline;
}

/* -------------------------------------------------------------------------
 * 4. EVENTS — Rendered in month/day/week views
 * ------------------------------------------------------------------------- */
/* Base event pill — category colors applied via data attribute below */
.calendar-wrapper .rbc-event {
  border: none;
  border-radius: 8px; /* rounded-lg */
  padding: 2px 6px;
  font-size: 11px;
  font-weight: 500;
  font-family: var(--font-sans);
  line-height: 1.4;
  cursor: pointer;
  transition: opacity 150ms ease-out;
}
.calendar-wrapper .rbc-event:hover {
  opacity: 0.85;
}
.calendar-wrapper .rbc-event:focus {
  outline: 2px solid var(--color-brand-ring);
  outline-offset: 1px;
}

/* Category color map — uses data-category attribute set by custom event component */
.calendar-wrapper .rbc-event[data-category="hearing"] {
  background: var(--color-danger);
  color: #FFFFFF;
}
.calendar-wrapper .rbc-event[data-category="deposition"] {
  background: var(--color-info);
  color: #FFFFFF;
}
.calendar-wrapper .rbc-event[data-category="deadline"] {
  background: var(--color-warning);
  color: #FFFFFF;
}
.calendar-wrapper .rbc-event[data-category="meeting"] {
  background: var(--color-success);
  color: #FFFFFF;
}
.calendar-wrapper .rbc-event[data-category="other"] {
  background: var(--color-surface-5);
  color: var(--color-text-primary);
}

/* All-day events: subtle background instead of pill */
.calendar-wrapper .rbc-allday-cell {
  background: var(--color-surface-1);
  border-bottom: 1px solid var(--color-border);
}
.calendar-wrapper .rbc-event.rbc-event-allday {
  background: var(--color-brand-bg);
  color: var(--color-brand);
  border: 1px solid var(--color-border-accent);
}

/* Event continues from previous / to next day indicators */
.calendar-wrapper .rbc-event-continues-prior,
.calendar-wrapper .rbc-event-continues-after {
  border-radius: 0;
}
.calendar-wrapper .rbc-event-continues-prior {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}
.calendar-wrapper .rbc-event-continues-after {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

/* Event label (time shown inside event pill) */
.calendar-wrapper .rbc-event-label {
  font-size: 10px;
  opacity: 0.8;
  font-family: var(--font-sans);
}

/* -------------------------------------------------------------------------
 * 5. TIME GRID — Week and Day views
 * ------------------------------------------------------------------------- */
/* Time column header */
.calendar-wrapper .rbc-time-header {
  background: var(--color-surface-1);
  border-bottom: 1px solid var(--color-border);
}
.calendar-wrapper .rbc-time-header-cell {
  font-size: 11px;
  font-weight: 500;
  font-family: var(--font-sans);
  color: var(--color-text-secondary);
  padding: 6px 8px;
  border-right: 1px solid var(--color-border-light);
}

/* Time gutter (left column showing hours) */
.calendar-wrapper .rbc-time-gutter {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--color-text-disabled);
  background: var(--color-surface-1);
  border-right: 1px solid var(--color-border);
}
.calendar-wrapper .rbc-time-gutter .rbc-timeslot-group {
  padding: 0 6px;
}

/* Time content area */
.calendar-wrapper .rbc-time-content {
  border-top: 1px solid var(--color-border);
}
.calendar-wrapper .rbc-timeslot-group {
  border-bottom: 1px solid var(--color-border-light);
  min-height: 40px; /* RBC default ~60px — reduced for density */
}
.calendar-wrapper .rbc-time-slot {
  border-top: 1px solid var(--color-border-light);
}

/* Current time indicator (red line in day/week view) */
.calendar-wrapper .rbc-current-time-indicator {
  background: var(--color-danger);
  height: 2px;
}
.calendar-wrapper .rbc-current-time-indicator::before {
  /* the dot on the time indicator */
  background: var(--color-danger);
  width: 8px;
  height: 8px;
}

/* Time view events */
.calendar-wrapper .rbc-time-view .rbc-event {
  border-radius: 6px;
  padding: 4px 6px;
  font-size: 11px;
}

/* -------------------------------------------------------------------------
 * 6. AGENDA VIEW — Mobile-focused list view
 * ------------------------------------------------------------------------- */
.calendar-wrapper .rbc-agenda-view {
  font-family: var(--font-sans);
}
.calendar-wrapper .rbc-agenda-table {
  width: 100%;
  font-size: 13px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}
.calendar-wrapper .rbc-agenda-table thead {
  display: none; /* hide table header — date labels serve as section headers */
}
.calendar-wrapper .rbc-agenda-table tbody tr {
  border-bottom: 1px solid var(--color-border-light);
}
.calendar-wrapper .rbc-agenda-table tbody tr:last-child {
  border-bottom: none;
}
.calendar-wrapper .rbc-agenda-date-cell {
  padding: 10px 12px;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  background: var(--color-surface-1);
  border-right: 1px solid var(--color-border);
  white-space: nowrap;
  vertical-align: top;
  width: 90px;
}
.calendar-wrapper .rbc-agenda-event-cell {
  padding: 10px 12px;
  font-size: 13px;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: background-color 150ms ease-out;
}
.calendar-wrapper .rbc-agenda-event-cell:hover {
  background: var(--color-surface-2);
}

/* Agenda empty state */
.calendar-wrapper .rbc-agenda-empty {
  text-align: center;
  padding: 24px 16px;
  font-size: 13px;
  font-family: var(--font-sans);
  color: var(--color-text-disabled);
}

/* -------------------------------------------------------------------------
 * 7. OVERLAY / POPUP — "Show more" popup in month view
 * ------------------------------------------------------------------------- */
.calendar-wrapper .rbc-overlay {
  background: var(--color-surface-1);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
  padding: 8px;
  z-index: 50;
}
.calendar-wrapper .rbc-overlay-header {
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  padding: 6px 8px 8px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 4px;
}

/* -------------------------------------------------------------------------
 * 8. BUTTONS — Any RBC-generated buttons
 * ------------------------------------------------------------------------- */
.calendar-wrapper .rbc-btn-group button {
  font-size: 12px;
  font-family: var(--font-sans);
  color: var(--color-text-secondary);
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  padding: 4px 10px;
  cursor: pointer;
  transition: background-color 150ms ease-out, color 150ms ease-out;
}
.calendar-wrapper .rbc-btn-group button:first-child {
  border-radius: 6px 0 0 6px;
}
.calendar-wrapper .rbc-btn-group button:last-child {
  border-radius: 0 6px 6px 0;
}
.calendar-wrapper .rbc-btn-group button:hover {
  background: var(--color-surface-3);
  color: var(--color-text-primary);
}
.calendar-wrapper .rbc-btn-group button.rbc-active {
  background: var(--color-brand-bg);
  color: var(--color-brand);
  border-color: var(--color-border-accent);
}

/* -------------------------------------------------------------------------
 * 9. LOADING STATE
 * ------------------------------------------------------------------------- */
.calendar-wrapper .rbc-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  font-size: 13px;
  font-family: var(--font-sans);
  color: var(--color-text-disabled);
}
```

#### 4.1.5 RBC Classes NOT Overridden (Left at Default)

These RBC classes control structural behavior (positioning, flexbox, absolute placement of events in time slots). Overriding them breaks the calendar's layout engine:

| Class | Purpose | Why Not Override |
|-------|---------|-----------------|
| `.rbc-time-content` flex/grid layout | Positions events in time slots using absolute positioning | Math is internal to RBC — touching it breaks time-slot event rendering |
| `.rbc-row` / `.rbc-row-segment` | Month view row and event placement | Internal layout math |
| `.rbc-event-content` | Event text overflow/ellipsis | Handles truncation; style-only changes are safe |
| `.rbc-addons-dnd` | Drag-and-drop addon (not used in v1) | Not imported |
| `.rbc-calendar` | Root container | Set `height: 100%` on our wrapper instead |

#### 4.1.6 Known Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| RBC hardcodes `font-size: 12px` in 15+ places | Explicit `font-size` on every text class in overrides |
| RBC uses `#3174ad` (blue) for selections | Override via `.rbc-active` button styles |
| RBC event z-index stacking for overlapping events | Do not touch z-index — RBC's internal math handles overlap |
| RBC assumes 600px+ width for month view labels | Mobile defaults to agenda view; month view explicitly labeled "best in landscape" |
| RBC v1.x `date-fns` support is newer than `moment` | Pin `react-big-calendar@^1.16` (first version with stable date-fns localizer) and `date-fns@^3` |
| New RBC release could change class names | Pin to exact minor version; no `^` ranges in `package.json` |

### 4.2 Custom Event Component

```tsx
interface CalendarEventProps {
  event: CalendarEvent;
  continuesAfter?: boolean;
  continuesPrior?: boolean;
  title: string;
}

// Rendered inside RBC's event slot
function CalendarEventComponent({ event }: CalendarEventProps) {
  return (
    <div
      className="rbc-event-content flex items-center gap-1"
      data-category={event.category}
    >
      {event.all_day ? null : (
        <span className="text-[10px] opacity-80 shrink-0">
          {format(event.start_time, "h:mm a")}
        </span>
      )}
      <span className="truncate">{event.title}</span>
    </div>
  );
}
```

### 4.3 Category Color Map

| Category | Background | Text | Use |
|----------|-----------|------|-----|
| `hearing` | `bg-danger` | `text-white` | Court appearances |
| `deposition` | `bg-info` | `text-white` | Witness depositions |
| `deadline` | `bg-warning` | `text-white` | Filing deadlines |
| `meeting` | `bg-success` | `text-white` | Client/team meetings |
| `other` | `bg-surface-5` | `text-text-primary` | Uncategorized |

**Note:** These deviate from semantic meaning (danger ≠ bad). The colors are chosen for visual distinction on the calendar grid. The `danger` color for hearings makes them visually urgent — this is intentional.

---

## 5. SidePanel

### 5.1 Desktop (right sidebar)

```html
<aside class="w-[320px] border-l border-border bg-surface-1 overflow-y-auto
              flex flex-col shrink-0">
  <!-- Content: EventDetail or ReminderList or EmptyState -->
</aside>
```

### 5.2 Mobile (bottom sheet)

```html
<!-- Collapsed state: thin bar at bottom -->
<div class="lg:hidden fixed bottom-14 left-0 right-0 bg-surface-1 border-t border-border
            px-4 py-2 flex items-center justify-between cursor-pointer z-20
            pb-[env(safe-area-inset-bottom,0px)]">
  <span class="text-xs text-text-secondary">Event Details</span>
  <ChevronUp size={16} class="text-text-disabled" />
</div>

<!-- Expanded state: bottom sheet overlay -->
<div class="lg:hidden fixed inset-0 z-50 bg-black/60 flex items-end">
  <div class="bg-surface-1 border border-border rounded-t-xl shadow-md
              w-full max-h-[70dvh] overflow-y-auto p-5">
    <div class="w-10 h-1 bg-surface-5 rounded-full mx-auto mb-4" />
    <!-- Same content as desktop sidebar -->
  </div>
</div>
```

### 5.3 Default State: Upcoming Reminders

When no event is selected, the side panel shows pending reminders:

```
┌────────────────────────┐
│ Upcoming Reminders (3) │  ← text-sm font-semibold
│                        │
│ ┌────────────────────┐ │
│ │ 🔔 Subpoena follow  │ │  ← reminder row
│ │    Jun 22 · other   │ │
│ └────────────────────┘ │
│ ┌────────────────────┐ │
│ │ 🔔 Cross-claim SOL   │ │
│ │    Jul 1 · deadline  │ │
│ └────────────────────┘ │
│ ┌────────────────────┐ │
│ │ ✅ Engagement letter │ │  ← fired (bell-ring icon)
│ │    Fired Jun 18      │ │
│ └────────────────────┘ │
└────────────────────────┘
```

**Reminder row component:**
```html
<div class="flex items-center gap-2.5 p-2.5 rounded-lg
            hover:bg-surface-2 active:bg-surface-5
            transition-colors duration-150 cursor-pointer">
  <!-- Status icon -->
  <Bell size={16} class="text-warning shrink-0" />  <!-- pending -->
  <!-- or BellRing for fired, BellOff for dismissed -->
  
  <div class="flex-1 min-w-0">
    <p class="text-sm text-text-primary truncate">{title}</p>
    <p class="text-[10px] text-text-disabled">
      {format(remind_at, "MMM d · h:mm a")} · {category}
    </p>
  </div>
  
  <!-- Dismiss button (pending only) -->
  <button class="size-6 rounded-sm text-text-disabled hover:text-text-secondary">
    <X size={14} />
  </button>
</div>
```

---

## 6. EventDetail

Shown in the side panel when the user clicks an event on the calendar grid.

```html
<div class="p-4 flex flex-col gap-4">
  <!-- Close button (mobile) -->
  <button class="lg:hidden min-h-[44px] ..."><X /></button>

  <!-- Title + Category badge -->
  <div>
    <div class="flex items-center gap-2 mb-2">
      <span class="text-xs px-2 py-0.5 rounded-sm font-medium {categoryColor}">
        {category}
      </span>
      {all_day && <span class="text-xs text-text-disabled">All day</span>}
    </div>
    <h3 class="text-lg font-semibold text-text-primary">{title}</h3>
  </div>

  <!-- Time -->
  <div class="flex items-start gap-2">
    <Clock size={16} class="text-text-disabled mt-0.5 shrink-0" />
    <div>
      <p class="text-sm text-text-primary">
        {all_day
          ? format(event_date, "EEEE, MMMM d, yyyy")
          : format(start_time, "EEEE, MMMM d, yyyy")}
      </p>
      {!all_day && (
        <p class="text-sm text-text-secondary">
          {format(start_time, "h:mm a")}
          {end_time ? ` — ${format(end_time, "h:mm a")}` : ""}
        </p>
      )}
    </div>
  </div>

  <!-- Location (if set) -->
  {location && (
    <div class="flex items-start gap-2">
      <MapPin size={16} class="text-text-disabled mt-0.5 shrink-0" />
      <p class="text-sm text-text-primary">
        {isUrl(location)
          ? <a href={location} target="_blank" class="text-info hover:text-brand">{location}</a>
          : location}
      </p>
    </div>
  )}

  <!-- Description -->
  {description && (
    <div>
      <p class="text-xs font-medium text-text-secondary mb-1">Description</p>
      <p class="text-sm text-text-primary whitespace-pre-wrap leading-relaxed">
        {description}
      </p>
    </div>
  )}

  <!-- Attached reminders -->
  <div>
    <p class="text-xs font-medium text-text-secondary mb-2">
      Reminders ({attachedReminders.length})
    </p>
    {attachedReminders.map(r => <ReminderRow key={r.id} reminder={r} />)}
    <button class="text-xs text-info hover:text-brand transition-colors mt-1
                   flex items-center gap-1">
      <Plus size={12} /> Add reminder
    </button>
  </div>

  <!-- Created by -->
  <p class="text-[10px] text-text-disabled">
    Created {format(created_at, "MMM d, yyyy")} by {created_by ? "user" : "Agent"}
  </p>

  <!-- Actions -->
  <div class="flex items-center gap-2 pt-2 border-t border-border">
    <button class="/* secondary sm */" onClick={onEdit}>Edit</button>
    <button class="/* danger ghost */" onClick={onDelete}>Delete</button>
  </div>
</div>
```

---

## 7. CalendarEventForm (Modal)

Opened by "+ New Event" button or "Edit" on EventDetail.

### 7.1 Fields

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| Title | `text` | Yes | Non-empty, max 200 chars |
| Description | `textarea` | No | Max 5000 chars |
| Start Date | `date` | Yes | Required |
| Start Time | `time` | No | Required unless all_day |
| End Date | `date` | No | Must be ≥ start date |
| End Time | `time` | No | Must be after start time if same date |
| All Day | `checkbox` | No | When checked, hides time inputs |
| Category | `select` | Yes | One of: hearing, deposition, deadline, meeting, other |
| Location | `text` | No | URL or physical address |

### 7.2 Layout

```html
<Modal open={open} onClose={onClose} title={editing ? "Edit Event" : "New Event"}>
  <form class="flex flex-col gap-4" onSubmit={handleSubmit}>
    <div class="flex flex-col gap-1.5">
      <label class="block text-sm font-medium text-text-secondary">Title</label>
      <input type="text" required maxLength={200}
             class="/* standard input */" autoFocus />
    </div>

    <div class="flex flex-col gap-1.5">
      <label class="block text-sm font-medium text-text-secondary">Description</label>
      <textarea rows={4} maxLength={5000}
                class="/* standard textarea */"
                placeholder="Event details..." />
    </div>

    <!-- Date/Time row -->
    <div class="grid grid-cols-2 gap-3">
      <div class="flex flex-col gap-1.5">
        <label class="block text-sm font-medium text-text-secondary">Start Date</label>
        <input type="date" required class="/* standard input */" />
      </div>
      <div class="flex flex-col gap-1.5">
        <label class="block text-sm font-medium text-text-secondary">Start Time</label>
        <input type="time" class="/* standard input */" disabled={allDay} />
      </div>
    </div>

    <div class="grid grid-cols-2 gap-3">
      <div class="flex flex-col gap-1.5">
        <label class="block text-sm font-medium text-text-secondary">End Date</label>
        <input type="date" class="/* standard input */" />
      </div>
      <div class="flex flex-col gap-1.5">
        <label class="block text-sm font-medium text-text-secondary">End Time</label>
        <input type="time" class="/* standard input */" disabled={allDay} />
      </div>
    </div>

    <!-- All day toggle -->
    <label class="inline-flex items-center gap-2 cursor-pointer">
      <input type="checkbox" class="size-4 rounded-sm ..." />
      <span class="text-sm text-text-primary">All day event</span>
    </label>

    <!-- Category + Location row -->
    <div class="grid grid-cols-2 gap-3">
      <div class="flex flex-col gap-1.5">
        <label class="block text-sm font-medium text-text-secondary">Category</label>
        <select required class="/* standard select */">
          <option value="hearing">Hearing</option>
          <option value="deposition">Deposition</option>
          <option value="deadline">Deadline</option>
          <option value="meeting">Meeting</option>
          <option value="other">Other</option>
        </select>
      </div>
      <div class="flex flex-col gap-1.5">
        <label class="block text-sm font-medium text-text-secondary">Location</label>
        <input type="text" class="/* standard input */" placeholder="Optional" />
      </div>
    </div>

    <!-- Footer: Cancel + Save (per component-patterns §2) -->
    <div class="flex flex-col sm:flex-row sm:justify-end gap-2 sm:gap-3 mt-2">
      <button type="button" class="/* secondary */ order-2 sm:order-1">Cancel</button>
      <button type="submit" disabled={saving}
              class="/* primary */ order-1 sm:order-2">
        {saving ? "Saving..." : (editing ? "Save Changes" : "Create Event")}
      </button>
    </div>
  </form>
</Modal>
```

**Mobile adaptations:**
- Date/time inputs use `text-[16px]` to prevent iOS auto-zoom
- Form buttons: full-width, stacked (Cancel below Save per mobile rules §11.8)
- All fields stack vertically (no grid-cols-2 on screens <640px)

---

## 8. ReminderForm (Modal)

Opened by "+ Reminder" button or "Add reminder" on EventDetail.

### 8.1 Fields

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| Title | `text` | Yes | Non-empty, max 200 chars |
| Description | `textarea` | No | Max 2000 chars |
| Date | `date` | Yes | Required |
| Time | `time` | Yes | Required |
| Category | `select` | Yes | Same options as events |
| Event | `select` (optional) | No | "Standalone reminder" by default, or select an existing event |

### 8.2 Event Attachment

When opened from an event (via "+ Add reminder" on EventDetail), the `event_id` is pre-set and the field is hidden. When opened standalone ("+ Reminder" from toolbar), the user can optionally link to an event:

```html
<div class="flex flex-col gap-1.5">
  <label class="block text-sm font-medium text-text-secondary">Attach to Event (optional)</label>
  <select class="/* standard select */">
    <option value="">Standalone reminder</option>
    {events.map(e => <option value={e.id}>{e.title} — {format(e.start_time, "MMM d")}</option>)}
  </select>
</div>
```

### 8.3 Layout

Same modal pattern as CalendarEventForm, but with fewer fields. Footer: Cancel + "Create Reminder" (or "Save Changes").

---

## 9. useReminderPolling Hook

### 9.1 Behavior

```typescript
function useReminderPolling(caseId: number, intervalMs: number = 30_000) {
  // 1. Fetch pending reminders on mount
  // 2. Poll every `intervalMs` (default 30 seconds)
  // 3. For each reminder where remind_at <= now():
  //    a. Fire in-app toast via existing toast pattern
  //    b. Fire browser notification if permission granted
  //    c. PATCH reminder status → "fired"
  // 4. Request browser notification permission once; store result in localStorage
  // 5. Clear interval on unmount
  // 6. No polling when tab is hidden (use document.visibilitychange)
}
```

### 9.2 Toast Format

```json
{
  "type": "warning",
  "title": "Reminder: {reminder.title}",
  "description": "{category} — {format(remind_at, 'MMM d, h:mm a')}"
}
```

### 9.3 Browser Notification Format

```javascript
new Notification("Reminder — Vision", {
  body: `${reminder.title}\n${category} · ${format(remind_at, "MMM d, h:mm a")}`,
  icon: "/favicon.ico",
  tag: `reminder-${reminder.id}`, // prevents duplicate notifications
});
```

### 9.4 Permission Request

```typescript
// On first calendar tab mount:
const stored = localStorage.getItem("vision_notify_permission");
if (!stored && "Notification" in window && Notification.permission === "default") {
  // Show a subtle inline banner, NOT a modal:
  // "Allow browser notifications for reminders? [Allow] [Not now]"
  // User choice stored in localStorage.
}
```

**Banner style:**
```html
<div class="bg-info-bg border border-info/20 rounded-lg p-3 flex items-center gap-3">
  <Bell size={16} class="text-info shrink-0" />
  <p class="text-xs text-text-secondary flex-1">
    Allow browser notifications when reminders are due?
  </p>
  <button class="/* primary sm */">Allow</button>
  <button class="/* ghost sm */">Not now</button>
</div>
```

---

## 10. Responsive Behavior Matrix

| State | Desktop (≥1024px) | Tablet (768-1023px) | Mobile (<768px) |
|-------|-------------------|---------------------|-----------------|
| **Layout** | CalendarGrid + SidePanel side by side | CalendarGrid full width, SidePanel as overlay | CalendarGrid full width, SidePanel as bottom sheet |
| **Default View** | Month | Month | Agenda |
| **View Switcher** | Segmented buttons | Segmented buttons | Native `<select>` dropdown |
| **New Event/Rem** | Buttons in toolbar | Buttons in toolbar | Buttons in toolbar (compact) |
| **Event Form** | Centered modal | Centered modal | Full-width bottom sheet |
| **Side Panel** | Fixed 320px right | Toggle overlay (tap to open) | Bottom sheet (slide up) |
| **Touch Targets** | Standard (32px+) | Hybrid (40px+) | 44px minimum |

### 10.1 Breakpoint Queries

```typescript
// In CalendarTab:
const isMobile = useMediaQuery("(max-width: 767px)");
const isTablet = useMediaQuery("(min-width: 768px) and (max-width: 1023px)");

const defaultView = isMobile ? "agenda" : "month";
const availableViews: View[] = isMobile
  ? ["agenda", "month", "day"]
  : ["month", "week", "day", "agenda"];
```

---

## 11. State Management

### 11.1 CalendarTab State

```typescript
interface CalendarTabState {
  // Data
  events: CalendarEvent[];
  reminders: Reminder[];
  loading: boolean;

  // Selection
  selectedEventId: number | null;
  selectedEvent: CalendarEvent | null;  // includes attached reminders

  // Modals
  eventFormOpen: boolean;
  editingEventId: number | null;        // null = create new
  reminderFormOpen: boolean;
  editingReminderId: number | null;
  prefillEventId: number | null;        // when creating reminder from event

  // Calendar display
  currentDate: Date;                    // RBC navigator state
  currentView: View;                    // "month" | "week" | "day" | "agenda"

  // Side panel (mobile)
  sidePanelOpen: boolean;

  // Notification
  notificationPermission: "granted" | "denied" | "default";
  showNotificationBanner: boolean;
}
```

### 11.2 Data Flow

```
CalendarTab (state owner)
├── fetches: GET /cases/{caseId}/calendar/events
│            GET /cases/{caseId}/calendar/reminders
├── passes events[] → CalendarGrid
├── passes selectedEvent → SidePanel > EventDetail
├── passes reminders[] → SidePanel > ReminderList
├── opens CalendarEventForm → creates/edits → POST/PATCH → refresh
├── opens ReminderForm → creates/edits → POST/PATCH → refresh
└── useReminderPolling → fires toasts + notifications → PATCH reminder status
```

### 11.3 Refresh Strategy

After any mutation (create, edit, delete), refetch both events and reminders:

```typescript
const refresh = useCallback(async () => {
  const [ev, rem] = await Promise.all([
    listCalendarEvents(caseId, { start_date: rangeStart, end_date: rangeEnd }),
    listReminders(caseId),
  ]);
  setEvents(ev.events);
  setReminders(rem.reminders);
}, [caseId, rangeStart, rangeEnd]);
```

---

## 12. Empty States

### 12.1 No Events

```html
<div class="flex flex-col items-center justify-center py-16 gap-4 text-center">
  <CalendarDays size={32} class="text-text-disabled" />
  <div>
    <p class="text-sm font-medium text-text-secondary">No calendar events</p>
    <p class="text-xs text-text-disabled mt-1">
      Create an event or ask the agent to add one.
    </p>
  </div>
  <button class="/* primary */">New Event</button>
</div>
```

### 12.2 No Reminders

```html
<div class="flex flex-col items-center justify-center py-8 gap-3 text-center px-4">
  <Bell size={24} class="text-text-disabled" />
  <p class="text-xs text-text-disabled">No upcoming reminders</p>
</div>
```

### 12.3 No Event Selected (Side Panel)

```html
<div class="flex flex-col items-center justify-center py-12 gap-3 text-center px-4">
  <CalendarDays size={28} class="text-text-disabled" />
  <p class="text-xs text-text-secondary">Select an event to see details</p>
</div>
```

---

## 13. Integration with TabNav

Calendar is added to `TabNav.tsx`:

```typescript
// TabId type
export type TabId = "overview" | "chat" | "documents" | "drafts"
  | "workspace" | "correspondence" | "tasks" | "calendar";

// TABS array (append at end)
{ id: "calendar", label: "Calendar", shortLabel: "Cal", icon: CalendarDays }
```

**Mobile impact:** Calendar is the 7th entry in `TABS` (index 6). With `PRIMARY_COUNT = 4`, it falls into `secondaryTabs` (index 4+), appearing in the "More" overflow menu on mobile. Desktop sidebar shows all tabs with equal weight — Calendar is simply the 7th item in the vertical icon rail.

---

## 14. Design System Compliance Checklist

Each component must pass before code is committed:

- [ ] All interactive elements have `min-h-[44px] min-w-[44px]` on mobile
- [ ] Every `hover:` is paired with an `active:` equivalent
- [ ] Tables (if any) wrapped in `overflow-x-auto`
- [ ] Modals become bottom sheets on screens <640px
- [ ] Toast notifications appear above the bottom tab bar (`bottom-16`)
- [ ] No arbitrary Tailwind values — all spacing is multiples of 4px
- [ ] All colors reference `--surface-*`, `--text-*`, `--brand`, `--border`, or semantic tokens
- [ ] Geist Sans for all text; Geist Mono only for code/timestamps
- [ ] Font weights limited to 400, 500, 600, 700
- [ ] Border radius: `rounded-sm` (inputs), `rounded-lg` (cards/modals), `rounded-xl` (containers)
- [ ] Shadows: `shadow-sm` (nested cards) or `shadow-md` (modals/dropdowns) — no glow effects
- [ ] Transitions: `duration-150` for hover/focus, `duration-250` for panel open/close
- [ ] Form inputs: `text-[16px]` on mobile to prevent iOS zoom
- [ ] `100dvh` used for full-screen panels, not `100vh`
- [ ] Bottom-fixed elements include `pb-[env(safe-area-inset-bottom,0px)]`
- [ ] No `user-select: none` on text content
