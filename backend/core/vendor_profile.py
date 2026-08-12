"""
Vision — Vendor Profile CRUD.

Each vendor user (role='vendor') gets one profile. Profiles store business
identity, capabilities, compliance documents, and financial info.
"""

from __future__ import annotations

from typing import Any

import psycopg2.extras

from core.db import connect, tx

VALID_VENDOR_TYPES = {"individual", "service", "manufacturer"}

_WRITABLE = {
    "business_name", "vendor_type", "uei", "cage_code", "tax_id",
    "naics_codes", "capabilities", "website", "phone",
    "address_line1", "address_line2", "city", "state", "zip",
    "license_doc_id", "bonding_doc_id", "insurance_doc_id",
    "certification_doc_ids",
    "bonding_capacity", "annual_revenue", "employee_count",
    "years_in_business", "status",
}


class VendorProfileManager:
    """Stateless CRUD for vendor_profiles."""

    _FULL = (
        "id, external_id, user_id, business_name, vendor_type, uei, "
        "cage_code, tax_id, naics_codes, capabilities, website, phone, "
        "address_line1, address_line2, city, state, zip, "
        "license_doc_id, bonding_doc_id, insurance_doc_id, "
        "certification_doc_ids, bonding_capacity, annual_revenue, "
        "employee_count, years_in_business, status, verified_at, "
        "created_at, updated_at"
    )

    def create(self, user_id: str, business_name: str,
               vendor_type: str = "service", **kwargs) -> dict:
        """Create a vendor profile. One per user."""
        if vendor_type not in VALID_VENDOR_TYPES:
            raise ValueError(f"Invalid vendor_type: {vendor_type!r}")

        fields = ["user_id", "business_name", "vendor_type"]
        values: list[Any] = [user_id, business_name, vendor_type]

        for k in _WRITABLE - {"business_name", "vendor_type"}:
            if k in kwargs and kwargs[k] is not None:
                fields.append(k)
                values.append(kwargs[k])

        cols = ", ".join(fields)
        placeholders = ", ".join(["%s"] * len(fields))

        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                try:
                    cur.execute(
                        f"INSERT INTO vendor_profiles ({cols}) "
                        f"VALUES ({placeholders}) RETURNING {self._FULL}",
                        tuple(values),
                    )
                    return dict(cur.fetchone())
                except psycopg2.errors.UniqueViolation:
                    raise ValueError("User already has a vendor profile")

    def get(self, profile_id: int) -> dict | None:
        """Get a profile by id."""
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"SELECT {self._FULL} FROM vendor_profiles WHERE id = %s",
                    (profile_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def get_by_user(self, user_id: str) -> dict | None:
        """Get a vendor's profile by user_id."""
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"SELECT {self._FULL} FROM vendor_profiles WHERE user_id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def list(self, status: str | None = None, vendor_type: str | None = None) -> list[dict]:
        """List vendor profiles, optionally filtered."""
        clauses = []
        params: list[Any] = []
        if status:
            clauses.append("status = %s")
            params.append(status)
        if vendor_type:
            clauses.append("vendor_type = %s")
            params.append(vendor_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"SELECT vp.*, u.username, u.email "
                    f"FROM vendor_profiles vp "
                    f"JOIN users u ON u.id = vp.user_id "
                    f"{where} "
                    f"ORDER BY vp.created_at DESC",
                    tuple(params),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def update(self, profile_id: int, **kwargs) -> dict | None:
        """Update profile fields. Validates vendor_type if changed."""
        updates = {k: v for k, v in kwargs.items()
                   if k in _WRITABLE and v is not None}

        if "vendor_type" in updates:
            if updates["vendor_type"] not in VALID_VENDOR_TYPES:
                raise ValueError(f"Invalid vendor_type: {updates['vendor_type']!r}")

        if not updates:
            return self.get(profile_id)

        set_parts = []
        values: list[Any] = []
        for k, v in updates.items():
            set_parts.append(f"{k} = %s")
            values.append(v)
        values.append(profile_id)

        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"UPDATE vendor_profiles SET {', '.join(set_parts)}, "
                    f"updated_at = now() WHERE id = %s "
                    f"RETURNING {self._FULL}",
                    tuple(values),
                )
                row = cur.fetchone()
                return dict(row) if row else None
