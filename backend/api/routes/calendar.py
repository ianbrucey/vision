"""
Vision — Calendar API Routes.

CRUD for per-case calendar events and reminders.
Follows the same patterns as tasks.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from core.db import (
    connect, tx,
    insert_calendar_event,
    update_calendar_event,
    get_calendar_event,
    list_calendar_events,
    delete_calendar_event,
    insert_reminder,
    update_reminder,
    get_reminder,
    list_reminders,
    delete_reminder,
)

router = APIRouter(prefix="/api", tags=["calendar"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateCalendarEventRequest(BaseModel):
    title: str
    start_time: str
    end_time: str | None = None
    all_day: bool = False
    category: str = "other"
    description: str | None = None
    location: str | None = None


class UpdateCalendarEventRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    all_day: bool | None = None
    category: str | None = None
    location: str | None = None


class CreateReminderRequest(BaseModel):
    title: str
    remind_at: str
    event_id: int | None = None
    category: str = "other"
    description: str | None = None


class UpdateReminderRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    remind_at: str | None = None
    category: str | None = None
    status: str | None = None


# ---------------------------------------------------------------------------
# Calendar Events — List + Get
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}/calendar/events")
def list_events_endpoint(
    case_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
    category: str | None = None,
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    conn = connect()
    try:
        events = list_calendar_events(
            conn, case_id,
            start_date=start_date,
            end_date=end_date,
            category=category,
            limit=limit,
        )
        return {"count": len(events), "events": events}
    finally:
        conn.close()


@router.get("/calendar/events/{event_id}")
def get_event_endpoint(
    event_id: int,
    user: dict = Depends(get_current_user),
):
    conn = connect()
    try:
        event = get_calendar_event(conn, event_id)
    finally:
        conn.close()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"event": event}


# ---------------------------------------------------------------------------
# Calendar Events — Create
# ---------------------------------------------------------------------------

@router.post("/cases/{case_id}/calendar/events")
def create_event_endpoint(
    case_id: int,
    body: CreateCalendarEventRequest,
    user: dict = Depends(get_current_user),
):
    with tx() as conn:
        event_id = insert_calendar_event(
            conn,
            case_id=case_id,
            title=body.title,
            start_time=body.start_time,
            end_time=body.end_time,
            all_day=body.all_day,
            category=body.category,
            description=body.description,
            location=body.location,
            created_by="user",
        )
        event = get_calendar_event(conn, event_id)
    return {"event": event}


# ---------------------------------------------------------------------------
# Calendar Events — Update
# ---------------------------------------------------------------------------

@router.patch("/calendar/events/{event_id}")
def update_event_endpoint(
    event_id: int,
    body: UpdateCalendarEventRequest,
    user: dict = Depends(get_current_user),
):
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    with tx() as conn:
        updated = update_calendar_event(conn, event_id, **kwargs)
    if not updated:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"event": updated}


# ---------------------------------------------------------------------------
# Calendar Events — Delete
# ---------------------------------------------------------------------------

@router.delete("/calendar/events/{event_id}")
def delete_event_endpoint(
    event_id: int,
    user: dict = Depends(get_current_user),
):
    with tx() as conn:
        ok = delete_calendar_event(conn, event_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Reminders — List + Get
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}/calendar/reminders")
def list_reminders_endpoint(
    case_id: int,
    status: str | None = None,
    category: str | None = None,
    event_id: int | None = None,
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    conn = connect()
    try:
        reminders = list_reminders(
            conn, case_id,
            status=status,
            category=category,
            event_id=event_id,
            limit=limit,
        )
        return {"count": len(reminders), "reminders": reminders}
    finally:
        conn.close()


@router.get("/calendar/reminders/{reminder_id}")
def get_reminder_endpoint(
    reminder_id: int,
    user: dict = Depends(get_current_user),
):
    conn = connect()
    try:
        reminder = get_reminder(conn, reminder_id)
    finally:
        conn.close()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"reminder": reminder}


# ---------------------------------------------------------------------------
# Reminders — Create
# ---------------------------------------------------------------------------

@router.post("/cases/{case_id}/calendar/reminders")
def create_reminder_endpoint(
    case_id: int,
    body: CreateReminderRequest,
    user: dict = Depends(get_current_user),
):
    with tx() as conn:
        reminder_id = insert_reminder(
            conn,
            case_id=case_id,
            title=body.title,
            remind_at=body.remind_at,
            event_id=body.event_id,
            category=body.category,
            description=body.description,
            created_by="user",
        )
        reminder = get_reminder(conn, reminder_id)
    return {"reminder": reminder}


# ---------------------------------------------------------------------------
# Reminders — Update
# ---------------------------------------------------------------------------

@router.patch("/calendar/reminders/{reminder_id}")
def update_reminder_endpoint(
    reminder_id: int,
    body: UpdateReminderRequest,
    user: dict = Depends(get_current_user),
):
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    with tx() as conn:
        updated = update_reminder(conn, reminder_id, **kwargs)
    if not updated:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"reminder": updated}


# ---------------------------------------------------------------------------
# Reminders — Delete
# ---------------------------------------------------------------------------

@router.delete("/calendar/reminders/{reminder_id}")
def delete_reminder_endpoint(
    reminder_id: int,
    user: dict = Depends(get_current_user),
):
    with tx() as conn:
        ok = delete_reminder(conn, reminder_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"deleted": True}
