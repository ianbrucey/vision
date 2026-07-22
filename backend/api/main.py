"""
Vision — REST API.

FastAPI application exposing case CRUD, party/allegation management,
and document ingestion. This is the backend that the UI (and CLI agent)
call into.

Usage:
    cd scripts && python -m uvicorn vision.api:app --reload --port 8400
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Depends, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.case import CaseManager
from core.db import ensure_schema, ensure_strategy_schema, ensure_chat_schema, ensure_correspondence_schema, ensure_solicitations_schema, ensure_solicitation_triage_schema, ensure_vendors_schema, ensure_vendor_matching_schema, ensure_vendor_matches_manual_schema, ensure_vendor_matches_cap_schema, ensure_vendor_outreach_schema, ensure_vendor_outreach_email_schema, ensure_vendor_outreach_messages_schema, ensure_workspace_pdf_filetype_schema, ensure_sam_notices_schema, ensure_sam_notice_import_job_schema, ensure_forecast_opportunities_schema
from core.vendor import VendorManager
from ingestion.storage import upload_file as _upload_to_minio
from ingestion.jobs import enqueue as _enqueue_job, get_job, list_jobs
from auth import create_user, authenticate_user, create_token, get_current_user

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Vision API",
    description="War Room Agent — Case Management & Document Ingestion",
    version="0.1.0",
)

# CORS — env-driven. Unset (local dev) keeps the historical wildcard behavior.
# In prod, set CORS_ALLOWED_ORIGINS=https://vision.justicequest.pro.
_cors_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS")
_cors_origins = (
    [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    if _cors_origins_env
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _apply_schemas():
    """Idempotent schema application on every startup.

    Ensures all three schema files are applied before the first request.
    Uses IF NOT EXISTS internally — safe to run on every restart.
    """
    ensure_schema()                 # 001 — cases, parties, evidence store, users
    ensure_strategy_schema()        # 002 — strategies, propositions, gauntlet
    ensure_chat_schema()            # 003 — chat sessions, messages, session store
    ensure_correspondence_schema()  # 004 — correspondence threads, items, attachments
    ensure_solicitations_schema()   # 007 — solicitations table (Option A)
    ensure_solicitation_triage_schema()  # 008 — triage classification + HTML artifacts
    ensure_vendors_schema()           # 009 — unified vendor registry (GSA + SBA)
    ensure_vendor_matching_schema()   # 010 — vendor_matches table + outreach columns
    ensure_vendor_matches_manual_schema()  # 011 — allow naics_match_type='manual'
    ensure_vendor_matches_cap_schema()     # 012 — raise rank cap 25 -> 30
    ensure_vendor_outreach_schema()        # 013 — outreach status tracking (T8)
    ensure_vendor_outreach_email_schema() # 014 — outreach email send/reply tracking (T10)
    ensure_vendor_outreach_messages_schema() # 015 — per-vendor message thread (T10c)
    ensure_workspace_pdf_filetype_schema()   # 016 — add 'pdf' file_type to workspace
    ensure_sam_notices_schema()             # 017 — SAM.gov databank notices table
    ensure_sam_notice_import_job_schema()   # 018 — sam_notice_import job type
    ensure_forecast_opportunities_schema()  # 019 — forecast opportunities table


mgr = CaseManager()
vendor_mgr = VendorManager()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register")
def register(body: RegisterRequest):
    """Create a new user account."""
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    new_user = create_user(body.username, body.password, body.email)
    token = create_token(new_user)
    return {"user": new_user, "token": token}


@app.post("/api/auth/login")
def login(body: LoginRequest):
    """Login and receive a JWT."""
    auth_user = authenticate_user(body.username, body.password)
    if auth_user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(auth_user)
    return {"user": auth_user, "token": token}


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)):
    """Return the current authenticated user."""
    return {"user": user}


# ---------------------------------------------------------------------------
# Request/Response Schemas
# ---------------------------------------------------------------------------

class CaseCreate(BaseModel):
    name: str
    case_type: str
    narrative: str | None = None
    description: str | None = None
    case_number: str | None = None
    jurisdiction: str | None = None
    filing_date: str | None = None


class CaseUpdate(BaseModel):
    name: str | None = None
    case_type: str | None = None
    status: str | None = None
    narrative: str | None = None
    description: str | None = None
    case_number: str | None = None
    jurisdiction: str | None = None
    filing_date: str | None = None


class PartyCreate(BaseModel):
    name: str
    party_kind: str = "individual"
    roles: list[str] = []
    notes: str | None = None
    contact_info: dict | None = None


class PartyUpdate(BaseModel):
    name: str | None = None
    party_kind: str | None = None
    roles: list[str] | None = None
    notes: str | None = None
    contact_info: dict | None = None


class AllegationCreate(BaseModel):
    allegation_id: str
    text: str
    category: str | None = None
    targets: list[int] = []
    extraction_focus: list[str] = []


class AllegationUpdate(BaseModel):
    allegation_id: str | None = None
    text: str | None = None
    category: str | None = None
    status: str | None = None
    targets: list[int] | None = None
    extraction_focus: list[str] | None = None
    sort_order: int | None = None


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

@app.get("/api/cases")
def list_cases(
    status: str | None = None,
    case_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(get_current_user),
):
    owner_id = user.get("id") if isinstance(user, dict) else None
    return mgr.list_cases(status=status, case_type=case_type,
                          limit=limit, offset=offset, owner_id=owner_id)


@app.post("/api/cases")
def create_case(body: CaseCreate, user: dict = Depends(get_current_user)):
    owner_id = user.get("id") if isinstance(user, dict) else None
    return mgr.create_case(**body.model_dump(exclude_none=True), owner_id=owner_id)


@app.get("/api/cases/{case_id}")
def get_case(case_id: int, user: dict = Depends(get_current_user)):
    case = mgr.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.patch("/api/cases/{case_id}")
def update_case(case_id: int, body: CaseUpdate, user: dict = Depends(get_current_user)):
    updated = mgr.update_case(case_id, **body.model_dump(exclude_none=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return updated


@app.delete("/api/cases/{case_id}")
def delete_case(case_id: int, user: dict = Depends(get_current_user)):
    if not mgr.delete_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Parties
# ---------------------------------------------------------------------------

@app.get("/api/cases/{case_id}/parties")
def list_parties(case_id: int, user: dict = Depends(get_current_user)):
    return mgr.list_parties(case_id)


@app.post("/api/cases/{case_id}/parties")
def add_party(case_id: int, body: PartyCreate, user: dict = Depends(get_current_user)):
    return mgr.add_party(case_id, **body.model_dump(exclude_none=True))


@app.patch("/api/parties/{party_id}")
def update_party(party_id: int, body: PartyUpdate, user: dict = Depends(get_current_user)):
    updated = mgr.update_party(party_id, **body.model_dump(exclude_none=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Party not found")
    return updated


@app.delete("/api/parties/{party_id}")
def remove_party(party_id: int, user: dict = Depends(get_current_user)):
    if not mgr.remove_party(party_id):
        raise HTTPException(status_code=404, detail="Party not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Allegations
# ---------------------------------------------------------------------------

@app.get("/api/cases/{case_id}/allegations")
def list_allegations(case_id: int, user: dict = Depends(get_current_user)):
    return mgr.list_allegations(case_id)


@app.post("/api/cases/{case_id}/allegations")
def add_allegation(case_id: int, body: AllegationCreate, user: dict = Depends(get_current_user)):
    return mgr.add_allegation(case_id, **body.model_dump(exclude_none=True))


@app.patch("/api/allegations/{allegation_id}")
def update_allegation(allegation_id: int, body: AllegationUpdate, user: dict = Depends(get_current_user)):
    updated = mgr.update_allegation(
        allegation_id, **body.model_dump(exclude_none=True)
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Allegation not found")
    return updated


@app.delete("/api/allegations/{allegation_id}")
def remove_allegation(allegation_id: int, user: dict = Depends(get_current_user)):
    if not mgr.remove_allegation(allegation_id):
        raise HTTPException(status_code=404, detail="Allegation not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Documents / Ingestion
# ---------------------------------------------------------------------------

@app.get("/api/cases/{case_id}/documents")
def list_documents(case_id: int, user: dict = Depends(get_current_user)):
    """Return documents for a case (uses CaseManager.get_case)."""
    case = mgr.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case.get("documents", [])


@app.post("/api/cases/{case_id}/ingest")
async def ingest_document(case_id: int, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Upload a file for ingestion. Returns immediately with a job ID.

    The file is stored in MinIO. A background worker picks up the job,
    processes the file (OCR/transcription/extraction), and indexes it into
    the evidence store.

    Poll GET /api/jobs/{job_id} for status.

    Supports: PDF, DOCX, JPG, PNG, CSV, XLSX, M4A, MP3, WAV, ZIP, and more.
    ZIP files are extracted by the worker — each contained file gets its own
    ingest job. Check job.metadata.child_job_ids after completion.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    # Save uploaded file to temp, then to MinIO
    suffix = Path(file.filename).suffix or ".pdf"
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix
    ) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # Upload to MinIO
        storage_ref = _upload_to_minio(tmp_path, file.filename)

        # Enqueue the job — worker detects ZIPs by extension
        job = _enqueue_job(
            case_id=case_id,
            job_type="ingest",
            storage_ref=storage_ref,
        )

        return {
            "job_id": job["id"],
            "status": job["status"],
            "storage_ref": storage_ref,
            "is_zip": suffix.lower() == ".zip",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@app.get("/api/documents/{doc_id}/preview")
def preview_document(doc_id: int, user: dict = Depends(get_current_user)):
    """Generate a presigned URL for viewing/downloading an ingested document.

    Documents with no `storage_path` (no underlying file — e.g. inbound
    Mailgun email replies stored as sections/blocks only, see
    ingestion/worker.py::process_inbound_email_job) fall back to returning
    their block text concatenated inline as `content`, with `type: "text"`
    and `url: null`. A document with neither a storage_path nor any blocks
    is a genuine error (undefined preview target).
    """
    from core.db import connect
    from ingestion.storage import get_public_url

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, storage_path FROM documents WHERE id = %s",
                (doc_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    _db_id, doc_name, storage_path = row

    if not storage_path:
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT text_content FROM blocks
                       WHERE document_id = %s
                       ORDER BY page, id""",
                    (doc_id,),
                )
                block_rows = cur.fetchall()
        finally:
            conn.close()

        if not block_rows:
            raise HTTPException(status_code=404, detail="Document has no storage path — was it ingested before the worker fix?")

        content = "\n\n".join(r[0] for r in block_rows if r[0])
        return {"url": None, "name": doc_name, "type": "text", "content": content}

    parts = storage_path.split("/", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=500, detail=f"Invalid storage path: {storage_path}")

    bucket, object_key = parts
    try:
        url = get_public_url(bucket, object_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL: {e}")

    # Infer file type from extension
    ext = doc_name.rsplit(".", 1)[-1].lower() if "." in doc_name else ""
    type_map = {
        "pdf": "pdf", "jpg": "image", "jpeg": "image", "png": "image",
        "gif": "image", "webp": "image", "bmp": "image",
        "mp3": "audio", "wav": "audio", "m4a": "audio", "ogg": "audio",
        "flac": "audio", "webm": "audio", "mp4": "audio",
        "txt": "text", "csv": "text", "md": "text", "json": "text",
        "docx": "office", "xlsx": "office",
    }
    return {
        "url": url,
        "name": doc_name,
        "type": type_map.get(ext, "unknown"),
    }


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int, user: dict = Depends(get_current_user)):
    """Delete a document: remove from MinIO, then cascade-delete from DB.

    DB cascade removes: sections → blocks → block_headings → embeddings.
    """
    from core.db import connect, tx
    from ingestion.storage import delete_file

    # 1. Look up the document and its storage path
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, storage_path FROM documents WHERE id = %s",
                (doc_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_id_db, storage_path = row

    # 2. Delete from MinIO (best-effort — don't fail if file is already gone)
    if storage_path:
        parts = storage_path.split("/", 1)
        if len(parts) == 2:
            try:
                delete_file(parts[0], parts[1])
            except Exception:
                pass  # file may already be removed

    # 3. Cascade-delete from DB (sections, blocks, headings, embeddings follow)
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id_db,))

    return {"deleted": True}


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: int, user: dict = Depends(get_current_user)):
    """Get the status of an ingestion job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/jobs")
def list_jobs_endpoint(case_id: int | None = None, status: str | None = None, limit: int = 50, user: dict = Depends(get_current_user)):
    """List jobs, optionally filtered by case or status."""
    return list_jobs(case_id=case_id, status=status, limit=limit)


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

@app.post("/api/cases/{case_id}/synthesize")
def synthesize_case(case_id: int, user: dict = Depends(get_current_user)):
    """Trigger narrative synthesis — extract parties and allegations.

    Enqueues a background job. Poll GET /api/jobs/{job_id} for completion.
    Only fires if the case has a narrative AND at least one document.
    """
    case = mgr.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if not case.get("narrative"):
        raise HTTPException(status_code=400, detail="Save a narrative first")
    if not case.get("documents"):
        raise HTTPException(status_code=400, detail="Ingest at least one document first")

    job = _enqueue_job(
        case_id=case_id,
        job_type="synthesize",
    )
    return {
        "job_id": job["id"],
        "status": job["status"],
    }


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

from api.routes.chat import router as chat_router
from api.routes.drafts import router as drafts_router
from api.routes.workspace import router as workspace_router
from api.routes.correspondence import router as correspondence_router
from api.routes.tasks import router as tasks_router
from api.routes.profiles import router as profiles_router
from api.routes.vault import router as vault_router
from api.routes.calendar import router as calendar_router
from api.routes.solicitations import router as solicitations_router
from api.routes.webhooks_mailgun import router as webhooks_mailgun_router
from api.routes.sam_notices import router as sam_notices_router
from api.routes.forecasts import router as forecasts_router
app.include_router(chat_router)
app.include_router(drafts_router)
app.include_router(workspace_router)
app.include_router(correspondence_router)
app.include_router(tasks_router)
app.include_router(profiles_router)
app.include_router(vault_router)
app.include_router(calendar_router)
app.include_router(solicitations_router)
app.include_router(webhooks_mailgun_router)
app.include_router(sam_notices_router)
app.include_router(forecasts_router)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Vendor Search / Creation
# ---------------------------------------------------------------------------

class VendorCreate(BaseModel):
    vendor_name: str
    trade_name: str | None = None
    uei: str | None = None
    cage_code: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zipcode: str | None = None
    county: str | None = None
    naics_code_primary: str | None = None
    naics_codes_all: str | None = None
    capabilities: str | None = None
    is_small_business: bool = False
    is_woman_owned: bool = False
    is_veteran_owned: bool = False
    is_sdvosb: bool = False
    is_hubzone: bool = False
    is_8a: bool = False


@app.post("/api/vendors", status_code=201)
def create_vendor(body: VendorCreate, user: dict = Depends(get_current_user)):
    """Manually create a vendor (source='manual').

    Distinct from the bulk GSA/SBA import that populates most of the
    `vendors` table. Used by VendorsTab/VendorMatchesTab's "Add Vendor"
    flow (T7).
    """
    return vendor_mgr.create(**body.model_dump(exclude_none=True))


@app.get("/api/vendors")
def search_vendors(
    q: str | None = Query(None, description="Full-text search on name and capabilities"),
    naics: str | None = Query(None, description="NAICS code filter (partial match, e.g. '541511')"),
    state: str | None = Query(None, description="State filter (2-letter abbreviation)"),
    set_aside: str | None = Query(
        None,
        description="Socioeconomic filter: small_business, woman_owned, veteran_owned, sdvosb, hubzone, 8a",
    ),
    source: str | None = Query(None, description="Data source: sba, gsa, both"),
    limit: int = Query(20, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    user: dict = Depends(get_current_user),
):
    """Search the unified vendor registry.

    Combines GSA Schedule holders and SBA-certified small businesses
    into a single searchable table. Use for manual vendor discovery
    and opportunity-vendor matching.
    """
    from core.db import connect

    conn = connect()
    try:
        with conn.cursor() as cur:
            filters = []
            filter_params: list = []

            # NAICS filter
            if naics:
                filters.append("naics_codes_all LIKE %s")
                filter_params.append(f"%{naics}%")

            # State filter
            if state:
                filters.append("state = UPPER(%s)")
                filter_params.append(state)

            # Set-aside filter
            set_aside_map = {
                "small_business": "is_small_business",
                "woman_owned": "is_woman_owned",
                "veteran_owned": "is_veteran_owned",
                "sdvosb": "is_sdvosb",
                "hubzone": "is_hubzone",
                "8a": "is_8a",
            }
            if set_aside and set_aside in set_aside_map:
                filters.append(f"{set_aside_map[set_aside]} = TRUE")

            # Source filter
            if source and source in ("sba", "gsa", "both"):
                filters.append("source = %s")
                filter_params.append(source)

            filter_clause = (" AND " + " AND ".join(filters)) if filters else ""

            # Keyword search strategy: if filters are present, apply them
            # first (they're fast: 0.16ms for NAICS+State) to get a small
            # candidate set, then keyword-search within that set. If no
            # filters, keyword-search directly with UNION ALL indexes.
            if q:
                like_q = f"%{q}%"
                kw_params = [q, like_q, like_q]

                if filters:
                    # Filters first → small candidate set → keyword within it
                    filter_where = " AND ".join(filters)
                    inner = (
                        f"SELECT id FROM vendors "
                        f"WHERE {filter_where} AND ("
                        f"to_tsvector('english', coalesce(vendor_name, '') || ' ' || coalesce(capabilities, '')) "
                        f"@@ plainto_tsquery('english', %s) "
                        f"OR vendor_name ILIKE %s "
                        f"OR capabilities ILIKE %s)"
                    )
                    cur.execute(
                        f"SELECT COUNT(*) FROM vendors v "
                        f"WHERE {filter_where} AND ("
                        f"to_tsvector('english', coalesce(vendor_name, '') || ' ' || coalesce(capabilities, '')) "
                        f"@@ plainto_tsquery('english', %s) "
                        f"OR vendor_name ILIKE %s "
                        f"OR capabilities ILIKE %s)",
                        filter_params + kw_params,
                    )
                    total = cur.fetchone()[0]

                    cur.execute(
                        f"SELECT * FROM vendors "
                        f"WHERE {filter_where} AND ("
                        f"to_tsvector('english', coalesce(vendor_name, '') || ' ' || coalesce(capabilities, '')) "
                        f"@@ plainto_tsquery('english', %s) "
                        f"OR vendor_name ILIKE %s "
                        f"OR capabilities ILIKE %s) "
                        f"ORDER BY vendor_name LIMIT %s OFFSET %s",
                        filter_params + kw_params + [limit, offset],
                    )
                else:
                    # No filters: keyword-search directly via UNION ALL indexes
                    inner = (
                        f"SELECT id FROM vendors "
                        f"WHERE to_tsvector('english', coalesce(vendor_name, '') || ' ' || coalesce(capabilities, '')) "
                        f"@@ plainto_tsquery('english', %s) "
                        f"UNION ALL "
                        f"SELECT id FROM vendors "
                        f"WHERE vendor_name ILIKE %s "
                        f"UNION ALL "
                        f"SELECT id FROM vendors "
                        f"WHERE capabilities ILIKE %s"
                    )
                    cur.execute(
                        f"SELECT COUNT(*) FROM ({inner}) AS m",
                        kw_params,
                    )
                    total = cur.fetchone()[0]

                    cur.execute(
                        f"SELECT v.* FROM vendors v "
                        f"INNER JOIN ({inner}) AS m ON v.id = m.id "
                        f"ORDER BY v.vendor_name LIMIT %s OFFSET %s",
                        kw_params + [limit, offset],
                    )
            else:
                where_clause = f" WHERE {filters[0]}" if filters else ""
                cur.execute(f"SELECT COUNT(*) FROM vendors{where_clause}", filter_params)
                total = cur.fetchone()[0]

                cur.execute(
                    f"SELECT * FROM vendors{where_clause} ORDER BY vendor_name LIMIT %s OFFSET %s",
                    filter_params + [limit, offset],
                )

            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]

    finally:
        conn.close()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "vendors": [dict(zip(cols, row)) for row in rows],
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
