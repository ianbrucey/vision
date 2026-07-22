"""
Vision — SAM.gov v2 API Client (sync).

Used by the ingestion worker's sam_fetch job handler (worker.py runs sync,
not async — unlike the chat tool in chat/external_tools.py). Provides:
  - extract_notice_id: pull noticeId out of a SAM.gov opportunity URL
  - fetch_notice: fetch full opportunity metadata for a notice_id
  - fetch_description: fetch the plain-text opportunity description (a
    separate endpoint — fetch_notice()'s "description" field is only a URL)
  - download_resource_link: download a single attachment, resolving its
    real filename from the Content-Disposition header (SAM.gov's
    resourceLinks entries are bare URLs with no filename/label — see
    context-engine/specs/solicitation-ingestion/03-fixtures.json).
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import httpx

_SAM_API_KEY = os.environ.get("SAM_GOV_API_KEY", "")
_SAM_SEARCH_URL = "https://api.sam.gov/opportunities/v2/search"

# SAM.gov opportunity URLs look like:
#   https://sam.gov/opp/{noticeId}/view
#   https://sam.gov/workspace/contract/opp/{noticeId}/view
# noticeId is a 32-char hex string.
_NOTICE_ID_URL_RE = re.compile(r"/opp/([0-9a-fA-F]{32})(?:/|$)")
_NOTICE_ID_QUERY_RE = re.compile(r"[?&]noticeid=([0-9a-fA-F]{32})", re.IGNORECASE)


class SamFetchError(Exception):
    """Raised when the SAM.gov API call fails or returns zero results."""


def extract_notice_id(url: str) -> str | None:
    """Extract the noticeId from a SAM.gov opportunity URL.

    Handles both `/opp/{id}/view` path shapes and `?noticeid={id}` query
    params. Returns None if no notice id pattern is found.
    """
    match = _NOTICE_ID_URL_RE.search(url)
    if match:
        return match.group(1)
    match = _NOTICE_ID_QUERY_RE.search(url)
    if match:
        return match.group(1)
    return None


def fetch_notice(notice_id: str) -> dict:
    """Fetch full opportunity metadata for a notice_id.

    SAM.gov v2's search endpoint requires a postedFrom/postedTo date range
    even when querying by noticeid; use a generous ~1-year lookback window
    so older-but-still-active notices are still found. Uses 364 days, not
    365 — the API rejects exactly-365-day ranges with
    "Date range must be null year(s) apart" (confirmed empirically).

    Raises SamFetchError if the API call fails or returns zero results.
    Returns the single opportunitiesData[0] dict on success.
    """
    if not _SAM_API_KEY:
        raise SamFetchError("SAM_GOV_API_KEY not configured.")

    today = datetime.now()
    lookback_start = today - timedelta(days=364)
    params = {
        "api_key": _SAM_API_KEY,
        "noticeid": notice_id,
        "postedFrom": lookback_start.strftime("%m/%d/%Y"),
        "postedTo": today.strftime("%m/%d/%Y"),
        "limit": 1,
    }

    try:
        resp = httpx.get(_SAM_SEARCH_URL, params=params, timeout=30)
    except httpx.HTTPError as exc:
        raise SamFetchError(f"SAM.gov API request failed: {exc}") from exc

    if resp.status_code != 200:
        raise SamFetchError(
            f"SAM.gov API returned status {resp.status_code} for noticeId={notice_id}"
        )

    data = resp.json()
    if data.get("totalRecords", 0) == 0:
        raise SamFetchError(
            f"SAM.gov API returned 0 results for noticeId={notice_id}"
        )

    opportunities = data.get("opportunitiesData") or []
    if not opportunities:
        raise SamFetchError(
            f"SAM.gov API returned 0 results for noticeId={notice_id}"
        )

    return opportunities[0]


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def fetch_description(notice_id: str) -> str:
    """Fetch and return the plain-text opportunity description for a notice.

    `fetch_notice()`'s "description" field is only a URL to this separate
    endpoint (see 03-fixtures.json) — the actual text requires a second
    call. Mirrors the HTML-stripping logic in
    chat/external_tools.py::get_sam_opportunity_detail.

    Non-fatal by design: returns "" on any failure (missing key, HTTP
    error, empty body) so callers (e.g. narrative synthesis) can proceed
    without the description rather than failing the whole job.
    """
    if not _SAM_API_KEY:
        return ""
    try:
        resp = httpx.get(
            "https://api.sam.gov/prod/opportunities/v1/noticedesc",
            params={"noticeid": notice_id, "api_key": _SAM_API_KEY},
            timeout=15,
        )
        if resp.status_code != 200:
            return ""
        desc_html = resp.json().get("description", "")
    except (httpx.HTTPError, ValueError):
        return ""

    plain_text = _HTML_TAG_RE.sub(" ", desc_html)
    return _WHITESPACE_RE.sub(" ", plain_text).strip()


_CONTENT_DISPOSITION_FILENAME_RE = re.compile(
    r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', re.IGNORECASE
)


def download_resource_link(url: str, dest_path: Path) -> dict:
    """Download a single SAM.gov attachment to dest_path.

    Filename is parsed from the Content-Disposition response header (the
    resourceLinks URL itself carries no filename). Falls back to a
    generated name if the header is absent or unparsable.

    Must use GET (not HEAD) — SAM.gov's S3-presigned resource URLs return
    403 on HEAD requests but 200 on GET with api_key as a query param.

    Raises on non-200 responses.
    """
    if not _SAM_API_KEY:
        raise SamFetchError("SAM_GOV_API_KEY not configured.")

    resp = httpx.get(
        url, params={"api_key": _SAM_API_KEY}, timeout=60, follow_redirects=True
    )
    if resp.status_code != 200:
        raise SamFetchError(
            f"Failed to download resource link (status {resp.status_code}): {url}"
        )

    filename = None
    content_disposition = resp.headers.get("content-disposition")
    if content_disposition:
        match = _CONTENT_DISPOSITION_FILENAME_RE.search(content_disposition)
        if match:
            filename = match.group(1).strip()

    if not filename:
        filename = f"attachment_{uuid.uuid4().hex[:12]}.bin"

    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(resp.content)

    return {"filename": filename, "path": dest_path}
