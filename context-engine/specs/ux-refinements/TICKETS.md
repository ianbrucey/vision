
# UX / Workflow Refinements — Ticket Backlog

> Source: `scratch.md` (2026-07-21 brain dump on solicitation pipeline UX).
> Ordered simplest → most complex. Work top to bottom unless priorities change.
> Status legend: `[ ]` not started · `[/]` in progress · `[x]` done

---

## T1 — Fix: case title never updates from SAM.gov placeholder

**Status:** [x] Done — `backend/core/solicitation.py`'s `update()` now
syncs `cases.name` whenever `title` changes. Verified live against case 46
(was stuck on placeholder, now shows the real SAM.gov title).
**Bug.** `SolicitationManager.create()` sets `cases.name = FEDERAL_TITLE_PLACEHOLDER`
("Untitled SAM.gov Opportunity (fetching...)"). `sam_fetch` later updates
`solicitations.title` with the real title, but never syncs `cases.name`. The
case page header reads `cases.name`, so it stays stuck on the placeholder
forever even after the list page (which reads `solicitations.title`) shows
the correct title.
**Fix:** `SolicitationManager.update()` should also update the backing
`cases.name` whenever `title` is in the update payload.
**Files:** `backend/core/solicitation.py`
**Acceptance:** After `sam_fetch` completes, case page header shows the real
opportunity title, not the placeholder.

---

## T2 — Home icon + navbar cleanup on case page

