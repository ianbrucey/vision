"""
Vision — Draft API Routes.

CRUD for drafts: list, get, create, update, delete, block-level update.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from core.db import (
    connect, tx, ensure_chat_schema,
    list_drafts as _list_drafts,
    get_draft as _get_draft,
    insert_draft,
    update_draft as _update_draft,
    delete_draft as _delete_draft,
    update_block as _update_block,
)

router = APIRouter(prefix="/api", tags=["drafts"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateDraftRequest(BaseModel):
    case_id: int
    name: str
    document_type: str = "letter"
    content: list = []


class UpdateDraftRequest(BaseModel):
    name: str | None = None
    document_type: str | None = None
    status: str | None = None
    content: list | None = None


class UpdateBlockRequest(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# List + Get
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}/drafts")
def list_drafts_endpoint(
    case_id: int,
    user: dict = Depends(get_current_user),
):
    """List all drafts for a case. Omits full content."""
    conn = connect()
    try:
        return {"drafts": _list_drafts(conn, case_id)}
    finally:
        conn.close()


@router.get("/drafts/{draft_id}")
def get_draft_endpoint(
    draft_id: int,
    user: dict = Depends(get_current_user),
):
    """Get a single draft with full block content."""
    conn = connect()
    try:
        draft = _get_draft(conn, draft_id)
    finally:
        conn.close()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"draft": draft}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("/drafts")
def create_draft_endpoint(
    body: CreateDraftRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new draft (user-initiated)."""
    with tx() as conn:
        draft_id = insert_draft(
            conn,
            case_id=body.case_id,
            name=body.name,
            document_type=body.document_type,
            content=body.content,
            created_by="user",
        )
        draft = _get_draft(conn, draft_id)
    return {"draft": draft}


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.patch("/drafts/{draft_id}")
def update_draft_endpoint(
    draft_id: int,
    body: UpdateDraftRequest,
    user: dict = Depends(get_current_user),
):
    """Update draft metadata or full content."""
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")

    with tx() as conn:
        updated = _update_draft(conn, draft_id, **kwargs)
    if not updated:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"draft": updated}


@router.patch("/drafts/{draft_id}/blocks/{block_id}")
def update_block_endpoint(
    draft_id: int,
    block_id: str,
    body: UpdateBlockRequest,
    user: dict = Depends(get_current_user),
):
    """Update a single block within a draft."""
    with tx() as conn:
        updated = _update_block(conn, draft_id, block_id, body.content)
    if not updated:
        raise HTTPException(status_code=404, detail="Draft or block not found")
    return {"draft": updated}


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/drafts/{draft_id}")
def delete_draft_endpoint(
    draft_id: int,
    user: dict = Depends(get_current_user),
):
    """Delete a draft."""
    with tx() as conn:
        ok = _delete_draft(conn, draft_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"deleted": True}
