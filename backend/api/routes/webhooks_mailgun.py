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
from ingestion.storage import upload_attachment

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

vendor_match_mgr = VendorMatchManager()

_SIGNING_KEY = os.environ.get("MAILGUN_WEBHOOK_SIGNING_KEY", "")
_RECIPIENT_RE = re.compile(r"^vmatch-([0-9a-f]{16})@", re.IGNORECASE)


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
    documented inbound multipart payload.

    Returns 200 for all "handled" outcomes once signature is verified —
    including "no correlation token" and "no matching message" — so
    Mailgun does not retry-storm us.
    """
    if not _verify_signature(timestamp, token, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    m = _RECIPIENT_RE.match(recipient)
    if not m:
        return {"status": "ignored", "reason": "no correlation token in recipient"}

    reply_token = m.group(1)
    message = vendor_match_mgr.find_message_by_reply_token(reply_token)
    if message is None:
        return {"status": "ignored", "reason": "no message for token"}

    text = stripped_text or body_plain or ""

    # Upload attachments directly to MinIO — no shared filesystem needed.
    # The worker downloads them from MinIO for OCR/ingestion.
    attachment_keys: list[dict] = []
    for file_obj in [attachment_1, attachment_2, attachment_3, attachment_4, attachment_5]:
        if file_obj is None or not file_obj.filename:
            continue
        try:
            content = await file_obj.read()
            safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", file_obj.filename or "attachment")
            obj_key = f"mailgun_attachments/{uuid.uuid4().hex}_{safe_name}"
            upload_attachment(obj_key, content)
            attachment_keys.append({"key": obj_key, "name": file_obj.filename})
        except Exception as e:
            print(f"Webhook: failed to upload attachment {file_obj.filename}: {e}")

    job = _enqueue_job(
        case_id=message["case_id"],
        job_type="inbound_email",
        metadata={
            "vendor_match_id": message["vendor_match_id"],
            "sender": sender,
            "subject": subject,
            "text": text,
            "attachment_keys": attachment_keys,
        },
    )
    return {"status": "queued", "job_id": job["id"]}
