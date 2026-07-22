# T10 — Mailgun Email Integration: Implementation Plan

Status: ready for implementation. This is the exact specification — no
architectural decisions are left to the implementer. Any ambiguity found
while coding must stop and ask, not be guessed (Commandment I).

Split into two independent halves. **10a (Outbound)** is buildable and
testable today. **10b (Inbound)** has a hard external prerequisite (below)
that blocks end-to-end testing until the human completes it.

---

## 0. Prerequisites (human-only — not code, do not attempt to script)

**Blocks 10b only. 10a can be built/tested without these.**

1. Mailgun sandbox domains (`MAILGUN_SANDBOX_DOMAIN`) **cannot receive mail**
   — they support outbound-to-authorized-recipients only. Inbound reply
   capture requires a real domain you control, with MX records pointed at
   `mxa.mailgun.org` / `mxb.mailgun.org`.
2. Once that domain is added in Mailgun and verified, set `MAILGUN_DOMAIN`
   in `.env` (uncomment/replace the existing commented line).
3. In the Mailgun dashboard, create a **Route**: filter
   `match_recipient("vmatch-.*@inbound.justicequest.pro")` → action
   `forward("https://vision.justicequest.pro/api/webhooks/mailgun/inbound")`
   (`inbound.justicequest.pro` is the verified `MAILGUN_DOMAIN` in `.env`;
   `vision.justicequest.pro` is assumed to be the Cloudflare tunnel's
   public hostname — confirm this matches your actual tunnel hostname
   before creating the Route, and correct it here if not. The tunnel
   referenced by `CLOUDFLARE_TUNNEL_TOKEN` must route that hostname to
   `127.0.0.1:8400`).
4. Add `MAILGUN_WEBHOOK_SIGNING_KEY` to `.env` — found in Mailgun dashboard
   under Settings → API Keys → Webhook Signing Key (**different** from
   `MAILGUN_API_KEY`). Not present in `.env` today; must be added.

If these aren't done yet, build 10b's code anyway (per spec below) — it
will just be untestable against a real inbound email until the domain/route
exist. It **can** be tested by manually POSTing a simulated multipart
payload to the endpoint (see §7 Verdict).

---

## 1. Schema — Migration v23

New file `backend/schemas/014_vendor_outreach_email.sql`:

```sql
-- ============================================================================
-- Vision — Vendor Outreach Email Migration v23
-- ============================================================================
-- Adds Mailgun send/reply-correlation columns to vendor_matches (T10a/b).
-- outreach_message_id: Mailgun's returned Message-Id for the sent email —
--   informational/debugging only, never required for correctness.
-- outreach_reply_token: random token embedded in the Reply-To address used
--   to correlate an inbound webhook back to this row. SECURITY: never
--   include this column in any SELECT reachable by a public API route —
--   see core/vendor_match.py::find_by_reply_token, which is the only
--   permitted reader, used exclusively by the webhook handler.
-- Also extends jobs.job_type with 'inbound_email' for the async ingest path.
--
-- Dependencies: 013_vendor_outreach.sql (vendor_matches outreach columns)
-- ============================================================================

SET search_path TO vision, public;

ALTER TABLE vendor_matches ADD COLUMN IF NOT EXISTS outreach_message_id TEXT;
ALTER TABLE vendor_matches ADD COLUMN IF NOT EXISTS outreach_reply_token TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_vendor_matches_reply_token
    ON vendor_matches (outreach_reply_token) WHERE outreach_reply_token IS NOT NULL;

ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_job_type_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_job_type_check
    CHECK (job_type IN ('ingest', 'ingest_pdf', 'ingest_docx', 'ingest_xlsx',
                         'analyze', 'export', 'ocr', 'embed', 'enrich',
                         'synthesize', 'profile_synthesis', 'capability_statement',
                         'sam_fetch', 'solicitation_triage', 'vendor_matching',
                         'inbound_email', 'other'));

INSERT INTO schema_migrations (version, name) VALUES (23, 'vendor_outreach_email')
ON CONFLICT (version) DO NOTHING;
```

### `backend/core/db.py` — add function (same pattern as `ensure_vendor_outreach_schema`)

