"""
Vision — Solicitation API Routes.

CRUD for solicitations (Option A architecture — domain table backed by a
generic `cases` row). Federal (SAM.gov) intake is async via the jobs queue;
state/local intake is fully synchronous. Per 02-api-contract.json.
"""

from __future__ import annotations

import io
import os
import shutil
import tempfile
import zipfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import get_current_user
from core.db import connect, tx
from core.solicitation import SolicitationManager, DuplicateNoticeError
from core.vendor import VendorManager
from core.vendor_match import VendorMatchManager
from core.email_mailgun import MailgunSendError
from ingestion.dispatcher import ingest_file
from ingestion.jobs import enqueue as _enqueue_job
from ingestion.sam_client import extract_notice_id, fetch_notice, fetch_description
from ingestion.storage import upload_file as _upload_to_minio, upload_attachment

import psycopg2.extras

router = APIRouter(prefix="/api", tags=["solicitations"])

mgr = SolicitationManager()
vendor_match_mgr = VendorMatchManager()
vendor_mgr = VendorManager()


def _safe_extract_zip(zip_path: Path, target_dir: Path) -> list[Path]:
    """Safely extract all valid files from a zip archive, ignoring macOS junk."""
    extracted = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                filename = member.filename
                parts = Path(filename).parts
                if any(p.startswith(".") or p.startswith("__MACOSX") or p == ".DS_Store" for p in parts):
                    continue
                clean_name = Path(filename).name
                if not clean_name or clean_name.startswith("."):
                    continue
                dest_path = target_dir / clean_name
                counter = 1
                while dest_path.exists():
                    dest_path = target_dir / f"{dest_path.stem}_{counter}{dest_path.suffix}"
                    counter += 1

                with zf.open(member) as src, open(dest_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted.append(dest_path)
    except Exception as e:
        print(f"[_safe_extract_zip] Error unzipping {zip_path}: {e}")
    return extracted


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


@router.get("/solicitations/preview-sam")
def preview_sam_metadata(
    url: str | None = Query(None),
    notice_id: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    """Pre-fetch metadata from SAM.gov v2 API without downloading attachments."""
    nid = (notice_id or "").strip()
    if not nid and url:
        nid = extract_notice_id(url) or ""
    if not nid:
        raise HTTPException(status_code=400, detail="A valid SAM.gov URL or Notice ID is required.")

    try:
        notice = fetch_notice(nid)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to query SAM.gov API: {e}")

    desc = None
    try:
        desc = fetch_description(nid)
    except Exception:
        pass

    return {
        "notice_id": nid,
        "title": notice.get("title"),
        "department": notice.get("department"),
        "sub_tier": notice.get("subTier"),
        "office": notice.get("office"),
        "posted_date": notice.get("postedDate"),
        "response_deadline": notice.get("responseDeadLine"),
        "naics_code": notice.get("naicsCode"),
        "set_aside": (
            notice.get("typeOfSetAsideDescription")
            or notice.get("typeOfSetAside")
        ),
        "description": desc,
    }


@router.post("/solicitations/ingest-package", status_code=201)
async def ingest_solicitation_package(
    files: list[UploadFile] = File(...),
    source_type: str = Form("federal"),
    url: str | None = Form(None),
    notice_id: str | None = Form(None),
    title: str | None = Form(None),
    description: str | None = Form(None),
    user: dict = Depends(get_current_user),
):
    """Directly ingest a solicitation package (ZIP archive or individual files).

    - Instant response: creates case & solicitation record, stages files to MinIO.
    - Asynchronously in worker: fetches SAM.gov metadata (if notice_id provided),
      extracts files/zips, ingests documents into MinIO/DB, and triggers triage.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one file or .zip archive is required.")

    resolved_url = (url or "").strip()
    resolved_notice_id = (notice_id or "").strip()
    if not resolved_notice_id and resolved_url:
        resolved_notice_id = extract_notice_id(resolved_url) or ""

    has_user_title = bool((title or "").strip())
    has_user_description = bool((description or "").strip())

    initial_title = (title or "").strip()
    if not initial_title:
        initial_title = f"Solicitation {resolved_notice_id}" if resolved_notice_id else "New Solicitation"

    # 1. Create Solicitation & Case records immediately (ingestion_status='pending')
    try:
        sol = mgr.create(
            source_type=source_type,
            url=resolved_url,
            title=initial_title,
            notice_id=resolved_notice_id or None,
            description=(description or "").strip() or None,
        )
    except DuplicateNoticeError as e:
        return JSONResponse(
            status_code=409,
            content={
                "detail": str(e),
                "existing_external_id": e.existing_external_id,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    case_id = sol["case_id"]
    sol_id = sol["id"]

    # 2. Stage uploaded files to MinIO
    staged_files = []
    for upload_file in files:
        fname = upload_file.filename or "upload"
        clean_fname = Path(fname).name
        if not clean_fname or clean_fname.startswith("."):
            continue
        content = await upload_file.read()
        if not content:
            continue
        obj_key = f"staging/{sol_id}/{uuid.uuid4().hex[:8]}_{clean_fname}"
        upload_attachment(obj_key, content)
        staged_files.append({"object_key": obj_key, "filename": clean_fname})

    if not staged_files:
        mgr.update(sol_id, ingestion_status="failed", error_message="No valid files provided")
        raise HTTPException(status_code=400, detail="No valid files uploaded.")

    # 3. Enqueue smart_ingest job for background worker
    job = _enqueue_job(
        case_id=case_id,
        job_type="smart_ingest",
        metadata={
            "solicitation_id": sol_id,
            "notice_id": resolved_notice_id or None,
            "has_user_title": has_user_title,
            "has_user_description": has_user_description,
            "staged_files": staged_files,
        },
    )

    refreshed_sol = mgr.get(sol_id) or sol
    return {
        "solicitation": refreshed_sol,
        "document_count": len(staged_files),
        "job_id": job["id"],
    }


# ---------------------------------------------------------------------------
# List + Get
# ---------------------------------------------------------------------------

@router.get("/solicitations/mine")
def my_solicitations(
    user: dict = Depends(get_current_user),
):
    """Return the current user's assigned solicitations with quote counts."""
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT s.*, nc.title AS naics_label,
                          u.username AS assignee_username,
                          COALESCE(qs.quotes_total, 0) AS quotes_total,
                          COALESCE(qs.quotes_draft, 0) AS quotes_draft,
                          COALESCE(qs.quotes_submitted, 0) AS quotes_submitted
                   FROM solicitations s
                   LEFT JOIN naics_codes nc ON nc.code = s.naics_code
                   LEFT JOIN users u ON u.id = s.assignee_id
                   LEFT JOIN (
                       SELECT solicitation_id,
                              COUNT(*) AS quotes_total,
                              COUNT(*) FILTER (WHERE status IN ('draft','pending_site_visit')) AS quotes_draft,
                              COUNT(*) FILTER (WHERE status IN ('submitted','awarded')) AS quotes_submitted
                       FROM quotes
                       GROUP BY solicitation_id
                   ) qs ON qs.solicitation_id = s.id
                   WHERE s.assignee_id = %s
                   ORDER BY s.response_deadline ASC NULLS LAST, s.assigned_at DESC""",
                (user["id"],),
            )
            solicitations = [dict(row) for row in cur.fetchall()]

        # Summary
        needs_triage = sum(1 for s in solicitations if s.get("triage_status") not in ("complete",))
        needs_quote = sum(1 for s in solicitations if s.get("triage_status") == "complete" and not s.get("quotes_total"))
        quotes_in_progress = sum(s.get("quotes_draft", 0) for s in solicitations)

        return {
            "solicitations": solicitations,
            "summary": {
                "total_assigned": len(solicitations),
                "needs_triage": needs_triage,
                "needs_quote": needs_quote,
                "quotes_in_progress": quotes_in_progress,
            },
        }
    finally:
        conn.close()


@router.get("/solicitations")
def list_solicitations_endpoint(
    source_type: str | None = None,
    ingestion_status: str | None = None,
    naics_code: str | None = None,
    state: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(get_current_user),
):
    sols, total = mgr.list(
        source_type=source_type,
        ingestion_status=ingestion_status,
        naics_code=naics_code,
        state=state,
        limit=limit,
        offset=offset,
    )

    # Attach unread reply counts for notification badges.
    if sols:
        sol_ids = [s["id"] for s in sols if s.get("id")]
        if sol_ids:
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
                        (sol_ids,),
                    )
                    unread_map = {row[0]: row[1] for row in cur.fetchall()}
            finally:
                conn.close()
            for sol in sols:
                sol["unread_replies"] = unread_map.get(sol["id"], 0)

    # Attach outreach-sent indicator.
    if sols:
        sol_ids = [s["id"] for s in sols if s.get("id")]
        if sol_ids:
            conn = connect()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT DISTINCT vm.solicitation_id
                           FROM vendor_matches vm
                           WHERE vm.solicitation_id = ANY(%s)
                             AND vm.outreach_status IN ('requested', 'received')""",
                        (sol_ids,),
                    )
                    outreach_set = {row[0] for row in cur.fetchall()}
            finally:
                conn.close()
            for sol in sols:
                sol["has_outreach"] = sol["id"] in outreach_set

    return {"total": total, "limit": limit, "offset": offset, "count": len(sols), "solicitations": sols}


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
# NAICS codes — lookup for filter dropdowns
# ---------------------------------------------------------------------------

@router.get("/naics-codes")
def list_naics_codes_endpoint(
    user: dict = Depends(get_current_user),
):
    """Return all 6-digit NAICS codes with titles for filter dropdowns."""
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT code, title FROM naics_codes ORDER BY code")
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


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
# Assignment — claim / release / admin assign
# ---------------------------------------------------------------------------

class AssignSolicitationRequest(BaseModel):
    user_id: str


@router.post("/solicitations/{solicitation_id}/claim")
def claim_solicitation(
    solicitation_id: int,
    user: dict = Depends(get_current_user),
):
    """Claim a solicitation for the current user."""
    sol = mgr.get(solicitation_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    if sol.get("assignee_id"):
        raise HTTPException(
            status_code=409,
            detail=f"Already claimed by another user",
        )
    updated = mgr.update(
        solicitation_id,
        assignee_id=user["id"],
        assigned_at="now",
    )
    return updated


@router.post("/solicitations/{solicitation_id}/release")
def release_solicitation(
    solicitation_id: int,
    user: dict = Depends(get_current_user),
):
    """Release a solicitation. Only the assignee or admin can release."""
    sol = mgr.get(solicitation_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    if not sol.get("assignee_id"):
        raise HTTPException(status_code=400, detail="Not currently claimed")
    if sol["assignee_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only the assignee or admin can release")
    updated = mgr.update(
        solicitation_id,
        assignee_id=None,
        assigned_at=None,
    )
    return updated


@router.post("/solicitations/{solicitation_id}/assign")
def assign_solicitation(
    solicitation_id: int,
    body: AssignSolicitationRequest,
    admin: dict = Depends(get_current_user),
):
    """Admin assigns a solicitation to any user."""
    if admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    sol = mgr.get(solicitation_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    # Verify user exists
    from auth import get_user_by_id
    target = get_user_by_id(body.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    updated = mgr.update(
        solicitation_id,
        assignee_id=body.user_id,
        assigned_at="now",
    )
    return updated


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
# Rerun — restart full pipeline from sam_fetch
# ---------------------------------------------------------------------------

@router.post("/solicitations/{solicitation_id}/rerun")
def rerun_solicitation_endpoint(
    solicitation_id: int,
    user: dict = Depends(get_current_user),
):
    """Restart a solicitation from scratch — re-fetch SAM.gov docs, re-triage,
    re-match. Resets all statuses, deletes old vendor matches and jobs, then
    enqueues a fresh sam_fetch job. Only works for federal solicitations
    with a notice_id."""
    sol = mgr.get(solicitation_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    if sol.get("source_type") != "federal":
        raise HTTPException(status_code=400, detail="Only federal solicitations can be re-run")
    if not sol.get("notice_id"):
        raise HTTPException(status_code=400, detail="Solicitation has no SAM.gov notice_id")

    case_id = sol["case_id"]
    notice_id = sol["notice_id"]

    # Reset solicitation status columns
    mgr.update(
        solicitation_id,
        ingestion_status="fetching",
        has_missing_docs=False,
        error_message=None,
        triage_status="pending",
        triage_error=None,
        has_partial_artifacts=False,
        notice_type=None,
        quick_kill=None,
        quick_kill_reason=None,
        matching_status="pending",
        matching_error=None,
    )

    # Clear old vendor messages, matches, and jobs
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM vendor_outreach_messages "
                "WHERE vendor_match_id IN (SELECT id FROM vendor_matches WHERE solicitation_id = %s)",
                (solicitation_id,),
            )
            cur.execute("DELETE FROM vendor_matches WHERE solicitation_id = %s", (solicitation_id,))
            cur.execute("DELETE FROM jobs WHERE case_id = %s", (case_id,))

    # Enqueue fresh sam_fetch
    job = _enqueue_job(
        case_id=case_id,
        job_type="sam_fetch",
        metadata={"solicitation_id": solicitation_id, "notice_id": notice_id},
    )

    return {"solicitation_id": solicitation_id, "job_id": job["id"], "status": "rerun_queued"}


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
