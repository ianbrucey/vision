"""
Vision — Subcontracting Leads API Routes.

Upload USASpending.gov Prime Award Summaries CSV exports and query
the resulting subcontracting lead list. The upload applies business
filters during import — only plan F/G vehicles in target NAICS
families with active ordering periods are inserted.

POST /api/subcontracting-leads/upload     — upload + filter CSV
POST /api/subcontracting-leads/query      — query leads
POST /api/subcontracting-leads/process-pools — compute pool groupings
GET  /api/subcontracting-leads/{id}       — get single lead
POST /api/subcontracting-leads/{id}/triage — update triage/priority
"""

from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from auth import get_current_user
from core.db import connect, tx

router = APIRouter(
    prefix="/api/subcontracting-leads",
    tags=["subcontracting_leads"],
)

# ---------------------------------------------------------------------------
# CSV column → DB column mapping
# ---------------------------------------------------------------------------

_CSV_COLUMN_MAP = {
    "award_id_piid": "award_id_piid",
    "parent_award_id_piid": "parent_award_id_piid",
    "solicitation_identifier": "solicitation_identifier",
    "idv_type": "idv_type",
    "multiple_or_single_award_idv": "multiple_or_single_award",
    "recipient_uei": "recipient_uei",
    "recipient_name": "recipient_name",
    "recipient_parent_name": "recipient_parent_name",
    "recipient_city_name": "recipient_city",
    "recipient_state_code": "recipient_state",
    "naics_code": "naics_code",
    "naics_description": "naics_description",
    "product_or_service_code": "psc_code",
    "product_or_service_code_description": "psc_description",
    "potential_total_value_of_award": "potential_value",
    "current_total_value_of_award": "current_value",
    "award_base_action_date": "base_action_date",
    "ordering_period_end_date": "ordering_period_end",
    "period_of_performance_current_end_date": "pop_current_end",
    "period_of_performance_potential_end_date": "pop_potential_end",
    "subcontracting_plan_code": "subcontracting_plan_code",
    "subcontracting_plan": "subcontracting_plan",
    "awarding_agency_name": "awarding_agency",
    "awarding_sub_agency_name": "awarding_sub_agency",
    "type_of_set_aside": "set_aside_type",
    "woman_owned_business": "is_woman_owned",
    "service_disabled_veteran_owned_business": "is_sdvosb",
    "historically_underutilized_business_zone_hubzone_firm": "is_hubzone",
    "c8a_program_participant": "is_8a",
    "small_disadvantaged_business": "is_small_disadvantaged",
    "minority_owned_business": "is_minority_owned",
    "usaspending_permalink": "usaspending_permalink",
}

# ---------------------------------------------------------------------------
# Filter constants
# ---------------------------------------------------------------------------

# Target NAICS families (numeric prefixes)
_TARGET_NAICS_PREFIXES = (
    "236", "237", "238",   # Construction
    "5415",                 # IT Services
    "5112", "5182",         # Software / Data Hosting
    "5612",                 # Facilities Support
    "5616",                 # Security
    "5617",                 # Janitorial / Landscaping
    "562",                  # Waste / Remediation
)

# Required plan codes
_REQUIRED_PLAN_CODES = {"F", "G"}

# Today for date comparisons
_TODAY = date.today().isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify_category(naics_code: str | None) -> str:
    """Tag a NAICS code into a pipeline category."""
    if not naics_code:
        return "other"
    nc = naics_code.strip()
    if nc[:3] in ("236", "237", "238"):
        return "construction"
    if nc[:4] == "5415":
        return "it"
    if nc[:4] == "5112" or nc[:4] == "5182":
        return "it"
    if nc[:4] == "5612":
        return "facilities"
    if nc[:4] in ("5616", "5617"):
        return "facilities"
    if nc[:3] == "562":
        return "facilities"
    return "other"


