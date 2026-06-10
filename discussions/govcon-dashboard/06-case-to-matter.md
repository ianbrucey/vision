# Case → Matter Rename

**Status:** Straightforward but large

## What it is

Rename "case" to "matter" throughout the entire codebase. This is a Clio-style
naming convention where everything is a "matter" rather than a "case" —
acknowledging that not everything is litigation (some are RFPs, contracts, etc.).

## Scope

This is a pure rename — no logic changes, no schema changes, no API contract
changes. It's a global find-and-replace across:

### Backend (~20 files)

- `backend/schemas/001_core.sql` — comments and the `cases` table name?
  **Actually, do NOT rename the database table** — that's a breaking migration.
  Only rename user-facing text, variable names, comments, and API docs.
- `backend/api/main.py` — route docstrings, variable names, comments
- `backend/api/routes/*.py` — route docstrings, comments
- `backend/chat/prompt.py` — system prompt references
- `backend/chat/tools.py` — tool descriptions
- `backend/core/case.py` — class name `CaseManager` → `MatterManager`,
  variable names, comments
- `backend/core/db.py` — function names like `insert_case` → `insert_matter`,
  docstrings
- `backend/ingestion/` — comments and variable names

### Frontend (~30 files)

- `frontend/src/lib/api.ts` — function names (`getCase` → `getMatter`),
  interface names (`Case` → `Matter`), URL paths
- `frontend/src/app/` — page names, component names, route paths
- `frontend/src/components/` — component names, prop names
- User-facing text: "Case" → "Matter", "Cases" → "Matters", "case" → "matter"

### Database considerations

**Do NOT rename:**
- The `cases` PostgreSQL table (this is a multi-day migration with downtime)
- The `case_id` columns (FK relationships across 15+ tables)
- The `/api/cases/` URL prefix (breaks API contract with frontend during
  transition)

**Do rename:**
- User-facing labels and text
- React component names and file names
- TypeScript interfaces and function names
- Variable names and comments
- System prompts and tool descriptions

## Strategy

Phased approach to avoid breaking everything at once:

### Phase 1: User-facing text only
- Change all UI labels from "Case" to "Matter"
- Update system prompts to say "matter" instead of "case"
- Zero API or DB changes — safe, deployable immediately

### Phase 2: Code identifiers
- Rename TypeScript interfaces, functions, variables
- Rename Python classes, functions, variables
- File renames (components, pages)
- Keep API paths and DB names unchanged

### Phase 3 (optional, future): Database + API
- Rename `cases` table → `matters`
- Rename `case_id` → `matter_id` across all tables
- Migrate API paths from `/api/cases/` → `/api/matters/`
- Requires downtime + migration scripts + backward compat layer

## Recommendation

Do **Phase 1 only** right now. It's 90% of the user-facing value with 10% of
the risk. A couple hours of find-and-replace. Phases 2 and 3 are nice-to-have
but introduce breaking changes that aren't worth it when "case" and "matter"
are functionally identical.

## Estimated effort

- Phase 1: ~1-2 hours (grep for "case"/"Case" in frontend, replace labels)
- Phase 2: ~3-4 hours (renames across entire codebase, testing everything)
- Phase 3: Do not attempt without a dedicated migration window
