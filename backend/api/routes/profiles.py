"""
Vision — Company Profile API Routes.

CRUD for account-level GovCon company profiles.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

import tempfile
from pathlib import Path as FilePath

from auth import get_current_user
from core.db import (
    connect, tx,
    list_company_profiles as _list,
    get_company_profile as _get,
    insert_company_profile as _insert,
    update_company_profile as _update,
    delete_company_profile as _delete,
)

router = APIRouter(prefix="/api", tags=["company_profiles"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateProfileRequest(BaseModel):
    name: str


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    content: dict | None = None
    status: str | None = None
    source_docs: list | None = None


# ---------------------------------------------------------------------------
# List + Get
# ---------------------------------------------------------------------------

@router.get("/profiles")
def list_profiles(user: dict = Depends(get_current_user)):
    conn = connect()
    try:
        return {"profiles": _list(conn)}
    finally:
        conn.close()


@router.get("/profiles/{profile_id}")
def get_profile(profile_id: int, user: dict = Depends(get_current_user)):
    conn = connect()
    try:
        profile = _get(conn, profile_id)
    finally:
        conn.close()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"profile": profile}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("/profiles")
def create_profile(
    body: CreateProfileRequest,
    user: dict = Depends(get_current_user),
):
    with tx() as conn:
        profile_id = _insert(conn, name=body.name)
        profile = _get(conn, profile_id)
    return {"profile": profile}


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.patch("/profiles/{profile_id}")
def update_profile(
    profile_id: int,
    body: UpdateProfileRequest,
    user: dict = Depends(get_current_user),
):
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    with tx() as conn:
        updated = _update(conn, profile_id, **kwargs)
    if not updated:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"profile": updated}


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.post("/profiles/{profile_id}/upload")
async def profile_upload(
    profile_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a document for profile synthesis.

    Creates a docs case for the profile if one doesn't exist yet,
    ingests the file, and adds it to source_docs.
    """
    conn = connect()
    try:
        profile = _get(conn, profile_id)
    finally:
        conn.close()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Get or create docs case
    docs_case_id = profile.get("docs_case_id")
    if not docs_case_id:
        from core.case import CaseManager
        owner_id = user.get("id") if isinstance(user, dict) else None
        mgr = CaseManager()
        c = mgr.create_case(
            name=f"Company Profile — {profile['name']} Docs",
            case_type="other",
            owner_id=owner_id,
        )
        docs_case_id = c["id"]
        with tx() as conn2:
            _update(conn2, profile_id, docs_case_id=docs_case_id)

    # Save and ingest the file
    suffix = FilePath(file.filename or "doc").suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        from ingestion.storage import upload_file as _upload_minio
        from ingestion.jobs import enqueue as _enqueue_job

        storage_ref = _upload_minio(tmp_path, file.filename or "document")
        job = _enqueue_job(
            case_id=docs_case_id,
            job_type="ingest",
            storage_ref=storage_ref,
        )

        # Add to source_docs immediately (optimistic)
        existing = (profile.get("source_docs") or [])
        if isinstance(existing, str):
            import json; existing = json.loads(existing)
        existing.append({
            "document_id": None,  # filled in after ingest completes
            "document_name": file.filename or "document",
            "job_id": job["id"],
        })
        with tx() as conn2:
            _update(conn2, profile_id, source_docs=existing)

        return {
            "job_id": job["id"],
            "status": job["status"],
            "document_name": file.filename,
        }
    finally:
        try:
            import os; os.unlink(tmp_path)
        except OSError:
            pass


@router.post("/profiles/{profile_id}/synthesize")
def synthesize_profile(profile_id: int, user: dict = Depends(get_current_user)):
    """Trigger profile synthesis. Enqueues a background job.

    The agent reads all documents in the profile's docs_case and
    populates the profile content fields automatically.
    """
    conn = connect()
    try:
        profile = _get(conn, profile_id)
    finally:
        conn.close()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from ingestion.jobs import enqueue as _enqueue_job

    # Use docs_case_id if available, otherwise create one
    docs_case_id = profile.get("docs_case_id")
    if not docs_case_id:
        from core.case import CaseManager
        owner_id = user.get("id") if isinstance(user, dict) else None
        mgr = CaseManager()
        c = mgr.create_case(
            name=f"Company Profile — {profile['name']} Docs",
            case_type="other",
            owner_id=owner_id,
        )
        docs_case_id = c["id"]
        with tx() as conn2:
            _update(conn2, profile_id, docs_case_id=docs_case_id)

    job = _enqueue_job(
        case_id=docs_case_id,
        job_type="profile_synthesis",
        metadata={"profile_id": profile_id},
    )
    return {"job_id": job["id"], "status": job["status"]}


@router.post("/profiles/{profile_id}/generate-statement")
def generate_capability_statement(profile_id: int, user: dict = Depends(get_current_user)):
    """Generate a capability statement draft from profile data.

    Enqueues a background job. The agent reads the profile and creates
    a draft with document_type='capability_statement'.
    """
    conn = connect()
    try:
        profile = _get(conn, profile_id)
    finally:
        conn.close()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    docs_case_id = profile.get("docs_case_id")
    if not docs_case_id:
        raise HTTPException(status_code=400, detail="Upload profile docs first")

    from ingestion.jobs import enqueue as _enqueue_job
    job = _enqueue_job(
        case_id=docs_case_id,
        job_type="capability_statement",
        metadata={"profile_id": profile_id},
    )
    return {"job_id": job["id"], "status": job["status"]}


@router.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int, user: dict = Depends(get_current_user)):
    with tx() as conn:
        ok = _delete(conn, profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"deleted": True}