**Status:** [x] Done — swapped `ArrowLeft` for `Home` (lucide-react) in the
case page header, routes to `/` (solicitations list). Left `ArrowLeft` intact
in the error-state "Back to cases" link since that's a genuine back action,
not home. `tsc --noEmit` shows no new errors from this file.
Left arrow in `cases/[id]/page.tsx` header only goes to `/cases`, not home.
Replace with a `Home` icon (lucide-react) routing to `/` (solicitations list,
the actual "home" per the app's IA). Review header for general polish —
consistent spacing/icons with `app/page.tsx` and `app/cases/page.tsx` navbars.
**Files:** `frontend/src/app/cases/[id]/page.tsx`
**Acceptance:** Icon reads as "home", not "back"; navigates to `/`.

---

## T3 — Search & sort on solicitations list page

**Status:** [x] Done — added a text search box (matches `title`/`agency`,
client-side) and a sort bar (Title/Agency/Deadline/Status, toggle
asc/desc) above the solicitations list in `app/page.tsx`. Composes with
existing type/status filters. `tsc --noEmit` shows no new errors from this
file.
`app/page.tsx` has type/status filters only. Add a text search box (matches
`title`/`agency`) and column sort (title, agency, deadline, status —
ascending/descending toggle).
**Files:** `frontend/src/app/page.tsx`
**Acceptance:** Typing in search narrows the list client-side; clicking a
sort control reorders it; both work together.

---

## T4 — Pipeline status/step bar on case page

**Status:** [x] Done — new `PipelineStatusBar.tsx` component renders below
the case header (only when `hasSolicitation`), showing Fetching → Triaging →
Matching → Done. Each step's icon/color reflects pending/active/complete/
failed/skipped state; failed steps show the error message as a tooltip,
quick-killed matching shows "Matching (skipped)" with the kill reason.
Polls every 3s (same pattern as `TriageTab`/`VendorMatchesTab`) only while
`ingestion_status === "fetching"` or `triage_status`/`matching_status === "running"`. `tsc --noEmit` shows no new errors from this file.
Add a step indicator at the top of the case page (for solicitation-backed
cases only) showing: Fetching → Triaging → Matching → Done, derived from
`ingestion_status` / `triage_status` / `matching_status`. Should reflect
failed/quick-killed states distinctly, not just linear progress.
**Files:** `frontend/src/app/cases/[id]/page.tsx`, new
`frontend/src/app/cases/[id]/PipelineStatusBar.tsx`
**Acceptance:** Visiting a case mid-pipeline shows the correct current step
without manual refresh (reuse existing polling pattern from
`VendorMatchesTab`/`TriageTab`).

---

## T5 — Populate case narrative from solicitation data

**Status:** [x]
`cases.narrative` grounds the agent (`chat/tools.py`) but stays empty for
solicitation cases. On `sam_fetch` completion, synthesize a short narrative
(agency, NAICS, set-aside, deadline, description) and write it to
`cases.narrative` if not already user-edited.
**Files:** `backend/ingestion/worker.py` (`process_sam_fetch_job`),
`backend/core/case.py`
**Acceptance:** New solicitation case shows a populated narrative/Overview
tab without manual entry; chat is "grounded" immediately after fetch.

---

## T6 — Vendor Matches UI redesign (cards, mobile-friendly)

**Status:** [x]
Current `VendorMatchesTab` table requires horizontal + vertical scrolling to
see all columns. Redesign as responsive info cards (mirroring `VendorsTab`'s
website/phone/email display), eliminate horizontal overflow scrolling, keep
existing Copy Email functionality.
**Files:** `frontend/src/app/cases/[id]/tabs/VendorMatchesTab.tsx`
**Acceptance:** No horizontal scrollbar at any viewport width; all vendor
contact fields (name, email, phone, website if available) visible without
scrolling within a card; Copy Email still works.

---

## T7 — Inline vendor creation

**Status:** [x]
Allow creating a new vendor directly from `VendorsTab` (search list) and
from `VendorMatchesTab`. A vendor created from the matches list is
automatically attached to that solicitation's match list.
**Depends on:** T6 (new card UI needs a slot for "Add Vendor")
**Files:** `frontend/src/app/cases/[id]/tabs/VendorsTab.tsx`,
`VendorMatchesTab.tsx`, `backend/api/routes/vendors.py` (new create endpoint
if none exists — verify first), `backend/core/vendor_match.py`
**Acceptance:** New vendor appears in the vendors table; if created from
matches, also appears in that solicitation's `vendor_matches` immediately.

---

## T8 — Outreach tracking fields (quote requested/received)

**Status:** [x]
Tracked per-vendor-match (not per-solicitation): `outreach_status`
(not_contacted | requested | received | declined), `outreach_requested_at`,
`outreach_received_at` (auto-stamped on first transition into
requested/received), and `outreach_doc_id` linking a received response to
a row in `documents`. Kept generic — no provider-specific columns — so
automated email capture (T10) can later become another writer of the same
columns rather than requiring new schema.
**Files:** `backend/schemas/013_vendor_outreach.sql` (migration v22),
`backend/core/db.py` (`ensure_vendor_outreach_schema`), `backend/api/main.py`,
`backend/init_db.py`, `backend/core/vendor_match.py`
(`update_outreach`, extended `get_match`/`list_for_solicitation`),
`backend/api/routes/solicitations.py`
(`PATCH /api/vendor-matches/{id}/outreach`), `frontend/src/lib/api.ts`,
new `frontend/src/app/cases/[id]/tabs/OutreachTab.tsx` (dedicated tab),
`TabNav.tsx`, `page.tsx`.
**Acceptance:** Can mark a vendor match's outreach status, attach/detach a
document to a received response, and see it surfaced in a new "Outreach"
tab — verified end-to-end against the live DB and via real HTTP requests
(success, 404 on missing match, 400 on invalid status).

---

## T9 — Solicitation lifecycle status

**Status:** [ ]
**Needs schema design.**
Add `proposal_status` to `solicitations` (e.g. `submitted`, `rejected`,
`awarded`) with UI to set/display it.
**Files:** new migration, `backend/core/solicitation.py`, case page header
(pairs naturally with T4's step bar)
**Acceptance:** Status is settable from the UI and displayed on both the
list page and case page.

---

## T10 — Email sending integration (Mailtrap/Resend/Mailgun)

**Status:** [ ]
**Largest ticket — needs a provider decision first.** Preview email, send to
one vendor, or send-all from Vendor Matches. Requires: provider choice,
API key config, backend send endpoint, delivery status tracking (ties into
T8's "quote requested" flag).
**Depends on:** T6 (UI), T8 (tracking fields)
**Files:** TBD pending provider choice — new `backend/core/email.py` or
similar, `backend/api/routes/solicitations.py`, `VendorMatchesTab.tsx`
**Acceptance:** Sending an email from the UI actually delivers (verified via
provider's sandbox/test mode), and updates outreach-tracking fields.
