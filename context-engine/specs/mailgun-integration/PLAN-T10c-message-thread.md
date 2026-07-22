# T10c — Per-Vendor Outreach Message Thread: Implementation Plan

Status: ready for implementation. No architectural decisions left to the
implementer. Supersedes the single "Send" button UX from `PLAN.md` §7 —
that button is removed and replaced by a thread page.

## 0. Why

`PLAN.md`'s 10a shipped a single ambient "Send" button per vendor-match
row: one click, no preview, no edit, fires a real email immediately.
User wants: inspect the drafted message per vendor, edit it, then send —
with a dedicated page per vendor showing the full conversation (sent +
received messages), not just a status pill.

Rejected alternative: reusing `correspondence_threads`/`correspondence_items`
(existing feature in `004_correspondence.sql`). Rejected because:
- Those tables FK `sender_party_id`/`receiver_party_id` to `parties`
  (litigation parties — plaintiff/defendant/counsel), not vendors. Forcing
  vendor contacts into `parties` is a semantic misuse of that table.
- `correspondence_items` has one freeform `notes` field — no
  subject/body split, no `draft` state, no Mailgun `message_id`/
  reply-token columns, and never triggers a real send. It's a manual
  "log what happened" feature; this is a "compose → edit → send" feature.

Each `vendor_matches` row is already the unique vendor↔solicitation
pairing, so it doubles as the "thread" — no separate threads table needed.

## 1. Schema — Migration v24

New file `backend/schemas/015_vendor_outreach_messages.sql`:

```sql
-- ============================================================================
-- Vision — Vendor Outreach Messages Migration v24
-- ============================================================================
-- One row per message (outbound draft/sent, or inbound reply) in a vendor
-- match's outreach thread. Replaces the one-shot outreach_message_id/
-- outreach_reply_token columns added to vendor_matches in v23 (014) as the
-- system of record for send state — those columns remain on vendor_matches
-- for now (still written by mark_email_sent for backward-compat/rollup
-- convenience) but are no longer the only place a send is tracked.
-- ============================================================================

SET search_path TO vision, public;

CREATE TABLE IF NOT EXISTS vendor_outreach_messages (
    id                  SERIAL PRIMARY KEY,
    vendor_match_id     INTEGER REFERENCES vendor_matches(id) ON DELETE CASCADE NOT NULL,
    direction           TEXT NOT NULL CHECK (direction IN ('outbound', 'inbound')),
    status              TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'sent', 'failed')),
    subject             TEXT NOT NULL,
    body                TEXT NOT NULL,
    mailgun_message_id  TEXT,
    reply_token         TEXT,
    document_id         INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    sent_at             TIMESTAMPTZ,
    received_at         TIMESTAMPTZ,
    error_message       TEXT,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_outreach_messages_match
    ON vendor_outreach_messages (vendor_match_id, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_outreach_messages_reply_token
    ON vendor_outreach_messages (reply_token) WHERE reply_token IS NOT NULL;

INSERT INTO schema_migrations (version, name) VALUES (24, 'vendor_outreach_messages')
ON CONFLICT (version) DO NOTHING;
```

Notes:
- `status='draft'` rows only exist for `direction='outbound'` (inbound
  messages are always terminal — created already `sent`... actually
  inbound has no `status` concept; see §3, inbound rows leave `status`
  at its default `'draft'` value unused/ignored — reader code must
  branch on `direction` first, never treat `status` as meaningful for
  inbound rows. Do not add a CHECK cross-referencing direction+status;
  keep it simple, document via docstring only, per existing codebase's
  tolerance for this pattern (see `documents.storage_path` nullable-with-
  comment precedent).
- `reply_token` moves here from `vendor_matches.outreach_reply_token`
  (v23) — the webhook handler (§4) now looks up by
  `vendor_outreach_messages.reply_token`, one row per sent message, so a
  vendor match can have multiple independent reply-token threads if
  re-sent.
- `vendor_matches.outreach_message_id`/`outreach_reply_token` (v23,
  `014_vendor_outreach_email.sql`) are left in place, unused going
  forward — no down-migration; additive-only per `database-design.md` §5.6.

### `core/db.py` — `ensure_vendor_outreach_messages_schema()`

Same pattern as `ensure_vendor_outreach_email_schema` (see `PLAN.md` §1),
reading `015_vendor_outreach_messages.sql`. Add to `__all__`.

### `api/main.py` / `init_db.py` — wire in

Same pattern as v23's wiring (import + call in `_apply_schemas()` /
`main()`), placed immediately after `ensure_vendor_outreach_email_schema()`.

