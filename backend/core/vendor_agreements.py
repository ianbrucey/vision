"""
Vision — Vendor Teaming Agreements (MTA e-signature).

Implements Contract 1 of the vendor-contract stack: the Master Teaming
Agreement. Vendors execute it in-portal via typed name + explicit checkbox;
the audit trail (identity, exact document hash, timestamp, IP, UA) is the
legal evidence under the E-SIGN Act (15 U.S.C. §7001) / GA UETA
(O.C.G.A. §10-12) — validity comes from intent + attribution, not the medium.

The gate (quote requests blocked until executed) is derived from the
existence of an executed agreement row — no denormalized column.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras

from core.db import connect, insert_document, tx
from core.vendor_profile import VendorProfileManager

TEMPLATE_PATH = (
    Path(__file__).resolve().parents[2]
    / "context-engine" / "templates" / "vendor-contracts" / "01-master-teaming-agreement.md"
)
BSTA_PATH = (
    Path(__file__).resolve().parents[2]
    / "context-engine" / "templates" / "vendor-contracts" / "02-bid-specific-teaming-addendum.md"
)
TEMPLATE_VERSION = "2026-08-16"  # bump when the MTA template or rendering changes

# The built-in PDF fonts (helv/hebo) lack em-dash (U+2014), which renders as
# '·' — wrong for a legal document. Prefer a real Unicode TTF when present;
# fall back to the built-ins if none is found.
_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",  # macOS
    "/Library/Fonts/Arial Unicode.ttf",                      # macOS (alt)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",       # Linux
)
_FONT_ALIAS = "contract"  # internal PDF font name (no spaces allowed)
_FONT_CACHE: dict = {}


def _load_unicode_font() -> str | None:
    """First available Unicode TTF, or None to fall back to built-ins."""
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            return path
    return None


def _get_font(fontfile: str):
    """Cached fitz.Font for width measurement."""
    if fontfile not in _FONT_CACHE:
        import fitz
        _FONT_CACHE[fontfile] = fitz.Font(fontfile=fontfile)
    return _FONT_CACHE[fontfile]


_ID_RE = re.compile(rb"/ID\s*\[[^\]]*\]")


def _stable_hash(data: bytes) -> str:
    """sha256 of PDF bytes with the random trailer /ID stripped.

    PyMuPDF generates a fresh random /ID per render — the only
    byte-level nondeterminism between identical renders. Excluding it
    makes content_hash reproducible from stored inputs (re-render →
    strip /ID → sha256 == DB value) while still binding the row to the
    exact artifact: any content change breaks the hash.
    """
    return hashlib.sha256(_ID_RE.sub(b"", data)).hexdigest()

_FULL = (
    "id, agreement_type, vendor_user_id, solicitation_id, document_id, "
    "naics_code, set_aside_type, contract_type, estimated_value, workshare_pct, "
    "los_applicable, los_check_passed, similarly_situated, similarly_situated_cert, "
    "signed_name, signed_title, signed_ip, signed_user_agent, content_hash, "
    "template_version, status, executed_at, expires_at, created_at, updated_at"
)


def _user_email(user_id: str) -> str:
    """User's email for the template party block (profile has no email)."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row and row[0] else ""
    finally:
        conn.close()


def _fill_template(
    profile: dict, email: str, sig: dict | None = None,
    path: Path = TEMPLATE_PATH,
) -> str:
    """Substitute vendor fields into a vendor-contract markdown template.

    Shared by the MTA (01) and the BSTA form used as Exhibit A (02) — the
    party-block placeholders are identical. sig carries the authorized
    signatory (name/title) for the vendor signature block; when None,
    placeholders are left as-is (preview / form).
    """
    template = path.read_text()

    address = ", ".join(
        p for p in (
            profile.get("address_line1"), profile.get("address_line2"),
            profile.get("city"), profile.get("state"), profile.get("zip"),
        ) if p
    ) or "Address not provided"
    naics = ", ".join(profile.get("naics_codes") or []) or "Not provided"
    date = datetime.now(timezone.utc).strftime("%B %d, %Y")

    subs = {
        "[VENDOR LEGAL BUSINESS NAME]": profile.get("business_name") or "Vendor",
        "[Vendor Physical Address]": address,
        "[Vendor Address]": address,          # BSTA (02) uses the shorter label
        "[Vendor UEI]": profile.get("uei") or "",
        "[Vendor CAGE]": profile.get("cage_code") or "",
        "[Vendor EIN]": profile.get("tax_id") or "",
        "[Vendor NAICS]": naics,
        "[Vendor Email]": email,
        "[Vendor Phone]": profile.get("phone") or "",
    }
    if sig:
        subs["[Authorized Signatory Name]"] = sig.get("name", "")
        subs["[Title]"] = sig.get("title", "")

    for key, value in subs.items():
        template = template.replace(key, value)

    # Both signature pages (JQ + Vendor) share the same effective date.
    template = template.replace(
        "Date: ___________________________________", f"Date: {date}"
    )
    return template


