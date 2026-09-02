"""
Vision — Vendor Teaming Agreement API Routes (MTA e-signature).

GET  /api/vendors/mta            — vendor's MTA status (+ unsigned preview PDF)
POST /api/vendors/mta/sign       — execute the MTA (typed name + consent)
GET  /api/vendors/mta-agreements — admin listing

Audit trail per E-SIGN Act (15 U.S.C. §7001) / GA UETA (O.C.G.A. §10-12):
intent (consent must be exactly true), attribution (JWT user + typed
name/title), and the exact signed document (content_hash).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from auth import get_current_user, require_admin
from core.vendor_agreements import VendorAgreementManager

router = APIRouter(prefix="/api/vendors", tags=["vendors"])
mgr = VendorAgreementManager()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MtaSignRequest(BaseModel):
    signed_name: str = Field(min_length=2, max_length=200)
    signed_title: str = Field(min_length=2, max_length=200)
    consent: bool = False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/mta")
def get_my_mta(
    user: dict = Depends(get_current_user),
):
    """Get the current vendor's MTA status; unsigned → presigned preview URL."""
    if user["role"] != "vendor":
        raise HTTPException(status_code=403, detail="Access denied")
    status = mgr.get_status(user["id"])
    if status is None:
        raise HTTPException(status_code=404, detail="No vendor profile found")
    return status


@router.post("/mta/sign")
def sign_my_mta(
    body: MtaSignRequest,
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user),
):
    """Execute the MTA. Idempotent — repeat returns the existing agreement."""
    if user["role"] != "vendor":
        raise HTTPException(status_code=403, detail="Access denied")
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent") or ""

    try:
        result = mgr.sign(
            user["id"], body.signed_name, body.signed_title,
            body.consent, ip, user_agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if result is None:
        raise HTTPException(status_code=404, detail="No vendor profile found")

    agreement, created = result
    response.status_code = 201 if created else 200
    return {"agreement": agreement, "already_signed": not created}


@router.get("/mta-agreements")
def list_mta_agreements(
    agreement_type: str | None = None,
    user: dict = Depends(require_admin),
):
    """Admin listing of teaming agreements (mta/bsta/subcontract)."""
    return {"agreements": mgr.list(agreement_type=agreement_type)}
