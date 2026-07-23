"""
Vision — Solicitation API Routes.

CRUD for solicitations (Option A architecture — domain table backed by a
generic `cases` row). Federal (SAM.gov) intake is async via the jobs queue;
state/local intake is fully synchronous. Per 02-api-contract.json.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import get_current_user
from core.db import connect
from core.solicitation import SolicitationManager, DuplicateNoticeError
from core.vendor import VendorManager
from core.vendor_match import VendorMatchManager
from core.email_mailgun import MailgunSendError
from ingestion.jobs import enqueue as _enqueue_job
from ingestion.sam_client import extract_notice_id

router = APIRouter(prefix="/api", tags=["solicitations"])

mgr = SolicitationManager()
vendor_match_mgr = VendorMatchManager()
vendor_mgr = VendorManager()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateSolicitationRequest(BaseModel):
    source_type: str
    url: str = ""
    title: str | None = None
    description: str | None = None


class AttachVendorMatchRequest(BaseModel):
    vendor_id: int


class UpdateOutreachRequest(BaseModel):
    outreach_status: str | None = None
    outreach_doc_id: int | None = None
    clear_outreach_doc: bool = False


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("/solicitations", status_code=201)
def create_solicitation_endpoint(
    body: CreateSolicitationRequest,
    user: dict = Depends(get_current_user),
):
    notice_id = None
    if body.source_type == "federal" and body.url:
        notice_id = extract_notice_id(body.url)

    try:
        sol = mgr.create(
            source_type=body.source_type,
            url=body.url,
            title=body.title,
            notice_id=notice_id,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateNoticeError as e:
        # Flat body per 02-api-contract.json: {"detail": "...", "existing_external_id": "..."}.
        # HTTPException always nests `detail` under a "detail" key, so a plain
        # JSONResponse is used here instead to keep the body flat.
        return JSONResponse(
            status_code=409,
            content={
                "detail": str(e),
                "existing_external_id": e.existing_external_id,
            },
        )

    job_id = None
    if body.source_type == "federal" and body.url:
        job = _enqueue_job(
            case_id=sol["case_id"],
            job_type="sam_fetch",
            metadata={"solicitation_id": sol["id"], "notice_id": notice_id},
        )
        job_id = job["id"]

    return {"solicitation": sol, "job_id": job_id}


# ---------------------------------------------------------------------------
# List + Get
# ---------------------------------------------------------------------------

@router.get("/solicitations")
def list_solicitations_endpoint(
    source_type: str | None = None,
    ingestion_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(get_current_user),
):
    sols = mgr.list(
        source_type=source_type,
        ingestion_status=ingestion_status,
        limit=limit,
        offset=offset,
    )

    # Attach unread reply counts for notification badges.
    if sols:
        case_ids = [s["case_id"] for s in sols if s.get("case_id")]
        if case_ids:
            conn = connect()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT vm.solicitation_id, COUNT(*) AS unread
                           FROM vendor_outreach_messages vom
                           JOIN vendor_matches vm ON vm.id = vom.vendor_match_id
                           WHERE vom.direction = 'inbound'
                             AND vom.read_at IS NULL
                             AND vm.solicitation_id = ANY(%s)
                           GROUP BY vm.solicitation_id""",
                        (case_ids,),
                    )
                    unread_map = {row[0]: row[1] for row in cur.fetchall()}
            finally:
                conn.close()
            for sol in sols:
                sol["unread_replies"] = unread_map.get(sol["id"], 0)

    return {"count": len(sols), "solicitations": sols}


