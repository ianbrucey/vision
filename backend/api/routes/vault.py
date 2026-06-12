"""
Vision — Business Vault API Routes.

CRUD for vault items + document attachment/detachment.
Modeled after the task and correspondence attachment patterns.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_user
from core.db import (
    connect, tx, ensure_chat_schema,
    list_vault_items as _list_vault_items,
    get_vault_item as _get_vault_item,
    insert_vault_item,
    update_vault_item as _update_vault_item,
    delete_vault_item as _delete_vault_item,
    attach_vault_documents as _attach_vault_documents,
    detach_vault_document as _detach_vault_document,
)

router = APIRouter(prefix="/api", tags=["vault"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateVaultItemRequest(BaseModel):
    case_id: int | None = None
    kind: str
    name: str
    status: str = "active"
    notes: str | None = None
    data: dict | None = None
    created_by: str = "user"


class UpdateVaultItemRequest(BaseModel):
    kind: str | None = None
    name: str | None = None
    status: str | None = None
    notes: str | None = None
    data: dict | None = None
    case_id: int | None = None


class AttachDocumentsRequest(BaseModel):
    document_ids: list[int]


# ---------------------------------------------------------------------------
# List + Get
# ---------------------------------------------------------------------------

@router.get("/vault")
def list_vault_endpoint(
    case_id: int | None = Query(None),
    kind: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    """List vault items. Pass ?case_id=X for case-scoped, omit for business-level. Optionally filter by ?kind=."""
    conn = connect()
    try:
        items = _list_vault_items(conn, case_id=case_id, kind=kind)
    finally:
        conn.close()
    return {"items": items}


@router.get("/vault/{item_id}")
def get_vault_endpoint(
    item_id: int,
    user: dict = Depends(get_current_user),
):
    """Get a single vault item with attached documents."""
    conn = connect()
    try:
        item = _get_vault_item(conn, item_id)
    finally:
        conn.close()
    if not item:
        raise HTTPException(status_code=404, detail="Vault item not found")
    return {"item": item}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("/vault")
def create_vault_endpoint(
    body: CreateVaultItemRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new vault item."""
    with tx() as conn:
        item_id = insert_vault_item(
            conn,
            case_id=body.case_id,
            kind=body.kind,
            name=body.name,
            status=body.status,
            notes=body.notes,
            data=body.data,
            created_by=body.created_by,
        )
        item = _get_vault_item(conn, item_id)
    return {"item": item}


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.patch("/vault/{item_id}")
def update_vault_endpoint(
    item_id: int,
    body: UpdateVaultItemRequest,
    user: dict = Depends(get_current_user),
):
    """Update vault item fields."""
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")

    with tx() as conn:
        updated = _update_vault_item(conn, item_id, **kwargs)
    if not updated:
        raise HTTPException(status_code=404, detail="Vault item not found")
    # Re-fetch to include documents
    item = _get_vault_item(conn, item_id)
    return {"item": item}


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/vault/{item_id}")
def delete_vault_endpoint(
    item_id: int,
    user: dict = Depends(get_current_user),
):
    """Delete a vault item."""
    with tx() as conn:
        ok = _delete_vault_item(conn, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Vault item not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Document attachments
# ---------------------------------------------------------------------------

@router.post("/vault/{item_id}/documents")
def attach_vault_documents_endpoint(
    item_id: int,
    body: AttachDocumentsRequest,
    user: dict = Depends(get_current_user),
):
    """Attach documents to a vault item."""
    with tx() as conn:
        # Verify item exists
        if not _get_vault_item(conn, item_id):
            raise HTTPException(status_code=404, detail="Vault item not found")
        count = _attach_vault_documents(conn, item_id, body.document_ids)
    return {"attached": count}


@router.delete("/vault/{item_id}/documents/{document_id}")
def detach_vault_document_endpoint(
    item_id: int,
    document_id: int,
    user: dict = Depends(get_current_user),
):
    """Remove a document from a vault item."""
    with tx() as conn:
        ok = _detach_vault_document(conn, item_id, document_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {"detached": True}
