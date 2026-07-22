"""
Vision — Vendor Match Data Layer.

Provides VendorMatchManager: tiered candidate-pool SQL (exact NAICS ->
NAICS family -> capabilities FTS, set-aside hard-gated, capped at 300),
plus save/list for the `vendor_matches` table. Sibling to
core/solicitation.py — see context-engine/specs/vendor-matching/.

Usage:
    from core.vendor_match import VendorMatchManager
    mgr = VendorMatchManager()
    pool = mgr.build_candidate_pool(naics_code="541511", set_aside_type="SDVOSB Set-Aside")
    mgr.save_matches(solicitation_id, ranked_matches)
    matches = mgr.list_for_solicitation(solicitation_id)
"""

from __future__ import annotations

from typing import Any

import os

import psycopg2.extras

from core.db import connect, tx

# vendors.contact_email sentinel — SBA/GSA source data uses this literal
# string in ~137k rows to mean "no public email available". Must never be
# surfaced to the API/UI as a real address.
CONTACT_EMAIL_SENTINEL = "The business owner has hidden this information from public searches"

# solicitations.set_aside_type is free-text SAM.gov copy (e.g. "SDVOSB
# Set-Aside"). Matched case-insensitively by substring against known
# keywords, in priority order (first match wins), to a vendors.is_* column.
_SET_ASIDE_KEYWORDS: list[tuple[str, str]] = [
    ("SDVOSB", "is_sdvosb"),
    ("SERVICE-DISABLED VETERAN", "is_sdvosb"),
    ("8(A)", "is_8a"),
    ("8A", "is_8a"),
    ("HUBZONE", "is_hubzone"),
    ("WOSB", "is_woman_owned"),
    ("WOMEN-OWNED", "is_woman_owned"),
    ("WOMEN OWNED", "is_woman_owned"),
    ("VOSB", "is_veteran_owned"),
    ("VETERAN-OWNED", "is_veteran_owned"),
    ("SMALL BUSINESS", "is_small_business"),
    ("SB SET-ASIDE", "is_small_business"),
]

_VENDOR_COLS = (
    "vendor_name, contact_name, contact_email, contact_phone, "
    "state, city, naics_code_primary, "
    "is_small_business, is_sdvosb, is_hubzone, is_8a, "
    "is_woman_owned, is_veteran_owned"
)


def _set_aside_column(set_aside_type: str | None) -> str | None:
    """Map a free-text set-aside description to a vendors.is_* column.

    Returns None if unrecognized/absent — no gate applied (open pool).
    """
    if not set_aside_type:
        return None
    upper = set_aside_type.upper()
    for keyword, column in _SET_ASIDE_KEYWORDS:
        if keyword in upper:
            return column
    return None


