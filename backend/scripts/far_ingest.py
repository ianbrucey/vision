"""
Vision — FAR Ingestion.

Downloads the Federal Acquisition Regulation HTML ZIP from acquisition.gov,
parses the structured HTML (Part → Subpart → Section → paragraphs), and
inserts into the Vision database with proper section hierarchy and embeddings.

The FAR is Title 48 of the CFR. It's published at:
    https://www.acquisition.gov/browse/index/far

One document per Part (53 total, 2 reserved). Each section's paragraphs
become blocks. Sections are embedded via Mistral for semantic search.

Usage:
    cd backend && python -m scripts.far_ingest
    cd backend && python -m scripts.far_ingest --skip-download  # use cached ZIP
    cd backend && python -m scripts.far_ingest --no-embed       # skip embedding
    cd backend && python -m scripts.far_ingest --part 15        # single part
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
import time
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve

from core.db import connect, tx
from core.db import (
    insert_case,
    insert_document,
    insert_section,
    insert_block,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAR_ZIP_URL = (
    "https://www.acquisition.gov/sites/default/files/"
    "current/far/zip/html/FARHTML.zip"
)
FAR_CASE_NAME = "FAR — Federal Acquisition Regulation"
FAR_CASE_TYPE = "other"
RESERVED_PARTS = {20, 21}
TEMP_DIR = Path(tempfile.gettempdir()) / "vision-far-ingest"

# Regex to parse file names like "1.106.html", "1.102-1.html", "Part_1.html"
SECTION_FILE_RE = re.compile(r"^(\d+)\.(\d+(?:-\d+)?)\.html$")
PART_FILE_RE = re.compile(r"^Part_(\d+)\.html$")
SUBPART_FILE_RE = re.compile(r"^Subpart_(\d+\.\d+)\.html$")


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


class _TOCParser(HTMLParser):
    """Parse a Part overview page to extract the TOC hierarchy.

    Classes are on the <p> tags, not the <a> tags. We track the current
    paragraph level and apply it to links inside.
    """

    def __init__(self):
        super().__init__()
        self.entries: list[dict[str, Any]] = []
        self._current_p_level: int | None = None
        self._in_link = False
        self._link_text = ""
        self._link_href = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attrs_d = dict(attrs)
        classes = attrs_d.get("class", "").split()

        if tag == "p":
            # Determine level from paragraph class
            for cls in classes:
                if cls == "ListL1":
                    self._current_p_level = 1
                elif cls == "ListL2":
                    self._current_p_level = 2
                elif cls == "ListL3":
                    self._current_p_level = 3
            if "Subpart" in classes:
                self._current_p_level = 1

        elif tag == "a" and self._current_p_level is not None:
            self._link_href = attrs_d.get("href", "")
            self._in_link = True
            self._link_text = ""

    def handle_endtag(self, tag: str):
        if tag == "a" and self._in_link:
            self._in_link = False
            title = self._link_text.strip()
            if not title or not self._link_href:
                return

            # Parse number from title
            number = ""
            if title.startswith("Subpart "):
                number = title.split(" - ")[0].replace("Subpart ", "").strip()
            else:
                parts = title.split(" ", 1)
                if parts:
                    number = parts[0].rstrip(".")

            self.entries.append({
                "level": self._current_p_level,
                "number": number,
                "title": title,
                "href": self._link_href,
            })

        elif tag == "p":
            self._current_p_level = None

    def handle_data(self, data: str):
        if self._in_link:
            self._link_text += data


class _SectionParser(HTMLParser):
    """Parse a single FAR section HTML file.

    Extracts:
      section_number: "1.106"
      section_title: "OMB approval under the Paperwork Reduction Act."
      paragraphs: list of plain-text paragraph strings
      html_body: raw inner HTML for storage
    """

    def __init__(self):
        super().__init__()
        self.section_number = ""
        self.section_title = ""
        self.paragraphs: list[str] = []
        self.html_body = ""
        self._in_title = False
        self._in_body = False
        self._in_autonumber = False
        self._current_text = ""
        self._skip_depth = 0
        self._para_texts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attrs_d = dict(attrs)
        classes = attrs_d.get("class", "").split()

        if "topictitle1" in classes or "title" in classes:
            self._in_title = True
        if "autonumber" in classes and self._in_title:
            # Only capture autonumber inside the H1 heading.
            # Sub-clause labels like (a), (b), (c) in the body are
            # paragraph content, not section numbers.
            self._in_autonumber = True
        if "conbody" in classes or "body" in classes:
            self._in_body = True
            self._in_title = False  # heading is done — body autonumbers are text
        if self._in_body and tag in ("p", "li", "td", "th"):
            self._current_text = ""
        # Capture autonumber text inside body paragraphs as part of the text
        if self._in_body and "autonumber" in classes:
            self._current_text += ""  # text will be captured in handle_data

    def handle_endtag(self, tag: str):
        if self._in_autonumber and tag == "span" and not self._in_body:
            self._in_autonumber = False
        if tag == "h1":
            self._in_title = False
        if self._in_body and tag in ("p", "li"):
            text = self._current_text.strip()
            if text and len(text) > 10:  # skip empty/near-empty
                self.paragraphs.append(text)
            self._current_text = ""

    def handle_data(self, data: str):
        if self._in_autonumber:
            self.section_number = data.strip()
        elif self._in_title and not self._in_autonumber:
            self.section_title += data
        if self._in_body:
            self._current_text += data

    def error(self, message: str):
        pass  # suppress parse errors for malformed HTML


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _ensure_far_case() -> int:
    """Get or create the FAR reference case. Returns case_id."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM cases WHERE name = %s AND case_type = 'other'",
                (FAR_CASE_NAME,),
            )
            row = cur.fetchone()
            if row:
                case_id = row[0]
                print(f"Found existing FAR case: case_id={case_id}")
                return case_id
    finally:
        conn.close()

    with tx() as conn:
        case_id = insert_case(conn, name=FAR_CASE_NAME, case_type=FAR_CASE_TYPE)
    print(f"Created FAR case: case_id={case_id}")
    return case_id