## 2. Backend — `core/vendor_match.py` additions

Add to `VendorMatchManager` (or a new lightweight module-level set of
functions in `core/db.py` if preferred — but per `python-fastapi-structure.md`
§2.3, since this touches vendor_matches state (outreach_status rollup) and
vendor identity (contact_email, template substitution), it belongs as
methods on the existing `VendorMatchManager`, not new bare `core/db.py`
functions):

```python
def create_draft_message(self, match_id: int) -> dict:
    """Create (or return existing) draft outbound message for a match.

    Idempotent: if a draft already exists for this match_id, returns it
    unchanged rather than creating a duplicate. Substitutes
    {{vendor_name}}/{{match_reason}} into the solicitation's
    outreach_email_subject/body (same substitution as the old
    send_outreach_email_endpoint — see PLAN.md lines 364-368). Raises
    ValueError if the match has no contact_email, or the solicitation has
    no outreach_email_subject/body.
    """

def list_messages(self, match_id: int) -> list[dict]:
    """All messages for a match, chronological (created_at ASC)."""

def update_draft_message(self, message_id: int, subject: str | None = None,
                          body: str | None = None) -> dict:
    """Edit a draft's subject/body. Raises ValueError if the message is
    not status='draft' (sent/failed messages are immutable)."""

def send_message(self, message_id: int) -> dict:
    """Send a draft message via Mailgun. Generates reply_token, sets
    Reply-To: vmatch-{token}@{MAILGUN_DOMAIN}, calls send_email() (from
    core/email_mailgun.py). On success: status='sent', sent_at=now(),
    mailgun_message_id set; also updates the parent vendor_matches row
    to outreach_status='requested' (COALESCE-guarded timestamp, reusing
    update_outreach()) for rollup display in OutreachTab/VendorMatchesTab.
    On MailgunSendError: status='failed', error_message set, re-raises
    so the route returns 502. Raises ValueError if message is not
    status='draft' (no re-sending a sent message; create a new draft
    instead — v1 has no "reply/follow-up" compose UI, see §6 open item)."""
```

## 3. Backend — `core/email_mailgun.py`

No changes — `send_email()` signature (`to_email, to_name, subject,
text_body, reply_to`) already fits `send_message()`'s needs exactly.

## 4. Backend — `backend/api/routes/webhooks_mailgun.py` changes

Replace the `find_by_reply_token`/enqueue logic (current lines 78-95) to
look up `vendor_outreach_messages.reply_token` instead of
`vendor_matches.outreach_reply_token`:

```python
message = vendor_match_mgr.find_message_by_reply_token(reply_token)
if message is None:
    return {"status": "ignored", "reason": "no message for token"}

job = _enqueue_job(
    case_id=message["case_id"],
    job_type="inbound_email",
    metadata={
        "vendor_match_id": message["vendor_match_id"],
        "sender": sender,
        "subject": subject,
        "text": text,
    },
)
```

New `VendorMatchManager.find_message_by_reply_token(token) -> dict | None`:
joins `vendor_outreach_messages` → `vendor_matches` → `solicitations` for
`case_id` + `vendor_match_id` (mirrors old `find_by_reply_token`, PLAN.md
lines 379-401, but sourced from the messages table).

## 5. Backend — `backend/ingestion/worker.py::process_inbound_email_job` changes

Currently creates a `documents` row and calls
`VendorMatchManager().update_outreach(vendor_match_id, outreach_status="received", outreach_doc_id=doc_id)`
(PLAN.md lines 706-774). Keep the document-creation logic unchanged, but
additionally insert a new `vendor_outreach_messages` row
(`direction='inbound'`, `subject`, `body=text`, `document_id=doc_id`,
`received_at=now()`) via a new `VendorMatchManager.record_inbound_message()`
method, so the reply shows up in the thread view (§7) alongside the
outbound message it replied to. Still call `update_outreach(...,
outreach_status="received", outreach_doc_id=doc_id)` for OutreachTab/
VendorMatchesTab rollup compatibility — no changes needed there.