class VendorMatchManager:
    """Stateless operations for the vendor_matches table + candidate pooling."""

    def build_candidate_pool(
        self,
        naics_code: str,
        set_aside_type: str | None = None,
        cap: int = 300,
    ) -> list[dict]:
        """Tiered candidate pool: exact NAICS -> NAICS family -> capabilities FTS.

        Each tier is only queried if the pool so far is below `cap`. Rows are
        deduplicated across tiers (by vendors.id) and tagged with
        `naics_match_type` ('exact' | 'family' | 'capability_only').
        A set-aside hard gate (if resolvable) is applied identically at every
        tier via `_set_aside_column`.
        """
        gate_col = _set_aside_column(set_aside_type)
        gate_sql = f" AND {gate_col} = TRUE" if gate_col else ""

        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                pool: dict[int, dict] = {}

                # Tier 1: exact NAICS match
                cur.execute(
                    f"SELECT id, {_VENDOR_COLS} FROM vendors "
                    f"WHERE naics_code_primary = %s{gate_sql} "
                    f"LIMIT %s",
                    (naics_code, cap),
                )
                for row in cur.fetchall():
                    row = dict(row)
                    row["naics_match_type"] = "exact"
                    pool[row["id"]] = row

                # Tier 2: NAICS family (first 4 digits)
                if len(pool) < cap and len(naics_code) >= 4:
                    family = naics_code[:4]
                    remaining = cap - len(pool)
                    cur.execute(
                        f"SELECT id, {_VENDOR_COLS} FROM vendors "
                        f"WHERE naics_code_primary LIKE %s "
                        f"AND naics_code_primary != %s{gate_sql} "
                        f"LIMIT %s",
                        (f"{family}%", naics_code, remaining),
                    )
                    for row in cur.fetchall():
                        row = dict(row)
                        if row["id"] in pool:
                            continue
                        row["naics_match_type"] = "family"
                        pool[row["id"]] = row

                # Tier 3: capabilities full-text search, seeded from the
                # NAICS code itself (no external description lookup available
                # in this data layer — the agent pipeline may supplement with
                # richer query terms from the solicitation's scope-of-work
                # artifact before calling this tier if needed).
                if len(pool) < cap:
                    remaining = cap - len(pool)
                    # Must match idx_vendors_fts's indexed expression exactly
                    # (vendor_name || ' ' || capabilities) to use the GIN
                    # index instead of a sequential scan over 5.5M rows.
                    cur.execute(
                        f"SELECT id, {_VENDOR_COLS} FROM vendors "
                        f"WHERE capabilities IS NOT NULL "
                        f"AND to_tsvector('english', coalesce(vendor_name, '') || ' ' || coalesce(capabilities, '')) "
                        f"@@ plainto_tsquery('english', %s){gate_sql} "
                        f"LIMIT %s",
                        (naics_code, remaining),
                    )
                    for row in cur.fetchall():
                        row = dict(row)
                        if row["id"] in pool:
                            continue
                        row["naics_match_type"] = "capability_only"
                        pool[row["id"]] = row

                return list(pool.values())[:cap]
        finally:
            conn.close()

    def save_matches(self, solicitation_id: int, matches: list[dict]) -> None:
        """Delete-then-insert: replaces all vendor_matches for this solicitation.

        Each match dict must contain: vendor_id, rank, match_score,
        match_rationale, naics_match_type.
        """
        with tx() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM vendor_matches WHERE solicitation_id = %s",
                    (solicitation_id,),
                )
                for m in matches:
                    cur.execute(
                        """INSERT INTO vendor_matches
                               (solicitation_id, vendor_id, rank, match_score,
                                match_rationale, naics_match_type)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (
                            solicitation_id,
                            m["vendor_id"],
                            m["rank"],
                            m["match_score"],
                            m["match_rationale"],
                            m["naics_match_type"],
                        ),
                    )

    def attach_manual_vendor(self, solicitation_id: int, vendor_id: int) -> dict:
        """Attach a manually-created vendor to a solicitation's match list.

        Assigns the next available rank (max existing rank + 1). The hard
        cap is 30 (requires migration 012) — 5 slots of headroom above the
        25 automated matching ever produces, so a manual add only competes
        for space with other manual adds. If the solicitation is already
        at the cap, the single lowest-ranked (worst) match is evicted
        (deleted) to make room, and the new vendor takes the vacated last
        slot. match_score is a fixed 100 (treated as fully curated — the
        user picked this vendor deliberately). naics_match_type is
        'manual' (requires migration 011). Raises ValueError if this
        vendor is already attached (UNIQUE (solicitation_id, vendor_id)).
        """
        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT 1 FROM vendor_matches "
                    "WHERE solicitation_id = %s AND vendor_id = %s",
                    (solicitation_id, vendor_id),
                )
                if cur.fetchone():
                    raise ValueError("This vendor is already matched to this solicitation")

                cur.execute(
                    "SELECT COALESCE(MAX(rank), 0) AS max_rank FROM vendor_matches "
                    "WHERE solicitation_id = %s",
                    (solicitation_id,),
                )
                next_rank = cur.fetchone()["max_rank"] + 1

                if next_rank > 30:
                    # At cap — evict the single worst-ranked match to make room.
                    cur.execute(
                        "DELETE FROM vendor_matches WHERE id = (\n"
                        "    SELECT id FROM vendor_matches\n"
                        "    WHERE solicitation_id = %s\n"
                        "    ORDER BY rank DESC LIMIT 1\n"
                        ")",
                        (solicitation_id,),
                    )
                    next_rank = 30

                cur.execute(
                    """INSERT INTO vendor_matches
                           (solicitation_id, vendor_id, rank, match_score,
                            match_rationale, naics_match_type)
                       VALUES (%s, %s, %s, 100, %s, 'manual')
                       RETURNING id""",
                    (
                        solicitation_id,
                        vendor_id,
                        next_rank,
                        "Manually added by user.",
                    ),
                )
                new_id = cur.fetchone()["id"]

        return self.get_match(new_id)

    def get_match(self, match_id: int) -> dict:
        """Single vendor_matches row joined with vendor fields, by match id."""
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT
                           vm.id, vm.external_id, vm.solicitation_id, vm.vendor_id,
                           vm.rank, vm.match_score, vm.match_rationale,
                           vm.naics_match_type, vm.created_at,
                           vm.outreach_status, vm.outreach_requested_at,
                           vm.outreach_received_at, vm.outreach_doc_id,
                           d.name AS outreach_doc_name,
                           v.vendor_name, v.contact_name,
                           CASE WHEN v.contact_email = %s THEN NULL
                                ELSE v.contact_email END AS contact_email,
                           v.contact_phone, v.website, v.state, v.city,
                           v.naics_code_primary,
                           v.is_small_business, v.is_sdvosb, v.is_hubzone,
                           v.is_8a, v.is_woman_owned, v.is_veteran_owned
                       FROM vendor_matches vm
                       JOIN vendors v ON v.id = vm.vendor_id
                       LEFT JOIN documents d ON d.id = vm.outreach_doc_id
                       WHERE vm.id = %s""",
                    (CONTACT_EMAIL_SENTINEL, match_id),
                )
                return dict(cur.fetchone())
        finally:
            conn.close()

    def list_for_solicitation(self, solicitation_id: int) -> list[dict]:
        """Ranked vendor_matches joined with vendor contact/capability fields.

        Sentinel-masked contact_email is converted to NULL at read time.
        """
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT
                           vm.id, vm.external_id, vm.solicitation_id, vm.vendor_id,
                           vm.rank, vm.match_score, vm.match_rationale,
                           vm.naics_match_type, vm.created_at,
                           vm.outreach_status, vm.outreach_requested_at,
                           vm.outreach_received_at, vm.outreach_doc_id,
                           d.name AS outreach_doc_name,
                           v.vendor_name, v.contact_name,
                           CASE WHEN v.contact_email = %s THEN NULL
                                ELSE v.contact_email END AS contact_email,
                           v.contact_phone, v.website, v.state, v.city,
                           v.naics_code_primary,
                           v.is_small_business, v.is_sdvosb, v.is_hubzone,
                           v.is_8a, v.is_woman_owned, v.is_veteran_owned
                       FROM vendor_matches vm
                       JOIN vendors v ON v.id = vm.vendor_id
                       LEFT JOIN documents d ON d.id = vm.outreach_doc_id
                       WHERE vm.solicitation_id = %s
                       ORDER BY vm.rank ASC""",
                    (CONTACT_EMAIL_SENTINEL, solicitation_id),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def update_outreach(
        self,
        match_id: int,
        outreach_status: str | None = None,
        outreach_doc_id: int | None = None,
        clear_outreach_doc: bool = False,
    ) -> dict:
        """Update outreach tracking fields on a vendor_matches row (T8).

        `outreach_status` transitions set companion timestamps automatically:
        moving to 'requested' stamps `outreach_requested_at` (if not already
        set), moving to 'received' stamps `outreach_received_at` (if not
        already set). Moving back to 'not_contacted' or 'declined' does not
        clear timestamps — they remain a historical record of when contact
        was first made / a response first arrived.

        `outreach_doc_id` links a received document to this match (e.g. a
        quote). Pass `clear_outreach_doc=True` to detach it (sets NULL);
        otherwise a `None` value for `outreach_doc_id` leaves it unchanged.

        Raises ValueError if `outreach_status` is not a recognized value, or
        if `outreach_doc_id` does not reference an existing document.
        """
        valid_statuses = {"not_contacted", "requested", "received", "declined"}
        if outreach_status is not None and outreach_status not in valid_statuses:
            raise ValueError(
                f"Invalid outreach_status '{outreach_status}'; "
                f"must be one of {sorted(valid_statuses)}"
            )

        sets: list[str] = []
        params: list[Any] = []

        if outreach_status is not None:
            sets.append("outreach_status = %s")
            params.append(outreach_status)
            if outreach_status == "requested":
                sets.append(
                    "outreach_requested_at = COALESCE(outreach_requested_at, now())"
                )
            elif outreach_status == "received":
                sets.append(
                    "outreach_received_at = COALESCE(outreach_received_at, now())"
                )

        if clear_outreach_doc:
            sets.append("outreach_doc_id = NULL")
        elif outreach_doc_id is not None:
            sets.append("outreach_doc_id = %s")
            params.append(outreach_doc_id)

        if not sets:
            return self.get_match(match_id)

        sets.append("updated_at = now()")
        params.append(match_id)

        with tx() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        f"UPDATE vendor_matches SET {', '.join(sets)} WHERE id = %s",
                        tuple(params),
                    )
                except psycopg2.errors.ForeignKeyViolation:
                    raise ValueError(
                        f"Document {outreach_doc_id} does not exist"
                    )
                if cur.rowcount == 0:
                    raise ValueError(f"Vendor match {match_id} not found")

        return self.get_match(match_id)

    def find_by_reply_token(self, token: str) -> dict | None:
        """Look up a vendor match by its outreach_reply_token (T10b).

        Used exclusively by the inbound webhook handler to correlate a
        reply back to the vendor match that sent the original outreach.
        Joins to solicitations for case_id (needed to enqueue the ingest
        job under the right case).
        """
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT vm.id, vm.solicitation_id, vm.vendor_id,
                              s.case_id
                       FROM vendor_matches vm
                       JOIN solicitations s ON s.id = vm.solicitation_id
                       WHERE vm.outreach_reply_token = %s""",
                    (token,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def mark_email_sent(self, match_id: int, message_id: str, reply_token: str) -> dict:
        """Record a successful outbound send (T10a).

        Sets outreach_message_id + outreach_reply_token, and moves
        outreach_status to 'requested' (via the same
        COALESCE(outreach_requested_at, now()) semantics as
        update_outreach, so this is safe to call even if the status was
        already 'requested' from a prior manual toggle).
        """
        with tx() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE vendor_matches
                       SET outreach_message_id = %s,
                           outreach_reply_token = %s,
                           outreach_status = 'requested',
                           outreach_requested_at = COALESCE(outreach_requested_at, now()),
                           updated_at = now()
                       WHERE id = %s""",
                    (message_id, reply_token, match_id),
                )
                if cur.rowcount == 0:
                    raise ValueError(f"Vendor match {match_id} not found")
        return self.get_match(match_id)

    # ------------------------------------------------------------------
    # T10c — Per-vendor message thread
    # ------------------------------------------------------------------

    def find_message_by_reply_token(self, token: str) -> dict | None:
        """Look up a vendor_outreach_messages row + case_id by reply_token.

        Used by the inbound webhook to correlate a reply to the message
        that was sent. Mirrors the old find_by_reply_token (T10b) but
        sources from vendor_outreach_messages instead of vendor_matches.
        """
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT vom.id, vom.vendor_match_id,
                              s.case_id
                       FROM vendor_outreach_messages vom
                       JOIN vendor_matches vm ON vm.id = vom.vendor_match_id
                       JOIN solicitations s ON s.id = vm.solicitation_id
                       WHERE vom.reply_token = %s""",
                    (token,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def create_draft_message(self, match_id: int) -> dict:
        """Create (or return existing) draft outbound message for a match.

        Idempotent: if a draft already exists for this match_id, returns it
        unchanged rather than creating a duplicate. Substitutes
        {{vendor_name}}/{{match_reason}} into the solicitation's
        outreach_email_subject/body (same substitution as the old
        send_outreach_email_endpoint). Raises ValueError if the match has
        no contact_email, or the solicitation has no
        outreach_email_subject/body.
        """
        match = self.get_match(match_id)
        if match is None:
            raise ValueError(f"Vendor match {match_id} not found")
        if not match.get("contact_email"):
            raise ValueError("This vendor has no email on file")

        # Check for existing draft
        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM vendor_outreach_messages
                       WHERE vendor_match_id = %s AND direction = 'outbound'
                       AND status = 'draft'""",
                    (match_id,),
                )
                existing = cur.fetchone()
                if existing:
                    return dict(existing)

        # Fetch solicitation template
        from core.solicitation import SolicitationManager
        sol = SolicitationManager().get(match["solicitation_id"])
        subject = sol.get("outreach_email_subject") if sol else None
        body = sol.get("outreach_email_body") if sol else None
        if not subject or not body:
            raise ValueError(
                "Solicitation has no outreach email template — run vendor matching first"
            )

        subject = subject.replace("{{vendor_name}}", match["vendor_name"])
        body = (
            body.replace("{{vendor_name}}", match["vendor_name"])
                .replace("{{match_reason}}", match["match_rationale"])
        )

        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO vendor_outreach_messages
                       (vendor_match_id, direction, status, subject, body)
                       VALUES (%s, 'outbound', 'draft', %s, %s)
                       RETURNING *""",
                    (match_id, subject, body),
                )
                return dict(cur.fetchone())

    def list_messages(self, match_id: int) -> list[dict]:
        """All messages for a match, chronological (created_at ASC)."""
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT vom.*, d.name AS document_name
                       FROM vendor_outreach_messages vom
                       LEFT JOIN documents d ON d.id = vom.document_id
                       WHERE vom.vendor_match_id = %s
                       ORDER BY vom.created_at ASC""",
                    (match_id,),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def mark_messages_read(self, match_id: int) -> None:
        """Mark all unread inbound messages in a thread as read."""
        with tx() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE vendor_outreach_messages
                       SET read_at = now()
                       WHERE vendor_match_id = %s
                         AND direction = 'inbound'
                         AND read_at IS NULL""",
                    (match_id,),
                )

    def update_draft_message(
        self, message_id: int, subject: str | None = None, body: str | None = None
    ) -> dict:
        """Edit a draft's subject/body. Raises ValueError if the message is
        not status='draft' (sent/failed messages are immutable)."""
        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM vendor_outreach_messages WHERE id = %s",
                    (message_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError(f"Message {message_id} not found")
                if row["status"] != "draft":
                    raise ValueError("Only draft messages can be edited")

                sets = []
                params = []
                if subject is not None:
                    sets.append("subject = %s")
                    params.append(subject)
                if body is not None:
                    sets.append("body = %s")
                    params.append(body)
                if not sets:
                    return dict(row)

                sets.append("updated_at = now()")
                params.append(message_id)

                cur.execute(
                    f"UPDATE vendor_outreach_messages SET {', '.join(sets)} WHERE id = %s RETURNING *",
                    tuple(params),
                )
                return dict(cur.fetchone())

    def send_message(self, message_id: int) -> dict:
        """Send a draft message via Mailgun. Generates reply_token, sets
        Reply-To: vmatch-{token}@{MAILGUN_DOMAIN}, calls send_email(). On
        success: status='sent', sent_at=now(), mailgun_message_id set; also
        updates the parent vendor_matches row to outreach_status='requested'
        for rollup display in OutreachTab/VendorMatchesTab. Raises ValueError
        if message is not status='draft'."""
        import secrets

        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM vendor_outreach_messages WHERE id = %s",
                    (message_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError(f"Message {message_id} not found")
                if row["status"] != "draft":
                    raise ValueError("Only draft messages can be sent")
                msg = dict(row)

        # Look up match for contact_email
        match = self.get_match(msg["vendor_match_id"])
        if match is None or not match.get("contact_email"):
            raise ValueError("Vendor has no contact email")

        reply_token = secrets.token_hex(8)
        reply_domain = os.environ.get("MAILGUN_DOMAIN") or os.environ.get("MAILGUN_SANDBOX_DOMAIN", "")
        reply_to = f"vmatch-{reply_token}@{reply_domain}"

        from core.email_mailgun import send_email, MailgunSendError

        try:
            result = send_email(
                to_email=match["contact_email"],
                to_name=match["vendor_name"],
                subject=msg["subject"],
                text_body=msg["body"],
                reply_to=reply_to,
            )
        except MailgunSendError:
            # Mark as failed
            with tx() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE vendor_outreach_messages
                           SET status = 'failed', error_message = 'Mailgun send failed',
                               updated_at = now()
                           WHERE id = %s""",
                        (message_id,),
                    )
            raise

        # Mark sent
        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """UPDATE vendor_outreach_messages
                       SET status = 'sent', sent_at = now(),
                           mailgun_message_id = %s, reply_token = %s,
                           updated_at = now()
                       WHERE id = %s
                       RETURNING *""",
                    (result["id"], reply_token, message_id),
                )
                updated = dict(cur.fetchone())

        # Rollup — also write legacy vendor_matches columns for compat
        self.mark_email_sent(msg["vendor_match_id"], result["id"], reply_token)

        return updated

    def record_inbound_message(
        self, vendor_match_id: int, subject: str, body: str, document_id: int
    ) -> dict:
        """Insert an inbound message row for a received reply (T10c).

        Called by process_inbound_email_job after storing the document.
        """
        with tx() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO vendor_outreach_messages
                       (vendor_match_id, direction, status, subject, body,
                        document_id, received_at)
                       VALUES (%s, 'inbound', 'received', %s, %s, %s, now())
                       RETURNING *""",
                    (vendor_match_id, subject, body, document_id),
                )
                return dict(cur.fetchone())
