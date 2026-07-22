"""
Vision — SAM.gov Databank Notices API Routes.

Upload CSVs from the SAM.gov databank and query them with dynamic filters
and full-text search. The agent tool query_sam_notices calls the same
underlying query logic.
"""

from __future__ import annotations

import csv
import io
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from auth import get_current_user
from core.db import connect, tx

router = APIRouter(prefix="/api/sam-notices", tags=["sam_notices"])

# Columns in the CSV that map 1:1 to sam_notices table columns
_CSV_COLUMN_MAP = {
    "Contracting Office": "contracting_office",
    "Procurement AAC Code": "procurement_aac_code",
    "Sub Tier Code": "sub_tier_code",
    "Sub Tier Name": "sub_tier_name",
    "Notice ID": "notice_id",
    "Contract Opportunity Type": "contract_opportunity_type",
    "Opportunity Title": "opportunity_title",
    "Description": "description",
    "Current Response Date": "current_response_date",
    "Current Set Aside": "current_set_aside",
    "Initiative": "initiative",
    "NAICS": "naics_code",
    "PSC": "psc_code",
    "Place of Performance - Country": "pop_country",
    "Place of Performance - Zip": "pop_zip",
    "Place of Performance - City": "pop_city",
    "Place of Performance - State": "pop_state",
    "Interested Vendor List (IVL) Enabled": "ivl_enabled",
    "Package Attachment Count (Public)": "attachment_count",
    "POC Name": "poc_name",
    "POC Email": "poc_email",
    "Unique Entity ID": "awardee_uei",
    "Legal Business Name": "awardee_name",
    "Last Published Date": "last_published_date",
    "Inactive Date": "inactive_date",
    "Last Updated Date": "last_updated_date",
    "Status": "status",
    "Current Set Aside Code": "current_set_aside_code",
}

# Whitelist of sortable columns
_SORTABLE_COLUMNS = {
    "opportunity_title", "contract_opportunity_type", "naics_code",
    "psc_code", "current_set_aside", "current_response_date",
    "last_published_date", "sub_tier_name", "pop_state", "pop_city",
    "status", "poc_name", "awardee_name", "attachment_count",
    "created_at",
}

