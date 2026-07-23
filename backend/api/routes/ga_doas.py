"""Vision — GA DOAS Procurement Opportunities API Routes."""

from __future__ import annotations

import csv, io, re, uuid
from io import StringIO
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from auth import get_current_user
from core.db import connect, tx

router = APIRouter(prefix="/api/ga-doas", tags=["ga_doas"])

_SORTABLE_COLUMNS = {"title", "government_entity", "event_id", "start_date", "end_date", "status"}


@router.post("/upload")
async def upload_ga_doas_html(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload rendered GA DOAS HTML table. Parses rows with BeautifulSoup."""
    content = await file.read()
    text = content.decode("utf-8")

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise HTTPException(status_code=500, detail="BeautifulSoup not installed")

    soup = BeautifulSoup(text, "html.parser")
    rows = soup.select("tbody tr")
    if not rows:
        raise HTTPException(status_code=400, detail="No table rows found")

    batch_id = str(uuid.uuid4())
    buf = StringIO()
    db_cols = ["event_id", "event_url", "title", "government_entity", "start_date", "end_date", "ends_in", "status", "source_file", "upload_batch_id"]
    rows_written = 0

    for row in rows:
        cells = row.select("td")
        if len(cells) < 7:
            continue
        eid_el = cells[1].select_one("a")
        event_id = eid_el.get_text(strip=True) if eid_el else cells[1].get_text(strip=True)
        event_url = eid_el.get("href", "") if eid_el else ""
        title = cells[2].get_text(strip=True)
        entity = cells[3].get_text(strip=True)
        start = cells[4].get_text(strip=True)
        end = cells[5].get_text(strip=True)
        ends = cells[6].get_text(strip=True)
        status = cells[7].get_text(strip=True) if len(cells) > 7 else ""

        vals = [
            event_id, event_url, title or "(no title)", entity,
            start, end, ends, status, file.filename, batch_id,
        ]
        buf.write("\t".join(v.replace("\\", "\\\\").replace("\t", " ") if v else "\\N" for v in vals) + "\n")
        rows_written += 1

    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TEMP TABLE IF NOT EXISTS _ga_import
                (LIKE ga_doas_opportunities INCLUDING DEFAULTS) ON COMMIT DROP
            """)
            cur.execute("DELETE FROM _ga_import")
            buf.seek(0)
            cur.copy_from(buf, "_ga_import", sep="\t", null="\\N", columns=db_cols)
            cur.execute("""
                INSERT INTO ga_doas_opportunities (event_id, event_url, title, government_entity, start_date, end_date, ends_in, status, source_file, upload_batch_id)
                SELECT event_id, event_url, title, government_entity, start_date, end_date, ends_in, status, source_file, upload_batch_id
                FROM _ga_import
                ON CONFLICT (event_id) DO UPDATE SET
                    title = EXCLUDED.title, government_entity = EXCLUDED.government_entity,
                    end_date = EXCLUDED.end_date, status = EXCLUDED.status
            """)
            inserted = cur.rowcount

    return {"batch_id": batch_id, "rows_imported": rows_written, "rows_inserted": inserted, "source": file.filename}


class GaDoasQuery(BaseModel):
    q: str | None = None
    government_entity: str | None = None
    event_id: str | None = None
    status: str | None = None
    limit: int = 100
    offset: int = 0
    order_by: str = "end_date"
    order_dir: str = "ASC"


@router.post("/query")
def query_ga_doas(body: GaDoasQuery, user: dict = Depends(get_current_user)):
    conn = connect()
    try:
        with conn.cursor() as cur:
            where_parts = []
            params: list[Any] = []

            if body.q and body.q.strip():
                words = body.q.strip().split()
                if len(words) == 1:
                    where_parts.append("search_vector @@ plainto_tsquery('english', %s)")
                    params.append(words[0])
                else:
                    or_expr = " || ".join(["plainto_tsquery('english', %s)"] * len(words))
                    where_parts.append(f"search_vector @@ ({or_expr})")
                    params.extend(words)

            for col, val, match in [("government_entity", body.government_entity, "like"), ("event_id", body.event_id, "exact"), ("status", body.status, "exact")]:
                if val and val.strip():
                    where_parts.append(f"{col} {'ILIKE' if match == 'like' else '='} %s")
                    params.append(f"%{val.strip()}%" if match == "like" else val.strip())

            where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""
            order_col = body.order_by if body.order_by in _SORTABLE_COLUMNS else "end_date"
            order_dir = "ASC" if body.order_dir.upper() == "ASC" else "DESC"
            limit = min(body.limit, 1000)
            offset = max(body.offset, 0)

            cur.execute(f"SELECT COUNT(*) FROM ga_doas_opportunities {where_clause}", tuple(params))
            total = cur.fetchone()[0]
            cur.execute(f"SELECT * FROM ga_doas_opportunities {where_clause} ORDER BY {order_col} {order_dir} LIMIT %s OFFSET %s", tuple(params + [limit, offset]))
            rows = cur.fetchall()
            columns = [d[0] for d in cur.description]
            return {"total": total, "limit": limit, "offset": offset, "count": len(rows), "results": [dict(zip(columns, r)) for r in rows]}
    finally:
        conn.close()


@router.delete("/all")
def delete_all(user: dict = Depends(get_current_user)):
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ga_doas_opportunities")
            return {"deleted": cur.rowcount}
