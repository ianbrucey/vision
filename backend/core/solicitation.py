"""
Vision — Solicitation CRUD.

Provides the SolicitationManager: create/get/list/update for solicitations
(Option A architecture — a domain table backed by a generic `cases` row via
case_id). Mirrors the shape of CaseManager in backend/core/case.py.

Usage:
    from core.solicitation import SolicitationManager
    mgr = SolicitationManager()
    sol = mgr.create(source_type="federal", url="https://sam.gov/...", notice_id="abc123")
"""

from __future__ import annotations

from typing import Any

import psycopg2.extras

from core.case import CaseManager
from core.db import connect, tx

FEDERAL_TITLE_PLACEHOLDER = "Untitled SAM.gov Opportunity (fetching...)"


class DuplicateNoticeError(Exception):
    """Raised when create() is called with a notice_id that already exists.

    Carries the existing solicitation's external_id so the API route can
    surface it in a 409 response (per CLAIM-09 / 02-api-contract.json).
    """

    def __init__(self, notice_id: str, existing_external_id: str):
        self.notice_id = notice_id
        self.existing_external_id = existing_external_id
        super().__init__(
            f"Solicitation already exists for notice_id={notice_id!r}"
        )


class SolicitationManager:
    """Stateless CRUD operations for solicitations."""

    def create(
        self,
        source_type: str,
        url: str,
        title: str | None = None,
        notice_id: str | None = None,
        description: str | None = None,
    ) -> dict:
        """Create a solicitation: a backing `cases` row + a `solicitations` row.

        Both inserts happen in a single transaction. For source_type='federal',
        title falls back to FEDERAL_TITLE_PLACEHOLDER when omitted. For
        'state'/'local', title is required (raises ValueError — caught by the
        route and turned into a 400).

        `description` is stored on the backing `cases` row (`cases.description`).
        It is optional for all source types — federal solicitations get their
        description-equivalent (agency/NAICS/etc.) from the sam_fetch job;
        state/local have no such job, so the UI should encourage supplying one.

        Raises DuplicateNoticeError if notice_id is already in use (checked
        inside the same transaction, before the case row is created, so no
        orphan case is left behind on conflict).
        """
        if source_type != "federal" and not title:
            raise ValueError(
                "title is required for source_type='state'|'local'"
            )

        resolved_title = title or FEDERAL_TITLE_PLACEHOLDER
        # 'complete' for state/local (fully synchronous, no async fetch job);
        # 'pending' for federal (sam_fetch job populates metadata/documents).
        ingestion_status = "pending" if source_type == "federal" else "complete"

        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if notice_id:
                    cur.execute(
                        "SELECT external_id FROM solicitations WHERE notice_id = %s",
                        (notice_id,),
                    )
                    existing = cur.fetchone()
                    if existing:
                        raise DuplicateNoticeError(
                            notice_id, str(existing["external_id"])
                        )

                cur.execute(
                    """INSERT INTO cases (name, case_type, description)
                       VALUES (%s, 'rfp_response', %s)
                       RETURNING id""",
                    (resolved_title, description),
                )
                case_id = cur.fetchone()["id"]

                cur.execute(
                    """INSERT INTO solicitations
                       (case_id, source_type, title, url, notice_id, ingestion_status)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       RETURNING *""",
                    (case_id, source_type, resolved_title, url, notice_id,
                     ingestion_status),
                )
                return dict(cur.fetchone())

    def get(self, solicitation_id: int) -> dict | None:
        """Return a solicitation with its backing case's documents."""
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM solicitations WHERE id = %s", (solicitation_id,)
                )
                row = cur.fetchone()
                if row is None:
                    return None
                sol = dict(row)
                sol["documents"] = CaseManager()._list_documents(
                    sol["case_id"], conn=conn
                )
                return sol
        finally:
            conn.close()

    def get_by_case_id(self, case_id: int) -> dict | None:
        """Look up the solicitation backed by a given `cases` row.

        Used by the case detail page's Triage tab, which only has case_id
        (from the URL) and needs the solicitation id + artifact columns.
        """
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM solicitations WHERE case_id = %s", (case_id,)
                )
                row = cur.fetchone()
                if row is None:
                    return None
                sol = dict(row)
                sol["documents"] = CaseManager()._list_documents(case_id, conn=conn)
                return sol
        finally:
            conn.close()

    def get_by_notice_id(self, notice_id: str) -> dict | None:
        """Idempotency lookup by SAM.gov notice_id."""
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM solicitations WHERE notice_id = %s", (notice_id,)
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def list(
        self,
        source_type: str | None = None,
        ingestion_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List solicitations, optionally filtered by source_type/ingestion_status."""
        conn = connect()
        try:
            clauses = []
            params: list[Any] = []
            if source_type:
                clauses.append("source_type = %s")
                params.append(source_type)
            if ingestion_status:
                clauses.append("ingestion_status = %s")
                params.append(ingestion_status)
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.extend([limit, offset])
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""SELECT * FROM solicitations {where}
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s""",
                    tuple(params),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def update(self, solicitation_id: int, **kwargs) -> dict | None:
        """Update solicitation fields. Only provided kwargs are changed."""
        allowed = {
            "title", "ingestion_status", "has_missing_docs", "error_message",
            "agency", "naics_code", "psc_code", "set_aside_type",
            "set_aside_description", "point_of_contact", "place_of_performance",
            "response_deadline", "posted_date",
            "triage_status", "triage_error", "has_partial_artifacts",
            "notice_type", "quick_kill", "quick_kill_reason",
            "artifact_scope_of_work", "artifact_technical_requirements",
            "artifact_deliverables_timeline", "artifact_evaluation_criteria",
            "artifact_submission_checklist",
            "matching_status", "matching_error",
            "outreach_email_subject", "outreach_email_body",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get(solicitation_id)

        set_parts = []
        values: list[Any] = []
        for k, v in updates.items():
            if k in ("point_of_contact", "place_of_performance"):
                set_parts.append(f"{k} = %s::jsonb")
                values.append(self._j(v))
            else:
                set_parts.append(f"{k} = %s")
                values.append(v)
        values.append(solicitation_id)

        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""UPDATE solicitations SET {', '.join(set_parts)}, updated_at = now()
                        WHERE id = %s
                        RETURNING *""",
                    tuple(values),
                )
                result = cur.fetchone()
                if result and "title" in updates:
                    # Keep the backing cases.name in sync — the case detail
                    # page's header reads cases.name, not solicitations.title.
                    # Without this, it stays stuck on FEDERAL_TITLE_PLACEHOLDER
                    # forever after sam_fetch resolves the real title.
                    cur.execute(
                        "UPDATE cases SET name = %s, updated_at = now() WHERE id = %s",
                        (updates["title"], result["case_id"]),
                    )
                return dict(result) if result else None

    def delete(self, solicitation_id: int) -> bool:
        """Delete a solicitation and everything attached to it.

        Removes the backing case's documents from MinIO (best-effort, since
        the FK cascade only touches the DB), deletes any queued/completed
        jobs for the case (jobs.case_id has no FK — not covered by cascade),
        then deletes the `cases` row. The cases FK cascade (ON DELETE CASCADE)
        takes care of solicitations, documents, sections/blocks, parties,
        allegations, drafts, tasks, events, workspaces, folders, calendar
        events/reminders, and citations.

        Returns False if no solicitation with this id exists.
        """
        from ingestion.storage import delete_file

        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT case_id FROM solicitations WHERE id = %s",
                    (solicitation_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return False
                case_id = row["case_id"]

                cur.execute(
                    """SELECT storage_path FROM documents
                       WHERE case_id = %s AND storage_path IS NOT NULL""",
                    (case_id,),
                )
                storage_paths = [r["storage_path"] for r in cur.fetchall()]
        finally:
            conn.close()

        for storage_path in storage_paths:
            parts = storage_path.split("/", 1)
            if len(parts) == 2:
                try:
                    delete_file(parts[0], parts[1])
                except Exception:
                    pass  # best-effort; file may already be gone

        with tx() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM jobs WHERE case_id = %s", (case_id,))
                cur.execute("DELETE FROM cases WHERE id = %s", (case_id,))
                return cur.rowcount > 0

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _j(d: dict | list | None) -> str:
        import json
        return json.dumps(d) if d is not None else "null"


# ---------------------------------------------------------------------------
# Module-level convenience — mirrors the class API for quick scripting
# ---------------------------------------------------------------------------

_default = SolicitationManager()

create           = _default.create
get              = _default.get
get_by_notice_id = _default.get_by_notice_id
list_            = _default.list
update           = _default.update
delete           = _default.delete
