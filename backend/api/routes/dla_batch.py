"""Vision — DLA Batch Search API Routes.

Query the enriched DIBBS solicitation data produced by the dibbs-enrich skill.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_current_user
from core.db import connect

router = APIRouter(prefix="/api/dla-batch", tags=["dla-batch"])

_SORTABLE = {
    "nsn", "nomenclature", "fsc", "amc", "competable", "unit_price",
    "vendor_name", "solicitation", "qty", "source_file",
}

# Allowed filter columns and their types
_FILTERS: dict[str, str] = {
    "fsc": "exact",
    "amc": "exact",
    "competable": "exact",
    "vendor_name": "like",
    "nomenclature": "like",
    "cage_company": "like",
    "contact_email": "exact",
    "source_file": "exact",
}


@router.get("/query")
def query_dla_batch(
    q: str | None = Query(None, description="Full-text search"),
    fsc: str | None = Query(None),
    amc: str | None = Query(None),
    competable: str | None = Query(None),
    vendor_name: str | None = Query(None),
    nomenclature: str | None = Query(None),
    cage_company: str | None = Query(None),
    contact_email: str | None = Query(None),
    source_file: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order_by: str = Query("unit_price", description="Sort column"),
    order_dir: str = Query("DESC", description="Sort direction"),
    user: dict = Depends(get_current_user),
):
    """Search and filter the enriched DLA batch data."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            where: list[str] = []
            params: list[Any] = []

            # Full-text search
            if q and q.strip():
                w = q.strip().split()
                if len(w) == 1:
                    where.append("search_vector @@ plainto_tsquery('english', %s)")
                    params.append(w[0])
                else:
                    parts = " || ".join(["plainto_tsquery('english', %s)"] * len(w))
                    where.append(f"search_vector @@ ({parts})")
                    params.extend(w)

            # Column filters
            raw_filters = {
                "fsc": fsc, "amc": amc, "competable": competable,
                "vendor_name": vendor_name, "nomenclature": nomenclature,
                "cage_company": cage_company, "contact_email": contact_email,
                "source_file": source_file,
            }
            for col, value in raw_filters.items():
                if not value or not value.strip():
                    continue
                op = _FILTERS.get(col, "exact")
                if op == "exact":
                    where.append(f"{col} = %s")
                    params.append(value.strip())
                else:
                    where.append(f"{col} ILIKE %s")
                    params.append(f"%{value.strip()}%")

            wc = "WHERE " + " AND ".join(where) if where else ""
            oc = order_by if order_by in _SORTABLE else "unit_price"
            od = "DESC" if order_dir.upper() == "DESC" else "ASC"
            lim = min(limit, 200)
            off = max(offset, 0)

            cur.execute(f"SELECT COUNT(*) FROM vision.dla_batch_search {wc}", tuple(params))
            total = cur.fetchone()[0]

            cur.execute(
                f"SELECT * FROM vision.dla_batch_search {wc} ORDER BY {oc} {od} NULLS LAST LIMIT %s OFFSET %s",
                tuple(params + [lim, off]),
            )
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]

    finally:
        conn.close()

    return {
        "total": total,
        "limit": lim,
        "offset": off,
        "count": len(rows),
        "results": [dict(zip(cols, r)) for r in rows],
    }


@router.get("/stats")
def dla_batch_stats(user: dict = Depends(get_current_user)):
    """Summary statistics for the batch search data."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE competable = 'true') AS competable,
                    COUNT(*) FILTER (WHERE vendor_name IS NOT NULL AND vendor_name != '') AS with_vendor,
                    COUNT(*) FILTER (WHERE contact_email IS NOT NULL AND contact_email != '') AS with_email,
                    COUNT(*) FILTER (WHERE unit_price IS NOT NULL) AS priced,
                    COUNT(DISTINCT nsn) AS unique_nsns,
                    COUNT(DISTINCT solicitation) FILTER (WHERE solicitation != '') AS unique_sols
                FROM vision.dla_batch_search
            """)
            row = cur.fetchone()
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
    finally:
        conn.close()
