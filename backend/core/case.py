"""
Vision — Case CRUD.

Provides the complete case management API: create, read, update, delete
for cases, parties, and allegations. Designed as the foundation that the
CLI, API, and UI all call into.

Usage:
    from vision.case import CaseManager
    mgr = CaseManager()
    case = mgr.create_case(name="Alhad v. Edmonds", case_type="medical_board_complaint", ...)
"""

from __future__ import annotations

from typing import Any

import psycopg2.extras

from core.db import connect, tx


# ---------------------------------------------------------------------------
# CaseManager
# ---------------------------------------------------------------------------

class CaseManager:
    """Stateless CRUD operations for cases, parties, and allegations."""

    # -- cases ---------------------------------------------------------------

    def create_case(
        self,
        name: str,
        case_type: str,
        narrative: str | None = None,
        description: str | None = None,
        case_number: str | None = None,
        jurisdiction: str | None = None,
        filing_date: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Create a new case. Returns the full case dict including generated id."""
        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO cases (name, case_type, narrative, description,
                       case_number, jurisdiction, filing_date, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                       RETURNING *""",
                    (name, case_type, narrative, description,
                     case_number, jurisdiction, filing_date,
                     self._j(metadata)),
                )
                return dict(cur.fetchone())

    def get_case(self, case_id: int) -> dict | None:
        """Return a case with its parties, allegations, and documents."""
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM cases WHERE id = %s", (case_id,)
                )
                case = cur.fetchone()
                if case is None:
                    return None
                case = dict(case)

                # Load related entities
                case["parties"] = self.list_parties(case_id, conn=conn)
                case["allegations"] = self.list_allegations(case_id, conn=conn)
                case["documents"] = self._list_documents(case_id, conn=conn)
                return case
        finally:
            conn.close()

    def list_cases(
        self,
        status: str | None = None,
        case_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List cases, optionally filtered by status or type."""
        conn = connect()
        try:
            clauses = []
            params: list[Any] = []
            if status:
                clauses.append("status = %s")
                params.append(status)
            if case_type:
                clauses.append("case_type = %s")
                params.append(case_type)
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.extend([limit, offset])
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""SELECT id, external_id, name, case_type, status,
                               jurisdiction, filing_date, description,
                               created_at, updated_at
                        FROM cases {where}
                        ORDER BY updated_at DESC
                        LIMIT %s OFFSET %s""",
                    tuple(params),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def update_case(self, case_id: int, **kwargs) -> dict | None:
        """Update case fields. Only provided kwargs are changed."""
        allowed = {
            "name", "case_number", "case_type", "status", "jurisdiction",
            "filing_date", "description", "narrative", "case_brief", "metadata",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get_case(case_id)

        set_clause = ", ".join(
            f"{k} = %s" for k in updates
        )
        # Handle JSONB
        values = []
        for k, v in updates.items():
            if k == "metadata":
                values.append(self._j(v))
            else:
                values.append(v)
        values.append(case_id)

        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""UPDATE cases SET {set_clause}, updated_at = now()
                        WHERE id = %s
                        RETURNING *""",
                    tuple(values),
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def delete_case(self, case_id: int) -> bool:
        """Delete a case and all related entities (CASCADE)."""
        with tx() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM cases WHERE id = %s", (case_id,)
                )
                return cur.rowcount > 0

    # -- parties -------------------------------------------------------------

    def add_party(
        self,
        case_id: int,
        name: str,
        party_kind: str = "individual",
        roles: list[str] | None = None,
        notes: str | None = None,
        contact_info: dict | None = None,
        discovered_by: str = "user",
        metadata: dict | None = None,
    ) -> dict:
        """Add a party to a case."""
        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO parties (case_id, name, party_kind, roles,
                       notes, contact_info, discovered_by, metadata)
                       VALUES (%s, %s, %s, %s::text[], %s, %s::jsonb, %s, %s::jsonb)
                       RETURNING *""",
                    (case_id, name, party_kind, roles or [], notes,
                     self._j(contact_info), discovered_by, self._j(metadata)),
                )
                return dict(cur.fetchone())

    def list_parties(
        self,
        case_id: int,
        conn: Any = None,
    ) -> list[dict]:
        """List all parties for a case."""
        _conn = conn or connect()
        own_conn = conn is None
        try:
            with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM parties
                       WHERE case_id = %s
                       ORDER BY created_at""",
                    (case_id,),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            if own_conn:
                _conn.close()

    def update_party(self, party_id: int, **kwargs) -> dict | None:
        """Update party fields."""
        allowed = {
            "name", "party_kind", "notes", "contact_info",
            "discovered_by", "metadata",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if "roles" in kwargs:
            updates["roles"] = kwargs["roles"]  # TEXT[] handled separately

        if not updates:
            return None

        set_parts = []
        values: list[Any] = []
        for k, v in updates.items():
            if k == "roles":
                set_parts.append("roles = %s::text[]")
                values.append(v or [])
            elif k in ("contact_info", "metadata"):
                set_parts.append(f"{k} = %s::jsonb")
                values.append(self._j(v))
            else:
                set_parts.append(f"{k} = %s")
                values.append(v)
        values.append(party_id)

        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""UPDATE parties SET {', '.join(set_parts)}, updated_at = now()
                        WHERE id = %s
                        RETURNING *""",
                    tuple(values),
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def remove_party(self, party_id: int) -> bool:
        """Remove a party from a case."""
        with tx() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM parties WHERE id = %s", (party_id,)
                )
                return cur.rowcount > 0

    # -- allegations ---------------------------------------------------------

    def add_allegation(
        self,
        case_id: int,
        allegation_id: str,
        text: str,
        category: str | None = None,
        targets: list[int] | None = None,
        extraction_focus: list[str] | None = None,
        sort_order: int = 0,
        metadata: dict | None = None,
    ) -> dict:
        """Add an allegation to a case."""
        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO allegations (case_id, allegation_id, text,
                       category, targets, extraction_focus, sort_order, metadata)
                       VALUES (%s, %s, %s, %s, %s::int[], %s::text[], %s, %s::jsonb)
                       ON CONFLICT (case_id, allegation_id)
                       DO UPDATE SET text = EXCLUDED.text,
                                     category = EXCLUDED.category,
                                     updated_at = now()
                       RETURNING *""",
                    (case_id, allegation_id, text, category,
                     targets or [], extraction_focus or [], sort_order,
                     self._j(metadata)),
                )
                return dict(cur.fetchone())

    def list_allegations(
        self,
        case_id: int,
        conn: Any = None,
    ) -> list[dict]:
        """List all allegations for a case."""
        _conn = conn or connect()
        own_conn = conn is None
        try:
            with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM allegations
                       WHERE case_id = %s
                       ORDER BY sort_order, allegation_id""",
                    (case_id,),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            if own_conn:
                _conn.close()

    def update_allegation(self, allegation_id_db: int, **kwargs) -> dict | None:
        """Update allegation fields by database id."""
        allowed = {
            "allegation_id", "text", "category", "status",
            "verdict", "extraction_focus", "sort_order", "metadata",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if "targets" in kwargs:
            updates["targets"] = kwargs["targets"]

        if not updates:
            return None

        set_parts = []
        values: list[Any] = []
        for k, v in updates.items():
            if k in ("targets",):
                set_parts.append(f"{k} = %s::int[]")
                values.append(v or [])
            elif k in ("extraction_focus",):
                set_parts.append(f"{k} = %s::text[]")
                values.append(v or [])
            elif k in ("verdict", "metadata"):
                set_parts.append(f"{k} = %s::jsonb")
                values.append(self._j(v))
            else:
                set_parts.append(f"{k} = %s")
                values.append(v)
        values.append(allegation_id_db)

        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""UPDATE allegations SET {', '.join(set_parts)}, updated_at = now()
                        WHERE id = %s
                        RETURNING *""",
                    tuple(values),
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def remove_allegation(self, allegation_id_db: int) -> bool:
        """Remove an allegation by database id."""
        with tx() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM allegations WHERE id = %s",
                    (allegation_id_db,),
                )
                return cur.rowcount > 0

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _j(d: dict | None) -> str:
        import json
        return json.dumps(d) if d else "{}"

    def _list_documents(
        self, case_id: int, conn: Any = None
    ) -> list[dict]:
        _conn = conn or connect()
        own_conn = conn is None
        try:
            with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT id, name, page_count, document_type,
                              ocr_status, source, storage_path, created_at
                       FROM documents
                       WHERE case_id = %s
                       ORDER BY created_at""",
                    (case_id,),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            if own_conn:
                _conn.close()


# ---------------------------------------------------------------------------
# Module-level convenience — mirrors the class API for quick scripting
# ---------------------------------------------------------------------------

_default = CaseManager()

create_case       = _default.create_case
get_case          = _default.get_case
list_cases        = _default.list_cases
update_case       = _default.update_case
delete_case       = _default.delete_case
add_party         = _default.add_party
list_parties      = _default.list_parties
update_party      = _default.update_party
remove_party      = _default.remove_party
add_allegation    = _default.add_allegation
list_allegations  = _default.list_allegations
update_allegation = _default.update_allegation
remove_allegation = _default.remove_allegation
