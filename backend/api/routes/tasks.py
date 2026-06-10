"""
Vision — Task API Routes.

CRUD for case tasks with document attachment support.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from core.db import (
    connect, tx,
    list_tasks as _list_tasks,
    get_task as _get_task,
    insert_task,
    update_task as _update_task,
    delete_task as _delete_task,
    attach_task_documents,
    detach_task_document,
)

router = APIRouter(prefix="/api", tags=["tasks"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateTaskRequest(BaseModel):
    title: str
    notes: str | None = None
    assignee_id: str | None = None
    deadline: str | None = None
    priority: str = "medium"
    document_ids: list[int] = []


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    notes: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee_id: str | None = None
    deadline: str | None = None


class AttachDocumentsRequest(BaseModel):
    document_ids: list[int]


# ---------------------------------------------------------------------------
# List + Get
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}/tasks")
def list_tasks_endpoint(
    case_id: int,
    status: str | None = None,
    assignee_id: str | None = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    conn = connect()
    try:
        return {"tasks": _list_tasks(conn, case_id, status, assignee_id, limit)}
    finally:
        conn.close()


@router.get("/tasks/{task_id}")
def get_task_endpoint(
    task_id: int,
    user: dict = Depends(get_current_user),
):
    conn = connect()
    try:
        task = _get_task(conn, task_id)
    finally:
        conn.close()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("/cases/{case_id}/tasks")
def create_task_endpoint(
    case_id: int,
    body: CreateTaskRequest,
    user: dict = Depends(get_current_user),
):
    user_id = user.get("id") if isinstance(user, dict) else None
    with tx() as conn:
        task_id = insert_task(
            conn,
            case_id=case_id,
            title=body.title,
            notes=body.notes,
            assignee_id=body.assignee_id or user_id,
            deadline=body.deadline,
            priority=body.priority,
            created_by=user_id,
        )
        if body.document_ids:
            attach_task_documents(conn, task_id, body.document_ids)
        task = _get_task(conn, task_id)
    return {"task": task}


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.patch("/tasks/{task_id}")
def update_task_endpoint(
    task_id: int,
    body: UpdateTaskRequest,
    user: dict = Depends(get_current_user),
):
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    with tx() as conn:
        updated = _update_task(conn, task_id, **kwargs)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": updated}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@router.post("/tasks/{task_id}/documents")
def attach_documents_endpoint(
    task_id: int,
    body: AttachDocumentsRequest,
    user: dict = Depends(get_current_user),
):
    if not body.document_ids:
        raise HTTPException(status_code=400, detail="No document_ids provided")
    with tx() as conn:
        count = attach_task_documents(conn, task_id, body.document_ids)
        task = _get_task(conn, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task, "attached": count}


@router.delete("/tasks/{task_id}/documents/{document_id}")
def detach_document_endpoint(
    task_id: int,
    document_id: int,
    user: dict = Depends(get_current_user),
):
    with tx() as conn:
        ok = detach_task_document(conn, task_id, document_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not attached")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/tasks/{task_id}")
def delete_task_endpoint(
    task_id: int,
    user: dict = Depends(get_current_user),
):
    with tx() as conn:
        ok = _delete_task(conn, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}
