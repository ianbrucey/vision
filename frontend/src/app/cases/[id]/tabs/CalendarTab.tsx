"use client";

import { useState, useEffect, useCallback } from "react";
import { Calendar, dateFnsLocalizer, type View } from "react-big-calendar";
import { format, parse, startOfWeek, getDay } from "date-fns";
import { enUS } from "date-fns/locale";

// RBC base CSS — must load BEFORE our overrides
import "react-big-calendar/lib/css/react-big-calendar.css";
import "@/app/calendar-overrides.css";
import { ChevronLeft, ChevronRight, Plus, CalendarDays, Bell, ChevronUp, X, Loader2 } from "lucide-react";

import { useReminderPolling } from "@/lib/useReminderPolling";
import {
  listCalendarEvents,
  listReminders,
  createCalendarEvent,
  updateCalendarEvent,
  deleteCalendarEvent,
  createReminder,
  updateReminder,
  deleteReminder,
  type CalendarEvent,
  type Reminder,
} from "@/lib/api";

/* ------------------------------------------------------------------ */
/* date-fns localizer for React Big Calendar                           */
/* ------------------------------------------------------------------ */

const locales = { "en-US": { /* provided by date-fns locale */ } };

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek: () => startOfWeek(new Date(), { weekStartsOn: 0 }),
  getDay,
  locales: { "en-US": enUS },
});

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const CATEGORY_COLORS: Record<string, string> = {
  hearing: "bg-danger text-white",
  deposition: "bg-info text-white",
  deadline: "bg-warning text-white",
  meeting: "bg-success text-white",
  other: "bg-surface-5 text-text-primary",
};

const CATEGORY_LABELS: Record<string, string> = {
  hearing: "Hearing",
  deposition: "Deposition",
  deadline: "Deadline",
  meeting: "Meeting",
  other: "Other",
};

const REMINDER_STATUS_ICONS: Record<string, string> = {
  pending: "text-warning",
  fired: "text-info",
  dismissed: "text-text-disabled",
};

function formatEventTime(event: CalendarEvent): string {
  if (event.all_day) return "All day";
  const start = new Date(event.start_time);
  const startStr = start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  if (!event.end_time) return startStr;
  const end = new Date(event.end_time);
  const endStr = end.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  return `${startStr} — ${endStr}`;
}

/* ------------------------------------------------------------------ */
/* Custom Event Component (rendered inside RBC)                        */
/* ------------------------------------------------------------------ */