def _exhibit_a(profile: dict, email: str) -> str:
    """Exhibit A — the BSTA form, with the vendor party block filled.

    The MTA's Article 2.2 makes marketing authorization conditional on a
    BSTA 'in the form of Exhibit A'; the vendor must see that form when
    executing the MTA. Solicitation-specific fields stay blank — it is a
    form, not an executed addendum.
    """
    form = _fill_template(profile, email, path=BSTA_PATH)
    return (
        "## EXHIBIT A — BID-SPECIFIC TEAMING ADDENDUM FORM\n\n"
        "This form is incorporated into the Master Teaming Agreement by "
        "reference (Article 2.2). It is NOT executed as part of this "
        "Agreement — it is the form that will be executed separately "
        "before Justice Quest submits a formal offer naming the Vendor "
        "for a specific solicitation.\n\n"
        + form
    )


def _signature_footer(name: str, title: str, ip: str, date_iso: str) -> list[str]:
    """Electronic-execution record appended to the signed PDF."""
    return [
        "",
        "SIGNATURE PAGE — ELECTRONIC EXECUTION",
        f"Signed electronically by: {name}",
        f"Title: {title}",
        f"Date: {date_iso} (UTC)",
        f"IP address: {ip}",
        "This document was executed electronically in accordance with the",
        "Electronic Signatures in Global and National Commerce Act (15 U.S.C. §7001)",
        "and the Georgia Electronic Transactions Act (O.C.G.A. §10-12).",
    ]


def _render_pdf(
    text: str,
    footer_lines: list[str] | None = None,
    exhibit: str | None = None,
    hash_line: str | None = None,
) -> bytes:
    """Render markdown-ish contract text to a letter-size PDF via pymupdf.

    Follows the text-block approach of chat/tools.py convert_docx_to_pdf:
    word-wrap by font metrics, new page at y > 720, markdown stripped
    (headings, bold, tables, blockquotes, horizontal rules).

    Layout order: body → footer (electronic execution record) → exhibit
    (Exhibit A on a fresh page) → hash_line (rendered last so content_hash
    covers everything before it).
    """
    import fitz  # pymupdf — lazy import (chat/tools.py pattern)

    fontfile = _load_unicode_font()
    if fontfile:
        font = _get_font(fontfile)
    else:
        font = None

    pdf_doc = fitz.open()
    page = pdf_doc.new_page(width=612, height=792)  # letter size
    y = 72
    margin_left = 72
    margin_right = 540
    line_height = 14

    def new_page():
        nonlocal page, y
        page = pdf_doc.new_page(width=612, height=792)
        y = 72

    def emit(line: str, fontsize: int = 11, bold: bool = False, gap: int = 4):
        nonlocal y
        words = line.split()
        lines = []
        current = ""
        fontname = _FONT_ALIAS if fontfile else ("hebo" if bold else "helv")
        for word in words:
            test = f"{current} {word}".strip()
            if font is not None:
                tw = font.text_length(test, fontsize=fontsize)
            else:
                tw = fitz.get_text_length(
                    test, fontname=fontname, fontsize=fontsize
                )
            if tw < (margin_right - margin_left):
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        for ln in lines:
            if y > 720:
                new_page()
            kwargs = {}
            if fontfile:
                # Bold via fill+stroke (Arial Unicode has no bold face).
                kwargs = {"fontfile": fontfile, "set_simple": 0}
                if bold:
                    kwargs["render_mode"] = 2
            page.insert_text(
                fitz.Point(margin_left, y + fontsize), ln,
                fontname=fontname, fontsize=fontsize, color=(0, 0, 0),
                **kwargs,
            )
            y += fontsize + 4
        y += gap

    def render_lines(lines: list[str]):
        nonlocal y
        for raw in lines:
            line = raw.strip()
            if not line:
                y += line_height
                continue
            if line.startswith("---"):
                continue  # horizontal rule
            if line.startswith("#"):
                heading = re.sub(r"^#+\s*", "", line)
                size = 18 if line.startswith("# ") else 15 if line.startswith("## ") else 13
                emit(heading, fontsize=size, bold=True, gap=6)
                continue
            if line.startswith("|") and line.endswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                emit(" | ".join(cells), fontsize=9, gap=2)
                continue
            if line.startswith(">"):
                emit(line.lstrip("> "), fontsize=10, gap=3)
                continue
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            emit(clean, fontsize=11, bold=("**" in line))

    render_lines(text.splitlines())

    if footer_lines:
        y += 18
        for fl in footer_lines:
            emit(fl, fontsize=10, gap=3)
        if y > 720:
            new_page()
        page.insert_text(
            fitz.Point(margin_left, y + 10), "=" * 80,
            fontname="helv", fontsize=10, color=(0, 0, 0),
        )

    if exhibit:
        new_page()
        render_lines(exhibit.splitlines())

    if hash_line:
        if y > 700:
            new_page()
        page.insert_text(
            fitz.Point(margin_left, y + 10), hash_line,
            fontname="helv", fontsize=10, color=(0, 0, 0),
        )

    return pdf_doc.tobytes()