@router.get("/solicitations/{solicitation_id}")
def get_solicitation_endpoint(
    solicitation_id: int,
    user: dict = Depends(get_current_user),
):
    sol = mgr.get(solicitation_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    return sol


@router.get("/cases/{case_id}/solicitation")
def get_solicitation_by_case_endpoint(
    case_id: int,
    user: dict = Depends(get_current_user),
):
    """Look up the solicitation backed by a case — used by the case detail
    page's Triage tab, which only knows case_id from the URL."""
    sol = mgr.get_by_case_id(case_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="No solicitation for this case")
    return sol


# ---------------------------------------------------------------------------
# Triage — manual trigger
# ---------------------------------------------------------------------------

@router.post("/solicitations/{solicitation_id}/triage")
def trigger_triage_endpoint(
    solicitation_id: int,
    user: dict = Depends(get_current_user),
):
    """Manually (re)run the unattended triage pipeline for a solicitation.

    Used for state/local (no auto-trigger — there's no sam_fetch job) and
    for federal solicitations where document retrieval had issues
    (has_missing_docs=True skips the auto-trigger). Requires at least one
    document already attached.
    """
    sol = mgr.get(solicitation_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitation not found")

    if not sol.get("documents"):
        raise HTTPException(
            status_code=400,
            detail="Cannot run triage — no documents attached to this solicitation",
        )

    if sol.get("triage_status") == "running":
        raise HTTPException(status_code=409, detail="Triage is already running")

    mgr.update(solicitation_id, triage_status="pending", triage_error=None)
    job = _enqueue_job(
        case_id=sol["case_id"],
        job_type="solicitation_triage",
        metadata={"solicitation_id": solicitation_id},
    )
    return {"job_id": job["id"], "triage_status": "pending"}


# ---------------------------------------------------------------------------
# Vendor Matching
# ---------------------------------------------------------------------------

@router.post("/solicitations/{solicitation_id}/vendor-matching")
def trigger_vendor_matching_endpoint(
    solicitation_id: int,
    user: dict = Depends(get_current_user),
):
    """Manually (re)trigger vendor matching for a solicitation.

    Requires triage_status='complete' and a NAICS code present (matching
    cannot function without a NAICS to query the vendor pool). quick_kill
    is informational only and does NOT block matching.
    """
    sol = mgr.get(solicitation_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitation not found")

    if sol.get("triage_status") != "complete":
        raise HTTPException(
            status_code=400,
            detail="Cannot run vendor matching — triage has not completed",
        )

    if not sol.get("naics_code"):
        raise HTTPException(
            status_code=400,
            detail="Cannot run vendor matching — solicitation has no NAICS code",
        )

    if sol.get("matching_status") == "running":
        raise HTTPException(status_code=400, detail="Vendor matching is already running")

    mgr.update(solicitation_id, matching_status="pending", matching_error=None)
    job = _enqueue_job(
        case_id=sol["case_id"],
        job_type="vendor_matching",
        metadata={"solicitation_id": solicitation_id},
    )
    return {"job_id": job["id"], "matching_status": "pending"}


@router.get("/solicitations/{solicitation_id}/vendor-matches")
def list_vendor_matches_endpoint(
    solicitation_id: int,
    user: dict = Depends(get_current_user),
):
    """Get ranked vendor matches for a solicitation, plus matching status
    and outreach email template, in one call.

    Returns 200 with matching_status='pending' and matches=[] before the
    first run — not a 404. matches=[] with matching_status='complete' is a
    legitimate zero-candidate outcome, distinct from 'not started yet'.
    """
    sol = mgr.get(solicitation_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitation not found")

    matches = vendor_match_mgr.list_for_solicitation(solicitation_id)
    return {
        "matching_status": sol.get("matching_status"),
        "matching_error": sol.get("matching_error"),
        "outreach_email_subject": sol.get("outreach_email_subject"),
        "outreach_email_body": sol.get("outreach_email_body"),
        "matches": matches,
    }


@router.post("/solicitations/{solicitation_id}/vendor-matches", status_code=201)
def attach_vendor_match_endpoint(
    solicitation_id: int,
    body: AttachVendorMatchRequest,
    user: dict = Depends(get_current_user),
):
    """Attach an existing vendor to a solicitation's match list manually
    (T7 — inline vendor creation). To attach a brand-new vendor, first
    POST /api/vendors, then call this with the returned vendor id.
    """
    sol = mgr.get(solicitation_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitation not found")

    try:
        return vendor_match_mgr.attach_manual_vendor(solicitation_id, body.vendor_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/vendor-matches/{match_id}/outreach")
def update_vendor_match_outreach_endpoint(
    match_id: int,
    body: UpdateOutreachRequest,
    user: dict = Depends(get_current_user),
):
    """Update outreach tracking (T8) on a single vendor match.

    `outreach_status` one of: not_contacted, requested, received, declined.
    `outreach_doc_id` links a received document (e.g. a quote) to this
    match; pass `clear_outreach_doc: true` to detach it.
    """
    try:
        return vendor_match_mgr.update_outreach(
            match_id,
            outreach_status=body.outreach_status,
            outreach_doc_id=body.outreach_doc_id,
            clear_outreach_doc=body.clear_outreach_doc,
        )
    except ValueError as e:
        detail = str(e)
        status_code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/solicitations/{solicitation_id}")
def delete_solicitation_endpoint(
    solicitation_id: int,
    user: dict = Depends(get_current_user),
):
    """Delete a solicitation, its backing case, and all attached documents.

    Removes documents from MinIO (best-effort), then deletes the `cases` row —
    the FK cascade removes the solicitation, documents, sections/blocks, jobs
    reference, and every other case-scoped entity.
    """
    if not mgr.delete(solicitation_id):
        raise HTTPException(status_code=404, detail="Solicitation not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Outreach: Message thread (T10c)
# ---------------------------------------------------------------------------

@router.get("/vendor-matches/{match_id}/messages")
def list_vendor_match_messages_endpoint(match_id: int, user: dict = Depends(get_current_user)):
    """All outreach messages (outbound + inbound) for a vendor match, plus
    the match itself, for the thread page (T10c)."""
    match = vendor_match_mgr.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Vendor match not found")
    return {"match": match, "messages": vendor_match_mgr.list_messages(match_id)}


@router.post("/vendor-matches/{match_id}/messages/draft", status_code=201)
def create_draft_message_endpoint(match_id: int, user: dict = Depends(get_current_user)):
    """Create (or return existing) draft outbound message for a match."""
    try:
        return vendor_match_mgr.create_draft_message(match_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class UpdateDraftMessageRequest(BaseModel):
    subject: str | None = None
    body: str | None = None


@router.patch("/vendor-match-messages/{message_id}")
def update_draft_message_endpoint(message_id: int, body: UpdateDraftMessageRequest, user: dict = Depends(get_current_user)):
    """Edit a draft message's subject or body (T10c). Immutable once sent."""
    try:
        return vendor_match_mgr.update_draft_message(message_id, subject=body.subject, body=body.body)
    except ValueError as e:
        detail = str(e)
        status_code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail)


@router.post("/vendor-match-messages/{message_id}/send")
def send_message_endpoint(message_id: int, user: dict = Depends(get_current_user)):
    """Send a draft message via Mailgun (T10c). Immutable once sent."""
    try:
        return vendor_match_mgr.send_message(message_id)
    except MailgunSendError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        detail = str(e)
        status_code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail)


@router.post("/vendor-matches/{match_id}/messages/read")
def mark_messages_read_endpoint(match_id: int, user: dict = Depends(get_current_user)):
    """Mark all inbound messages in a thread as read."""
    vendor_match_mgr.mark_messages_read(match_id)
    return {"read": True}