function CalendarEventComponent({ event }: { event: CalendarEvent }) {
  return (
    <div className="flex items-center gap-1 truncate" data-category={event.category}>
      {!event.all_day && (
        <span className="text-[10px] opacity-80 shrink-0">
          {format(new Date(event.start_time), "h:mm a")}
        </span>
      )}
      <span className="truncate">{event.title}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

interface CalendarTabProps {
  caseId: number;
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function CalendarTab({ caseId }: CalendarTabProps) {
  /* ---- state ---- */
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [sidePanelOpen, setSidePanelOpen] = useState(false); // mobile

  const [currentDate, setCurrentDate] = useState(new Date());
  const [currentView, setCurrentView] = useState<View>("month");

  const [showEventForm, setShowEventForm] = useState(false);
  const [editingEventId, setEditingEventId] = useState<number | null>(null);
  const [showReminderForm, setShowReminderForm] = useState(false);
  const [editingReminderId, setEditingReminderId] = useState<number | null>(null);
  const [prefillEventId, setPrefillEventId] = useState<number | null>(null);

  const [saving, setSaving] = useState(false);

  /* ---- reminder polling ---- */
  useReminderPolling(caseId, {
    onFire: (reminder) => {
      // Refresh reminders list when one fires
      refresh();
    },
  });

  /* ---- responsive ---- */
  const isMobile = typeof window !== "undefined" ? window.innerWidth < 768 : false;
  const defaultView: View = isMobile ? "agenda" : "month";

  /* ---- data fetching ---- */
  const refresh = useCallback(async () => {
    try {
      const [evRes, remRes] = await Promise.all([
        listCalendarEvents(caseId),
        listReminders(caseId),
      ]);
      setEvents(evRes.events);
      setReminders(remRes.reminders);
    } catch {
      /* silent — keep existing data */
    }
    setLoading(false);
  }, [caseId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  /* ---- event handlers ---- */
  const handleSelectEvent = (event: CalendarEvent) => {
    setSelectedEvent(event);
    setSidePanelOpen(true);
  };

  const handleSelectSlot = ({ start }: { start: Date }) => {
    // Clicking an empty slot: pre-fill start time in new event form
    setEditingEventId(null);
    setPrefillEventId(null);
    setShowEventForm(true);
  };

  const handleNavigate = (newDate: Date) => {
    setCurrentDate(newDate);
  };

  const handleViewChange = (view: View) => {
    setCurrentView(view);
  };

  const handleEventCreate = async (data: {
    title: string;
    start_time: string;
    end_time?: string;
    all_day?: boolean;
    category?: string;
    description?: string;
    location?: string;
  }) => {
    setSaving(true);
    try {
      if (editingEventId) {
        await updateCalendarEvent(editingEventId, data);
      } else {
        await createCalendarEvent(caseId, data);
      }
      setShowEventForm(false);
      setEditingEventId(null);
      refresh();
    } catch {
      /* handled by form */
    }
    setSaving(false);
  };

  const handleReminderCreate = async (data: {
    title: string;
    remind_at: string;
    event_id?: number;
    category?: string;
    description?: string;
  }) => {
    setSaving(true);
    try {
      if (editingReminderId) {
        await updateReminder(editingReminderId, data);
      } else {
        await createReminder(caseId, data);
      }
      setShowReminderForm(false);
      setEditingReminderId(null);
      setPrefillEventId(null);
      refresh();
    } catch {
      /* handled by form */
    }
    setSaving(false);
  };

  const handleEventDelete = async (eventId: number) => {
    await deleteCalendarEvent(eventId);
    setSelectedEvent(null);
    setSidePanelOpen(false);
    refresh();
  };

  const handleReminderDelete = async (reminderId: number) => {
    await deleteReminder(reminderId);
    refresh();
  };

  const handleReminderDismiss = async (reminderId: number) => {
    await updateReminder(reminderId, { status: "dismissed" });
    refresh();
  };

  /* ---- RBC event style ---- */
  const eventPropGetter = (event: CalendarEvent) => ({
    className: `rbc-event-custom`,
    "data-category": event.category,
  });

  /* ---- loading ---- */
  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  /* ---- render ---- */
  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* ================================================================ */}
      {/* CalendarHeader                                                    */}
      {/* ================================================================ */}
      <header className="shrink-0 bg-surface-1 border-b border-border px-3 py-2
                        flex items-center justify-between gap-2 flex-wrap">
        {/* Left: date navigator */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => {
              const d = new Date(currentDate);
              if (currentView === "month") d.setMonth(d.getMonth() - 1);
              else if (currentView === "week") d.setDate(d.getDate() - 7);
              else d.setDate(d.getDate() - 1);
              setCurrentDate(d);
            }}
            className="size-8 rounded-sm inline-flex items-center justify-center
                       text-text-secondary hover:bg-surface-2 hover:text-text-primary
                       transition-colors duration-150"
            aria-label="Previous"
          >
            <ChevronLeft size={18} />
          </button>
          <h2 className="text-sm font-semibold text-text-primary min-w-[140px] text-center">
            {format(currentDate, currentView === "month" ? "MMMM yyyy" : "MMMM d, yyyy")}
          </h2>
          <button
            onClick={() => {
              const d = new Date(currentDate);
              if (currentView === "month") d.setMonth(d.getMonth() + 1);
              else if (currentView === "week") d.setDate(d.getDate() + 7);
              else d.setDate(d.getDate() + 1);
              setCurrentDate(d);
            }}
            className="size-8 rounded-sm inline-flex items-center justify-center
                       text-text-secondary hover:bg-surface-2 hover:text-text-primary
                       transition-colors duration-150"
            aria-label="Next"
          >
            <ChevronRight size={18} />
          </button>
          <button
            onClick={() => setCurrentDate(new Date())}
            className="ml-2 text-xs px-2.5 py-1 rounded-md border border-border
                       text-text-secondary hover:bg-surface-2 transition-colors"
          >
            Today
          </button>
        </div>

        {/* Right: view switcher + action buttons */}
        <div className="flex items-center gap-2">
          {/* View switcher */}
          <select
            value={currentView}
            onChange={(e) => setCurrentView(e.target.value as View)}
            className="text-xs bg-surface-2 border border-border rounded px-2 py-1
                       text-text-secondary cursor-pointer hidden sm:block"
          >
            <option value="month">Month</option>
            <option value="week">Week</option>
            <option value="day">Day</option>
            <option value="agenda">Agenda</option>
          </select>
          {/* Mobile: simplified view switcher */}
          <select
            value={currentView}
            onChange={(e) => setCurrentView(e.target.value as View)}
            className="text-xs bg-surface-2 border border-border rounded px-2 py-1
                       text-text-secondary cursor-pointer sm:hidden"
          >
            <option value="agenda">Agenda</option>
            <option value="month">Month</option>
            <option value="day">Day</option>
          </select>

          <button
            onClick={() => { setEditingEventId(null); setShowEventForm(true); }}
            className="text-xs px-3 py-1.5 rounded-md bg-brand text-white
                       hover:bg-brand-hover transition-colors flex items-center gap-1"
          >
            <Plus size={13} /> <span className="hidden sm:inline">New Event</span>
          </button>
          <button
            onClick={() => { setEditingReminderId(null); setPrefillEventId(null); setShowReminderForm(true); }}
            className="text-xs px-3 py-1.5 rounded-md bg-surface-2 text-text-secondary
                       border border-border hover:bg-surface-3 transition-colors
                       flex items-center gap-1"
          >
            <Bell size={13} /> <span className="hidden sm:inline">Reminder</span>
          </button>
        </div>
      </header>

      {/* ================================================================ */}
      {/* Calendar Body                                                     */}
      {/* ================================================================ */}
      <div className="flex-1 flex min-h-0">
        {/* Calendar Grid */}
        <div className="flex-1 min-w-0 calendar-wrapper h-full p-2 md:p-4">
          {events.length === 0 && !loading ? (
            <div className="flex flex-col items-center justify-center py-16 gap-4 text-center h-full">
              <CalendarDays size={32} className="text-text-disabled" />
              <div>
                <p className="text-sm font-medium text-text-secondary">No calendar events</p>
                <p className="text-xs text-text-disabled mt-1">
                  Create an event or ask the agent to add one.
                </p>
              </div>
              <button
                onClick={() => { setEditingEventId(null); setShowEventForm(true); }}
                className="text-xs px-3 py-1.5 rounded-md bg-brand text-white
                           hover:bg-brand-hover transition-colors inline-flex items-center gap-1"
              >
                <Plus size={13} /> New Event
              </button>
            </div>
          ) : (
            <Calendar
              localizer={localizer}
              events={events}
              startAccessor={(e: CalendarEvent) => new Date(e.start_time)}
              endAccessor={(e: CalendarEvent) => e.end_time ? new Date(e.end_time) : new Date(e.start_time)}
              date={currentDate}
              view={currentView}
              onNavigate={handleNavigate}
              onView={handleViewChange}
              defaultView={defaultView}
              onSelectEvent={handleSelectEvent}
              onSelectSlot={handleSelectSlot}
              selectable
              eventPropGetter={eventPropGetter as any}
              components={{ event: CalendarEventComponent as any }}
              style={{ height: "100%" }}
              views={["month", "week", "day", "agenda"] as View[]}
              popup
              tooltipAccessor={null}
            />
          )}
        </div>

        {/* ================================================================ */}
        {/* Side Panel — Desktop (always visible when event selected)         */}
        {/* ================================================================ */}
        {selectedEvent && (
          <aside className="hidden lg:flex flex-col w-[320px] border-l border-border bg-surface-1
                            overflow-y-auto shrink-0">
            <EventDetailPanel
              event={selectedEvent}
              reminders={reminders.filter((r) => r.event_id === selectedEvent.id)}
              onEdit={() => { setEditingEventId(selectedEvent.id); setShowEventForm(true); }}
              onDelete={() => handleEventDelete(selectedEvent.id)}
              onAddReminder={() => {
                setEditingReminderId(null);
                setPrefillEventId(selectedEvent.id);
                setShowReminderForm(true);
              }}
            />
          </aside>
        )}
        {!selectedEvent && (
          <aside className="hidden lg:flex flex-col w-[320px] border-l border-border bg-surface-1
                            overflow-y-auto shrink-0 p-4">
            <ReminderListPanel
              reminders={reminders}
              onDismiss={handleReminderDismiss}
              onDelete={handleReminderDelete}
            />
          </aside>
        )}
      </div>

      {/* ================================================================ */}
      {/* Mobile Bottom Sheet (event detail / reminders)                     */}
      {/* ================================================================ */}
      {sidePanelOpen && selectedEvent && (
        <div className="lg:hidden fixed inset-0 z-50 bg-black/60 flex items-end"
             onClick={(e) => { if (e.target === e.currentTarget) setSidePanelOpen(false); }}>
          <div className="bg-surface-1 border border-border rounded-t-xl shadow-md
                        w-full max-h-[70dvh] overflow-y-auto p-5">
            <div className="w-10 h-1 bg-surface-5 rounded-full mx-auto mb-4" />
            <EventDetailPanel
              event={selectedEvent}
              reminders={reminders.filter((r) => r.event_id === selectedEvent.id)}
              onEdit={() => { setEditingEventId(selectedEvent.id); setShowEventForm(true); }}
              onDelete={() => handleEventDelete(selectedEvent.id)}
              onAddReminder={() => {
                setEditingReminderId(null);
                setPrefillEventId(selectedEvent.id);
                setShowReminderForm(true);
              }}
              onClose={() => setSidePanelOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Mobile: Collapsed reminder bar */}
      {!selectedEvent && (
        <div className="lg:hidden fixed bottom-14 left-0 right-0 bg-surface-1 border-t border-border
                        px-4 py-2 flex items-center justify-between cursor-pointer z-20
                        pb-[env(safe-area-inset-bottom,0px)]"
             onClick={() => setSidePanelOpen(true)}>
          <span className="text-xs text-text-secondary">
            Upcoming · {reminders.filter((r) => r.status === "pending").length} pending
          </span>
          <ChevronUp size={16} className="text-text-disabled" />
        </div>
      )}

      {/* ================================================================ */}
      {/* CalendarEventForm (Modal)                                         */}
      {/* ================================================================ */}
      {showEventForm && (
        <CalendarEventFormModal
          editingEvent={editingEventId ? events.find((e) => e.id === editingEventId) || null : null}
          onSave={handleEventCreate}
          onClose={() => { setShowEventForm(false); setEditingEventId(null); }}
          saving={saving}
        />
      )}

      {/* ================================================================ */}
      {/* ReminderForm (Modal)                                              */}
      {/* ================================================================ */}
      {showReminderForm && (
        <ReminderFormModal
          editingReminder={editingReminderId ? reminders.find((r) => r.id === editingReminderId) || null : null}
          prefillEventId={prefillEventId}
          events={events}
          onSave={handleReminderCreate}
          onClose={() => {
            setShowReminderForm(false);
            setEditingReminderId(null);
            setPrefillEventId(null);
          }}
          saving={saving}
        />
      )}
    </div>
  );
}

/* ==================================================================== */
/* EventDetailPanel                                                      */
/* ==================================================================== */

function EventDetailPanel({
  event,
  reminders,
  onEdit,
  onDelete,
  onAddReminder,
  onClose,
}: {
  event: CalendarEvent;
  reminders: Reminder[];
  onEdit: () => void;
  onDelete: () => void;
  onAddReminder: () => void;
  onClose?: () => void;
}) {
  const [confirmDelete, setConfirmDelete] = useState(false);

  return (
    <div className="flex flex-col gap-4">
      {/* Close button (mobile) */}
      {onClose && (
        <button
          onClick={onClose}
          className="lg:hidden min-h-[44px] min-w-[44px] inline-flex items-center justify-center
                     rounded-sm text-text-secondary hover:bg-surface-2 self-end"
        >
          <X size={18} />
        </button>
      )}

      {/* Title + Category badge */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className={`text-xs px-2 py-0.5 rounded-sm font-medium ${CATEGORY_COLORS[event.category]}`}>
            {CATEGORY_LABELS[event.category]}
          </span>
          {event.all_day && <span className="text-xs text-text-disabled">All day</span>}
        </div>
        <h3 className="text-lg font-semibold text-text-primary">{event.title}</h3>
      </div>

      {/* Time */}
      <div className="flex items-start gap-2">
        <CalendarDays size={16} className="text-text-disabled mt-0.5 shrink-0" />
        <div>
          <p className="text-sm text-text-primary">
            {event.all_day
              ? format(new Date(event.start_time), "EEEE, MMMM d, yyyy")
              : format(new Date(event.start_time), "EEEE, MMMM d, yyyy")}
          </p>
          {!event.all_day && (
            <p className="text-sm text-text-secondary">{formatEventTime(event)}</p>
          )}
        </div>
      </div>

      {/* Location */}
      {event.location && (
        <div className="flex items-start gap-2">
          <span className="text-text-disabled mt-0.5 shrink-0 text-sm">📍</span>
          <p className="text-sm text-text-primary break-all">
            {event.location.startsWith("http") ? (
              <a href={event.location} target="_blank" rel="noopener noreferrer"
                 className="text-info hover:text-brand underline-offset-2 hover:underline">
                {event.location}
              </a>
            ) : event.location}
          </p>
        </div>
      )}

      {/* Description */}
      {event.description && (
        <div>
          <p className="text-xs font-medium text-text-secondary mb-1">Description</p>
          <p className="text-sm text-text-primary whitespace-pre-wrap leading-relaxed">
            {event.description}
          </p>
        </div>
      )}

      {/* Attached reminders */}
      <div>
        <p className="text-xs font-medium text-text-secondary mb-2">
          Reminders ({reminders.length})
        </p>
        {reminders.map((r) => (
          <div key={r.id} className="flex items-center gap-2 py-1.5 text-sm">
            <Bell size={14} className={REMINDER_STATUS_ICONS[r.status]} />
            <span className={r.status === "dismissed" ? "line-through text-text-disabled" : "text-text-primary"}>
              {r.title}
            </span>
            <span className="text-xs text-text-disabled ml-auto">
              {format(new Date(r.remind_at), "MMM d, h:mm a")}
            </span>
          </div>
        ))}
        <button
          onClick={onAddReminder}
          className="text-xs text-info hover:text-brand transition-colors mt-1
                     flex items-center gap-1"
        >
          <Plus size={12} /> Add reminder
        </button>
      </div>

      {/* Created by */}
      <p className="text-[10px] text-text-disabled">
        Created {format(new Date(event.created_at), "MMM d, yyyy")} by{" "}
        {event.created_by === "agent" ? "Agent" : "User"}
      </p>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2 border-t border-border">
        <button
          onClick={onEdit}
          className="text-xs px-3 py-1.5 rounded-md bg-surface-2 text-text-secondary
                     border border-border hover:bg-surface-3 transition-colors"
        >
          Edit
        </button>
        {confirmDelete ? (
          <div className="flex items-center gap-1">
            <span className="text-xs text-danger">Delete?</span>
            <button
              onClick={() => { onDelete(); setConfirmDelete(false); }}
              className="text-xs px-2 py-1 rounded bg-danger text-white hover:opacity-90"
            >
              Yes
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="text-xs px-2 py-1 rounded bg-surface-2 text-text-secondary"
            >
              No
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmDelete(true)}
            className="text-xs px-3 py-1.5 rounded-md text-danger
                       hover:bg-danger-bg transition-colors"
          >
            Delete
          </button>
        )}
      </div>
    </div>
  );
}

/* ==================================================================== */
/* ReminderListPanel                                                     */
/* ==================================================================== */

function ReminderListPanel({
  reminders,
  onDismiss,
  onDelete,
}: {
  reminders: Reminder[];
  onDismiss: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  const pending = reminders.filter((r) => r.status === "pending");
  const fired = reminders.filter((r) => r.status === "fired");
  const dismissed = reminders.filter((r) => r.status === "dismissed");

  if (reminders.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
        <Bell size={28} className="text-text-disabled" />
        <p className="text-xs text-text-disabled">No reminders yet</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-sm font-semibold text-text-primary">Reminders</h3>

      {pending.length > 0 && (
        <div>
          <p className="text-xs font-medium text-text-secondary mb-2">
            Upcoming ({pending.length})
          </p>
          {pending.map((r) => (
            <ReminderRow key={r.id} reminder={r} onDismiss={onDismiss} onDelete={onDelete} />
          ))}
        </div>
      )}

      {fired.length > 0 && (
        <div>
          <p className="text-xs font-medium text-text-secondary mb-2">
            Fired ({fired.length})
          </p>
          {fired.map((r) => (
            <ReminderRow key={r.id} reminder={r} onDismiss={onDismiss} onDelete={onDelete} />
          ))}
        </div>
      )}

      {dismissed.length > 0 && (
        <div>
          <p className="text-xs font-medium text-text-secondary mb-2">
            Dismissed ({dismissed.length})
          </p>
          {dismissed.map((r) => (
            <ReminderRow key={r.id} reminder={r} onDismiss={onDismiss} onDelete={onDelete} />
          ))}
        </div>
      )}
    </div>
  );
}

function ReminderRow({
  reminder,
  onDismiss,
  onDelete,
}: {
  reminder: Reminder;
  onDismiss: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <div className="flex items-center gap-2.5 p-2 rounded-lg
                    hover:bg-surface-2 transition-colors duration-150 group">
      <Bell size={14} className={`shrink-0 ${REMINDER_STATUS_ICONS[reminder.status]}`} />
      <div className="flex-1 min-w-0">
        <p className={`text-sm truncate ${reminder.status === "dismissed" ? "line-through text-text-disabled" : "text-text-primary"}`}>
          {reminder.title}
        </p>
        <p className="text-[10px] text-text-disabled">
          {format(new Date(reminder.remind_at), "MMM d · h:mm a")} · {CATEGORY_LABELS[reminder.category]}
        </p>
      </div>
      {reminder.status === "pending" && (
        <button
          onClick={() => onDismiss(reminder.id)}
          className="size-5 rounded-sm text-text-disabled hover:text-text-secondary
                     opacity-0 group-hover:opacity-100 transition-opacity"
          title="Dismiss"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}

/* ==================================================================== */
/* CalendarEventFormModal                                                */
/* ==================================================================== */

function CalendarEventFormModal({
  editingEvent,
  onSave,
  onClose,
  saving,
}: {
  editingEvent: CalendarEvent | null;
  onSave: (data: { title: string; start_time: string; end_time?: string; all_day?: boolean; category?: string; description?: string; location?: string }) => void;
  onClose: () => void;
  saving: boolean;
}) {
  const [title, setTitle] = useState(editingEvent?.title || "");
  const [description, setDescription] = useState(editingEvent?.description || "");
  const [startDate, setStartDate] = useState(
    editingEvent ? format(new Date(editingEvent.start_time), "yyyy-MM-dd") : ""
  );
  const [startTime, setStartTime] = useState(
    editingEvent && !editingEvent.all_day
      ? format(new Date(editingEvent.start_time), "HH:mm")
      : ""
  );
  const [endDate, setEndDate] = useState(
    editingEvent?.end_time ? format(new Date(editingEvent.end_time), "yyyy-MM-dd") : ""
  );
  const [endTime, setEndTime] = useState(
    editingEvent?.end_time && !editingEvent.all_day
      ? format(new Date(editingEvent.end_time), "HH:mm")
      : ""
  );
  const [allDay, setAllDay] = useState(editingEvent?.all_day || false);
  const [category, setCategory] = useState(editingEvent?.category || "other");
  const [location, setLocation] = useState(editingEvent?.location || "");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !startDate) return;

    const tzOffset = new Date().getTimezoneOffset();
    const tzSign = tzOffset <= 0 ? "+" : "-";
    const tzHours = String(Math.floor(Math.abs(tzOffset) / 60)).padStart(2, "0");
    const tzMins = String(Math.abs(tzOffset) % 60).padStart(2, "0");
    const tz = `${tzSign}${tzHours}:${tzMins}`;

    const start_time = allDay
      ? `${startDate}T00:00:00${tz}`
      : `${startDate}T${startTime || "00:00"}${tz}`;

    const data: any = { title: title.trim(), start_time, category };
    if (description.trim()) data.description = description.trim();
    if (location.trim()) data.location = location.trim();
    if (allDay) {
      data.all_day = true;
    } else {
      if (endDate) {
        const end_time = `${endDate}T${endTime || "23:59"}${tz}`;
        data.end_time = end_time;
      }
    }

    onSave(data);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-end sm:items-center justify-center"
         onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-surface-1 border border-border rounded-t-xl sm:rounded-xl shadow-md
                      w-full sm:min-w-[400px] sm:max-w-[560px] max-h-[90dvh] sm:max-h-[85vh]
                      overflow-y-auto p-5 sm:p-6
                      animate-in slide-in-from-bottom-4 sm:zoom-in-95 duration-250">
        <div className="sm:hidden w-10 h-1 bg-surface-5 rounded-full mx-auto mb-4" />
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">
            {editingEvent ? "Edit Event" : "New Event"}
          </h2>
          <button onClick={onClose}
                  className="min-h-[44px] min-w-[44px] sm:size-8 rounded-sm
                             inline-flex items-center justify-center
                             text-text-secondary hover:bg-surface-2 transition-colors">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Title */}
          <div className="flex flex-col gap-1.5">
            <label className="block text-sm font-medium text-text-secondary">Title</label>
            <input type="text" required maxLength={200} value={title}
                   onChange={(e) => setTitle(e.target.value)}
                   className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                              border-border rounded-sm placeholder:text-text-disabled
                              focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                              transition-colors duration-150"
                   placeholder="Event title..." autoFocus />
          </div>

          {/* Description */}
          <div className="flex flex-col gap-1.5">
            <label className="block text-sm font-medium text-text-secondary">Description</label>
            <textarea rows={3} maxLength={5000} value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                                 border-border rounded-sm placeholder:text-text-disabled
                                 focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                                 transition-colors duration-150 resize-none"
                      placeholder="Event details..." />
          </div>

          {/* Date/Time — stacked on mobile, grid on desktop */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="block text-sm font-medium text-text-secondary">Start Date</label>
              <input type="date" required value={startDate}
                     onChange={(e) => setStartDate(e.target.value)}
                     className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                                border-border rounded-sm focus:border-brand focus:ring-2
                                focus:ring-brand-ring focus:outline-hidden transition-colors
                                text-[16px] sm:text-sm" />
            </div>
            {!allDay && (
              <div className="flex flex-col gap-1.5">
                <label className="block text-sm font-medium text-text-secondary">Start Time</label>
                <input type="time" value={startTime}
                       onChange={(e) => setStartTime(e.target.value)}
                       className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                                  border-border rounded-sm focus:border-brand focus:ring-2
                                  focus:ring-brand-ring focus:outline-hidden transition-colors
                                  text-[16px] sm:text-sm" />
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="block text-sm font-medium text-text-secondary">End Date</label>
              <input type="date" value={endDate}
                     onChange={(e) => setEndDate(e.target.value)}
                     className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                                border-border rounded-sm focus:border-brand focus:ring-2
                                focus:ring-brand-ring focus:outline-hidden transition-colors
                                text-[16px] sm:text-sm" />
            </div>
            {!allDay && (
              <div className="flex flex-col gap-1.5">
                <label className="block text-sm font-medium text-text-secondary">End Time</label>
                <input type="time" value={endTime}
                       onChange={(e) => setEndTime(e.target.value)}
                       className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                                  border-border rounded-sm focus:border-brand focus:ring-2
                                  focus:ring-brand-ring focus:outline-hidden transition-colors
                                  text-[16px] sm:text-sm" />
              </div>
            )}
          </div>

          {/* All day */}
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={allDay}
                   onChange={(e) => setAllDay(e.target.checked)}
                   className="size-4 rounded-sm border-border-strong bg-surface-2
                              text-brand focus:ring-brand-ring focus:ring-2 focus:outline-hidden" />
            <span className="text-sm text-text-primary">All day event</span>
          </label>

          {/* Category + Location */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="block text-sm font-medium text-text-secondary">Category</label>
              <select value={category} onChange={(e) => setCategory(e.target.value as typeof category)}
                      className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                                 border-border rounded-sm focus:border-brand focus:ring-2
                                 focus:ring-brand-ring focus:outline-hidden transition-colors">
                <option value="hearing">Hearing</option>
                <option value="deposition">Deposition</option>
                <option value="deadline">Deadline</option>
                <option value="meeting">Meeting</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="block text-sm font-medium text-text-secondary">Location</label>
              <input type="text" value={location}
                     onChange={(e) => setLocation(e.target.value)}
                     placeholder="Optional"
                     className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                                border-border rounded-sm placeholder:text-text-disabled
                                focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                                transition-colors duration-150 text-[16px] sm:text-sm" />
            </div>
          </div>

          {/* Footer */}
          <div className="flex flex-col sm:flex-row sm:justify-end gap-2 sm:gap-3 mt-2">
            <button type="button" onClick={onClose}
                    className="order-2 sm:order-1 text-sm px-4 py-2 rounded-lg
                               bg-surface-2 text-text-secondary border border-border
                               hover:bg-surface-3 transition-colors duration-150
                               min-h-[44px] sm:min-h-0">
              Cancel
            </button>
            <button type="submit" disabled={!title.trim() || !startDate || saving}
                    className="order-1 sm:order-2 text-sm px-4 py-2 rounded-lg
                               bg-brand text-white hover:bg-brand-hover
                               disabled:opacity-50 disabled:cursor-not-allowed
                               transition-colors duration-150 min-h-[44px] sm:min-h-0
                               inline-flex items-center justify-center gap-2">
              {saving && <Loader2 size={14} className="animate-spin" />}
              {saving ? "Saving..." : editingEvent ? "Save Changes" : "Create Event"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ==================================================================== */
/* ReminderFormModal                                                     */
/* ==================================================================== */

function ReminderFormModal({
  editingReminder,
  prefillEventId,
  events,
  onSave,
  onClose,
  saving,
}: {
  editingReminder: Reminder | null;
  prefillEventId: number | null;
  events: CalendarEvent[];
  onSave: (data: { title: string; remind_at: string; event_id?: number; category?: string; description?: string }) => void;
  onClose: () => void;
  saving: boolean;
}) {
  const [title, setTitle] = useState(editingReminder?.title || "");
  const [description, setDescription] = useState(editingReminder?.description || "");
  const [remindDate, setRemindDate] = useState(
    editingReminder ? format(new Date(editingReminder.remind_at), "yyyy-MM-dd") : ""
  );
  const [remindTime, setRemindTime] = useState(
    editingReminder ? format(new Date(editingReminder.remind_at), "HH:mm") : ""
  );
  const [category, setCategory] = useState(editingReminder?.category || "other");
  const [eventId, setEventId] = useState<number | null>(
    editingReminder?.event_id ?? prefillEventId ?? null
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !remindDate || !remindTime) return;

    const tzOffset = new Date().getTimezoneOffset();
    const tzSign = tzOffset <= 0 ? "+" : "-";
    const tzHours = String(Math.floor(Math.abs(tzOffset) / 60)).padStart(2, "0");
    const tzMins = String(Math.abs(tzOffset) % 60).padStart(2, "0");
    const tz = `${tzSign}${tzHours}:${tzMins}`;
    const remind_at = `${remindDate}T${remindTime}${tz}`;

    const data: any = { title: title.trim(), remind_at, category };
    if (description.trim()) data.description = description.trim();
    if (eventId) data.event_id = eventId;

    onSave(data);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-end sm:items-center justify-center"
         onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-surface-1 border border-border rounded-t-xl sm:rounded-xl shadow-md
                      w-full sm:min-w-[400px] sm:max-w-[480px] max-h-[90dvh] sm:max-h-[85vh]
                      overflow-y-auto p-5 sm:p-6
                      animate-in slide-in-from-bottom-4 sm:zoom-in-95 duration-250">
        <div className="sm:hidden w-10 h-1 bg-surface-5 rounded-full mx-auto mb-4" />
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">
            {editingReminder ? "Edit Reminder" : "New Reminder"}
          </h2>
          <button onClick={onClose}
                  className="min-h-[44px] min-w-[44px] sm:size-8 rounded-sm
                             inline-flex items-center justify-center
                             text-text-secondary hover:bg-surface-2 transition-colors">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Title */}
          <div className="flex flex-col gap-1.5">
            <label className="block text-sm font-medium text-text-secondary">Title</label>
            <input type="text" required maxLength={200} value={title}
                   onChange={(e) => setTitle(e.target.value)}
                   className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                              border-border rounded-sm placeholder:text-text-disabled
                              focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                              transition-colors duration-150"
                   placeholder="What to remember..." autoFocus />
          </div>

          {/* Description */}
          <div className="flex flex-col gap-1.5">
            <label className="block text-sm font-medium text-text-secondary">Description</label>
            <textarea rows={2} maxLength={2000} value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                                 border-border rounded-sm placeholder:text-text-disabled
                                 focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                                 transition-colors duration-150 resize-none"
                      placeholder="Additional context..." />
          </div>

          {/* Date + Time */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="block text-sm font-medium text-text-secondary">Date</label>
              <input type="date" required value={remindDate}
                     onChange={(e) => setRemindDate(e.target.value)}
                     className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                                border-border rounded-sm focus:border-brand focus:ring-2
                                focus:ring-brand-ring focus:outline-hidden transition-colors
                                text-[16px] sm:text-sm" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="block text-sm font-medium text-text-secondary">Time</label>
              <input type="time" required value={remindTime}
                     onChange={(e) => setRemindTime(e.target.value)}
                     className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                                border-border rounded-sm focus:border-brand focus:ring-2
                                focus:ring-brand-ring focus:outline-hidden transition-colors
                                text-[16px] sm:text-sm" />
            </div>
          </div>

          {/* Category */}
          <div className="flex flex-col gap-1.5">
            <label className="block text-sm font-medium text-text-secondary">Category</label>
            <select value={category} onChange={(e) => setCategory(e.target.value as typeof category)}
                    className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                               border-border rounded-sm focus:border-brand focus:ring-2
                               focus:ring-brand-ring focus:outline-hidden transition-colors">
              <option value="hearing">Hearing</option>
              <option value="deposition">Deposition</option>
              <option value="deadline">Deadline</option>
              <option value="meeting">Meeting</option>
              <option value="other">Other</option>
            </select>
          </div>

          {/* Event attachment */}
          <div className="flex flex-col gap-1.5">
            <label className="block text-sm font-medium text-text-secondary">
              Attach to Event (optional)
            </label>
            <select
              value={eventId ?? ""}
              onChange={(e) => setEventId(e.target.value ? Number(e.target.value) : null)}
              className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border
                         border-border rounded-sm focus:border-brand focus:ring-2
                         focus:ring-brand-ring focus:outline-hidden transition-colors"
            >
              <option value="">Standalone reminder</option>
              {events.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.title} — {format(new Date(ev.start_time), "MMM d, yyyy")}
                </option>
              ))}
            </select>
          </div>

          {/* Footer */}
          <div className="flex flex-col sm:flex-row sm:justify-end gap-2 sm:gap-3 mt-2">
            <button type="button" onClick={onClose}
                    className="order-2 sm:order-1 text-sm px-4 py-2 rounded-lg
                               bg-surface-2 text-text-secondary border border-border
                               hover:bg-surface-3 transition-colors duration-150
                               min-h-[44px] sm:min-h-0">
              Cancel
            </button>
            <button type="submit" disabled={!title.trim() || !remindDate || !remindTime || saving}
                    className="order-1 sm:order-2 text-sm px-4 py-2 rounded-lg
                               bg-brand text-white hover:bg-brand-hover
                               disabled:opacity-50 disabled:cursor-not-allowed
                               transition-colors duration-150 min-h-[44px] sm:min-h-0
                               inline-flex items-center justify-center gap-2">
              {saving && <Loader2 size={14} className="animate-spin" />}
              {saving ? "Saving..." : editingReminder ? "Save Changes" : "Create Reminder"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
