"""
Vision — Saved Reports API Routes.

CRUD for saved filter presets used by the Forecasts and Sam Notices views.
A report stores query_filters as JSONB — the exact object passed to the
existing query tools. No transformation needed.

Reports are case-agnostic by default (case_id is optional). When saved from
within a case, the case_id is stored for scoping; when saved from the global
Reference Desk, case_id is NULL.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_user
from core.db import connect, tx

router = APIRouter(prefix="/api/reports", tags=["reports"])

_DATA_SOURCES = {"forecasts", "sam_notices"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateReportRequest(BaseModel):
    name: str
    data_source: str
    query_filters: dict
    case_id: int | None = None
    sort_by: str | None = None
    sort_dir: str | None = "ASC"


class UpdateReportRequest(BaseModel):
    name: str | None = None
    query_filters: dict | None = None
    sort_by: str | None = None
    sort_dir: str | None = None


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("")
def list_reports(
    case_id: int | None = Query(None, description="Case ID (omit for global reports)"),
    data_source: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    """List saved reports — optionally scoped to a case or data_source."""
    if data_source and data_source not in _DATA_SOURCES:
        raise HTTPException(status_code=400, detail=f"data_source must be one of {sorted(_DATA_SOURCES)}")

    conn = connect()
    try:
        with conn.cursor() as cur:
            clauses = []
            params: list[Any] = []

            if case_id is not None:
                clauses.append("case_id = %s")
                params.append(case_id)
            else:
                clauses.append("case_id IS NULL")

            if data_source:
                clauses.append("data_source = %s")
                params.append(data_source)

            where = " AND ".join(clauses) if clauses else "TRUE"
            cur.execute(
                f"""SELECT id, case_id, name, data_source, query_filters,
                           sort_by, sort_dir, created_by, created_at, updated_at
                    FROM saved_reports
                    WHERE {where}
                    ORDER BY updated_at DESC""",
                tuple(params),
            )
            rows = cur.fetchall()
            columns = [d[0] for d in cur.description]
    finally:
        conn.close()

    return {"reports": [dict(zip(columns, r)) for r in rows]}


@router.post("", status_code=201)
def create_report(
    body: CreateReportRequest,
    user: dict = Depends(get_current_user),
):
    """Save a new report filter preset."""
    if body.data_source not in _DATA_SOURCES:
        raise HTTPException(status_code=400, detail=f"data_source must be one of {sorted(_DATA_SOURCES)}")

    import json

    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO saved_reports (case_id, name, data_source, query_filters, sort_by, sort_dir)
                   VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                   RETURNING *""",
                (
                    body.case_id, body.name.strip(), body.data_source,
                    json.dumps(body.query_filters),
                    body.sort_by, body.sort_dir or "ASC",
                ),
            )
            row = cur.fetchone()
            columns = [d[0] for d in cur.description]
    return {"report": dict(zip(columns, row))}


@router.get("/{report_id}")
def get_report(
    report_id: int,
    user: dict = Depends(get_current_user),
):
    """Get a single report definition."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM saved_reports WHERE id = %s", (report_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Report not found")
            columns = [d[0] for d in cur.description]
    finally:
        conn.close()
    return {"report": dict(zip(columns, row))}


@router.patch("/{report_id}")
def update_report(
    report_id: int,
    body: UpdateReportRequest,
    user: dict = Depends(get_current_user),
):
    """Update a report's name or filters."""
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM saved_reports WHERE id = %s", (report_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Report not found")

            sets = []
            params: list[Any] = []
            if body.name is not None:
                sets.append("name = %s")
                params.append(body.name.strip())
            if body.query_filters is not None:
                sets.append("query_filters = %s::jsonb")
                params.append(__import__("json").dumps(body.query_filters))
            if body.sort_by is not None:
                sets.append("sort_by = %s")
                params.append(body.sort_by)
            if body.sort_dir is not None:
                if body.sort_dir not in ("ASC", "DESC"):
                    raise HTTPException(status_code=400, detail="sort_dir must be ASC or DESC")
                sets.append("sort_dir = %s")
                params.append(body.sort_dir)

            if not sets:
                raise HTTPException(status_code=400, detail="No fields to update")

            sets.append("updated_at = now()")
            params.append(report_id)

            cur.execute(
                f"UPDATE saved_reports SET {', '.join(sets)} WHERE id = %s RETURNING *",
                tuple(params),
            )
            row = cur.fetchone()
            columns = [d[0] for d in cur.description]
    return {"report": dict(zip(columns, row))}


@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    user: dict = Depends(get_current_user),
):
    """Delete a saved report."""
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM saved_reports WHERE id = %s", (report_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Report not found")
    return {"deleted": report_id}
