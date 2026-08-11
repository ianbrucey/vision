# Roles, Assignment & Quotes — Implementation Plan

**Date:** August 11, 2026
**Author:** Vision Product

---

## Current State

| What | Exists? | Details |
|---|---|---|
| Users table | ✅ | `users`: id (uuid), username, email, password_hash, role (text), is_active |
| Auth system | ✅ | JWT login/register, `role` = `"admin"` or `"user"` |
| Admin user | ✅ | 1 admin (`username: admin`), 11 regular users |
| User management UI | ❌ | No page for admin to create/edit/disable users |
| Solicitation assignment | ❌ | No way to assign a solicitation to a user |
| Quotes | ❌ | No quotes table, no quotes UI |

---

## Ticket Hierarchy

```
T1 — Admin User Management
│
├── T1.1 — Backend: User CRUD endpoints (admin-only)
├── T1.2 — Frontend: Admin Settings page
│
T2 — Solicitation Assignment
│
├── T2.1 — DB: solicitations.assignee_id → users.id
├── T2.2 — Backend: Claim / Release endpoints
├── T2.3 — Frontend: Assign button on solicitation rows / case header
│
T3 — Quotes
│
├── T3.1 — DB: quotes table
├── T3.2 — Backend: Quotes CRUD endpoints
├── T3.3 — Frontend: Quotes tab on case detail
│
T4 — My Work Dashboard (stretch)
│
├── T4.1 — Backend: "my solicitations" endpoint
├── T4.2 — Frontend: "My Queue" page
```

---

## T1 — Admin User Management

### T1.1 — Backend: User CRUD Endpoints

**Goal:** Admin can create, list, update, and disable users via the API.

**Routes (all require `role=admin`):**

```
POST   /api/admin/users          — create a user (username, email, password, role)
GET    /api/admin/users          — list all users
PATCH  /api/admin/users/{id}     — update user (email, role, is_active)
```

**Status:** `pending`

**Files to touch:**
- `backend/api/routes/admin.py` (new)
- `backend/auth/__init__.py` (add `require_admin` dependency)
- `backend/api/main.py` (register router)

**Acceptance criteria:**
- Admin can create a user with username + password + optional email
- Admin can list all users
- Admin can toggle `is_active` (soft-disable)
- Admin can change a user's role (user ↔ admin)
- Non-admin requests return 403
- New user can log in immediately

---

### T1.2 — Frontend: Admin Settings Page

**Goal:** Admin sees a Settings/Users page to manage accounts.

**Route:** `/settings` (admin-only, hidden from nav for non-admins)

**Status:** `pending` (depends on T1.1)

**Files to touch:**
- `frontend/src/app/settings/page.tsx` (new)
- `frontend/src/lib/api.ts` (add `listUsers`, `createUser`, `updateUser`)
- `frontend/src/components/Nav.tsx` or equivalent (add Settings link for admin)

**Acceptance criteria:**
- Admin navigates to /settings → sees user table
- "Add User" button → modal with username, email, password, role dropdown
- Edit button → inline edit email, role, active toggle
- Disable button → sets is_active=false (can be re-enabled)
- Non-admin users don't see the Settings link, get 403 if they navigate directly

---

## T2 — Solicitation Assignment

### T2.1 — DB: add `assignee_id` to solicitations

**Goal:** Each solicitation can be claimed by one user.

**Migration:**

```sql
ALTER TABLE solicitations
  ADD COLUMN assignee_id uuid REFERENCES users(id),
  ADD COLUMN assigned_at timestamptz;
```

**Status:** `pending`

**Acceptance criteria:**
- Column exists, FK to users.id
- NULL = unassigned
- Can query "show me all solicitations assigned to user X"

---

### T2.2 — Backend: Claim / Release Endpoints

**Goal:** Users can claim and release solicitations. Admin can reassign.

**Routes:**

```
POST   /api/solicitations/{id}/claim     — claim for current user
POST   /api/solicitations/{id}/release   — release (unclaim)
POST   /api/solicitations/{id}/assign    — admin assigns to any user (body: {user_id})
GET    /api/solicitations?assignee=me    — my solicitations (add filter to existing list)
```

**Status:** `pending` (depends on T2.1)

**Files to touch:**
- `backend/api/routes/solicitations.py`
- `backend/core/solicitation.py` (`SolicitationManager.update` already handles arbitrary columns)

**Acceptance criteria:**
- User clicks "Claim" → `assignee_id` = current user, `assigned_at` = now
- User clicks "Release" → `assignee_id` = NULL
- Admin can assign any solicitation to any user
- Claiming an already-claimed solicitation returns 409 Conflict
- `GET /api/solicitations?assignee=me` returns only the current user's solicitations

---

### T2.3 — Frontend: Assign/Claim Button

**Goal:** Users see and interact with assignment status on the solicitations list and case detail.

**Status:** `pending` (depends on T2.2)

**Files to touch:**
- `frontend/src/app/solicitations/page.tsx` (add assignee column + claim button)
- `frontend/src/app/cases/[id]/page.tsx` or case header (show assignee, claim button)
- `frontend/src/lib/api.ts` (add `claimSolicitation`, `releaseSolicitation`, `assignSolicitation`)

**Acceptance criteria:**
- Solicitations list shows assignee name (or "Unassigned")
- "Claim" button visible on unassigned rows
- "Release" button visible on rows assigned to current user
- Admin sees a dropdown to assign any user
- Case detail header shows assignee