# Whitelist of filterable columns (prevents SQL injection via column names)
_FILTERABLE_COLUMNS = _SORTABLE_COLUMNS | {
    "notice_id", "contracting_office", "procurement_aac_code",
    "sub_tier_code", "naics_description", "initiative",
    "current_set_aside_code", "pop_country", "pop_zip",
    "poc_email", "awardee_uei", "ivl_enabled",
}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_sam_notices_csv(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a SAM.gov databank CSV. Replaces all rows from previous uploads
    in the same batch, or appends if ?replace=false is set.

    The CSV must have the standard SAM.gov databank column headers. Rows
    are bulk-inserted in a single transaction. On success, returns the
    row count and batch ID.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no headers")

    # Map CSV columns to DB columns
    db_columns = []
    csv_indices = {}
    for csv_col, db_col in _CSV_COLUMN_MAP.items():
        if csv_col in reader.fieldnames:
            db_columns.append(db_col)
            csv_indices[db_col] = csv_col

    if not db_columns:
        raise HTTPException(
            status_code=400,
            detail="No recognized SAM.gov databank columns found in CSV headers",
        )

    batch_id = uuid.uuid4()
    rows_inserted = 0

    db_columns.append("upload_batch_id")
    db_columns.append("source_csv")

    # DATE_COLS that need conversion
    _DATE_COLS = {
        "current_response_date", "last_published_date",
        "inactive_date", "last_updated_date",
    }

    with tx() as conn:
        with conn.cursor() as cur:
            # Build INSERT
            placeholders = ", ".join(["%s"] * len(db_columns))
            col_list = ", ".join(db_columns)
            sql = f"INSERT INTO sam_notices ({col_list}) VALUES ({placeholders})"

            batch = []
            for row in reader:
                values = []
                for db_col in db_columns[:-2]:  # skip upload_batch_id, source_csv
                    csv_col = csv_indices.get(db_col)
                    if not csv_col:
                        values.append(None)
                        continue
                    val = row.get(csv_col, "").strip()
                    if not val:
                        values.append(None)
                    elif db_col in _DATE_COLS:
                        # Try common date formats
                        parsed = None
                        for fmt in [
                            "%b %d, %Y %I:%M %p UTC",  # Jul 10, 2026 09:06 PM UTC
                            "%b %d, %Y",                 # Jul 10, 2026
                            "%Y-%m-%d",                  # 2026-07-10
                            "%m/%d/%Y",                  # 07/10/2026
                        ]:
                            try:
                                from datetime import datetime as _dt
                                parsed = _dt.strptime(val, fmt)
                                break
                            except ValueError:
                                continue
                        values.append(parsed)
                    elif db_col == "attachment_count":
                        try:
                            values.append(int(val))
                        except (ValueError, TypeError):
                            values.append(None)
                    elif db_col == "ivl_enabled":
                        values.append(val.lower() in ("true", "yes", "1", "t"))
                    else:
                        values.append(val)
                values.append(batch_id)
                values.append(file.filename)
                batch.append(values)

                if len(batch) >= 500:
                    for b in batch:
                        cur.execute(sql, b)
                    rows_inserted += len(batch)
                    batch = []

            # Flush remaining
            for b in batch:
                cur.execute(sql, b)
            rows_inserted += len(batch)

    return {
        "batch_id": str(batch_id),
        "rows_inserted": rows_inserted,
        "source": file.filename,
    }


# ---------------------------------------------------------------------------
# Query / Search
# ---------------------------------------------------------------------------

class SamNoticesQuery(BaseModel):
    """Dynamic query filters. All fields optional — empty = return all."""
    q: str | None = None              # full-text search query
    naics_code: str | None = None
    naics_description: str | None = None
    psc_code: str | None = None
    contract_opportunity_type: str | None = None
    current_set_aside: str | None = None
    current_set_aside_code: str | None = None
    sub_tier_name: str | None = None
    pop_state: str | None = None
    pop_city: str | None = None
    status: str | None = None
    awardee_name: str | None = None
    awardee_uei: str | None = None
    notice_id: str | None = None
    contracting_office: str | None = None
    initiative: str | None = None
    response_date_from: str | None = None
    response_date_to: str | None = None
    published_date_from: str | None = None
    published_date_to: str | None = None
    has_attachments: bool | None = None
    ivl_enabled: bool | None = None
    limit: int = 100
    offset: int = 0
    order_by: str = "last_published_date"
    order_dir: str = "DESC"


@router.post("/query")
def query_sam_notices(
    body: SamNoticesQuery,
    user: dict = Depends(get_current_user),
):
    """Query SAM.gov databank notices with dynamic filters and full-text search.

    All filter fields are optional. Combine multiple filters for precise
    matching. The `q` field performs full-text search across title,
    description, NAICS, agency, and POC name.
    """
    conn = connect()
    try:
        with conn.cursor() as cur:
            where_parts = []
            params: list[Any] = []

            # Full-text search
            if body.q and body.q.strip():
                where_parts.append(
                    "search_vector @@ plainto_tsquery('english', %s)"
                )
                params.append(body.q.strip())

            # Exact / LIKE filters
            _str_filters = [
                ("naics_code", body.naics_code, "exact"),
                ("naics_description", body.naics_description, "like"),
                ("psc_code", body.psc_code, "exact"),
                ("contract_opportunity_type", body.contract_opportunity_type, "exact"),
                ("current_set_aside", body.current_set_aside, "like"),
                ("current_set_aside_code", body.current_set_aside_code, "exact"),
                ("sub_tier_name", body.sub_tier_name, "like"),
                ("pop_state", body.pop_state, "exact"),
                ("pop_city", body.pop_city, "like"),
                ("status", body.status, "exact"),
                ("awardee_name", body.awardee_name, "like"),
                ("awardee_uei", body.awardee_uei, "exact"),
                ("notice_id", body.notice_id, "exact"),
                ("contracting_office", body.contracting_office, "like"),
                ("initiative", body.initiative, "like"),
            ]
            for col, val, match_type in _str_filters:
                if val and val.strip():
                    if match_type == "exact":
                        where_parts.append(f"{col} = %s")
                        params.append(val.strip())
                    else:
                        where_parts.append(f"{col} ILIKE %s")
                        params.append(f"%{val.strip()}%")

            # Boolean filters
            if body.has_attachments is not None:
                if body.has_attachments:
                    where_parts.append("attachment_count > 0")
                else:
                    where_parts.append("(attachment_count IS NULL OR attachment_count = 0)")

            if body.ivl_enabled is not None:
                where_parts.append("ivl_enabled = %s")
                params.append(body.ivl_enabled)

            # Date range filters
            if body.response_date_from:
                where_parts.append("current_response_date >= %s")
                params.append(body.response_date_from)
            if body.response_date_to:
                where_parts.append("current_response_date <= %s")
                params.append(body.response_date_to)
            if body.published_date_from:
                where_parts.append("last_published_date >= %s")
                params.append(body.published_date_from)
            if body.published_date_to:
                where_parts.append("last_published_date <= %s")
                params.append(body.published_date_to)

            where_clause = ""
            if where_parts:
                where_clause = "WHERE " + " AND ".join(where_parts)

            # Ordering (whitelist-checked)
            order_col = body.order_by if body.order_by in _SORTABLE_COLUMNS else "last_published_date"
            order_dir = "DESC" if body.order_dir.upper() == "DESC" else "ASC"

            # Count
            cur.execute(
                f"SELECT COUNT(*) FROM sam_notices {where_clause}",
                tuple(params),
            )
            total = cur.fetchone()[0]

            # Fetch
            limit = min(body.limit, 1000)
            offset = max(body.offset, 0)
            cur.execute(
                f"""SELECT id, notice_id, opportunity_title, contract_opportunity_type,
                           naics_code, naics_description, psc_code,
                           current_set_aside, current_set_aside_code,
                           sub_tier_name, contracting_office,
                           pop_city, pop_state, pop_country,
                           current_response_date, last_published_date,
                           status, poc_name, poc_email,
                           awardee_name, awardee_uei,
                           attachment_count, ivl_enabled,
                           description,
                           upload_batch_id, source_csv, created_at
                    FROM sam_notices
                    {where_clause}
                    ORDER BY {order_col} {order_dir}
                    LIMIT %s OFFSET %s""",
                tuple(params + [limit, offset]),
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, row)) for row in rows]

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "count": len(results),
                "results": results,
            }
    finally:
        conn.close()


