"""
Vision — Workspace API Routes.

CRUD for workspace items: list, get, create, update, delete, block-level update.
Workspace items are stored in the drafts table with file_type and folder columns.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
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
from schemas.view_envelope import validate_view_envelope

router = APIRouter(prefix="/api", tags=["workspace"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateWorkspaceItemRequest(BaseModel):
    case_id: int
    name: str
    file_type: str = "markdown"
    document_type: str = "other"
    folder: str = "freestyle"
    content: list | dict = []


class UpdateWorkspaceItemRequest(BaseModel):
    name: str | None = None
    document_type: str | None = None
    status: str | None = None
    content: list | dict | None = None
    file_type: str | None = None
    folder: str | None = None


class UpdateBlockRequest(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# List + Get
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}/workspace")
def list_workspace_items_endpoint(
    case_id: int,
    folder: str | None = Query(None),
    file_type: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    """List all workspace items for a case. Supports ?folder= and ?file_type= filters."""
    conn = connect()
    try:
        items = _list_drafts(conn, case_id, folder=folder)
    finally:
        conn.close()

    if file_type is not None:
        items = [i for i in items if i.get("file_type") == file_type]

    return {"items": items}


@router.get("/workspace/{item_id}")
def get_workspace_item_endpoint(
    item_id: int,
    user: dict = Depends(get_current_user),
):
    """Get a single workspace item with full content."""
    conn = connect()
    try:
        item = _get_draft(conn, item_id)
    finally:
        conn.close()
    if not item:
        raise HTTPException(status_code=404, detail="Workspace item not found")
    return {"item": item}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("/workspace")
def create_workspace_item_endpoint(
    body: CreateWorkspaceItemRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new workspace item (user-initiated)."""
    # Validate json_view content against the view envelope schema
    if body.file_type == "json_view":
        valid, error = validate_view_envelope(body.content)
        if not valid:
            raise HTTPException(status_code=422, detail=f"Invalid view envelope: {error}")

    with tx() as conn:
        item_id = insert_draft(
            conn,
            case_id=body.case_id,
            name=body.name,
            document_type=body.document_type,
            content=body.content,
            created_by="user",
            file_type=body.file_type,
            folder=body.folder,
        )
        item = _get_draft(conn, item_id)
    return {"item": item}


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.patch("/workspace/{item_id}")
def update_workspace_item_endpoint(
    item_id: int,
    body: UpdateWorkspaceItemRequest,
    user: dict = Depends(get_current_user),
):
    """Update workspace item metadata or full content."""
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Validate json_view content when updating a dict payload (non-list).
    # Must check file_type — dict content isn't exclusive to json_view
    # (markdown also accepts direct-object content like {markdown: "..."}).
    new_content = kwargs.get("content")
    if isinstance(new_content, dict):
        # Determine file_type: from the update body, or fall back to the stored item
        file_type = kwargs.get("file_type")
        if file_type is None:
            conn = connect()
            try:
                existing = _get_draft(conn, item_id)
            finally:
                conn.close()
            if existing:
                file_type = existing.get("file_type")
        if file_type == "json_view":
            valid, error = validate_view_envelope(new_content)
            if not valid:
                raise HTTPException(status_code=422, detail=f"Invalid view envelope: {error}")

    with tx() as conn:
        updated = _update_draft(conn, item_id, **kwargs)
    if not updated:
        raise HTTPException(status_code=404, detail="Workspace item not found")
    return {"item": updated}


@router.patch("/workspace/{item_id}/blocks/{block_id}")
def update_workspace_block_endpoint(
    item_id: int,
    block_id: str,
    body: UpdateBlockRequest,
    user: dict = Depends(get_current_user),
):
    """Update a single block within a workspace item (structured_draft)."""
    with tx() as conn:
        updated = _update_block(conn, item_id, block_id, body.content)
    if not updated:
        raise HTTPException(status_code=404, detail="Workspace item or block not found")
    return {"item": updated}


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/workspace/{item_id}")
def delete_workspace_item_endpoint(
    item_id: int,
    user: dict = Depends(get_current_user),
):
    """Delete a workspace item."""
    with tx() as conn:
        ok = _delete_draft(conn, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workspace item not found")
    return {"deleted": True}
