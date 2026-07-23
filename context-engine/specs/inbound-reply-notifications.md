# Inbound Reply Notifications — Spec

> **Status:** Draft  
> **Date:** 2026-07-22  

---

## 1. Problem

When a vendor replies to an outreach email, there is no way to know unless you:

- Manually open the Outreach tab for each solicitation
- Check every vendor match for a green "Received" badge

Scale: 20 RFQs × 5 vendors each = 100 potential replies. Missing one could mean
losing a subcontracting partner.

---

## 2. Requirements

### R1 — In-app unread indicator

A persistent badge/count visible from:

1. **Dashboard** (`/solicitations`) — each solicitation row shows a reply count
   badge if it has unread vendor replies
2. **Case sidebar** — "Outreach" tab shows a count badge (e.g. "Outreach (3)")
3. **Outreach tab** — individual vendor rows highlight unread replies

### R2 — Email notification on inbound reply

When a vendor reply is processed, send a notification email to
`ian.b@justicequest.pro` (address configurable via env var) containing:

- Vendor name and contact
- Solicitation title
- Reply subject and first 300 chars of body
- Direct link to the thread page

### R3 — Mark as read

Opening a vendor match thread page marks all inbound messages in that
thread as read. No manual "mark read" button needed — opening the thread
is sufficient.

---

## 3. Data Model

### New column on `vendor_outreach_messages`

```sql
ALTER TABLE vendor_outreach_messages
  ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ;
```

- `NULL` = unread
- Non-null = the timestamp when the message thread was opened
- Set to `now()` when the user visits the thread page
- Only relevant for `direction = 'inbound'` messages

### New env var

```
NOTIFICATION_EMAIL=ian.b@justicequest.pro
```

---

## 4. Implementation Plan

### T1 — Database migration (5 min)

- Schema `023_inbound_read_at.sql` — add `read_at` column to
  `vendor_outreach_messages`

### T2 — Backend: mark-as-read endpoint (15 min)

- `PATCH /api/vendor-matches/{matchId}/messages/read` — sets `read_at = now()`
  on all inbound messages for that match where `read_at IS NULL`
- Called by the frontend when the thread page loads

### T3 — Backend: unread count endpoint (10 min)

- `GET /api/solicitations/{id}/unread-replies` — returns
  `{count: N, match_ids: [...]}`
- Or fold into the existing `getVendorMatches` response as
  `unread_count` per match

### T4 — Backend: email notification (15 min)

- In `process_inbound_email_job`, after successfully storing the reply,
  call `send_email()` to `NOTIFICATION_EMAIL`
- Subject: `[Vision] Reply from {vendor_name} — {solicitation_title}`
- Body: reply summary + link to thread
- Non-fatal — if the notification email fails, the inbound reply is still
  stored successfully

### T5 — Frontend: tab badge (20 min)

- `OutreachTab` fetches unread count per match
- `TabNav` accepts optional badge counts per tab
- When `unreadCount > 0`, show a red dot/badge on the Outreach tab

### T6 — Frontend: solicitation list badge (15 min)

- `listSolicitations` response includes `unread_reply_count`
- Solicitation rows show a badge if count > 0

### T7 — Frontend: mark read on thread open (10 min)

- Thread page calls `PATCH .../messages/read` on mount
- Immediately clears the unread indicator for that match

---

## 5. Data Flow

```
Vendor replies
  → Mailgun webhook
    → process_inbound_email_job
      → stores document + message (read_at = NULL)
      → sends notification email to ian.b@justicequest.pro
      
User opens Vision
  → solicitation list shows unread count per case
  → Outreach tab shows badge with count
  → Opens thread page → marks messages as read
```

---

## 6. Open Questions

1. **Notification email address** — hardcode `ian.b@justicequest.pro` or
   env var? Recommendation: env var `NOTIFICATION_EMAIL` with that default.
2. **Badge persistence** — should unread count persist across sessions?
   Yes (it's stored in the DB via `read_at`).
3. **Batch notifications** — if 5 replies come in at once, send 5 emails
   or batch them? Send individually for now (simpler, immediate).