## 6. Backend — `backend/api/routes/solicitations.py` changes

Remove `send_outreach_email_endpoint` (`POST /vendor-matches/{id}/outreach/send`,
lines 324-385) and its now-unused `secrets`/`send_email`/`MailgunSendError`
imports if nothing else in the file uses them (confirm via grep before
removing — `os` is still used for `MAILGUN_DOMAIN` lookups if kept
elsewhere, else remove too).

Add:

```python
@router.get("/vendor-matches/{match_id}/messages")
def list_vendor_match_messages_endpoint(match_id: int, user: dict = Depends(get_current_user)):
    """All outreach messages (outbound + inbound) for a vendor match, plus
    the match itself, for the thread page (T10c)."""
    match = vendor_match_mgr.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Vendor match not found")
    return {"match": match, "messages": vendor_match_mgr.list_messages(match_id)}


@router.post("/vendor-matches/{match_id}/messages/draft", status_code=201)
def create_draft_message_endpoint(match_id: int, user: dict = Depends(get_current_user)):
    """Create (or return existing) draft outbound message for a match."""
    try:
        return vendor_match_mgr.create_draft_message(match_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class UpdateDraftMessageRequest(BaseModel):
    subject: str | None = None
    body: str | None = None


@router.patch("/vendor-match-messages/{message_id}")
def update_draft_message_endpoint(message_id: int, body: UpdateDraftMessageRequest, user: dict = Depends(get_current_user)):
    try:
        return vendor_match_mgr.update_draft_message(message_id, subject=body.subject, body=body.body)
    except ValueError as e:
        detail = str(e)
        status_code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail)


@router.post("/vendor-match-messages/{message_id}/send")
def send_message_endpoint(message_id: int, user: dict = Depends(get_current_user)):
    try:
        return vendor_match_mgr.send_message(message_id)
    except MailgunSendError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        detail = str(e)
        status_code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail)
```

Route naming: `/vendor-match-messages/{message_id}` (not nested under
`/vendor-matches/{match_id}/messages/{message_id}`) because a message id
alone is globally unique and sufficient — matches the existing flat
`/vendor-matches/{match_id}/outreach` precedent in this same file (not
nested under `/solicitations/{id}/...`).

## 7. Frontend

### `frontend/src/lib/api.ts` additions

```typescript
export interface VendorOutreachMessage {
  id: number;
  vendor_match_id: number;
  direction: "outbound" | "inbound";
  status: "draft" | "sent" | "failed";
  subject: string;
  body: string;
  mailgun_message_id: string | null;
  document_id: number | null;
  sent_at: string | null;
  received_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export const getVendorMatchMessages = (
  matchId: number,
): Promise<{ match: VendorMatch; messages: VendorOutreachMessage[] }> =>
  fetchAPI(`/api/vendor-matches/${matchId}/messages`);

export const createDraftMessage = (
  matchId: number,
): Promise<VendorOutreachMessage> =>
  fetchAPI(`/api/vendor-matches/${matchId}/messages/draft`, { method: "POST" });

export const updateDraftMessage = (
  messageId: number,
  updates: { subject?: string; body?: string },
): Promise<VendorOutreachMessage> =>
  fetchAPI(`/api/vendor-match-messages/${messageId}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });

export const sendMessage = (
  messageId: number,
): Promise<VendorOutreachMessage> =>
  fetchAPI(`/api/vendor-match-messages/${messageId}/send`, { method: "POST" });
```

Remove `sendVendorMatchOutreachEmail` (superseded by `sendMessage`).

### `OutreachTab.tsx` changes

Remove the inline "Send" button (lines 193-205) and `sendVendorMatchOutreachEmail`
import/`handleSendEmail`/`sendingId` state. Replace the Status `<td>`'s
button with a link/button that navigates to the thread page:

```tsx
<button
  onClick={() => router.push(`/cases/${caseId}/vendor-matches/${m.id}`)}
  className="ml-1.5 inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded border border-border
             bg-surface-1 hover:bg-surface-3 text-text-primary transition-colors"
>
  <MessageSquare size={10} />
  Messages
