"""
Vision — Databank Pipeline Processor.

Reads raw rows from the sam_notices table, applies business filters
(NAICS category, set-aside type, urgency, opportunity type), and feeds
qualifying notices into the existing solicitation pipeline.

Architecture:
    sam_notices (raw CSV dump) ──[process_batch()]──> solicitations
                                                         │
                                            sam_fetch job enqueued
                                            (existing pipeline, unchanged)

Idempotency: solicitations.notice_id has a UNIQUE constraint. On
DuplicateNoticeError, the row is marked 'duplicate' and linked to the
existing solicitation. Running the same batch twice is safe.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import psycopg2.extras

from core.db import connect, tx

# ---------------------------------------------------------------------------
# Constants — filter lists
# ---------------------------------------------------------------------------

# Types we EXCLUDE (not bid opportunities)
_EXCLUDED_TYPES: set[str] = {
    "Award Notice",
    "Justification",
    "Sale of Surplus Property",
}

# Types we INCLUDE
_INCLUDED_TYPES: set[str] = {
    "Combined Synopsis/Solicitation",
    "Solicitation",
    "Presolicitation",
    "Sources Sought",
    # "Special Notice",                     # commented out — too broad, mostly announcements
    # "Consolidate/(Substantially) Bundle",  # commented out — bundling notices, not bid opportunities
}

# NAICS keyword matching — construction trades
_CONSTRUCTION_KW: list[str] = [
    "Construction",
    "Building",
    "Plumbing",
    "HVAC",
    "Electrical Contractors",
    "Carpentry",
    "Masonry",
    "Roofing",
    "Concrete",
    "Painting",
    "Welding",
    "Excavation",
    "Demolition",
    "Flooring",
    "Drywall",
    "Fencing",
    "Paving",
    "Structural Steel",
    "Fire Protection",
    "Elevator",
    "Asphalt",
    "Sheet Metal",
    "Finishing Contractors",
    "Power and Communication Line",
    "Water and Sewer Line",
    "Highway, Street, and Bridge",
    "Industrial Building",
]

# NAICS descriptions that LOOK like construction but are actually
# manufacturing, supply, or equipment — exclude from construction category
_CONSTRUCTION_EXCLUDES: set[str] = {
    "Ship Building",
    "Machinery Manufacturing",
    "Equipment Manufacturing",
    "Mining",
    "Equipment Rental",
    "Equipment Merchant",
    "Sand and Gravel",
    "Prefabricated Metal Building",
    "Construction Machinery",
}

# NAICS keyword matching — facilities support
_FACILITIES_KW: list[str] = [
    "Facilities Support",
    "Janitorial",
    "Custodial",
    "Landscaping",
    "Grounds",
    "Security Guards",
    "Security Systems",
    "Waste Collection",
    "Waste Treatment",
    "Pest Control",
    "Laundry",
    "Food Service",
    "Cafeteria",
]

# NAICS keyword matching — IT services
_IT_KW: list[str] = [
    "Software",
    "Computer Programming",
    "Computer Systems Design",
    "Electronic Computer",
    "Computing Infrastructure",
    "Data Processing",
    "Custom Computer",
    "Cloud",
    "Cybersecurity",
    "Information Technology",
    "Telecom",
    "Wireless",
    "Satellite",
    "Internet",
]

# Set-aside keywords (case-insensitive match against current_set_aside)
_SB_SET_ASIDE_KW: list[str] = [
    "Total Small Business",
    "Service-Disabled Veteran-Owned Small Business",
    "SDVOSB",
    "Historically Underutilized Business",
    "HUBZone",
    "8(a)",
    "SBA Certified Women-Owned Small Business",
    "WOSB",
    "Women-Owned Small Business",
    "EDWOSB",
    "Economically Disadvantaged WOSB",
    "Indian Small Business Economic Enterprise",
    "ISBEE",
    "Indian Economic Enterprise",
    "IEE",
    "Veteran-Owned Small Business",
    "Buy Indian",
    "Local Area Set-Aside",
]

# Set-aside keywords that indicate NOT a clean SB opportunity
_EXCLUDED_SET_ASIDE_KW: list[str] = [
    "Partial Small Business",
]


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def classify_naics(naics_description: str | None) -> str:
    """Classify a NAICS text description into a pipeline category.

    Returns 'construction', 'facilities', 'it', or 'other'.
    Order matters: construction checked first (most specific excludes),
    then IT, then facilities. First match wins.
    """
    if not naics_description:
        return "other"

    naics_lower = naics_description.lower()

    # Check construction excludes first
    for kw in _CONSTRUCTION_EXCLUDES:
        if kw.lower() in naics_lower:
            return "other"

    for kw in _CONSTRUCTION_KW:
        if kw.lower() in naics_lower:
            return "construction"

    for kw in _IT_KW:
        if kw.lower() in naics_lower:
            return "it"

    for kw in _FACILITIES_KW:
        if kw.lower() in naics_lower:
            return "facilities"

    return "other"


def classify_set_aside(set_aside: str | None) -> str:
    """Classify a set-aside string into a group.

    Returns 'sb_set_aside', 'full_and_open', or 'partial_set_aside'.
    """
    if not set_aside or not set_aside.strip():
        return "full_and_open"

    for kw in _EXCLUDED_SET_ASIDE_KW:
        if kw.lower() in set_aside.lower():
            return "partial_set_aside"

    for kw in _SB_SET_ASIDE_KW:
        if kw.lower() in set_aside.lower():
            return "sb_set_aside"

    return "full_and_open"


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse a SAM.gov databank date string into a datetime.

    Handles the formats seen in databank CSV exports:
        'Aug 7, 2026 02:30 PM UTC'
        'Jul 22, 2026 03:00 PM UTC'
        '2026-07-15' (less common)
    """
    if not date_str or not date_str.strip():
        return None

    date_str = date_str.strip()

    for fmt in [
        "%b %d, %Y %I:%M %p UTC",
        "%b %d, %Y %I:%M %p",
        "%Y-%m-%d",
        "%m/%d/%Y",
    ]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def bucket_urgency(
    response_date_str: str | None,
    opportunity_type: str | None = None,
) -> str:
    """Bucket a notice by how soon its response deadline is.

    Returns 'red', 'yellow', 'green', 'unknown', or 'past_due'.

    Sources Sought are always 'red' — short window, high strategic value
    for getting on the vendor list before the formal RFP drops.
    """
    if opportunity_type == "Sources Sought":
        return "red"

    dt = _parse_date(response_date_str)
    if dt is None:
        return "unknown"

    today = date.today()
    days = (dt.date() - today).days

    if days < 0:
        return "past_due"
    if days <= 7:
        return "red"
    if days <= 14:
        return "yellow"
    return "green"


