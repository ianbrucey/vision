"""
Vision — Quote CRUD.

Stateless operations for the quotes table. One quote per solicitation per
subcontractor contact (POC). Permissioned: owner can edit their own quotes,
admin can edit all.
"""

from __future__ import annotations

from typing import Any

import psycopg2.extras

from core.db import connect, tx

VALID_STATUSES = {"draft", "pending_site_visit", "submitted", "awarded", "lost"}
TERMINAL_STATUSES = {"awarded", "lost"}

# Valid transitions from each status
_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_site_visit", "submitted", "lost"},
    "pending_site_visit": {"submitted", "lost"},
    "submitted": {"awarded", "lost"},
    "awarded": set(),
    "lost": set(),
}


class QuoteManager:
    """Stateless CRUD for quotes."""

    _COLUMNS = (
        "id, external_id, solicitation_id, created_by, "
        "notes, amount, poc_name, poc_email, poc_phone, "
        "status, document_id, created_at, updated_at"
    )

    def create(self, solicitation_id: int, created_by: str, **kwargs) -> dict:
        """Create a quote. Returns the full quote dict."""
        fields = []
        values: list[Any] = []
        for k in ("notes", "amount", "poc_name", "poc_email", "poc_phone"):
            if k in kwargs:
                fields.append(k)
                values.append(kwargs[k])

        cols = ", ".join(fields)
        placeholders = ", ".join(["%s"] * len(fields))

        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"INSERT INTO quotes (solicitation_id, created_by, {cols}) "
                    f"VALUES (%s, %s, {placeholders}) "
                    f"RETURNING {self._COLUMNS}",
                    (solicitation_id, created_by, *values),
                )
                return dict(cur.fetchone())

    def get(self, quote_id: int) -> dict | None:
        """Return a single quote by id."""
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"SELECT {self._COLUMNS} FROM quotes WHERE id = %s",
                    (quote_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def list_for_solicitation(self, solicitation_id: int) -> list[dict]:
        """Return all quotes for a solicitation, newest first."""
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"SELECT q.*, u.username AS created_by_username "
                    f"FROM quotes q "
                    f"LEFT JOIN users u ON u.id = q.created_by "
                    f"WHERE q.solicitation_id = %s "
                    f"ORDER BY q.created_at DESC",
                    (solicitation_id,),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def update(self, quote_id: int, **kwargs) -> dict | None:
        """Update quote fields. Validates status transitions."""
        allowed = {
            "notes", "amount", "poc_name", "poc_email", "poc_phone",
            "status", "document_id",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not updates:
            return self.get(quote_id)

        # Validate status transition
        if "status" in updates:
            current = self.get(quote_id)
            if current is None:
                return None
            new_status = updates["status"]
            if new_status not in VALID_STATUSES:
                raise ValueError(f"Invalid status: {new_status!r}")
            allowed_next = _TRANSITIONS.get(current["status"], set())
            if new_status not in allowed_next:
                raise ValueError(
                    f"Cannot transition from {current['status']!r} to {new_status!r}"
                )

        set_parts = []
        values: list[Any] = []
        for k, v in updates.items():
            set_parts.append(f"{k} = %s")
            values.append(v)
        values.append(quote_id)

        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"UPDATE quotes SET {', '.join(set_parts)}, updated_at = now() "
                    f"WHERE id = %s "
                    f"RETURNING {self._COLUMNS}",
                    tuple(values),
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def delete(self, quote_id: int) -> bool:
        """Delete a quote. Only draft quotes can be deleted."""
        quote = self.get(quote_id)
        if quote is None:
            return False
        if quote["status"] not in ("draft",):
            raise ValueError("Only draft quotes can be deleted")

        with tx() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM quotes WHERE id = %s", (quote_id,))
                return cur.rowcount > 0