def _parse_part_toc(html_path: Path) -> list[dict[str, Any]]:
    """Parse a Part overview HTML for its TOC hierarchy."""
    parser = _TOCParser()
    parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
    return parser.entries


def _parse_section_html(html_path: Path) -> dict[str, Any]:
    """Parse a section HTML file for content."""
    parser = _SectionParser()
    parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
    return {
        "number": parser.section_number,
        "title": parser.section_title.strip(),
        "paragraphs": parser.paragraphs,
    }


def _build_part_hierarchy(
    extract_dir: Path, part_num: int
) -> list[dict[str, Any]]:
    """Build a nested hierarchy for a FAR Part.

    Returns list of top-level entries (subparts), each containing child
    sections and subsections with their parsed paragraph content.
    """
    part_file = extract_dir / f"Part_{part_num}.html"
    if not part_file.exists():
        print(f"  Part {part_num}: no Part_{part_num}.html — skipping")
        return []

    toc = _parse_part_toc(part_file)
    if not toc:
        print(f"  Part {part_num}: empty TOC — skipping")
        return []

    # Build hierarchy: Subpart → Section → Subsection
    subparts: list[dict[str, Any]] = []
    current_subpart: dict[str, Any] | None = None
    current_section: dict[str, Any] | None = None

    for entry in toc:
        level = entry["level"]

        if level == 1:  # Subpart
            current_subpart = {
                "number": entry["number"],
                "title": entry["title"],
                "sections": [],
            }
            subparts.append(current_subpart)
            current_section = None

        elif level == 2:  # Section
            href_clean = entry["href"].split("#")[0]
            html_path = extract_dir / href_clean
            sec_data: dict[str, Any] = {
                "number": entry["number"],
                "title": entry["title"],
            }
            if html_path.exists():
                parsed = _parse_section_html(html_path)
                sec_data["number"] = parsed["number"] or entry["number"]
                sec_data["title"] = parsed["title"] or entry["title"]
                sec_data["paragraphs"] = parsed["paragraphs"]
            else:
                sec_data["paragraphs"] = []
            sec_data["subsections"] = []

            current_section = sec_data
            if current_subpart:
                current_subpart["sections"].append(sec_data)

        elif level == 3:  # Subsection
            href_clean = entry["href"].split("#")[0]
            html_path = extract_dir / href_clean
            sub_data: dict[str, Any] = {
                "number": entry["number"],
                "title": entry["title"],
            }
            if html_path.exists():
                parsed = _parse_section_html(html_path)
                sub_data["number"] = parsed["number"] or entry["number"]
                sub_data["title"] = parsed["title"] or entry["title"]
                sub_data["paragraphs"] = parsed["paragraphs"]
            else:
                sub_data["paragraphs"] = []

            if current_section:
                current_section["subsections"].append(sub_data)
            elif current_subpart:
                current_subpart["sections"].append(sub_data)

    return subparts