---

## T3 — Quotes

### T3.1 — DB: `quotes` table

**Goal:** Store quotes attached to solicitations.

**Schema:**

```sql
CREATE TABLE quotes (
    id              serial PRIMARY KEY,
    external_id     uuid DEFAULT gen_random_uuid(),
    solicitation_id integer NOT NULL REFERENCES solicitations(id) ON DELETE CASCADE,
    created_by      uuid NOT NULL REFERENCES users(id),

    -- Quote content
    notes           text,              -- freeform text area
    amount          numeric(12,2),     -- optional dollar amount
    poc_name        text,              -- point of contact at the subcontractor
    poc_email       text,
    poc_phone       text,

    -- Status
    status          text NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'pending_site_visit', 'submitted', 'awarded', 'lost')),

    -- Attachments (link to documents table)
    document_id     integer REFERENCES documents(id),

    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

CREATE INDEX idx_quotes_solicitation ON quotes(solicitation_id);
CREATE INDEX idx_quotes_created_by ON quotes(created_by);
```

**Status descriptions:**
| Status | Meaning |
|---|---|
| `draft` | Being worked on, not ready |
| `pending_site_visit` | Waiting on a site visit before the sub can quote |
| `submitted` | Quote received, under review |
| `awarded` | This sub won the work |
| `lost` | This sub didn't win / quote was rejected |

**Status:** `pending`

**Acceptance criteria:**
- Table created with FK to solicitations and users
- Status enum enforces valid states
- Document attachment support via documents FK

---

### T3.2 — Backend: Quotes CRUD Endpoints

**Goal:** Full CRUD for quotes, permissioned to the user who created them + admin.

**Routes:**

```
POST   /api/solicitations/{id}/quotes          — create a quote
GET    /api/solicitations/{id}/quotes           — list quotes for a solicitation
PATCH  /api/solicitations/{id}/quotes/{qid}     — update quote (notes, amount, poc, status)
DELETE /api/solicitations/{id}/quotes/{qid}     — delete a quote
```

**Status:** `pending` (depends on T3.1)

**Files to touch:**
- `backend/api/routes/quotes.py` (new)
- `backend/core/quote.py` (new — QuoteManager CRUD)
- `backend/api/main.py` (register router)

**Acceptance criteria:**
- User creates a quote → `created_by` = current user, status = `draft`
- User edits their own quote → updates fields
- User can change status: draft → pending_site_visit → submitted
- Admin can see/edit all quotes
- Non-owner non-admin gets 403 on edit/delete
- List endpoint returns all quotes for a solicitation

---

### T3.3 — Frontend: Quotes Tab

**Goal:** New tab on the case detail page for managing quotes.

**Status:** `pending` (depends on T3.2)

**Files to touch:**
- `frontend/src/app/cases/[id]/tabs/QuotesTab.tsx` (new)
- `frontend/src/app/cases/[id]/TabNav.tsx` (add "Quotes" tab)
- `frontend/src/app/cases/[id]/page.tsx` (wire tab)
- `frontend/src/lib/api.ts` (add `createQuote`, `listQuotes`, `updateQuote`, `deleteQuote`)

**Acceptance criteria:**
- "Quotes" tab visible on solicitation-backed cases
- "Add Quote" button → form with:
  - Text area for notes/details
  - Amount field (optional, dollar)
  - POC name, email, phone fields
- Each quote shows: status badge, amount, POC, created by, age
- "Mark Pending Site Visit" button → sets status to `pending_site_visit`
- "Submit" button → sets status to `submitted`
- Edit/delete available to quote owner and admin

---

## T4 — My Work Dashboard (Stretch)

### T4.1 — Backend: "My Solicitations" Endpoint

**Goal:** Quick endpoint returning the current user's assigned solicitations with quote counts.

**Route:**

```
GET /api/solicitations/mine   — returns assigned solicitations + quote summary
```

**Status:** `pending` (depends on T2.2, T3.2)

---

### T4.2 — Frontend: "My Queue" Page

**Goal:** A dashboard showing the user's assigned work at a glance.

**Route:** `/my-work`

**Status:** `pending` (depends on T4.1)

**Acceptance criteria:**
- Shows assigned solicitations grouped by status (needs triage, needs quote, ready)
- Shows quote pipeline: draft count, pending site visit count, submitted count
- Sorted by response deadline (closest first)

---

## Dependency Graph

```
T1.1 (Admin CRUD backend)
  └── T1.2 (Admin UI)

T2.1 (assignee_id column)
  └── T2.2 (Claim endpoints)
        └── T2.3 (Claim UI)
              └── T4.1 (My work endpoint)
                    └── T4.2 (My Queue page)

T3.1 (quotes table)
  └── T3.2 (Quotes endpoints)
        └── T3.3 (Quotes tab)
              └── T4.2 (My Queue shows quote counts)

T1 and T2/T3 are independent — can be built in parallel.
```

---

## Recommended Build Order

1. **T1.1 + T1.2** — Admin user management (unblocks nothing else but is foundational)
2. **T2.1 + T2.2 + T2.3** — Assignment system (users need to claim work)
3. **T3.1 + T3.2 + T3.3** — Quotes (the core feature)
4. **T4.1 + T4.2** — My Queue (ties everything together)

T1 and T2 can be built in parallel if needed — they don't depend on each other.