```python
def ensure_vendor_outreach_email_schema() -> list[str]:
    """Apply the vendor outreach email migration (T10).

    Adds outreach_message_id/outreach_reply_token to vendor_matches and
    extends jobs.job_type with 'inbound_email'. Idempotent.
    """
    sql_path = _SCHEMA_DIR / "014_vendor_outreach_email.sql"
    if not sql_path.exists():
        raise FileNotFoundError(f"Vendor outreach email schema file not found: {sql_path}")
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
    return [str(sql_path)]
```

Add `"ensure_vendor_outreach_email_schema"` to the `__all__` list at the
bottom of `db.py` (alongside the existing `ensure_vendor_outreach_schema`
entry).

### `backend/api/main.py` — wire into startup

Add `ensure_vendor_outreach_email_schema` to the import line 24, and call it
in `_apply_schemas()` right after `ensure_vendor_outreach_schema()`:
```python
ensure_vendor_outreach_email_schema()  # 014 — outreach email send/reply tracking (T10)
```

### `backend/init_db.py` — same import + call, mirroring how
`ensure_vendor_outreach_schema` is already wired in (import list + the
schema-application sequence in `main()`).


---

## 2. Backend — `core/email_mailgun.py` (new file)

Uses `httpx` (already an installed transitive dependency — confirmed via
`pip show httpx` — used the same way `ingestion/sam_client.py` uses it: a
module-level sync client call, no async needed since routes here are sync
`def`, not `async def`, matching every other route in `solicitations.py`).

```python
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
```

---

## 3. Backend — `core/vendor_match.py` additions

Add two new methods to `VendorMatchManager` (after `update_outreach`):

```python
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
```

**Do not** add `outreach_message_id`/`outreach_reply_token` to the SELECT
column lists in `get_match()` or `list_for_solicitation()` — these stay
backend-internal (reply_token in particular must never reach the frontend;
see PLAN.md §1 security note).


---

## 4. Backend — `POST /api/vendor-matches/{match_id}/outreach/send` (10a)

Add to `backend/api/routes/solicitations.py`. No new request body schema
needed beyond what's below (uses the match's own contact_email + the
solicitation's shared `outreach_email_subject`/`outreach_email_body`
template columns — same template `VendorMatchesTab.tsx`'s `CopyEmailButton`
already substitutes client-side; this endpoint does the substitution
server-side once, at send time).

```python
import secrets

from core.email_mailgun import send_email, MailgunSendError

...

@router.post("/vendor-matches/{match_id}/outreach/send")
def send_outreach_email_endpoint(
    match_id: int,
    user: dict = Depends(get_current_user),
):
    """Send the solicitation's outreach email template to this vendor match (T10a).

    Substitutes {{vendor_name}} and {{match_reason}} placeholders (same
    placeholders CopyEmailButton substitutes client-side in
    VendorMatchesTab.tsx). Requires the vendor match to have a
    contact_email (raises 400 if not — sentinel-masked emails read as
    NULL per CONTACT_EMAIL_SENTINEL, so this naturally excludes hidden
    vendors) and the solicitation to have both outreach_email_subject and
    outreach_email_body set (raises 400 otherwise — these are populated by
    the vendor_matching pipeline, not user-editable in v1).

    On success: records outreach_message_id + outreach_reply_token via
    mark_email_sent(), sets outreach_status='requested'. On Mailgun
    failure: returns 502 with Mailgun's error, vendor_matches is
    untouched (no partial state).
    """
    match = vendor_match_mgr.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Vendor match not found")
    if not match.get("contact_email"):
        raise HTTPException(status_code=400, detail="This vendor has no email on file")

    sol = mgr.get(match["solicitation_id"])
    subject = sol.get("outreach_email_subject") if sol else None
    body = sol.get("outreach_email_body") if sol else None
    if not subject or not body:
        raise HTTPException(
            status_code=400,
            detail="Solicitation has no outreach email template — run vendor matching first",
        )

    subject = subject.replace("{{vendor_name}}", match["vendor_name"])
    body = (
        body.replace("{{vendor_name}}", match["vendor_name"])
            .replace("{{match_reason}}", match["match_rationale"])
    )

    reply_token = secrets.token_hex(8)
    reply_domain = os.environ.get("MAILGUN_DOMAIN") or os.environ.get("MAILGUN_SANDBOX_DOMAIN", "")
    reply_to = f"vmatch-{reply_token}@{reply_domain}"

    try:
        result = send_email(
            to_email=match["contact_email"],
            to_name=match["vendor_name"],
            subject=subject,
            text_body=body,
            reply_to=reply_to,
        )
    except MailgunSendError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return vendor_match_mgr.mark_email_sent(match_id, result["id"], reply_token)
```

