"""
Vision — Quotes API Routes.

CRUD for subcontractor quotes attached to solicitations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from core.quote import QuoteManager

router = APIRouter(prefix="/api", tags=["quotes"])
mgr = QuoteManager()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateQuoteRequest(BaseModel):
    notes: str | None = None
    amount: float | None = None
    poc_name: str | None = None
    poc_email: str | None = None
    poc_phone: str | None = None


class UpdateQuoteRequest(BaseModel):
    notes: str | None = None
    amount: float | None = None
    poc_name: str | None = None
    poc_email: str | None = None
    poc_phone: str | None = None
    status: str | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/solicitations/{solicitation_id}/quotes", status_code=201)
def create_quote(
    solicitation_id: int,
    body: CreateQuoteRequest,
    user: dict = Depends(get_current_user),
):
    """Create a quote for a solicitation."""
    kwargs = {}
    if body.notes is not None:
        kwargs["notes"] = body.notes
    if body.amount is not None:
        kwargs["amount"] = body.amount
    if body.poc_name is not None:
        kwargs["poc_name"] = body.poc_name
    if body.poc_email is not None:
        kwargs["poc_email"] = body.poc_email
    if body.poc_phone is not None:
        kwargs["poc_phone"] = body.poc_phone
    return mgr.create(solicitation_id, user["id"], **kwargs)


@router.get("/solicitations/{solicitation_id}/quotes")
def list_quotes(
    solicitation_id: int,
    user: dict = Depends(get_current_user),
):
    """List all quotes for a solicitation."""
    return {"quotes": mgr.list_for_solicitation(solicitation_id)}


@router.patch("/solicitations/{solicitation_id}/quotes/{quote_id}")
def update_quote(
    solicitation_id: int,
    quote_id: int,
    body: UpdateQuoteRequest,
    user: dict = Depends(get_current_user),
):
    """Update a quote. Owner or admin only."""
    quote = mgr.get(quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote["solicitation_id"] != solicitation_id:
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote["created_by"] != user["id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only the quote owner or admin can edit")

    kwargs = {}
    for field in ("notes", "amount", "poc_name", "poc_email", "poc_phone", "status"):
        val = getattr(body, field, None)
        if val is not None:
            kwargs[field] = val

    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        updated = mgr.update(quote_id, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if updated is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return updated


@router.delete("/solicitations/{solicitation_id}/quotes/{quote_id}")
def delete_quote(
    solicitation_id: int,
    quote_id: int,
    user: dict = Depends(get_current_user),
):
    """Delete a quote. Owner or admin only. Only draft quotes can be deleted."""
    quote = mgr.get(quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote["solicitation_id"] != solicitation_id:
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote["created_by"] != user["id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only the quote owner or admin can delete")

    try:
        deleted = mgr.delete(quote_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"deleted": quote_id}
