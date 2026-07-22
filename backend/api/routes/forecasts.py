"""
Vision — Acquisition Gateway Forecast API Routes.

Upload rendered HTML from the Acquisition Gateway forecast tool and
query the parsed rows with dynamic filters and full-text search.
"""

from __future__ import annotations

import re
import uuid
from io import StringIO
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from auth import get_current_user
from core.db import connect, tx

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])

# Field label → DB column mapping
_FIELD_MAP = {
    "Agency": "agency",
    "NAICS Code": "naics_raw",
    "Organization/Contracting Office": "office",
    "Acquisition Strategy/Type of Set-Aside": "set_aside",
    "Place of Performance": "place_of_performance",
    "Period of Performance": "period_of_performance",
    "Estimated Award FY": "fiscal_year",
    "Created": "created_date",
    "Estimated Contract Value": "estimated_value_text",
    "Last Updated": "last_updated_date",
}

_SORTABLE_COLUMNS = {
    "title", "agency", "office", "naics_code", "set_aside",
    "fiscal_year", "estimated_value_text", "created_date",
    "last_updated_date", "place_of_performance",
}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_forecast_html(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a rendered forecast HTML page from the Acquisition Gateway.

    Parses forecast rows from the HTML using BeautifulSoup and bulk-inserts
    via PostgreSQL COPY. The HTML must be the fully rendered page (View
    Source after the Angular app loads), not the raw source.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise HTTPException(status_code=500, detail="BeautifulSoup not installed")

    soup = BeautifulSoup(text, "html.parser")
    rows = soup.select(".ag-item.ag-item--set")

    if not rows:
        raise HTTPException(status_code=400, detail="No forecast rows found — ensure this is the fully rendered HTML (View Source after page loads)")

    batch_id = str(uuid.uuid4())
    buf = StringIO()

    db_cols = [
        "title", "description", "source_url",
        "agency", "office", "naics_code", "naics_description",
        "set_aside", "place_of_performance", "period_of_performance",
        "fiscal_year", "estimated_value_text",
        "created_date", "last_updated_date",
        "upload_batch_id",
    ]

    _clean = lambda s: re.sub(r"\s+", " ", (s or "").replace("\\", "\\\\").replace("\t", " ").replace("\n", " ").replace("\r", "")).strip()
    rows_written = 0

    for row in rows:
        # Title + link
        title_el = row.select_one(".ag-header__title a")
        title = _clean(title_el.get_text()) if title_el else ""
        link = title_el.get("href", "") if title_el else ""

        # Description
        desc_el = row.select_one(".ag-body__description")
        description = _clean(desc_el.get_text(" ")) if desc_el else ""

        # Key-value fields
        fields: dict[str, str] = {}
        for display in row.select(".ag-item-additional_content__display"):
            key_el = display.select_one(".ag-body-additional_content__key")
            val_el = display.select_one(".ag-body-additional_content__value")
            if key_el and val_el:
                fields[_clean(key_el.get_text())] = _clean(val_el.get_text(" "))

        # Map to DB columns
        agency = fields.get("Agency", "")
        office = fields.get("Organization/Contracting Office", "")
        set_aside = fields.get("Acquisition Strategy/Type of Set-Aside", "")
        pop = fields.get("Place of Performance", "")
        period = fields.get("Period of Performance", "")
        fy = fields.get("Estimated Award FY", "")
        created = fields.get("Created", "")
        updated = fields.get("Last Updated", "")
        value_text = fields.get("Estimated Contract Value", "")

        # Parse NAICS: "532420\n\nOffice Machinery..." → code + description
        naics_raw = fields.get("NAICS Code", "")
        naics_code = ""
        naics_desc = ""
        if naics_raw:
            parts = naics_raw.split()
            if parts and parts[0].isdigit():
                naics_code = parts[0]
                naics_desc = " ".join(parts[1:])

        # Extract nid from source_url for dedup key
        source_id = ""
        if link:
            m = re.search(r"nid%3D(\d+)", link)
            if m:
                source_id = m.group(1)

        vals = [
            title or "(no title)", description, link,
            agency, office, naics_code, naics_desc,
            set_aside, pop, period,
            fy, value_text,
            created, updated,
            batch_id, source_id,
        ]
        buf.write("\t".join(v.replace("\\", "\\\\").replace("\t", " ") if v else "\\N" for v in vals) + "\n")
        rows_written += 1

    all_cols = db_cols + ["source_id"]
    with tx() as conn:
        with conn.cursor() as cur:
            # COPY into a temp table, then UPSERT to handle dedup
            cur.execute("""
                CREATE TEMP TABLE IF NOT EXISTS _forecast_import
                (LIKE forecast_opportunities INCLUDING DEFAULTS)
                ON COMMIT DROP
            """)
            cur.execute("DELETE FROM _forecast_import")
            buf.seek(0)
            cur.copy_from(buf, "_forecast_import", sep="\t", null="\\N", columns=all_cols)
            # Merge: insert new, skip duplicates
            cur.execute("""
                INSERT INTO forecast_opportunities (
                    title, description, source_url, agency, office,
                    naics_code, naics_description, set_aside,
                    place_of_performance, period_of_performance,
                    estimated_value_text, fiscal_year,
                    created_date, last_updated_date,
                    upload_batch_id, source_id
                )
                SELECT title, description, source_url, agency, office,
                       naics_code, naics_description, set_aside,
                       place_of_performance, period_of_performance,
                       estimated_value_text, fiscal_year,
                       created_date, last_updated_date,
                       upload_batch_id, source_id
                FROM _forecast_import
                ON CONFLICT (source_id) DO NOTHING
            """)
            inserted = cur.rowcount
            cur.execute("SELECT COUNT(*) FROM _forecast_import")
            total_imported = cur.fetchone()[0]
            skipped = total_imported - inserted

    return {
        "batch_id": batch_id,
        "rows_imported": rows_written,
        "rows_inserted": inserted,
        "rows_skipped": skipped,
        "source": file.filename,
    }


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

class ForecastQuery(BaseModel):
    q: str | None = None
    agency: str | None = None
    naics_code: str | None = None
    set_aside: str | None = None
    fiscal_year: str | None = None
    estimated_value_text: str | None = None
    value_under: float | None = None
    value_over: float | None = None
    office: str | None = None
    place_of_performance: str | None = None
    limit: int = 100
    offset: int = 0
    order_by: str = "created_date"
    order_dir: str = "DESC"


@router.post("/query")
def query_forecasts(
    body: ForecastQuery,
    user: dict = Depends(get_current_user),
):
    """Query forecast opportunities with dynamic filters."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            where_parts = []
            params: list[Any] = []

            if body.q and body.q.strip():
                where_parts.append("search_vector @@ plainto_tsquery('english', %s)")
                params.append(body.q.strip())

            # Numeric value filters
            if body.value_under is not None:
                where_parts.append("(estimated_value_high <= %s OR (estimated_value_high IS NULL AND estimated_value_low <= %s))")
                params.extend([body.value_under, body.value_under])
            if body.value_over is not None:
                where_parts.append("estimated_value_low >= %s")
                params.append(body.value_over)

            for col, val, match_type in [
                ("agency", body.agency, "like"),
                ("naics_code", body.naics_code, "exact"),
                ("set_aside", body.set_aside, "like"),
                ("fiscal_year", body.fiscal_year, "exact"),
                ("estimated_value_text", body.estimated_value_text, "like"),
                ("office", body.office, "like"),
                ("place_of_performance", body.place_of_performance, "like"),
            ]:
                if val and val.strip():
                    if match_type == "exact":
                        where_parts.append(f"{col} = %s")
                        params.append(val.strip())
                    else:
                        where_parts.append(f"{col} ILIKE %s")
                        params.append(f"%{val.strip()}%")

            where_clause = ""
            if where_parts:
                where_clause = "WHERE " + " AND ".join(where_parts)

            order_col = body.order_by if body.order_by in _SORTABLE_COLUMNS else "created_date"
            order_dir = "DESC" if body.order_dir.upper() == "DESC" else "ASC"
            limit = min(body.limit, 1000)
            offset = max(body.offset, 0)

            cur.execute(f"SELECT COUNT(*) FROM forecast_opportunities {where_clause}", tuple(params))
            total = cur.fetchone()[0]

            cur.execute(
                f"""SELECT id, title, description, source_url,
                           agency, office, naics_code, naics_description,
                           set_aside, place_of_performance, period_of_performance,
                           fiscal_year, estimated_value_text,
                           estimated_value_low, estimated_value_high,
                           created_date, last_updated_date,
                           upload_batch_id, created_at
                    FROM forecast_opportunities
                    {where_clause}
                    ORDER BY {order_col} {order_dir}
                    LIMIT %s OFFSET %s""",
                tuple(params + [limit, offset]),
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, row)) for row in rows]

            return {"total": total, "limit": limit, "offset": offset, "count": len(results), "results": results}
    finally:
        conn.close()


@router.delete("/all")
def delete_all_forecasts(user: dict = Depends(get_current_user)):
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM forecast_opportunities")
            deleted = cur.rowcount
    return {"deleted": deleted}


@router.delete("/{forecast_id}")
def delete_forecast(forecast_id: int, user: dict = Depends(get_current_user)):
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM forecast_opportunities WHERE id = %s", (forecast_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": forecast_id}