Add `import os` to the top of `solicitations.py` if not already present
(check first — it currently is not imported there).

### Route file registration

No change needed — this is added to the existing `solicitations_router`,
already registered in `api/main.py` (`app.include_router(solicitations_router)`).

---

## 5. Backend — Inbound webhook (10b)

New file `backend/api/routes/webhooks_mailgun.py`:

```python
"""
Vision — Mailgun Inbound Webhook.

Receives Mailgun's inbound-route POST (multipart/form-data — Mailgun's
inbound parse webhook, NOT the JSON event webhook used for
delivered/bounced/opened events). Verifies signature, correlates to a
vendor_matches row via the `vmatch-{token}@domain` recipient address,
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

from fastapi import APIRouter, Form, HTTPException

from core.vendor_match import VendorMatchManager
from ingestion.jobs import enqueue as _enqueue_job

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
):
    """Mailgun inbound route target. Field names/casing per Mailgun's
    documented inbound multipart payload (see PLAN.md §0 research —
    'recipient', 'sender', 'subject', 'stripped-text', 'body-plain',
    'timestamp', 'token', 'signature' are exact Mailgun field names).

    Returns 200 for all "handled" outcomes once signature is verified —
    including "no correlation token" and "no matching vendor_match" — so
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
    match = vendor_match_mgr.find_by_reply_token(reply_token)
    if match is None:
        return {"status": "ignored", "reason": "no vendor_match for token"}

    text = stripped_text or body_plain or ""

    job = _enqueue_job(
        case_id=match["case_id"],
        job_type="inbound_email",
        metadata={
            "vendor_match_id": match["id"],
            "sender": sender,
            "subject": subject,
            "text": text,
        },
    )
    return {"status": "queued", "job_id": job["id"]}
```

### Route registration — `backend/api/main.py`

Add alongside the other router imports/includes (~line 492-502):
```python
from api.routes.webhooks_mailgun import router as webhooks_mailgun_router
...
app.include_router(webhooks_mailgun_router)
```

### CORS / auth note

This route is intentionally NOT behind `get_current_user` — Mailgun is an
external caller with no JWT. Do not add the auth dependency here. The
existing `CORSMiddleware(allow_origins=["*"])` has no bearing on
server-to-server POSTs (CORS only affects browser-originated requests), so
no CORS change is needed either.

---

## 6. Backend — Worker job handler (10b)

Add to `backend/ingestion/worker.py`, following the exact pattern of
`process_enrich_job`/`process_solicitation_triage_job` (same file, same
`update_progress`/`mark_complete`/`mark_failed` calls imported at the top —
already imported at line 37).