@router.get("/batches")
def list_upload_batches(user: dict = Depends(get_current_user)):
    """List all upload batches with row counts."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT upload_batch_id, source_csv, COUNT(*) as row_count,
                          MIN(created_at) as uploaded_at
                   FROM sam_notices
                   WHERE upload_batch_id IS NOT NULL
                   GROUP BY upload_batch_id, source_csv
                   ORDER BY uploaded_at DESC"""
            )
            rows = cur.fetchall()
            return {
                "batches": [
                    {"batch_id": str(r[0]), "source": r[1],
                     "rows": r[2], "uploaded_at": str(r[3])}
                    for r in rows
                ]
            }
    finally:
        conn.close()


@router.delete("/batches/{batch_id}")
def delete_upload_batch(
    batch_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete all rows from a specific upload batch."""
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM sam_notices WHERE upload_batch_id = %s",
                (batch_id,),
            )
            deleted = cur.rowcount
    return {"deleted": deleted, "batch_id": batch_id}


# ---------------------------------------------------------------------------
# Solicitation URL lookup — resolve solicitation number → SAM.gov UI link
# ---------------------------------------------------------------------------

@router.get("/lookup")
async def lookup_solicitation_url(
    sol: str = Query(..., description="Solicitation number from the databank CSV"),
    user: dict = Depends(get_current_user),
):
    """Look up the SAM.gov UI link for a solicitation number.

    Calls the SAM.gov v2 search API with the `solnum` parameter for
    exact solicitation number matching. Returns the ui_link from the
    first matching opportunity so the frontend can open it directly.
    """
    import os
    from datetime import date, timedelta
    import httpx

    api_key = os.environ.get("SAM_GOV_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="SAM_GOV_API_KEY not configured")

    # Same pattern as _sam_search in external_tools.py — requires date range
    to_date = date.today()
    from_date = to_date - timedelta(days=364)

    url = (
        f"https://api.sam.gov/opportunities/v2/search"
        f"?api_key={api_key}"
        f"&solnum={sol}"
        f"&postedFrom={from_date.strftime('%m/%d/%Y')}"
        f"&postedTo={to_date.strftime('%m/%d/%Y')}"
        f"&limit=3"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SAM.gov API call failed: {e}")

    opportunities = data.get("opportunitiesData") or []
    if not opportunities:
        raise HTTPException(status_code=404, detail=f"No SAM.gov match for solicitation '{sol}'")

    best = opportunities[0]
    return {
        "solicitation_number": sol,
        "title": best.get("title", ""),
        "notice_id": best.get("noticeId", ""),
        "ui_link": best.get("uiLink", ""),
        "response_deadline": best.get("responseDeadLine"),
        "posted_date": best.get("postedDate"),
    }