class VendorAgreementManager:
    """Stateless CRUD for vendor_teaming_agreements + MTA PDF rendering."""

    def get_status(self, user_id: str) -> dict | None:
        """MTA status for a vendor. None if the user has no profile."""
        profile = VendorProfileManager().get_by_user(user_id)
        if profile is None:
            return None

        agreement = self._get_executed_mta(user_id)
        if agreement:
            return {
                "signed": True,
                "agreement": agreement,
                "document_id": agreement.get("document_id"),
            }

        # Unsigned: render the MTA (party block filled, no signature,
        # Exhibit A attached) and hand back a 1h presigned preview URL.
        # No documents row exists until signing.
        email = _user_email(user_id)
        pdf = _render_pdf(
            _fill_template(profile, email),
            exhibit=_exhibit_a(profile, email),
        )

        from ingestion.storage import get_public_url, upload_attachment
        ref = upload_attachment(f"mta/unsigned/{user_id}.pdf", pdf)
        return {
            "signed": False,
            "agreement": None,
            "document_id": None,
            "preview_url": get_public_url(ref["bucket"], ref["object_key"]),
            "preview_name": (
                f"Master Teaming Agreement - "
                f"{profile.get('business_name') or 'Vendor'}.pdf"
            ),
        }

    def sign(
        self,
        user_id: str,
        signed_name: str,
        signed_title: str,
        consent: bool,
        ip: str | None,
        user_agent: str | None,
    ) -> tuple[dict, bool] | None:
        """Execute the MTA. Returns (agreement, created) or None if the user
        has no profile (route maps to 404).

        Idempotent: an existing executed MTA is returned unchanged
        (created=False). Race-safe via uq_vta_one_executed_mta.
        """
        if consent is not True:
            raise ValueError("You must agree to be legally bound by the Master Teaming Agreement.")
        if not signed_name or not signed_title:
            raise ValueError("Signed name and title are required.")

        profile = VendorProfileManager().get_by_user(user_id)
        if profile is None:
            return None

        # Pass 1: full document with signature block + Exhibit A — this
        # byte stream (minus the random trailer /ID) is what content_hash
        # covers. Pass 2 appends the hash line. exhibit is computed ONCE
        # so pass 2 byte-matches pass 1 + hash line exactly.
        #
        # Verification: re-render pass 1 with the stored inputs (profile,
        # signer, executed_at→UTC as the footer date), strip the trailer
        # /ID, sha256 — must equal content_hash. executed_at is therefore
        # derived HERE, in Python, and written to the row — NOT now() at
        # INSERT — so the re-render is byte-exact.
        email = _user_email(user_id)
        executed_at_dt = datetime.now(timezone.utc)
        date_iso = executed_at_dt.isoformat(timespec="seconds")
        text = _fill_template(
            profile, email, sig={"name": signed_name, "title": signed_title}
        )
        footer = _signature_footer(signed_name, signed_title, ip or "unknown", date_iso)
        exhibit = _exhibit_a(profile, email)
        pass1 = _render_pdf(text, footer, exhibit=exhibit)
        content_hash = _stable_hash(pass1)
        pass2 = _render_pdf(
            text, footer, exhibit=exhibit,
            hash_line=f"Document SHA-256: {content_hash}",
        )

        slug = re.sub(r"[^a-z0-9]+", "-", profile["business_name"].lower()).strip("-") or "vendor"
        object_key = (
            f"mta/signed/{uuid.uuid4().hex[:12]}/"
            f"Master Teaming Agreement - {slug}.pdf"
        )

        from ingestion.storage import delete_file, upload_attachment
        ref = upload_attachment(object_key, pass2)

        try:
            with tx() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        "SELECT 1 FROM vendor_teaming_agreements "
                        "WHERE vendor_user_id = %s AND agreement_type = 'mta' "
                        "AND status = 'executed' LIMIT 1",
                        (user_id,),
                    )
                    if cur.fetchone():
                        return self._get_executed_mta(user_id), False

                    doc_id = insert_document(
                        conn, None, f"Master Teaming Agreement - {slug}.pdf",
                        storage_path=f"{ref['bucket']}/{ref['object_key']}",
                        document_type="contract",
                        source="portal",
                        metadata={"kind": "mta_signed", "template_version": TEMPLATE_VERSION},
                        vendor_user_id=user_id,
                    )
                    cur.execute(
                        f"INSERT INTO vendor_teaming_agreements "
                        f"(agreement_type, vendor_user_id, document_id, status, "
                        f"executed_at, expires_at, signed_name, signed_title, "
                        f"signed_ip, signed_user_agent, content_hash, template_version) "
                        f"VALUES ('mta', %s, %s, 'executed', %s, "
                        f"%s + interval '2 years', %s, %s, %s::inet, %s, %s, %s) "
                        f"RETURNING {_FULL}",
                        (
                            user_id, doc_id, executed_at_dt,
                            executed_at_dt, signed_name, signed_title,
                            ip or None, (user_agent or "")[:512],
                            content_hash, TEMPLATE_VERSION,
                        ),
                    )
                    return dict(cur.fetchone()), True
        except psycopg2.errors.UniqueViolation:
            # Race: another request executed the MTA first — drop our
            # orphan object and return the winner's row.
            delete_file(ref["bucket"], ref["object_key"])
            return self._get_executed_mta(user_id), False
        except Exception:
            # MinIO write precedes DB commit — clean up the orphan object.
            delete_file(ref["bucket"], ref["object_key"])
            raise

    def list(self, agreement_type: str | None = None) -> list[dict]:
        """All agreements, joined with username + document name. Admin only."""
        clauses = ["1 = 1"]
        params: list[str] = []
        if agreement_type:
            clauses.append("vta.agreement_type = %s")
            params.append(agreement_type)

        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"SELECT vta.*, u.username, d.name AS document_name "
                    f"FROM vendor_teaming_agreements vta "
                    f"JOIN users u ON u.id = vta.vendor_user_id "
                    f"LEFT JOIN documents d ON d.id = vta.document_id "
                    f"WHERE {' AND '.join(clauses)} "
                    f"ORDER BY vta.created_at DESC",
                    tuple(params),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def _get_executed_mta(self, user_id: str) -> dict | None:
        conn = connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"SELECT {_FULL} FROM vendor_teaming_agreements "
                    f"WHERE vendor_user_id = %s AND agreement_type = 'mta' "
                    f"AND status = 'executed' ORDER BY id DESC LIMIT 1",
                    (user_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()