```python
def process_inbound_email_job(job: dict) -> None:
    """Store an inbound Mailgun reply as a document + flip outreach_status.

    job['metadata'] = {"vendor_match_id": int, "sender": str,
                        "subject": str, "text": str} — set by
    api/routes/webhooks_mailgun.py at enqueue time.

    Creates a documents row with source='email' (an existing, already-
    allowed value in the documents.source CHECK constraint — see
    001_core.sql line 167-170) containing the reply's sender/subject/body
    as plain text (no attachment/MinIO upload — T10b v1 stores the body
    text only; a follow-up ticket can add multipart attachment handling
    if replies carry file attachments). Links the new document to the
    vendor_matches row via outreach_doc_id and sets outreach_status='received'
    by calling core/vendor_match.py's existing update_outreach() — the
    same code path a manual status change uses (per 013_vendor_outreach.sql's
    original design intent).
    """
    job_id = job["id"]
    case_id = job["case_id"]
    meta = job.get("metadata") or {}
    vendor_match_id = meta.get("vendor_match_id")
    sender = meta.get("sender", "unknown")
    subject = meta.get("subject", "(no subject)")
    text = meta.get("text", "")

    if not vendor_match_id:
        mark_failed(job_id, "Missing vendor_match_id in job metadata")
        return

    try:
        from core.db import tx, insert_document
        from core.vendor_match import VendorMatchManager

        doc_name = f"Reply from {sender} — {subject}"[:250]
        content = f"From: {sender}\nSubject: {subject}\n\n{text}"

        with tx() as conn:
            doc_id = insert_document(
                conn,
                case_id=case_id,
                name=doc_name,
                source="email",
                metadata={"vendor_match_id": vendor_match_id, "sender": sender},
            )
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE documents SET storage_path = NULL WHERE id = %s",
                    (doc_id,),
                )

        # Store the body text so it's readable — documents needs at least
        # one section/block to render in DocumentPreviewModal. Confirmed
        # exact signatures against core/db.py: insert_section(conn,
        # document_id, ..., title=None, search_text="", ...) -> int;
        # insert_block(conn, document_id, ..., section_id=None,
        # block_type="Text", ..., text_content=None, ...) -> int.
        from core.db import insert_section, insert_block
        with tx() as conn:
            section_id = insert_section(conn, document_id=doc_id, title=subject, search_text=content)
            insert_block(conn, document_id=doc_id, section_id=section_id, text_content=content)

        VendorMatchManager().update_outreach(
            vendor_match_id, outreach_status="received", outreach_doc_id=doc_id
        )

        mark_complete(job_id, document_id=doc_id)
        print(f"[{WORKER_ID}] Job {job_id}: inbound email stored as doc_id={doc_id}, vendor_match_id={vendor_match_id}")

    except Exception as e:
        print(f"[{WORKER_ID}] Job {job_id}: inbound email processing FAILED — {e}")
        traceback.print_exc()
        mark_failed(job_id, str(e))
```

### Dispatch wiring — `backend/ingestion/worker.py::main()`

Add one `elif` branch to the job-type dispatch chain (~line 734, after
`vendor_matching`):
```python
            elif job["job_type"] == "inbound_email":
                process_inbound_email_job(job)
```

Note: `insert_document`'s `UNIQUE (case_id, name)` constraint means two
replies with an identical sender+subject in the same case collide;
`insert_document`'s existing `ON CONFLICT ... DO UPDATE` only touches
`page_count`/`updated_at`, so the second reply's body would not overwrite
the first, but would harmlessly reuse the same `doc_id`. Acceptable for
v1 (edge case — identical sender+subject replies are rare); not in scope
to fix here.

---

## 7. Frontend

### `frontend/src/lib/api.ts` additions

```typescript
export const sendVendorMatchOutreachEmail = (
  matchId: number,
): Promise<VendorMatch> =>
  fetchAPI(`/api/vendor-matches/${matchId}/outreach/send`, { method: "POST" });
```

Place this directly after the existing `updateVendorMatchOutreach` export
(~line 168), using the identical `fetchAPI` wrapper pattern.

### `frontend/src/app/cases/[id]/tabs/OutreachTab.tsx` changes

