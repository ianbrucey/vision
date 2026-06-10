"""
Vision — Correspondence API Routes.

CRUD for correspondence threads, items, and document attachments.
"""

from __future__ import annotations

import psycopg2.extras

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from core.db import connect, tx

router = APIRouter(prefix="/api", tags=["correspondence"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateThreadRequest(BaseModel):
    title: str


class UpdateThreadRequest(BaseModel):
    title: str | None = None
    status: str | None = None


class CreateItemRequest(BaseModel):
    sender_party_id: int | None = None
    receiver_party_id: int | None = None
    direction: str  # "sent" or "received"
    notes: str | None = None
    date_sent: str | None = None   # ISO date
    date_received: str | None = None
    document_ids: list[int] = []


class UpdateItemRequest(BaseModel):
    sender_party_id: int | None = None
    receiver_party_id: int | None = None
    direction: str | None = None
    notes: str | None = None
    date_sent: str | None = None
    date_received: str | None = None


class AttachDocumentRequest(BaseModel):
    document_id: int


# ---------------------------------------------------------------------------
# Threads
# ---------------------------------------------------------------------------


def _thread_row(row: dict) -> dict:
    """Convert a thread row to the API response shape."""
    return {
        "id": row["id"],
        "case_id": row["case_id"],
        "title": row["title"],
        "status": row["status"],
        "item_count": row.get("item_count", 0),
        "last_activity": row.get("last_activity"),
        "created_at": str(row["created_at"]) if row.get("created_at") else None,
        "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
    }


@router.get("/cases/{case_id}/correspondence/threads")
def list_threads(
    case_id: int,
    status: str | None = None,
    user: dict = Depends(get_current_user),
):
    """List correspondence threads for a case, with item counts and last activity."""
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            where = "t.case_id = %s"
            params: list = [case_id]
            if status:
                where += " AND t.status = %s"
                params.append(status)
            else:
                where += " AND t.status = 'active'"

            cur.execute(
                f"""SELECT t.*,
                           COALESCE(i.item_count, 0) AS item_count,
                           i.last_activity
                    FROM correspondence_threads t
                    LEFT JOIN (
                        SELECT thread_id,
                               COUNT(*) AS item_count,
                               MAX(created_at) AS last_activity
                        FROM correspondence_items
                        GROUP BY thread_id
                    ) i ON i.thread_id = t.id
                    WHERE {where}
                    ORDER BY COALESCE(i.last_activity, t.updated_at) DESC""",
                params,
            )
            return {"threads": [_thread_row(r) for r in cur.fetchall()]}
    finally:
        conn.close()


@router.post("/cases/{case_id}/correspondence/threads")
def create_thread(
    case_id: int,
    body: CreateThreadRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new correspondence thread."""
    with tx() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO correspondence_threads (case_id, title)
                   VALUES (%s, %s)
                   RETURNING *""",
                (case_id, body.title),
            )
            row = cur.fetchone()
    return {"thread": _thread_row(row)}


@router.patch("/correspondence/threads/{thread_id}")
def update_thread(
    thread_id: int,
    body: UpdateThreadRequest,
    user: dict = Depends(get_current_user),
):
    """Update thread title or status."""
    updates = {}
    if body.title is not None:
        updates["title"] = body.title
    if body.status is not None:
        updates["status"] = body.status

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    params = list(updates.values()) + [thread_id]

    with tx() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""UPDATE correspondence_threads
                    SET {set_clause}, updated_at = now()
                    WHERE id = %s
                    RETURNING *""",
                params,
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"thread": _thread_row(row)}


@router.delete("/correspondence/threads/{thread_id}")
def delete_thread(
    thread_id: int,
    user: dict = Depends(get_current_user),
):
    """Delete a thread and all its items (cascade)."""
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM correspondence_threads WHERE id = %s",
                (thread_id,),
            )
            ok = cur.rowcount > 0
    if not ok:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


def _item_row(row: dict) -> dict:
    """Convert an item row to the API response shape."""
    return {
        "id": row["id"],
        "thread_id": row["thread_id"],
        "sender_party_id": row.get("sender_party_id"),
        "sender_name": row.get("sender_name"),
        "receiver_party_id": row.get("receiver_party_id"),
        "receiver_name": row.get("receiver_name"),
        "direction": row["direction"],
        "notes": row.get("notes"),
        "date_sent": str(row["date_sent"]) if row.get("date_sent") else None,
        "date_received": str(row["date_received"]) if row.get("date_received") else None,
        "attachments": row.get("attachments", []),
        "created_at": str(row["created_at"]) if row.get("created_at") else None,
        "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
    }


@router.get("/correspondence/threads/{thread_id}/items")
def list_items(
    thread_id: int,
    user: dict = Depends(get_current_user),
):
    """List items in a thread, with party names and attachment doc IDs."""
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Fetch items with party names
            cur.execute(
                """SELECT ci.*,
                          sp.name AS sender_name,
                          rp.name AS receiver_name
                   FROM correspondence_items ci
                   LEFT JOIN parties sp ON sp.id = ci.sender_party_id
                   LEFT JOIN parties rp ON rp.id = ci.receiver_party_id
                   WHERE ci.thread_id = %s
                   ORDER BY ci.created_at DESC""",
                (thread_id,),
            )
            items = [dict(r) for r in cur.fetchall()]

            # Batch-fetch attachments for all items
            item_ids = [it["id"] for it in items]
            attachments_by_item: dict[int, list] = {iid: [] for iid in item_ids}
            if item_ids:
                cur.execute(
                    """SELECT ca.item_id, ca.id AS att_id, ca.document_id, d.name AS document_name
                       FROM correspondence_attachments ca
                       JOIN documents d ON d.id = ca.document_id
                       WHERE ca.item_id = ANY(%s)
                       ORDER BY ca.id""",
                    (item_ids,),
                )
                for arow in cur.fetchall():
                    attachments_by_item[arow["item_id"]].append({
                        "id": arow["att_id"],
                        "document_id": arow["document_id"],
                        "document_name": arow["document_name"],
                    })

            for it in items:
                it["attachments"] = attachments_by_item.get(it["id"], [])

        return {"items": [_item_row(it) for it in items]}
    finally:
        conn.close()


@router.post("/correspondence/threads/{thread_id}/items")
def create_item(
    thread_id: int,
    body: CreateItemRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new correspondence item, optionally with document attachments."""
    if body.direction not in ("sent", "received"):
        raise HTTPException(status_code=422, detail="direction must be 'sent' or 'received'")

    with tx() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO correspondence_items
                   (thread_id, sender_party_id, receiver_party_id, direction,
                    notes, date_sent, date_received)
                   VALUES (%s, %s, %s, %s, %s,
                           %s::date, %s::date)
                   RETURNING *""",
                (
                    thread_id,
                    body.sender_party_id,
                    body.receiver_party_id,
                    body.direction,
                    body.notes,
                    body.date_sent,
                    body.date_received,
                ),
            )
            item = dict(cur.fetchone())

            # Attach documents if provided
            if body.document_ids:
                for doc_id in body.document_ids:
                    cur.execute(
                        """INSERT INTO correspondence_attachments (item_id, document_id)
                           VALUES (%s, %s)
                           ON CONFLICT (item_id, document_id) DO NOTHING""",
                        (item["id"], doc_id),
                    )

            # Touch thread updated_at
            cur.execute(
                "UPDATE correspondence_threads SET updated_at = now() WHERE id = %s",
                (thread_id,),
            )

            # Fetch party names
            if item.get("sender_party_id"):
                cur.execute("SELECT name FROM parties WHERE id = %s", (item["sender_party_id"],))
                sp = cur.fetchone()
                item["sender_name"] = sp["name"] if sp else None
            if item.get("receiver_party_id"):
                cur.execute("SELECT name FROM parties WHERE id = %s", (item["receiver_party_id"],))
                rp = cur.fetchone()
                item["receiver_name"] = rp["name"] if rp else None

            item["attachments"] = []

    return {"item": _item_row(item)}


@router.patch("/correspondence/items/{item_id}")
def update_item(
    item_id: int,
    body: UpdateItemRequest,
    user: dict = Depends(get_current_user),
):
    """Update an item's fields."""
    updates = {}
    for field in ("sender_party_id", "receiver_party_id", "direction", "notes",
                  "date_sent", "date_received"):
        val = getattr(body, field, None)
        if val is not None:
            if field in ("date_sent", "date_received"):
                updates[field] = val + "::date"
            else:
                updates[field] = val

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Build SET clause carefully for date casting
    set_parts = []
    params: list = []
    for k, v in updates.items():
        if k in ("date_sent", "date_received"):
            set_parts.append(f"{k} = %s::date")
        else:
            set_parts.append(f"{k} = %s")
        # The value may be '2024-01-01::date' for dates — extract base
        if isinstance(v, str) and "::date" in v:
            params.append(v.replace("::date", ""))
        else:
            params.append(v)
    params.append(item_id)

    with tx() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""UPDATE correspondence_items
                    SET {', '.join(set_parts)}, updated_at = now()
                    WHERE id = %s
                    RETURNING *""",
                params,
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": _item_row(row)}


@router.delete("/correspondence/items/{item_id}")
def delete_item(
    item_id: int,
    user: dict = Depends(get_current_user),
):
    """Delete a correspondence item (attachments cascade)."""
    with tx() as conn:
        with conn.cursor() as cur:
            # Get thread_id to touch it
            cur.execute("SELECT thread_id FROM correspondence_items WHERE id = %s", (item_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Item not found")
            thread_id = row[0]

            cur.execute("DELETE FROM correspondence_items WHERE id = %s", (item_id,))
            # Touch thread
            cur.execute(
                "UPDATE correspondence_threads SET updated_at = now() WHERE id = %s",
                (thread_id,),
            )
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


@router.post("/correspondence/items/{item_id}/attachments")
def attach_document(
    item_id: int,
    body: AttachDocumentRequest,
    user: dict = Depends(get_current_user),
):
    """Link a document to a correspondence item."""
    with tx() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Verify item exists
            cur.execute("SELECT id, thread_id FROM correspondence_items WHERE id = %s", (item_id,))
            item = cur.fetchone()
            if not item:
                raise HTTPException(status_code=404, detail="Item not found")

            # Verify document exists
            cur.execute("SELECT id, name FROM documents WHERE id = %s", (body.document_id,))
            doc = cur.fetchone()
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")

            cur.execute(
                """INSERT INTO correspondence_attachments (item_id, document_id)
                   VALUES (%s, %s)
                   ON CONFLICT (item_id, document_id) DO NOTHING
                   RETURNING id""",
                (item_id, body.document_id),
            )
            att = cur.fetchone()

            # Touch thread
            cur.execute(
                "UPDATE correspondence_threads SET updated_at = now() WHERE id = %s",
                (item["thread_id"],),
            )

    return {
        "attachment": {
            "id": att["id"] if att else None,
            "item_id": item_id,
            "document_id": body.document_id,
            "document_name": doc["name"],
        }
    }


@router.delete("/correspondence/items/{item_id}/attachments/{document_id}")
def detach_document(
    item_id: int,
    document_id: int,
    user: dict = Depends(get_current_user),
):
    """Remove a document attachment link."""
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """DELETE FROM correspondence_attachments
                   WHERE item_id = %s AND document_id = %s""",
                (item_id, document_id),
            )
            ok = cur.rowcount > 0
    if not ok:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {"deleted": True}