def _build_search_text(title: str, paragraphs: list[str]) -> str:
    """Build search_text for a section: title + first ~16K chars of body."""
    body = title + "\n\n" + "\n".join(paragraphs)
    return body[:16_000]


def _ingest_part(
    case_id: int,
    extract_dir: Path,
    part_num: int,
    dry_run: bool = False,
) -> dict[str, int]:
    """Ingest one FAR Part as a document with sections and blocks.

    Hierarchy:
      Document (= Part)
        Section (= Subpart, heading_level=1)
          Section (= Section, heading_level=2)
            Section (= Subsection, heading_level=3)
              Block (= paragraph)
    """
    hierarchy = _build_part_hierarchy(extract_dir, part_num)
    if not hierarchy:
        return {"subparts": 0, "sections": 0, "subsections": 0, "blocks": 0}

    part_title = f"Part {part_num}"
    part_file = extract_dir / f"Part_{part_num}.html"
    if part_file.exists():
        import re as _re
        text = part_file.read_text(encoding="utf-8", errors="replace")
        m = _re.search(r"<title>(.*?)</title>", text, _re.DOTALL)
        if m:
            part_title = m.group(1).strip()

    if dry_run:
        counts = {"subparts": 0, "sections": 0, "subsections": 0, "blocks": 0}
        for sp in hierarchy:
            counts["subparts"] += 1
            for sec in sp.get("sections", []):
                counts["sections"] += 1
                counts["blocks"] += len(sec.get("paragraphs", []))
                for sub in sec.get("subsections", []):
                    counts["subsections"] += 1
                    counts["blocks"] += len(sub.get("paragraphs", []))
        return counts

    with tx() as conn:
        # Create the Part document
        doc_id = insert_document(
            conn,
            case_id=case_id,
            name=part_title,
            document_type="other",
            source="other",
            metadata={"part": part_num, "source_url": FAR_ZIP_URL},
        )

        section_count = 0
        block_count = 0

        for sp in hierarchy:
            # Subpart section
            sp_search = _build_search_text(
                sp["title"], []
            )
            sp_id = insert_section(
                conn,
                document_id=doc_id,
                heading_level=1,
                title=sp["title"],
                search_text=sp_search,
                metadata={"far_number": sp["number"]},
            )
            section_count += 1

            for sec in sp.get("sections", []):
                paragraphs = sec.get("paragraphs", [])
                sec_search = _build_search_text(
                    f"{sec['number']} {sec['title']}", paragraphs
                )
                sec_id = insert_section(
                    conn,
                    document_id=doc_id,
                    parent_id=sp_id,
                    heading_level=2,
                    title=f"{sec['number']} {sec['title']}",
                    search_text=sec_search,
                    metadata={"far_number": sec["number"]},
                )
                section_count += 1

                # Blocks for section paragraphs
                for para in paragraphs:
                    insert_block(
                        conn,
                        document_id=doc_id,
                        section_id=sec_id,
                        block_type="Text",
                        text_content=para,
                    )
                    block_count += 1

                # Subsections
                for sub in sec.get("subsections", []):
                    sub_paras = sub.get("paragraphs", [])
                    sub_search = _build_search_text(
                        f"{sub['number']} {sub['title']}", sub_paras
                    )
                    sub_id = insert_section(
                        conn,
                        document_id=doc_id,
                        parent_id=sec_id,
                        heading_level=3,
                        title=f"{sub['number']} {sub['title']}",
                        search_text=sub_search,
                        metadata={"far_number": sub["number"]},
                    )
                    section_count += 1

                    for para in sub_paras:
                        insert_block(
                            conn,
                            document_id=doc_id,
                            section_id=sub_id,
                            block_type="Text",
                            text_content=para,
                        )
                        block_count += 1

    return {
        "subparts": len(hierarchy),
        "sections": section_count,
        "blocks": block_count,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Ingest the FAR into the Vision database"
    )
    parser.add_argument(
        "--skip-download", action="store_true",
        help="Use previously downloaded ZIP from temp dir"
    )
    parser.add_argument(
        "--no-embed", action="store_true",
        help="Skip embedding generation"
    )
    parser.add_argument(
        "--part", type=int,
        help="Ingest only a single Part (e.g., --part 15)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and count without inserting"
    )
    args = parser.parse_args()

    # ---- Download ----
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = TEMP_DIR / "FARHTML.zip"

    if args.skip_download and zip_path.exists():
        print(f"Using cached ZIP: {zip_path} ({zip_path.stat().st_size:,} bytes)")
    else:
        print(f"Downloading FAR ZIP from {FAR_ZIP_URL}...")
        urlretrieve(FAR_ZIP_URL, zip_path)
        print(f"Downloaded: {zip_path.stat().st_size:,} bytes")

    # ---- Extract ----
    extract_dir = TEMP_DIR / "extracted"
    if extract_dir.exists():
        import shutil
        shutil.rmtree(extract_dir)
    extract_dir.mkdir()

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Only extract HTML files from dita_html/
        members = [
            m for m in zf.infolist()
            if m.filename.startswith("dita_html/") and m.filename.endswith(".html")
        ]
        zf.extractall(extract_dir, members=members)
    print(f"Extracted {len(members)} HTML files to {extract_dir}")

    html_dir = extract_dir / "dita_html"

    # ---- Determine parts to ingest ----
    if args.part:
        parts = [args.part]
    else:
        parts = sorted(
            int(m.group(1))
            for f in html_dir.glob("Part_*.html")
            if (m := PART_FILE_RE.match(f.name))
        )
        parts = [p for p in parts if p not in RESERVED_PARTS]
    print(f"Parts to ingest: {parts}")

    # ---- Create/get FAR case ----
    if args.dry_run:
        case_id = 0
        print("Dry run mode — no database writes.")
    else:
        case_id = _ensure_far_case()

    # ---- Ingest each Part ----
    doc_ids: list[int] = []
    grand_totals = {"subparts": 0, "sections": 0, "blocks": 0, "parts": 0}

    for part_num in parts:
        t0 = time.time()
        print(f"\nPart {part_num}...", end=" ", flush=True)
        counts = _ingest_part(case_id, html_dir, part_num, dry_run=args.dry_run)
        elapsed = time.time() - t0
        print(
            f"{counts['subparts']} subparts, "
            f"{counts['sections']} sections, "
            f"{counts['blocks']} blocks "
            f"({elapsed:.1f}s)"
        )
        for k in grand_totals:
            if k in counts:
                grand_totals[k] += counts[k]

    print(f"\n{'Would ingest' if args.dry_run else 'Ingested'}:")
    print(f"  Parts:      {grand_totals['parts'] or len(parts)}")
    print(f"  Subparts:   {grand_totals['subparts']}")
    print(f"  Sections:   {grand_totals['sections']}")
    print(f"  Blocks:     {grand_totals['blocks']}")

    if args.dry_run:
        return

    # ---- Embed ----
    if not args.no_embed:
        print("\n--- Embedding ---")
        from search.embed import embed_case
        embed_case(case_id)

    print("\nDone.")


if __name__ == "__main__":
    main()
