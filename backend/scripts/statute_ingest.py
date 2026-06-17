"""
Vision — Federal Statute Ingestion.

Downloads a U.S. Code subchapter from uscode.house.gov, parses
sections and statutory paragraphs, and inserts into the Vision
database with proper hierarchy and embeddings.

Supports FCRA and FDCPA out of the box. Extensible to any
statute available on uscode.house.gov.

Usage:
    cd backend && python -m scripts.statute_ingest --statute fcra
    cd backend && python -m scripts.statute_ingest --statute fdcpa
    cd backend && python -m scripts.statute_ingest --statute all
    cd backend && python -m scripts.statute_ingest --statute all --no-embed
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from core.db import connect, tx
from core.db import insert_case, insert_document, insert_section, insert_block

# ---------------------------------------------------------------------------
# Statute registry
# ---------------------------------------------------------------------------

STATUTES = {
    "fcra": {
        "name": "FCRA — Fair Credit Reporting Act",
        "url": (
            "https://www.govinfo.gov/content/pkg/"
            "USCODE-2023-title15/html/"
            "USCODE-2023-title15-chap41-subchapIII.htm"
        ),
        "doc_title": "Fair Credit Reporting Act (15 USC §§ 1681-1681x)",
        "sections_range": "§§ 1681 – 1681x",
    },
    "fdcpa": {
        "name": "FDCPA — Fair Debt Collection Practices Act",
        "url": (
            "https://www.govinfo.gov/content/pkg/"
            "USCODE-2023-title15/html/"
            "USCODE-2023-title15-chap41-subchapV.htm"
        ),
        "doc_title": "Fair Debt Collection Practices Act (15 USC §§ 1692-1692p)",
        "sections_range": "§§ 1692 – 1692p",
    },
}

CASE_NAME = "FCRA & FDCPA — Consumer Protection Statutes"
CASE_TYPE = "other"

# ---------------------------------------------------------------------------
# HTML parser
# ---------------------------------------------------------------------------


class _StatuteParser(HTMLParser):
    """Parse uscode.house.gov subchapter HTML.

    Extracts statutory sections (identified by <h3> tags containing §)
    and their body paragraphs (<p class="statutory-body">). Skips
    editorial notes, amendment histories, and other non-statutory content.
    """

    def __init__(self):
        super().__init__()
        self.sections: list[dict[str, Any]] = []
        self._current_section: dict | None = None
        self._current_tag: str | None = None
        self._text_buf: str = ""
        self._in_statutory_body = False
        self._para_order = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attrs_d = dict(attrs)
        classes = (attrs_d.get("class", "") or "").split()
        self._current_tag = tag
        self._text_buf = ""

        # <h3 class="section-head"> marks a new section
        if tag == "h3" and "section-head" in classes:
            return  # section title extracted from handle_data

        # Only <p class="statutory-body*"> is actual statute text
        if tag == "p" and any(c.startswith("statutory-body") for c in classes):
            self._in_statutory_body = True
            self._para_order += 1
            return

    def handle_endtag(self, tag: str):
        if tag == "h3" and self._text_buf.strip():
            text = self._text_buf.strip()
            # Check if this is a section heading (contains §)
            has_section = "§" in text or "&sect;" in text.lower()
            if has_section:
                # Extract section number from pattern like "§ 1681."
                num_match = re.search(
                    r"(?:§|&sect;)\s*(\d+[a-z]*(?:\.\d+)?)",
                    text,
                )
                section_number = num_match.group(1) if num_match else ""
                # Clean title: remove HTML tags and § prefix
                clean_title = re.sub(r"<[^>]+>", "", text).strip()
                clean_title = re.sub(r"^§\s*\d+[a-z]*\.?\s*", "", clean_title).strip()

                self._current_section = {
                    "number": section_number,
                    "title": clean_title,
                    "paragraphs": [],
                    "datalab_id": f"/section/{section_number}",
                }
                self.sections.append(self._current_section)

        elif tag == "p" and self._in_statutory_body:
            self._in_statutory_body = False
            if self._current_section is not None and self._text_buf.strip():
                # Strip HTML tags from paragraph text
                clean_text = re.sub(r"<[^>]+>", " ", self._text_buf.strip())
                clean_text = re.sub(r"\s+", " ", clean_text).strip()
                if clean_text:
                    self._current_section["paragraphs"].append(clean_text)

        self._current_tag = None
        self._text_buf = ""

    def handle_data(self, data: str):
        if self._current_tag in ("h3", "p"):
            self._text_buf += data

    def handle_entityref(self, name: str):
        if self._current_tag in ("h3", "p"):
            self._text_buf += f"&{name};"


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------


def _ensure_case(conn, case_name: str, case_type: str) -> int:
    """Get or create a case by name. Returns case_id."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM cases WHERE name = %s AND case_type = %s",
            (case_name, case_type),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        return insert_case(conn, name=case_name, case_type=case_type)


