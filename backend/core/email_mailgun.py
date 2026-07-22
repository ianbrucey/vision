"""
Vision — Mailgun Email Client (sync).

Outbound send only. Inbound is handled by api/routes/webhooks_mailgun.py
(a separate concern — signature verification, not sending).
"""

from __future__ import annotations

import os

import httpx

_API_KEY = os.environ.get("MAILGUN_API_KEY", "")
_BASE_URL = os.environ.get("MAILGUN_BASE_URL", "https://api.mailgun.net/v3")
# Ensure the base URL includes the /v3 path prefix. If an operator sets
# "https://api.mailgun.net" (without /v3), all domain lookups 404.
if not _BASE_URL.rstrip("/").endswith("/v3"):
    _BASE_URL = _BASE_URL.rstrip("/") + "/v3"
# Prefer a real verified domain (MAILGUN_DOMAIN) if set; fall back to the
# sandbox domain for local dev (sandbox can only send to authorized
# recipients — see PLAN.md §0).
_DOMAIN = os.environ.get("MAILGUN_DOMAIN") or os.environ.get("MAILGUN_SANDBOX_DOMAIN", "")


class MailgunSendError(Exception):
    """Raised when the Mailgun API call fails (non-2xx response)."""


def send_email(
    to_email: str,
    to_name: str | None,
    subject: str,
    text_body: str,
    reply_to: str | None = None,
) -> dict:
    """Send a plain-text email via Mailgun. Returns {"id": str, "message": str}.

    `reply_to` sets the Reply-To header — used by outreach sends to route
    vendor replies back through the vmatch-{token}@domain correlation
    address (see core/vendor_match.py::find_by_reply_token).

    Raises MailgunSendError on any non-2xx response, with Mailgun's error
    body included in the message.
    """
    if not _API_KEY or not _DOMAIN:
        raise MailgunSendError("Mailgun is not configured (MAILGUN_API_KEY/MAILGUN_DOMAIN missing)")

    to_field = f"{to_name} <{to_email}>" if to_name else to_email
    data = {
        "from": f"Vision Outreach <postmaster@{_DOMAIN}>",
        "to": to_field,
        "subject": subject,
        "text": text_body,
    }
    if reply_to:
        data["h:Reply-To"] = reply_to

    resp = httpx.post(
        f"{_BASE_URL}/{_DOMAIN}/messages",
        auth=("api", _API_KEY),
        data=data,
        timeout=15.0,
    )
    if resp.status_code >= 300:
        raise MailgunSendError(f"Mailgun send failed ({resp.status_code}): {resp.text}")

    body = resp.json()
    return {"id": body.get("id", ""), "message": body.get("message", "")}
