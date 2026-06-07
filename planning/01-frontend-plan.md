# Frontend UI/UX Plan — Vision War Room Agent

## Current State Audit

| Component | Status | Issue |
|---|---|---|
| API backend | Running on :8400 | Working. 15 endpoints. |
| Frontend scaffold | Next.js 16 + Tailwind | Shell only. Dashboard page exists but non-functional. |
| Auth | None in vision DB | Main app has users table in separate `aionui` DB. No auth in vision API. |
| Case creation | Button does nothing | API client calls `http://127.0.0.1:8400/api/cases` but no error handling, no auth, no CORS confirmation. |
| Document upload | Partial | Upload endpoint exists but frontend doesn't show feedback. Worker polls but frontend doesn't poll intelligently. |

## Architecture Decision: Auth

**Decision:** Self-contained auth in the vision database, with sync path to main app later.

The main war_room app has a `users` table in the `aionui` database with bcrypt password hashes and JWT secrets. The vision database is separate. Rather than cross-database queries now, we:

1. Add a `users` table to the vision database (matching the main app's schema)
2. Implement login/register endpoints in the FastAPI app with bcrypt + JWT
3. Frontend stores JWT in localStorage, sends via `Authorization: Bearer` header
4. Later: sync users from main app or share a common auth service

**Trade-off:** Two user tables during prototyping. Acceptable because vision is self-contained and the user count is low. The sync path is: export users from aionui → import to vision, or point vision at the aionui DB for user queries.

## Screen Flow

```
/login          →  Login page (username + password)
/register       →  Register page (username + email + password)
/ (dashboard)   →  Case list + job queue [PROTECTED]
/cases/[id]     →  Case detail: parties, allegations, documents, timeline [PROTECTED]
/cases/new      →  New case form (narrative-first) [PROTECTED]
/cases/[id]/upload →  Upload documents (drag-and-drop) [PROTECTED]
```

## Screen Designs

### 1. Login Page (`/login`)

```
┌──────────────────────────────────────────────────┐
│                                                  │
│              ⚖️  Vision                          │
│         War Room Agent                           │
│                                                  │
│    ┌──────────────────────────────────┐          │
│    │  Username                         │          │
│    └──────────────────────────────────┘          │
│    ┌──────────────────────────────────┐          │
│    │  Password                         │          │
│    └──────────────────────────────────┘          │
│                                                  │
│    ┌──────────────────────────────────┐          │
│    │         Sign In                   │          │
│    └──────────────────────────────────┘          │
│                                                  │
│    Don't have an account? Register               │
│                                                  │
└──────────────────────────────────────────────────┘
```

- Clean, centered, dark theme
- Username + password fields
- Error state: red border + "Invalid credentials" message
- Loading state: spinner on button
- On success: redirect to `/`
- JWT stored in localStorage
- Redirect to `/login` if any API call returns 401

### 2. Dashboard (`/`)

Same layout as now, but with:

**Header bar:**
```
┌──────────────────────────────────────────────────────────┐
│ ⚖️ Vision    Cases   [+] New Case         🔔 3 jobs  👤 user │
└──────────────────────────────────────────────────────────┘
```
- `Vision` → links to dashboard
- `Cases` → active nav item
- `[+] New Case` → opens create modal or navigates to `/cases/new`
- `🔔` → job notifications dropdown (queued/processing/failed counts)
- `👤` → user menu (logout)

**Create Case:**

Option A: Modal (current — inline form at top)
Option B: Full page at `/cases/new`

**Recommendation:** Full page at `/cases/new`. Reasoning:
- The case creation form is not trivial — case type selection, narrative text area, optional structured fields
- A modal constrains the narrative field (the most important one)
- Full page lets us show adaptive placeholder text based on case type
- Consistent with the "narrative-first" design principle from Destination.md

### 3. New Case Page (`/cases/new`)

```
┌──────────────────────────────────────────────────────────────┐
│ ← Back to Cases                                             │
│                                                              │
│ New Case                                                     │
│                                                              │
│ Case Name *               Case Type ▼                        │
│ ┌────────────────────┐   ┌─────────────────────────┐        │
│ │ Alhad v. Edmonds   │   │ Medical Board Complaint  │        │
│ └────────────────────┘   └─────────────────────────┘        │
│                                                              │
│ Case Number (optional)     Jurisdiction (optional)           │
│ ┌────────────────────┐   ┌─────────────────────────┐        │
│ │                    │   │ Georgia                  │        │
│ └────────────────────┘   └─────────────────────────┘        │
│                                                              │
│ Case Narrative *                          (?) Help           │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ Tell us everything you know about this case.         │    │
│ │                                                      │    │
│ │ For a medical board complaint:                       │    │
│ │ - Who is the patient? What procedure?                │    │
│ │ - Who is the respondent physician? Specialty?        │    │
│ │ - What facility? When?                               │    │
│ │ - What went wrong? What are the allegations?         │    │
│ │ - What records do you have?                          │    │
│ │ - What is your case theory?                          │    │
│ │                                                      │    │
│ │ The more detail you provide, the better the agent     │    │
│ │ can organize evidence and target relevant records.   │    │
│ └──────────────────────────────────────────────────────┘    │
│                                                              │
│ ┌──────────────────┐                                        │
│ │   Create Case    │                                        │
│ └──────────────────┘                                        │
└──────────────────────────────────────────────────────────────┘
```

- `(?)` icon opens a tooltip explaining what the agent does with the narrative
- Placeholder text adapts based on selected `case_type`
- On submit: POST to API → redirect to case detail page
- Validation: name and narrative are required

### 4. Case Detail Page (`/cases/[id]`)

```
┌──────────────────────────────────────────────────────────────┐
│ ← Dashboard   |   Alhad v. Edmonds                           │
│              Medical Board Complaint · Intake                │
│ ┌──────────┬──────────┬──────────┬──────────┐               │
│ │ Overview │ Parties  │Allegations│Documents │               │
│ └──────────┴──────────┴──────────┴──────────┘               │
│                                                              │
│ [Tab content below]                                          │
└──────────────────────────────────────────────────────────────┘
```

**Overview Tab:**
- Case metadata (name, type, status, dates, jurisdiction)
- Quick stats: X parties, Y allegations, Z documents
- Recent job activity (last 5 jobs for this case)

**Parties Tab:**
- List of parties with role badges
- Add party button → inline form or modal
- Each party: name, kind (individual/org), role tags, notes

**Allegations Tab:**
- Numbered list of allegations
- Each: ID, text, category, status (pending/supported/contradicted)
- Add allegation button

**Documents Tab:**
- Document list with type icons, page counts, OCR status
- **Upload area** (primary interaction):
```
┌──────────────────────────────────────────┐
│                                          │
│        📁  Drop files here               │
│            or click to browse            │
│                                          │
│   Supports: PDF, DOCX, JPG, PNG, CSV,    │
│   XLSX, M4A, MP3, WAV — up to 500MB     │
│                                          │
└──────────────────────────────────────────┘
```
- Uploaded files appear as cards with progress bars
- Status per file: queued → processing → complete/failed
- Completed documents are clickable (future: document viewer)

### 5. Document Upload Flow (Detailed)

```
User drops file(s)
    │
    ▼
┌─────────────────────────────┐
│ File card appears instantly │  ← Optimistic UI
│ [filename.pdf]  ████░░ 40%  │  ← Progress updates via polling
│ Status: Processing          │
└─────────────────────────────┘
    │
    │  POST /api/cases/{id}/ingest (multipart)
    │  → MinIO stored → job queued
    │  → Returns { job_id, status: "queued" }
    │
    ▼
┌─────────────────────────────┐
│ Poll GET /api/jobs/{id}     │  ← Every 2 seconds
│ Update progress bar         │
└─────────────────────────────┘
    │
    │  Worker picks up job
    │  → downloads from MinIO
    │  → OCR/transcription/extraction
    │  → indexes into evidence store
    │  → marks complete
    │
    ▼
┌─────────────────────────────┐
│ [filename.pdf]  ████████100%│
│ Status: ✓ Complete          │  ← Green checkmark
│ 327 pages · 5,687 blocks    │  ← Stats from job result
└─────────────────────────────┘
```

**Multi-file upload:**
- User can drop multiple files at once
- Each file gets its own job and progress card
- Files process in parallel (multiple workers claim different jobs)
- Drag-and-drop zone remains active even while files are processing

**Error states:**
- File too large (>500MB): reject immediately with message
- Unsupported format: reject immediately with message
- Processing failed: show error card with retry button
- Network error during upload: show error card with retry button

## Technical Implementation

### New Database Table

```sql
-- Vision users table (matches main app schema for future sync)
CREATE TABLE IF NOT EXISTS vision.users (
    id              TEXT PRIMARY KEY,           -- UUID
    username        TEXT UNIQUE NOT NULL,
    email           TEXT UNIQUE,
    password_hash   TEXT NOT NULL,
    jwt_secret      TEXT,
    role            TEXT NOT NULL DEFAULT 'user'
                    CHECK (role IN ('super_admin', 'admin', 'user')),
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    last_login      TIMESTAMPTZ
);
```

### New API Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | No | Create account |
| POST | `/api/auth/login` | No | Login → JWT |
| GET | `/api/auth/me` | Yes | Current user info |
| All existing | `/api/*` | Yes | Add JWT dependency |

### Auth Flow

```
1. User registers or logs in
2. Server validates credentials (bcrypt verify)
3. Server returns JWT (HS256, 24h expiry) + user info
4. Frontend stores JWT in localStorage
5. API client attaches `Authorization: Bearer <token>` to all requests
6. Server middleware validates JWT, extracts user_id
7. If 401, frontend redirects to /login
```

### Frontend File Structure

```
frontend/src/
├── app/
│   ├── layout.tsx           # Root layout + auth provider
│   ├── page.tsx             # Dashboard (protected)
│   ├── login/
│   │   └── page.tsx         # Login page
│   ├── register/
│   │   └── page.tsx         # Register page
│   ├── cases/
│   │   ├── new/
│   │   │   └── page.tsx     # New case form
│   │   └── [id]/
│   │       └── page.tsx     # Case detail (tabs)
│   └── globals.css
├── components/
│   ├── AuthProvider.tsx      # JWT context + redirect logic
│   ├── Navbar.tsx            # Top bar with user menu, job notifications
│   ├── CaseCard.tsx          # Case list item
│   ├── JobCard.tsx           # Job queue item with progress bar
│   ├── FileUploadZone.tsx    # Drag-and-drop upload area
│   ├── FileProgressCard.tsx  # Per-file progress card
│   ├── PartyForm.tsx         # Add/edit party form
│   ├── AllegationForm.tsx    # Add/edit allegation form
│   └── TabBar.tsx            # Tab navigation
└── lib/
    ├── api.ts               # API client (adds auth header)
    └── auth.ts              # Auth helpers (login, logout, getToken)
```

### Build Order

1. **Auth backend** — users table, register/login endpoints, JWT middleware
2. **Auth frontend** — login/register pages, AuthProvider, protected routes
3. **API client** — add JWT header, error handling for 401
4. **New case page** — narrative-first form at /cases/new
5. **Case detail page** — tabs for overview, parties, allegations, documents
6. **Document upload** — drag-and-drop zone, progress cards, multi-file
7. **Job notifications** — navbar indicator, polling, status updates
8. **Polish** — error states, loading states, empty states, responsive

### Fix: Why Create Button Doesn't Work

1. **API URL mismatch**: The API client defaults to `http://127.0.0.1:8400` but the frontend may be running on a different origin → CORS. The API has CORS middleware allowing `*` — this should work.
2. **No error feedback**: The `handleCreate` function doesn't show errors. If the API returns 500, the user sees nothing.
3. **No loading state**: Button doesn't show spinner, so user clicks multiple times.
4. **No auth**: If auth middleware is added to API, request fails with 401 with no feedback.

**Fix:** Add toast notifications for success/error, loading spinner on button, and wire up auth first.
