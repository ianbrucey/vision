#!/usr/bin/env python3
"""
Page Budget Estimator — Justice Quest LLC Sources Sought / RFI Responses
========================================================================
Predicts how many pages a response letter will print to BEFORE submission,
and computes character budgets BEFORE drafting.

Three modes:
  estimate <response.html>            Structural estimate from the HTML alone
                                      (no browser needed; ~seconds)
  measure <response.html>             Exact page count via headless Chrome
                                      (the ground truth; used to confirm)
  budget <page_limit>                 Character budget for a response with an
                                      N-page limit, for pre-draft planning

Usage examples:
  python3 page-budget.py estimate response.html
  python3 page-budget.py measure response.html --limit 10
  python3 page-budget.py budget 10

Calibration (measured on the C5ISRT response, Notice N6133126SNQ36)
=====================================================================
Rendered in Chrome with the compact template (Times New Roman 12pt,
line-height 1.22, 1in margins, banded sections):

  - 14 pages @ 1,636 chars/page  (original layout: 1.6 line-height, 40px bands)
  - 10 pages @ 2,094 chars/page  (compact layout)

Model — line-based, no double counting:
  lines = ceil(text_chars / CHARS_PER_LINE) + structural_lines + fixed_lines
  pages = ceil(lines / LINES_PER_PAGE)

  CHARS_PER_LINE = 86   (TNR 12pt over 6.5in text width)
  LINES_PER_PAGE = 44   (9in text height at 12pt * 1.22 = 14.64pt lines)

Element line-costs (beyond the text they contain):
  section band ~4 lines | sub-title ~2 | label ~1.5 | bullet ~1
  table row ~1 (+1 header row per table) | caveat/quote box ~1.5 | paragraph ~0.5
  fixed (letterhead + date + TO/FROM/POC/RE/submit + signature) ~20 lines

To re-calibrate for a changed template: run 'measure' on a finished doc,
then adjust constants until 'estimate' matches.
"""

import argparse
import html as html_mod
import math
import re
import subprocess
import sys
from pathlib import Path

# ---- Calibrated constants (see docstring) ----
CHARS_PER_LINE = 86
LINES_PER_PAGE = 44
FIXED_LINES    = 20        # letterhead + blocks + signature
BAND_LINES     = 4
SUB_TITLE_LINES = 2
SUB_HEAD_LINES = 1
LABEL_LINES    = 1.5
LI_LINES       = 1
TABLE_ROW_LINES = 1
TABLE_HEAD_LINES = 1
BOX_LINES      = 1.5
P_LINES        = 0.5

CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def strip_tags(s: str) -> str:
    s = re.sub(r"<style[^>]*>.*?</style>", "", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return html_mod.unescape(s)


def count(body: str, pattern: str) -> int:
    return len(re.findall(pattern, body, flags=re.S))


def estimate(html_file: str) -> dict:
    text = Path(html_file).read_text()
    body = text[text.find("<body"): text.find("</body>")]

    text_chars = len(strip_tags(body).strip())

    n_band = count(body, r'class="section-band"')
    n_sub = count(body, r'class="sub-title"')
    n_subhead = count(body, r'class="sub-head"')
    n_label = count(body, r'class="label[^"]*"')
    n_li = count(body, r"<li")
    n_tr = count(body, r"<tr>")
    n_caveat = count(body, r'class="caveat"')
    n_quote = count(body, r'class="quote"')
    n_p = count(body, r"<p>")

    text_lines = math.ceil(text_chars / CHARS_PER_LINE)
    struct_lines = (
        FIXED_LINES
        + n_band * BAND_LINES
        + n_sub * SUB_TITLE_LINES
        + n_subhead * SUB_HEAD_LINES
        + n_label * LABEL_LINES
        + n_li * LI_LINES
        + n_tr * TABLE_ROW_LINES
        + n_band * TABLE_HEAD_LINES            # one header row per table
        + n_caveat * BOX_LINES
        + n_quote * BOX_LINES
        + n_p * P_LINES
    )
    total_lines = text_lines + struct_lines
    pages = max(1, math.ceil(total_lines / LINES_PER_PAGE))

    return {
        "text_chars": text_chars,
        "text_lines": text_lines,
        "structure_lines": round(struct_lines, 1),
        "total_lines": round(total_lines, 1),
        "estimated_pages": pages,
        "elements": {
            "bands": n_band, "sub_titles": n_sub, "labels": n_label,
            "bullets": n_li, "table_rows": n_tr, "caveat_boxes": n_caveat,
            "quote_boxes": n_quote, "paragraphs": n_p,
        },
    }


def measure(html_file: str) -> int:
    chrome = next((c for c in CHROME_PATHS if Path(c).exists()), None)
    if not chrome:
        sys.exit("ERROR: headless Chrome not found — 'measure' needs Chrome. Use 'estimate' instead.")
    out = Path("/tmp") / f"page-budget-{abs(hash(html_file))}.pdf"
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={out}", Path(html_file).resolve().as_uri()],
        check=True, capture_output=True,
    )
    try:
        import fitz  # pymupdf
    except ImportError:
        sys.exit("ERROR: pymupdf required for 'measure' — pip install pymupdf")
    doc = fitz.open(out)
    pages = len(doc)
    chars = sum(len(p.get_text()) for p in doc)
    doc.close()
    print(f"MEASURED: {pages} pages | {chars} chars | {round(chars / pages)} chars/page")
    return pages