def _ingest_document(
    conn,
    case_id: int,
    doc_title: str,
    sections: list[dict],
) -> int:
    """Create a document with sections and blocks from parsed data."""
    doc_id = insert_document(
        conn,
        case_id=case_id,
        name=doc_title,
        page_count=1,
        document_type="other",
        source="other",
    )

    for i, sec in enumerate(sections):
        section_id = insert_section(
            conn,
            document_id=doc_id,
            datalab_id=sec["datalab_id"],
            heading_level=1,
            title=sec["title"],
            page_start=1,
            page_end=1,
            block_count=len(sec["paragraphs"]),
            search_text=f"§ {sec['number']}. {sec['title']}\n\n"
            + "\n".join(sec["paragraphs"]),
            heading_chain=[sec["title"]],
        )

        for j, para_text in enumerate(sec["paragraphs"]):
            insert_block(
                conn,
                document_id=doc_id,
                datalab_id=f"{sec['datalab_id']}/paragraph/{j+1}",
                section_id=section_id,
                block_type="Text",
                page=1,
                text_content=para_text,
            )

    return doc_id


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------


def _embed_document(document_id: int) -> None:
    """Generate Mistral embeddings for all sections in a document."""
    from search.embed import embed_document as _embed_doc
    start = time.time()
    _embed_doc(document_id)
    elapsed = time.time() - start
    print(f"  Embedding complete ({elapsed:.1f}s)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _fetch_html(url: str) -> str:
    """Download HTML from a URL."""
    print(f"  Downloading: {url}")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; Vision/1.0; +https://vision.local)"
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def _parse(html: str) -> list[dict]:
    """Parse HTML into structured sections."""
    parser = _StatuteParser()
    parser.feed(html)
    return parser.sections


def main() -> int:
    ap = argparse.ArgumentParser(description="Vision — Statute Ingestion")
    ap.add_argument(
        "--statute",
        choices=["fcra", "fdcpa", "all"],
        default="all",
        help="Which statute to ingest (default: all)",
    )
    ap.add_argument(
        "--no-embed",
        action="store_true",
        help="Skip Mistral embedding",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and count without inserting",
    )
    args = ap.parse_args()

    statutes_to_run = (
        list(STATUTES.keys()) if args.statute == "all" else [args.statute]
    )

    print("=" * 60)
    print("Vision — Statute Ingestion")
    print("=" * 60)

    for key in statutes_to_run:
        info = STATUTES[key]
        print(f"\n{'='*60}")
        print(f"Ingesting: {info['name']}")
        print(f"Source:    {info['url']}")
        print(f"Document:  {info['doc_title']}")
        print(f"{'='*60}")

        # Fetch
        html = _fetch_html(info["url"])

        # Parse
        sections = _parse(html)
        if not sections:
            print("  ERROR: No sections parsed. Check the URL and HTML structure.")
            return 1

        para_count = sum(len(s["paragraphs"]) for s in sections)
        print(f"  Parsed: {len(sections)} sections, {para_count} paragraphs")

        if args.dry_run:
            print("\n  Sections found:")
            for s in sections:
                print(
                    f"    § {s['number']}: {s['title'][:80]} "
                    f"({len(s['paragraphs'])} paragraphs)"
                )
            continue

        # Insert
        with tx() as conn:
            case_id = _ensure_case(conn, CASE_NAME, CASE_TYPE)
            print(f"  Case ID: {case_id}")

            doc_id = _ingest_document(conn, case_id, info["doc_title"], sections)
            print(f"  Document ID: {doc_id}")

        # Embed
        if not args.no_embed:
            _embed_document(doc_id)

        print(f"  ✅ Done — {info['name']}")

    print(f"\n{'='*60}")
    print("Ingestion complete.")
    print(f"Case: {CASE_NAME}")

    if not args.dry_run and not args.no_embed:
        print("Embeddings generated for semantic search.")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
