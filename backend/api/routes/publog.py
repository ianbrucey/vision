"""Vision — Publog FLIS Query API.

Public query endpoint for the FLIS database tables loaded from the
DLA Publog DVD. Auth via API key in query string.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core.db import connect

router = APIRouter(prefix="/api/publog", tags=["publog"])

# ---------------------------------------------------------------------------
# API key — server-side constant (rotate via env var in production)
# ---------------------------------------------------------------------------
_API_KEY = os.environ.get(
    "PUBLOG_API_KEY",
    "jq_vision_8f3a1c9d2e7b4056a1f8c3d9e2b7a041c8f3e9d1a2b7c4059f1e8d3a7c2b9014",
)

# ---------------------------------------------------------------------------
# Table allowlist — string → schema.table (never interpolate raw params)
# ---------------------------------------------------------------------------
_TABLE_MAP: dict[str, str] = {
    # User-facing name          →  Actual schema-qualified table
    "P_FLIS_NSN":                 "vision.publog_flis_nsn",
    "V_FLIS_MANAGEMENT":          "vision.publog_flis_management",
    "V_FLIS_IDENTIFICATION":      "vision.publog_flis_identification",
    "V_MOE_RULE":                 "vision.publog_moe_rule",
    "P_CAGE":                     "vision.publog_cage",
    "V_FLIS_PART":                "vision.publog_flis_part",
    "P_PART_PICK":                "vision.publog_flis_part",
}

# ---------------------------------------------------------------------------
# Column allowlist — allowed filter params per table
# Mapping: filter_name → (db_column, operator)
#   operator: 'exact' (=) or 'like' (ILIKE %…%)
# ---------------------------------------------------------------------------
_COLUMN_MAP: dict[str, dict[str, tuple[str, str]]] = {
    "P_FLIS_NSN": {
        "fsc":       ("fsc", "exact"),
        "niin":      ("niin", "exact"),
        "inc":       ("inc", "exact"),
        "item_name": ("item_name", "like"),
    },
    "V_FLIS_MANAGEMENT": {
        "niin":      ("niin", "exact"),
        "moe":       ("moe", "exact"),
        "aac":       ("aac", "exact"),
        "sos":       ("sos", "exact"),
        "usc":       ("usc", "exact"),
    },
    "V_FLIS_IDENTIFICATION": {
        "niin":      ("niin", "exact"),
        "dmil":      ("dmil", "exact"),
        "hmic":      ("hmic", "exact"),
        "crit_cd":   ("crit_cd", "exact"),
        "inc":       ("inc", "exact"),
    },
    "V_MOE_RULE": {
        "niin":      ("niin", "exact"),
        "amc":       ("amc", "exact"),
        "amsc":      ("amsc", "exact"),
        "aac":       ("aac", "exact"),
        "moe_cd":    ("moe_cd", "exact"),
    },
    "P_CAGE": {
        "cage_code": ("cage_code", "exact"),
        "company":   ("company", "like"),
        "state_province": ("state_province", "exact"),
        "country":   ("country", "exact"),
    },
    "V_FLIS_PART": {
        "niin":        ("niin", "exact"),
        "part_number": ("part_number", "like"),
        "cage_code":   ("cage_code", "exact"),
        "rncc":        ("rncc", "exact"),
        "rnvc":        ("rnvc", "exact"),
    },
    "P_PART_PICK": {
        "niin":        ("niin", "exact"),
        "part_number": ("part_number", "like"),
        "cage_code":   ("cage_code", "exact"),
    },
}

# All tables also support a full-text `q` param that searches item_name
_TABLES_WITH_FTS = {"P_FLIS_NSN", "P_PART_PICK", "V_FLIS_PART", "P_CAGE"}


@router.get("/query")
def publog_query(
    table: str = Query(..., description="Table name: P_FLIS_NSN, V_FLIS_MANAGEMENT, etc."),
    key: str = Query(..., description="API key"),
    # Filters — any column from the table's allowlist
    fsc: str | None = Query(None),
    niin: str | None = Query(None),
    inc: str | None = Query(None),
    item_name: str | None = Query(None),
    moe: str | None = Query(None),
    aac: str | None = Query(None),
    sos: str | None = Query(None),
    usc: str | None = Query(None),
    dmil: str | None = Query(None),
    hmic: str | None = Query(None),
    crit_cd: str | None = Query(None),
    amc: str | None = Query(None),
    amsc: str | None = Query(None),
    moe_cd: str | None = Query(None),
    cage_code: str | None = Query(None),
    company: str | None = Query(None),
    state_province: str | None = Query(None),
    country: str | None = Query(None),
    part_number: str | None = Query(None),
    rncc: str | None = Query(None),
    rnvc: str | None = Query(None),
    q: str | None = Query(None, description="Full-text search on item name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Query a Publog FLIS table with optional filters.

    Auth: API key in query string.
    Tables: P_FLIS_NSN, V_FLIS_MANAGEMENT, V_FLIS_IDENTIFICATION,
            V_MOE_RULE, P_CAGE, V_FLIS_PART, P_PART_PICK.
    Max 200 rows per request.
    """
    # --- 1. Auth check (fail closed, first) ---
    if key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # --- 2. Table allowlist check ---
    db_table = _TABLE_MAP.get(table)
    if db_table is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown table '{table}'. Allowed: {', '.join(sorted(_TABLE_MAP.keys()))}",
        )

    # --- 3. Build filters from allowed columns ---
    col_allowlist = _COLUMN_MAP.get(table, {})
    filters: list[str] = []
    params: list[Any] = []

    # Collect all user-supplied filter values
    raw_filters = {
        "fsc": fsc, "niin": niin, "inc": inc, "item_name": item_name,
        "moe": moe, "aac": aac, "sos": sos, "usc": usc,
        "dmil": dmil, "hmic": hmic, "crit_cd": crit_cd,
        "amc": amc, "amsc": amsc, "moe_cd": moe_cd,
        "cage_code": cage_code, "company": company,
        "state_province": state_province, "country": country,
        "part_number": part_number, "rncc": rncc, "rnvc": rnvc,
    }

    for filter_name, value in raw_filters.items():
        if value is None or not value.strip():
            continue
        # Only allow filters defined for this table
        if filter_name not in col_allowlist:
            continue
        db_col, op = col_allowlist[filter_name]
        if op == "exact":
            filters.append(f"{db_col} = %s")
            params.append(value.strip())
        elif op == "like":
            filters.append(f"{db_col} ILIKE %s")
            params.append(f"%{value.strip()}%")

    # --- 4. Full-text search (q param) ---
    if q and q.strip() and table in _TABLES_WITH_FTS:
        fts_col = "item_name"
        if table == "P_CAGE":
            fts_col = "company"
        filters.append(
            f"to_tsvector('english', coalesce({fts_col}, '')) "
            f"@@ plainto_tsquery('english', %s)"
        )
        params.append(q.strip())

    # --- 5. Execute ---
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    conn = connect()
    try:
        with conn.cursor() as cur:
            # Count
            cur.execute(f"SELECT COUNT(*) FROM {db_table} {where}", tuple(params))
            total = cur.fetchone()[0]

            # Fetch
            cur.execute(
                f"SELECT * FROM {db_table} {where} LIMIT %s OFFSET %s",
                tuple(params + [limit, offset]),
            )
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
    finally:
        conn.close()

    return {
        "table": table,
        "count": len(rows),
        "total": total,
        "limit": limit,
        "offset": offset,
        "rows": [dict(zip(cols, row)) for row in rows],
    }