def is_sources_sought_recently_closed(response_date_str: str | None) -> bool:
    """Check if a Sources Sought closed within the last 30 days.

    Past-due Sources Sought ≤30 days old may still accept late responses
    or provide useful intel for the upcoming RFP.
    """
    dt = _parse_date(response_date_str)
    if dt is None:
        return False

    days_since_close = (date.today() - dt.date()).days
    return 0 <= days_since_close <= 30


# ---------------------------------------------------------------------------
# Processor
# ---------------------------------------------------------------------------


class PipelineProcessor:
    """Read sam_notices rows, apply filters, feed into solicitation pipeline."""

    def process_batch(
        self,
        batch_id: str,
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Process all unprocessed rows in a sam_notices upload batch.

        Args:
            batch_id: The upload_batch_id UUID from the CSV upload.
            dry_run: If True, compute counts but don't create solicitations
                     or enqueue jobs.

        Returns:
            Dict with counts: queued, skipped, duplicate, errors,
            and a skipped_breakdown by reason.
        """
        rows = _get_unprocessed_rows(batch_id)
        results: dict[str, Any] = {
            "batch_id": batch_id,
            "dry_run": dry_run,
            "total_rows": len(rows),
            "queued": 0,
            "skipped": 0,
            "duplicate": 0,
            "skipped_breakdown": {},
            "errors": [],
        }

        if not rows:
            return results

        # Lazy import — avoid circular imports at module level
        from core.solicitation import SolicitationManager, DuplicateNoticeError

        sol_mgr = SolicitationManager()

        # Batch-update accumulators: collect row IDs by reason, then
        # bulk-UPDATE at the end. Avoids 44K+ individual transactions.
        skipped_by_reason: dict[str, list[int]] = {}
        queued_rows: list[tuple[int, str, str, int]] = []   # (row_id, cat, urg, sol_id)
        duplicate_rows: list[tuple[int, str, str, int]] = [] # same shape

        for row in rows:
            try:
                notice_id = (row.get("notice_id") or "").strip()
                opp_type = (row.get("contract_opportunity_type") or "").strip()
                naics_desc = (row.get("naics_description") or "").strip()
                set_aside = (row.get("current_set_aside") or "").strip()
                response_date = (row.get("current_response_date") or "").strip()
                opp_title = (row.get("opportunity_title") or "").strip()
                row_id = row["id"]

                # ---- Filter gates ----

                # Gate 1: Type
                if opp_type in _EXCLUDED_TYPES or (
                    opp_type not in _INCLUDED_TYPES and opp_type != ""
                ):
                    skipped_by_reason.setdefault("excluded_type", []).append(row_id)
                    results["skipped"] += 1
                    results["skipped_breakdown"]["excluded_type"] = (
                        results["skipped_breakdown"].get("excluded_type", 0) + 1
                    )
                    continue

                # Gate 2: NAICS category
                category = classify_naics(naics_desc)
                if category == "other":
                    skipped_by_reason.setdefault("wrong_naics", []).append(row_id)
                    results["skipped"] += 1
                    results["skipped_breakdown"]["wrong_naics"] = (
                        results["skipped_breakdown"].get("wrong_naics", 0) + 1
                    )
                    continue

                # Gate 3: Set-aside
                set_aside_group = classify_set_aside(set_aside)
                if set_aside_group == "full_and_open":
                    skipped_by_reason.setdefault("full_and_open", []).append(row_id)
                    results["skipped"] += 1
                    results["skipped_breakdown"]["full_and_open"] = (
                        results["skipped_breakdown"].get("full_and_open", 0) + 1
                    )
                    continue
                if set_aside_group == "partial_set_aside":
                    skipped_by_reason.setdefault("partial_set_aside", []).append(row_id)
                    results["skipped"] += 1
                    results["skipped_breakdown"]["partial_set_aside"] = (
                        results["skipped_breakdown"].get("partial_set_aside", 0) + 1
                    )
                    continue

                # Gate 4: Urgency / past-due
                urgency = bucket_urgency(response_date, opp_type)
                if urgency == "past_due":
                    if opp_type == "Sources Sought" and is_sources_sought_recently_closed(
                        response_date
                    ):
                        urgency = "red"
                    else:
                        skipped_by_reason.setdefault("past_due", []).append(row_id)
                        results["skipped"] += 1
                        results["skipped_breakdown"]["past_due"] = (
                            results["skipped_breakdown"].get("past_due", 0) + 1
                        )
                        continue

                # Gate 5: Notice ID validity
                if not notice_id or len(notice_id) < 8:
                    skipped_by_reason.setdefault("invalid_notice_id", []).append(row_id)
                    results["skipped"] += 1
                    results["skipped_breakdown"]["invalid_notice_id"] = (
                        results["skipped_breakdown"].get("invalid_notice_id", 0) + 1
                    )
                    continue

                # ---- All gates passed — qualify ----

                if dry_run:
                    results["queued"] += 1
                    continue

                try:
                    sol = sol_mgr.create(
                        source_type="federal",
                        url=f"https://sam.gov/opp/{notice_id}/view",
                        notice_id=notice_id,
                        title=opp_title or "Untitled SAM.gov Opportunity (fetching...)",
                    )
                except DuplicateNoticeError:
                    existing_id = _lookup_solicitation_id(notice_id)
                    duplicate_rows.append((row_id, category, urgency, existing_id or 0))
                    results["duplicate"] += 1
                    continue

                queued_rows.append((row_id, category, urgency, sol["id"]))
                results["queued"] += 1

            except Exception as exc:
                results["errors"].append({
                    "sam_notice_id": row.get("id"),
                    "notice_id": row.get("notice_id"),
                    "error": str(exc),
                })
                skipped_by_reason.setdefault("error", []).append(row["id"])
                results["skipped"] += 1

        # ---- Bulk UPDATE skipped rows ----
        if not dry_run:
            for reason, ids in skipped_by_reason.items():
                _bulk_mark_skipped(ids, reason)

        # ---- Bulk UPDATE queued rows ----
        if not dry_run and queued_rows:
            _bulk_mark_processed(queued_rows, "queued")

        # ---- Bulk UPDATE duplicate rows ----
        if not dry_run and duplicate_rows:
            _bulk_mark_processed(duplicate_rows, "duplicate")

        return results

    # ------------------------------------------------------------------
    # Batch status operations (reset only — updates are bulk helpers)
    # ------------------------------------------------------------------

    def reset_batch(self, batch_id: str) -> int:
        """Reset processing status for all rows in a batch.

        Returns the number of rows reset. Use to re-process after
        filter rule changes.
        """
        with tx() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE sam_notices
                       SET pipeline_status = NULL,
                           pipeline_category = NULL,
                           pipeline_urgency = NULL,
                           pipeline_skip_reason = NULL,
                           pipeline_solicitation_id = NULL,
                           pipeline_processed_at = NULL
                       WHERE upload_batch_id = %s
                         AND pipeline_status IS NOT NULL""",
                    (batch_id,),
                )
                return cur.rowcount


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_unprocessed_rows(batch_id: str) -> list[dict]:
    """Fetch sam_notices rows that haven't been processed yet.

    Returns dicts with all values as plain strings (dates are cast
    to text in SQL to avoid datetime objects that break .strip()).
    """
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, notice_id, opportunity_title,
                          contract_opportunity_type,
                          naics_code AS naics_description,
                          current_set_aside,
                          current_response_date::text AS current_response_date
                   FROM sam_notices
                   WHERE upload_batch_id = %s
                     AND pipeline_status IS NULL""",
                (batch_id,),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def _lookup_solicitation_id(notice_id: str) -> int | None:
    """Find an existing solicitation by notice_id."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM solicitations WHERE notice_id = %s",
                (notice_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def _bulk_mark_skipped(ids: list[int], reason: str) -> None:
    """Mark a batch of sam_notices rows as skipped in a single UPDATE."""
    if not ids:
        return
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE sam_notices
                   SET pipeline_status = 'skipped',
                       pipeline_skip_reason = %s,
                       pipeline_processed_at = now()
                   WHERE id = ANY(%s)""",
                (reason, ids),
            )


def _bulk_mark_processed(
    rows: list[tuple[int, str, str, int]],
    status: str,
) -> None:
    """Mark a batch of sam_notices rows as processed (queued/duplicate).

    All updates happen in a single transaction. For the ~1,400 qualifying
    rows per batch this is fast — no need for a complex VALUES clause.
    """
    if not rows:
        return
    with tx() as conn:
        with conn.cursor() as cur:
            for row_id, category, urgency, sol_id in rows:
                cur.execute(
                    """UPDATE sam_notices
                       SET pipeline_status = %s,
                           pipeline_category = %s,
                           pipeline_urgency = %s,
                           pipeline_solicitation_id = %s,
                           pipeline_processed_at = now()
                       WHERE id = %s""",
                    (status, category, urgency, sol_id, row_id),
                )


def get_batch_status(batch_id: str) -> dict:
    """Return processing status summary for a batch."""
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT
                       COUNT(*) FILTER (WHERE pipeline_status IS NULL) AS pending,
                       COUNT(*) FILTER (WHERE pipeline_status = 'queued') AS queued,
                       COUNT(*) FILTER (WHERE pipeline_status = 'skipped') AS skipped,
                       COUNT(*) FILTER (WHERE pipeline_status = 'duplicate') AS duplicate,
                       COUNT(*) FILTER (WHERE pipeline_status = 'error') AS errors,
                       COUNT(*) AS total
                   FROM sam_notices
                   WHERE upload_batch_id = %s""",
                (batch_id,),
            )
            row = dict(cur.fetchone())
            return row
    finally:
        conn.close()