def budget(page_limit: int) -> None:
    per_page = CHARS_PER_LINE * LINES_PER_PAGE
    print(f"PAGE BUDGET for a {page_limit}-page limit (compact template):")
    print(f"  Capacity: ~{per_page:,} chars/page | {LINES_PER_PAGE} lines/page | ~{CHARS_PER_LINE} chars/line (TNR 12pt)")
    print(f"  Fixed overhead: ~{FIXED_LINES} lines (letterhead, date, TO/FROM/POC/RE, signature)")
    available_lines = page_limit * LINES_PER_PAGE - FIXED_LINES
    print(f"  Lines available for body content: ~{available_lines}")
    print(f"    = ~{available_lines * CHARS_PER_LINE:,} chars if pure text")
    print()
    print("  Budget the structure first (lines, beyond the text inside):")
    print(f"    section band        = {BAND_LINES} lines each")
    print(f"    sub-section heading = {SUB_TITLE_LINES} lines each")
    print(f"    label               = {LABEL_LINES} lines each")
    print(f"    bullet / table row  = {LI_LINES} line each")
    print(f"    caveat / quote box  = {BOX_LINES} lines each")
    print(f"  Remaining lines = text budget: {available_lines} - structure_lines, "
          f"then multiply by {CHARS_PER_LINE} for the character allowance.")
    print()
    print(f"  TARGET: aim for {page_limit - 1} pages of content to leave a buffer "
          f"against renderer variance (font fallbacks, browser differences).")


def main():
    ap = argparse.ArgumentParser(description="Page budget estimator for SSN/RFI responses")
    ap.add_argument("mode", choices=["estimate", "measure", "budget"])
    ap.add_argument("target", help="HTML file for estimate/measure, or page limit for budget")
    ap.add_argument("--limit", type=int, default=None, help="page limit (estimate/measure modes)")
    args = ap.parse_args()

    if args.mode == "budget":
        budget(int(args.target))
        return

    if not Path(args.target).exists():
        sys.exit(f"ERROR: file not found: {args.target}")

    if args.mode == "estimate":
        r = estimate(args.target)
        print(f"ESTIMATE: {r['estimated_pages']} pages")
        print(f"  text: {r['text_chars']:,} chars = {r['text_lines']} lines | "
              f"structure: {r['structure_lines']} lines | total: {r['total_lines']} lines")
        print(f"  elements: {r['elements']}")
        if args.limit:
            verdict = "OK" if r["estimated_pages"] <= args.limit else "OVER LIMIT"
            print(f"  vs limit {args.limit}: {verdict}")
        return

    if args.mode == "measure":
        pages = measure(args.target)
        if args.limit:
            print(f"  vs limit {args.limit}: {'OK' if pages <= args.limit else 'OVER LIMIT'}")
        return


if __name__ == "__main__":
    main()