</button>
```
Always rendered (not gated on `outreach_status === "not_contacted"` —
the thread page itself handles "no draft yet" vs "has messages" states).
Requires `useRouter` import from `next/navigation` and `caseId` prop
(already passed into `OutreachTab`).

### New page: `frontend/src/app/cases/[id]/vendor-matches/[matchId]/page.tsx`

Full-page route (per user decision), same auth/layout shell pattern as
`cases/[id]/page.tsx` (header with back button → `/cases/${id}?tab=outreach`,
`"use client"`, wrapped in `<Suspense>` if it uses `useSearchParams` —
it doesn't need to, so a plain client component is sufficient here,
following the simpler pattern of e.g. `login/page.tsx` rather than the
`Suspense`-wrapped `cases/[id]/page.tsx`).

Structure:
- Header: vendor name, contact_email, back link.
- Message list: chronological cards, `direction === "outbound"` right-
  aligned/brand-tinted, `inbound` left-aligned/neutral (standard chat-
  thread visual convention — no existing precedent in this codebase to
  match, so this is a new but conventional pattern within
  `design-system.md`'s existing color tokens: `bg-brand-bg` for outbound,
  `bg-surface-2` for inbound).
- Each outbound `status='draft'` message renders **editable** subject
  (text input) + body (`textarea`), autosaving on blur via
  `updateDraftMessage` (debounce not required — v1 can save on blur only,
  matches existing codebase's lack of a shared debounce utility), plus a
  "Send" button calling `sendMessage`.
- Each outbound `status='sent'`/`'failed'` message renders read-only
  (no textarea) with a status pill (`sent` = success color, `failed` =
  danger color + `error_message` shown).
- Each inbound message renders read-only, with a "View document" link
  (reuses `DocumentPreviewModal`, `document_id`) if attached.
- If no draft exists yet (checked via `messages.some(m => m.status === 'draft')`
  being false) and no `sent` outbound message exists either, show a
  "Create Draft" button calling `createDraftMessage`, then refresh.
- Loading/error states follow `OutreachTab.tsx`'s existing pattern
  (`Loader2` spinner, `error` string banner).

### `TabNav.tsx`/`page.tsx`

No changes — this is a standalone route, not a tab.

## 8. Verdict

1. `python backend/init_db.py` — migration 24 applies, `schema_migrations`
   has `(24, 'vendor_outreach_messages')`.
2. Restart `start.sh`. `/openapi.json` lists the 4 new routes from §6 and
   no longer lists `POST /api/vendor-matches/{match_id}/outreach/send`.
3. `POST /api/vendor-matches/{id}/messages/draft` on a match with a
   contact_email + template → 201, `status: "draft"`, subject/body
   substituted. Calling again on the same match → returns the same draft
   (no duplicate row) — verify via `SELECT count(*) FROM
   vendor_outreach_messages WHERE vendor_match_id = {id}` staying at 1.
4. `PATCH /api/vendor-match-messages/{id}` with edited body → 200,
   persisted; `GET .../messages` reflects the edit.
5. Frontend: open thread page, confirm draft is editable, edit + blur
   persists (reload page, edit still there), "Create Draft" button is
   absent once a draft exists.
6. **Do not call `POST /vendor-match-messages/{id}/send` against a real
   vendor email during this verdict pass** — that step requires explicit
   user go-ahead per the earlier conversation. Verify the send code path
   only via the existing Tier-1 curl-style reasoning (code review) until
   user approves a live send test.
7. Tier 1 inbound (webhook curl simulation) re-run against a real
   `reply_token` sourced from a `vendor_outreach_messages` row (not
   `vendor_matches.outreach_reply_token`, which is now unused) — confirm
   a new `direction='inbound'` message row appears, plus a `documents`
   row, plus `vendor_matches.outreach_status` flips to `received`.

## 9. Open items (explicitly out of scope for this pass)

- No "compose follow-up" UI yet (creating a second outbound draft after
  the first is sent) — `send_message` blocks re-sending a sent message,
  and there's no button to create a second draft once one exists. Flag
  to user as a fast-follow if needed.
- No manual thread creation for a vendor match with no template/contact
  email — `create_draft_message` raises ValueError, surfaced as a 400 in
  the UI's error banner, no dedicated empty-state copy for that case.