Add a "Send" button per row, next to the status dropdown. Only enabled
when: `m.outreach_status === "not_contacted"` (a match already
requested/received/declined shouldn't get a duplicate automated send —
manual re-sends aren't in scope for v1) AND the solicitation has both
`outreach_email_subject`/`outreach_email_body` (already available on
`sol`, no new fetch needed) AND `m.contact_email` is present (note:
`VendorMatch.contact_email` already exists on the type per
`frontend/src/lib/api.ts` line 119 — no type change needed).

```tsx
// New import
import { sendVendorMatchOutreachEmail } from "@/lib/api";

// New state (top of component, alongside existing useState calls)
const [sendingId, setSendingId] = useState<number | null>(null);

// New handler (alongside handleStatusChange etc.)
const handleSendEmail = async (matchId: number) => {
  setSendingId(matchId);
  try {
    const updated = await sendVendorMatchOutreachEmail(matchId);
    applyUpdate(updated);
  } catch (err) {
    setError(err instanceof Error ? err.message : "Failed to send email");
  } finally {
    setSendingId(null);
  }
};
```

In the table row, add a "Send" button in the Status `<td>`, after the
`<select>`:
```tsx
{m.outreach_status === "not_contacted" && (
  <button
    onClick={() => handleSendEmail(m.id)}
    disabled={sendingId === m.id || !sol.outreach_email_body}
    title={!sol.outreach_email_body ? "No outreach email template — run vendor matching first" : undefined}
    className="ml-1.5 inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded border border-border
               bg-surface-1 hover:bg-surface-3 text-text-primary transition-colors
               disabled:opacity-50 disabled:cursor-not-allowed"
  >
    {sendingId === m.id ? <Loader2 size={10} className="animate-spin" /> : <Send size={10} />}
    Send
  </button>
)}
```
`Send` and `Loader2` are already imported in this file (line 4). No new
icon imports needed. `sol` is already in scope (component-level state).

If `m.contact_email` is falsy, don't render the button at all — nest the
above inside `{m.contact_email && (...)}`. This mirrors the existing
`contact_email ? ... : "hidden"` pattern in `VendorMatchesTab.tsx`
(lines 335-348) rather than inventing a new convention.

---

## 8. Verdict — how each half is proven done

### 10a (Outbound) — testable now, no prerequisites

1. `python backend/init_db.py` — confirm migration 23 applies cleanly, no
   errors, `schema_migrations` has a row `(23, 'vendor_outreach_email')`.
2. Restart `start.sh`. Confirm `/openapi.json` lists
   `POST /api/vendor-matches/{match_id}/outreach/send`.
3. Real HTTP request (matching the existing "success, 404, 400" pattern
   T8's acceptance criteria used): pick a `vendor_matches` row whose
   `contact_email` is not the sentinel and whose solicitation has
   `outreach_email_subject`/`body` set. If using the sandbox domain,
   the `to_email` must be an authorized recipient in the Mailgun sandbox
   dashboard first (Mailgun sandbox restriction — not app-controlled).
   - `POST /api/vendor-matches/{id}/outreach/send` → 200, response has
     `outreach_status: "requested"`, `outreach_requested_at` set.
   - `POST` again on a match with no `contact_email` → 400.
   - `POST` on a non-existent match id → 404.
4. Confirm in Mailgun's dashboard (Sending → Logs) that the message shows
   as accepted/delivered.
5. Frontend: reload Outreach tab, confirm "Send" button appears only for
   `not_contacted` rows with an email, click it, confirm status flips to
   Requested with a timestamp and the button disappears (since status is
   no longer `not_contacted`).

### 10b (Inbound) — two-tier verdict

**Tier 1 (buildable/testable today, no domain prerequisite):** simulate
Mailgun's POST directly against the running local server:
```bash
curl -X POST http://127.0.0.1:8400/api/webhooks/mailgun/inbound \
  -F "recipient=vmatch-<realtoken>@inbound.justicequest.pro" \
  -F "sender=vendor@example.com" \
  -F "subject=Re: Quote Request" \
  -F "stripped-text=Here is our quote, attached." \
  -F "timestamp=<unix_ts>" \
  -F "token=<any_50_char_string>" \
  -F "signature=<hmac_sha256_hex(signing_key, ts+token)>"
```
Compute the signature locally with the same `MAILGUN_WEBHOOK_SIGNING_KEY`
from `.env` (Python: `hmac.new(key.encode(), f"{ts}{token}".encode(), hashlib.sha256).hexdigest()`).
Use a real `<realtoken>` from a `vendor_matches.outreach_reply_token` row
(seed one via a completed 10a send). Confirm: 200 response, a `jobs` row
with `job_type='inbound_email'` appears and reaches `status='complete'`,
a new `documents` row exists with `source='email'`, and the vendor match's
`outreach_status` flips to `received` with `outreach_doc_id` set.
Also test: wrong signature → 401. Unknown recipient token → 200 with
`{"status": "ignored", ...}` (not an error — Mailgun must not retry this).

**Tier 2 (needs human-completed §0 prerequisites):** send a real email to
a `vmatch-{token}@inbound.justicequest.pro` address from an external mailbox, confirm
it flows through Mailgun's route → Cloudflare tunnel → the same pipeline
as Tier 1, end-to-end, with no manual curl involved.

**Do not mark T10b "done" in `TICKETS.md` until at least Tier 1 passes.**
Tier 2 requires the human to complete §0 first — flag back if blocked
there rather than guessing tunnel/route configuration.


