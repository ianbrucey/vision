"""
Vision — Vendor CRUD (manual creation).

Provides VendorManager.create() for vendors added directly by a user
(as opposed to the bulk GSA/SBA import that populates most of the
`vendors` table — see backend/schemas/009_vendors.sql). Manually-created
vendors are tagged `source='manual'`.

Usage:
    from core.vendor import VendorManager
    mgr = VendorManager()
    vendor = mgr.create(vendor_name="Acme Consulting LLC", contact_email="foo@acme.com")
"""

from __future__ import annotations

from typing import Any

import psycopg2.extras

from core.db import tx

# Columns a caller may set on manual creation (vendor_name handled separately,
# source is always forced to 'manual'). Mirrors backend/schemas/009_vendors.sql.
_OPTIONAL_COLUMNS = (
    "trade_name", "uei", "cage_code",
    "contact_name", "contact_email", "contact_phone", "website",
    "address_line1", "address_line2", "city", "state", "zipcode", "county",
    "naics_code_primary", "naics_codes_all", "capabilities",
    "is_small_business", "is_woman_owned", "is_veteran_owned",
    "is_sdvosb", "is_hubzone", "is_8a",
)


class VendorManager:
    """CRUD for manually-created vendors."""

    def create(self, vendor_name: str, **fields: Any) -> dict:
        """Insert a new vendor row with source='manual'.

        `fields` may contain any subset of `_OPTIONAL_COLUMNS`; unset/None
        values are omitted so column defaults (e.g. is_small_business=FALSE)
        apply. Unknown keys are silently ignored.
        """
        cols: list[str] = ["vendor_name", "source"]
        vals: list[Any] = [vendor_name, "manual"]
        for col in _OPTIONAL_COLUMNS:
            if fields.get(col) is not None:
                cols.append(col)
                vals.append(fields[col])

        placeholders = ", ".join(["%s"] * len(vals))
        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"INSERT INTO vendors ({', '.join(cols)}) "
                    f"VALUES ({placeholders}) RETURNING *",
                    vals,
                )
                return dict(cur.fetchone())