def _compute_priority_score(
    plan_code: str,
    category: str,
    potential_value_raw: str | None,
    ordering_period_end: str | None,
) -> int:
    """Compute an initial priority score (0–70 before pool enrichment).

    Pool membership adds up to +20 in a separate post-import pass.
    Active SAM solicitations (enrichment) adds up to +10 later.
    """
    score = 0

    # Plan type
    if plan_code == "F":
        score += 30
    elif plan_code == "G":
        score += 15

    # Category — construction is our primary wedge
    if category == "construction":
        score += 10
    elif category in ("facilities", "it"):
        score += 5

    # Value
    try:
        val = float(potential_value_raw or "0")
    except (ValueError, TypeError):
        val = 0
    if val > 1_000_000_000:
        score += 10
    elif val > 100_000_000:
        score += 7
    elif val > 10_000_000:
        score += 3

    # Runway
    if ordering_period_end and ordering_period_end.strip():
        if ordering_period_end > "2028-12-31":
            score += 10
        elif ordering_period_end > "2027-12-31":
            score += 5

    return score


def _priority_label(score: int) -> str:
    if score >= 40:
        return "high"
    if score >= 20:
        return "medium"
    return "low"


def _parse_bool(val: str | None) -> bool | None:
    """Parse a USASpending boolean string."""
    if not val or not val.strip():
        return None
    v = val.strip().lower()
    return v in ("true", "yes", "1", "t", "y")


def _parse_date(val: str | None) -> str | None:
    """Normalize a date string to YYYY-MM-DD or return None."""
    if not val or not val.strip():
        return None
    v = val.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _parse_numeric(val: str | None) -> float | None:
    """Parse a numeric string, handling currency formats."""
    if not val or not val.strip():
        return None
    v = val.strip().replace("$", "").replace(",", "")
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class QueryLeadsRequest(BaseModel):
    pipeline_status: str | None = None
    pipeline_category: str | None = None
    pipeline_priority: str | None = None
    naics_code: str | None = None
    subcontracting_plan_code: str | None = None
    recipient_uei: str | None = None
    recipient_name: str | None = None
    q: str | None = None              # Full-text on recipient_name
    limit: int = 100
    offset: int = 0
    order_by: str = "pipeline_priority_score"
    order_dir: str = "DESC"


