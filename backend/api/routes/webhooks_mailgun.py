"""
Vision — Mailgun Inbound Webhook.

Receives Mailgun's inbound-route POST (multipart/form-data — Mailgun's
inbound parse webhook, NOT the JSON event webhook used for
delivered/bounced/opened events). Verifies signature, correlates to a
vendor_outreach_messages row via the `vmatch-{token}@domain` recipient address,
stores the raw reply as a document, and updates outreach_status='received'.

No auth dependency — Mailgun calls this directly, authenticated only by
signature verification (see _verify_signature). Must NOT be behind
get_current_user.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Form, File, UploadFile, HTTPException

from core.vendor_match import VendorMatchManager
from ingestion.jobs import enqueue as _enqueue_job

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

vendor_match_mgr = VendorMatchManager()

_SIGNING_KEY = os.environ.get("MAILGUN_WEBHOOK_SIGNING_KEY", "")
_RECIPIENT_RE = re.compile(r"^vmatch-([0-9a-f]{16})@", re.IGNORECASE)

# Temp dir for saving inbound attachments before enqueuing
# Shared volume between API and worker containers so the worker can
# access attachment files saved by the webhook.
_ATTACH_TMP = Path(os.environ.get("VISION_MAILGUN_TMP", "/tmp/vision-mailgun"))


def _verify_signature(timestamp: str, token: str, signature: str) -> bool:
    """HMAC-SHA256(timestamp + token, key=signing_key) == signature.

    Per https://documentation.mailgun.com/docs/mailgun/user-manual/webhooks/securing-webhooks —
    constant-time compare via hmac.compare_digest.
    """
    if not _SIGNING_KEY:
        return False
    digest = hmac.new(
        _SIGNING_KEY.encode(), f"{timestamp}{token}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(digest, signature)


@router.post("/mailgun/inbound")
async def mailgun_inbound_webhook(
    recipient: str = Form(...),
    sender: str = Form(...),
    subject: str = Form(""),
    stripped_text: str = Form("", alias="stripped-text"),
    body_plain: str = Form("", alias="body-plain"),
    timestamp: str = Form(...),
    token: str = Form(...),
    signature: str = Form(...),
    attachment_count: str = Form("0", alias="attachment-count"),
    attachment_1: UploadFile | None = File(None, alias="attachment-1"),
    attachment_2: UploadFile | None = File(None, alias="attachment-2"),
    attachment_3: UploadFile | None = File(None, alias="attachment-3"),
    attachment_4: UploadFile | None = File(None, alias="attachment-4"),
    attachment_5: UploadFile | None = File(None, alias="attachment-5"),
):
    """Mailgun inbound route target. Field names/casing per Mailgun's
    documented inbound multipart payload (see PLAN.md §0 research —
    'recipient', 'sender', 'subject', 'stripped-text', 'body-plain',
    'timestamp', 'token', 'signature' are exact Mailgun field names).

    Returns 200 for all "handled" outcomes once signature is verified —
    including "no correlation token" and "no matching message" — so
    Mailgun does not retry-storm us for cases we can never resolve. Only
    signature failure (401) and genuine 5xx (e.g. DB down) are non-200.
    """
    if not _verify_signature(timestamp, token, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    m = _RECIPIENT_RE.match(recipient)
    if not m:
        # Not a reply-correlation address — ignore silently (200, not an error).
        return {"status": "ignored", "reason": "no correlation token in recipient"}

    reply_token = m.group(1)
    message = vendor_match_mgr.find_message_by_reply_token(reply_token)
    if message is None:
        return {"status": "ignored", "reason": "no message for token"}

    text = stripped_text or body_plain or ""

    # Save any attachments to temp files for the worker to pick up.
    attachment_paths: list[str] = []
    attach_count = int(attachment_count) if attachment_count else 0
    for file_obj in [attachment_1, attachment_2, attachment_3, attachment_4, attachment_5]:
        if file_obj is None or not file_obj.filename:
            continue
        _ATTACH_TMP.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", file_obj.filename or "attachment")
        dest = _ATTACH_TMP / f"{uuid.uuid4().hex}_{safe_name}"
        content = await file_obj.read()
        dest.write_bytes(content)
        attachment_paths.append(str(dest))

    job = _enqueue_job(
        case_id=message["case_id"],
        job_type="inbound_email",
        metadata={
            "vendor_match_id": message["vendor_match_id"],
            "sender": sender,
            "subject": subject,
            "text": text,
            "attachment_paths": attachment_paths,
        },
    )
    return {"status": "queued", "job_id": job["id"]}