class UpdateTriageRequest(BaseModel):
    pipeline_priority: str | None = None
    pipeline_priority_score: int | None = None
    pipeline_notes: str | None = None
    pipeline_status: str | None = None


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@router.post("/upload")
async def upload_subcontracting_leads_csv(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a USASpending.gov Prime Award Summaries CSV.

    Streams the file to avoid loading the entire CSV into memory.
    Processes in batches of 2000 rows, committing each batch in its
    own transaction. Handles 136K+ row files safely.

    Filters are applied during import — only IDV vehicles with
    plan F or G, in target NAICS families, with active ordering
    periods are inserted. The dedup key is (award_id_piid, recipient_uei).
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    # Stream the file — don't load all 232MB into memory.
    # file.file is a SpooledTemporaryFile; wrap for text reading.
    await file.seek(0)
    text_stream = io.TextIOWrapper(file.file, encoding="utf-8-sig")

    reader = csv.DictReader(text_stream)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no headers")

    # Build column index from CSV headers
    csv_headers_lower = {h.strip().lower(): h for h in reader.fieldnames}
    col_index: dict[str, str] = {}
    for csv_header_lower, db_col in _CSV_COLUMN_MAP.items():
        if csv_header_lower in csv_headers_lower:
            col_index[db_col] = csv_headers_lower[csv_header_lower]

    batch_id = str(uuid.uuid4())
    today_str = _TODAY

    stats = {
        "batch_id": batch_id,
        "source": file.filename,
        "total_rows": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "skipped_breakdown": {
            "not_idv": 0,
            "no_plan": 0,
            "not_active": 0,
            "wrong_naics": 0,
            "invalid_key": 0,
        },
        "errors": [],
    }

    batch = []
    BATCH_SIZE = 2000

    for row in reader:
        stats["total_rows"] += 1

        try:
            # -- Filter gates --

            # Gate 1: IDV check
            idv_flag = (row.get("award_or_idv_flag") or "").strip()
            if idv_flag and idv_flag != "IDV":
                stats["skipped"] += 1
                stats["skipped_breakdown"]["not_idv"] += 1
                continue

            # Gate 2: Plan F or G
            plan_code = (row.get("subcontracting_plan_code") or "").strip()
            if plan_code not in _REQUIRED_PLAN_CODES:
                stats["skipped"] += 1
                stats["skipped_breakdown"]["no_plan"] += 1
                continue

            # Gate 3: Active ordering period
            ordering_end = (row.get("ordering_period_end_date") or "").strip()
            if ordering_end and ordering_end < today_str:
                stats["skipped"] += 1
                stats["skipped_breakdown"]["not_active"] += 1
                continue

            # Gate 4: Target NAICS
            naics_code = (row.get("naics_code") or "").strip()
            if not naics_code or not any(
                naics_code.startswith(p) for p in _TARGET_NAICS_PREFIXES
            ):
                stats["skipped"] += 1
                stats["skipped_breakdown"]["wrong_naics"] += 1
                continue

            # Gate 5: Valid keys
            piid = (row.get("award_id_piid") or "").strip()
            uei = (row.get("recipient_uei") or "").strip()
            if not piid or not uei:
                stats["skipped"] += 1
                stats["skipped_breakdown"]["invalid_key"] += 1
                continue

            # -- All gates passed --

            category = _classify_category(naics_code)
            raw_value = row.get("potential_total_value_of_award") or ""
            priority_score = _compute_priority_score(
                plan_code, category, raw_value, ordering_end
            )
            priority = _priority_label(priority_score)

            vals = _build_row_values(
                row, col_index, batch_id, file.filename,
                category, priority, priority_score,
            )
            batch.append(vals)

            if len(batch) >= BATCH_SIZE:
                inserted, updated = _flush_and_commit(batch)
                stats["inserted"] += inserted
                stats["updated"] += updated
                batch = []

        except Exception as exc:
            stats["errors"].append({
                "row": stats["total_rows"],
                "piid": (row.get("award_id_piid") or "").strip(),
                "error": str(exc),
            })

    # Flush remaining
    if batch:
        try:
            inserted, updated = _flush_and_commit(batch)
            stats["inserted"] += inserted
            stats["updated"] += updated
        except Exception as exc:
            stats["errors"].append({
                "row": "final_batch",
                "error": str(exc),
            })

    return stats


def _flush_and_commit(batch: list[tuple]) -> tuple[int, int]:
    """INSERT a batch in its own transaction and return (inserted, updated)."""
    with tx() as conn:
        with conn.cursor() as cur:
            return _flush_batch(cur, batch)



def _build_row_values(
    row: dict,
    col_index: dict[str, str],
    batch_id: str,
    source_csv: str,
    category: str,
    priority: str,
    priority_score: int,
) -> tuple:
    """Build a tuple of values for INSERT from a CSV row."""

    def _get(db_col: str, default: Any = "") -> str:
        csv_header = col_index.get(db_col)
        if not csv_header:
            return default if default != "" else None
        return (row.get(csv_header) or "").strip() or default

    is_woman = _parse_bool(_get("is_woman_owned"))
    is_sdvosb = _parse_bool(_get("is_sdvosb"))
    is_hubzone = _parse_bool(_get("is_hubzone"))
    is_8a = _parse_bool(_get("is_8a"))
    is_sdadb = _parse_bool(_get("is_small_disadvantaged"))
    is_minority = _parse_bool(_get("is_minority_owned"))

    return (
        _get("award_id_piid"),
        _get("parent_award_id_piid") or None,
        _get("solicitation_identifier") or None,
        _get("idv_type") or None,
        _get("multiple_or_single_award") or None,
        _get("recipient_uei"),
        _get("recipient_name"),
        _get("recipient_parent_name") or None,
        _get("recipient_city") or None,
        _get("recipient_state") or None,
        _get("naics_code") or None,
        _get("naics_description") or None,
        _get("psc_code") or None,
        _get("psc_description") or None,
        _parse_numeric(row.get(col_index.get("potential_value", "")) if col_index.get("potential_value") else None),
        _parse_numeric(row.get(col_index.get("current_value", "")) if col_index.get("current_value") else None),
        _parse_date(_get("base_action_date")),
        _parse_date(_get("ordering_period_end")),
        _parse_date(_get("pop_current_end")),
        _parse_date(_get("pop_potential_end")),
        _get("subcontracting_plan_code") or None,
        _get("subcontracting_plan") or None,
        _get("awarding_agency") or None,
        _get("awarding_sub_agency") or None,
        _get("set_aside_type") or None,
        is_woman,
        is_sdvosb,
        is_hubzone,
        is_8a,
        is_sdadb,
        is_minority,
        category,
        priority,
        priority_score,
        batch_id,
        source_csv,
        _get("usaspending_permalink") or None,
    )


def _flush_batch(cur, batch: list[tuple]) -> tuple[int, int]:
    """INSERT batch with ON CONFLICT UPDATE. Returns (inserted, updated)."""
    from psycopg2.extras import execute_values

    inserted = 0
    updated = 0

    execute_values(
        cur,
        """INSERT INTO subcontracting_leads (
               award_id_piid, parent_award_id_piid, solicitation_identifier,
               idv_type, multiple_or_single_award,
               recipient_uei, recipient_name, recipient_parent_name,
               recipient_city, recipient_state,
               naics_code, naics_description, psc_code, psc_description,
               potential_value, current_value,
               base_action_date, ordering_period_end, pop_current_end, pop_potential_end,
               subcontracting_plan_code, subcontracting_plan,
               awarding_agency, awarding_sub_agency, set_aside_type,
               is_woman_owned, is_sdvosb, is_hubzone, is_8a,
               is_small_disadvantaged, is_minority_owned,
               pipeline_category, pipeline_priority, pipeline_priority_score,
               upload_batch_id, source_csv, usaspending_permalink
           ) VALUES %s
           ON CONFLICT (award_id_piid, recipient_uei) DO UPDATE SET
               parent_award_id_piid = EXCLUDED.parent_award_id_piid,
               solicitation_identifier = EXCLUDED.solicitation_identifier,
               idv_type = EXCLUDED.idv_type,
               multiple_or_single_award = EXCLUDED.multiple_or_single_award,
               recipient_name = EXCLUDED.recipient_name,
               recipient_parent_name = EXCLUDED.recipient_parent_name,
               recipient_city = EXCLUDED.recipient_city,
               recipient_state = EXCLUDED.recipient_state,
               naics_code = EXCLUDED.naics_code,
               naics_description = EXCLUDED.naics_description,
               psc_code = EXCLUDED.psc_code,
               psc_description = EXCLUDED.psc_description,
               potential_value = EXCLUDED.potential_value,
               current_value = EXCLUDED.current_value,
               base_action_date = EXCLUDED.base_action_date,
               ordering_period_end = EXCLUDED.ordering_period_end,
               pop_current_end = EXCLUDED.pop_current_end,
               pop_potential_end = EXCLUDED.pop_potential_end,
               subcontracting_plan_code = EXCLUDED.subcontracting_plan_code,
               subcontracting_plan = EXCLUDED.subcontracting_plan,
               awarding_agency = EXCLUDED.awarding_agency,
               awarding_sub_agency = EXCLUDED.awarding_sub_agency,
               set_aside_type = EXCLUDED.set_aside_type,
               is_woman_owned = EXCLUDED.is_woman_owned,
               is_sdvosb = EXCLUDED.is_sdvosb,
               is_hubzone = EXCLUDED.is_hubzone,
               is_8a = EXCLUDED.is_8a,
               is_small_disadvantaged = EXCLUDED.is_small_disadvantaged,
               is_minority_owned = EXCLUDED.is_minority_owned,
               pipeline_category = EXCLUDED.pipeline_category,
               pipeline_priority = EXCLUDED.pipeline_priority,
               pipeline_priority_score = EXCLUDED.pipeline_priority_score,
               upload_batch_id = EXCLUDED.upload_batch_id,
               source_csv = EXCLUDED.source_csv,
               usaspending_permalink = EXCLUDED.usaspending_permalink,
               updated_at = now()""",
        batch,
        template=None,
        page_size=len(batch),
    )

    # execute_values doesn't easily return xmax-style counts.
    # For now we treat all as inserted (ON CONFLICT handles the rest).
    # A more precise approach would use RETURNING with a marker.
    return len(batch), 0


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


@router.post("/query")
def query_subcontracting_leads(
    body: QueryLeadsRequest,
    user: dict = Depends(get_current_user),
):
    """Query subcontracting leads with dynamic filters."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            where_parts = []
            params: list[Any] = []

            _str_filters = [
                ("pipeline_status", body.pipeline_status, "exact"),
                ("pipeline_category", body.pipeline_category, "exact"),
                ("pipeline_priority", body.pipeline_priority, "exact"),
                ("naics_code", body.naics_code, "exact"),
                ("subcontracting_plan_code", body.subcontracting_plan_code, "exact"),
                ("recipient_uei", body.recipient_uei, "exact"),
            ]
            for col, val, match_type in _str_filters:
                if val and val.strip():
                    where_parts.append(f"{col} = %s")
                    params.append(val.strip())

            if body.recipient_name and body.recipient_name.strip():
                where_parts.append("recipient_name ILIKE %s")
                params.append(f"%{body.recipient_name.strip()}%")

            if body.q and body.q.strip():
                where_parts.append(
                    "(recipient_name ILIKE %s OR naics_description ILIKE %s "
                    "OR awarding_agency ILIKE %s)"
                )
                q = f"%{body.q.strip()}%"
                params.extend([q, q, q])

            where_clause = ""
            if where_parts:
                where_clause = "WHERE " + " AND ".join(where_parts)

            # Ordering
            allowed_order = {
                "pipeline_priority_score", "potential_value",
                "ordering_period_end", "recipient_name",
                "created_at", "updated_at", "pipeline_category",
            }
            order_col = body.order_by if body.order_by in allowed_order else "pipeline_priority_score"
            order_dir = "DESC" if body.order_dir.upper() == "DESC" else "ASC"

            # Count
            cur.execute(
                f"SELECT COUNT(*) FROM subcontracting_leads {where_clause}",
                tuple(params),
            )
            total = cur.fetchone()[0]

            # Fetch
            limit = min(body.limit, 1000)
            offset = max(body.offset, 0)
            cur.execute(
                f"""SELECT id, external_id, award_id_piid, solicitation_identifier,
                           idv_type, multiple_or_single_award,
                           recipient_uei, recipient_name, recipient_parent_name,
                           recipient_city, recipient_state,
                           naics_code, naics_description, psc_code, psc_description,
                           potential_value, current_value,
                           base_action_date, ordering_period_end,
                           pop_current_end, pop_potential_end,
                           subcontracting_plan_code, subcontracting_plan,
                           awarding_agency, awarding_sub_agency, set_aside_type,
                           pool_id, pool_awardee_count,
                           is_woman_owned, is_sdvosb, is_hubzone, is_8a,
                           is_small_disadvantaged, is_minority_owned,
                           pipeline_status, pipeline_category, pipeline_priority,
                           pipeline_priority_score, pipeline_notes,
                           outreach_status, outreach_last_contact,
                           usaspending_permalink,
                           upload_batch_id, source_csv, created_at, updated_at
                    FROM subcontracting_leads
                    {where_clause}
                    ORDER BY {order_col} {order_dir}
                    LIMIT %s OFFSET %s""",
                tuple(params + [limit, offset]),
            )
            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, row)) for row in cur.fetchall()]

            # Serialize dates
            for r in results:
                for k in list(r.keys()):
                    if isinstance(r[k], (date, datetime)):
                        r[k] = r[k].isoformat()

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "count": len(results),
                "results": results,
            }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Single lead
# ---------------------------------------------------------------------------


@router.get("/{lead_id}")
def get_subcontracting_lead(
    lead_id: int,
    user: dict = Depends(get_current_user),
):
    """Get a single subcontracting lead by ID."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, external_id, award_id_piid, solicitation_identifier,
                          idv_type, multiple_or_single_award,
                          recipient_uei, recipient_name, recipient_parent_name,
                          recipient_city, recipient_state,
                          naics_code, naics_description, psc_code, psc_description,
                          potential_value, current_value,
                          base_action_date, ordering_period_end,
                          pop_current_end, pop_potential_end,
                          subcontracting_plan_code, subcontracting_plan,
                          awarding_agency, awarding_sub_agency, set_aside_type,
                          pool_id, pool_awardee_count,
                          is_woman_owned, is_sdvosb, is_hubzone, is_8a,
                          is_small_disadvantaged, is_minority_owned,
                          pipeline_status, pipeline_category, pipeline_priority,
                          pipeline_priority_score, pipeline_notes,
                          outreach_status, outreach_last_contact, outreach_notes,
                          last_enriched_at, enrichment_data,
                          usaspending_permalink,
                          upload_batch_id, source_csv, created_at, updated_at
                   FROM subcontracting_leads
                   WHERE id = %s""",
                (lead_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Lead not found")

            columns = [desc[0] for desc in cur.description]
            result = dict(zip(columns, row))
            for k in list(result.keys()):
                if isinstance(result[k], (date, datetime)):
                    result[k] = result[k].isoformat()
            return result
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Triage update
# ---------------------------------------------------------------------------


@router.post("/{lead_id}/triage")
def update_lead_triage(
    lead_id: int,
    body: UpdateTriageRequest,
    user: dict = Depends(get_current_user),
):
    """Update triage fields on a subcontracting lead."""
    with tx() as conn:
        with conn.cursor() as cur:
            updates = []
            params: list[Any] = []

            if body.pipeline_priority is not None:
                updates.append("pipeline_priority = %s")
                params.append(body.pipeline_priority)
            if body.pipeline_priority_score is not None:
                updates.append("pipeline_priority_score = %s")
                params.append(body.pipeline_priority_score)
            if body.pipeline_notes is not None:
                updates.append("pipeline_notes = %s")
                params.append(body.pipeline_notes)
            if body.pipeline_status is not None:
                updates.append("pipeline_status = %s")
                params.append(body.pipeline_status)

            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")

            updates.append("updated_at = now()")
            params.append(lead_id)

            cur.execute(
                f"UPDATE subcontracting_leads SET {', '.join(updates)} WHERE id = %s",
                params,
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Lead not found")

    return {"id": lead_id, "updated": True}


# ---------------------------------------------------------------------------
# Pool processing (post-import)
# ---------------------------------------------------------------------------


@router.post("/process-pools")
def process_pools(
    user: dict = Depends(get_current_user),
):
    """Compute pool groupings from solicitation_identifier.

    Groups leads by solicitation_identifier, counts awardees per pool,
    and boosts priority scores for multi-award pool members (+20 for
    5+ awardees, +10 for 2–4 awardees).

    Run after each upload to refresh pool intelligence.
    """
    with tx() as conn:
        with conn.cursor() as cur:
            # Compute pool counts
            cur.execute(
                """WITH pool_counts AS (
                       SELECT solicitation_identifier,
                              COUNT(DISTINCT recipient_uei) as awardee_count
                       FROM subcontracting_leads
                       WHERE solicitation_identifier IS NOT NULL
                         AND solicitation_identifier != ''
                       GROUP BY solicitation_identifier
                       HAVING COUNT(DISTINCT recipient_uei) > 1
                   )
                   UPDATE subcontracting_leads sl
                   SET pool_id = pc.solicitation_identifier,
                       pool_awardee_count = pc.awardee_count,
                       pipeline_priority_score =
                           pipeline_priority_score
                           + CASE
                               WHEN pc.awardee_count >= 5 THEN 20
                               WHEN pc.awardee_count >= 2 THEN 10
                               ELSE 0
                             END,
                       pipeline_priority =
                           CASE
                               WHEN (pipeline_priority_score
                                     + CASE
                                         WHEN pc.awardee_count >= 5 THEN 20
                                         WHEN pc.awardee_count >= 2 THEN 10
                                         ELSE 0
                                       END) >= 40 THEN 'high'
                               WHEN (pipeline_priority_score
                                     + CASE
                                         WHEN pc.awardee_count >= 5 THEN 20
                                         WHEN pc.awardee_count >= 2 THEN 10
                                         ELSE 0
                                       END) >= 20 THEN 'medium'
                               ELSE 'low'
                           END,
                       updated_at = now()
                   FROM pool_counts pc
                   WHERE sl.solicitation_identifier = pc.solicitation_identifier""",
            )
            updated = cur.rowcount

    return {"pools_updated": updated}


# ---------------------------------------------------------------------------
# Batch management
# ---------------------------------------------------------------------------


@router.get("/batches")
def list_upload_batches(user: dict = Depends(get_current_user)):
    """List all upload batches with row counts."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT upload_batch_id, source_csv, COUNT(*) as row_count,
                          MIN(created_at) as uploaded_at
                   FROM subcontracting_leads
                   WHERE upload_batch_id IS NOT NULL
                   GROUP BY upload_batch_id, source_csv
                   ORDER BY uploaded_at DESC"""
            )
            rows = cur.fetchall()
            return {
                "batches": [
                    {
                        "batch_id": str(r[0]),
                        "source": r[1],
                        "rows": r[2],
                        "uploaded_at": str(r[3]),
                    }
                    for r in rows
                ]
            }
    finally:
        conn.close()
