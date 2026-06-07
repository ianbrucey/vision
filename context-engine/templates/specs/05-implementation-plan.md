# Implementation Plan - Zero Ambiguity Artifact

> **Generated From:** All Specs (00-Brief, 01-Schema, 02-Contract, 03-Fixtures, 04-UI)
> **Rule:** Each ticket is atomic. Backend-Out sequencing (DB → API → UI).
> **Executor:** `python scripts/executor.py`

---

## Sequencing Rules

1. **Database tickets** complete before API tickets start
2. **API tickets** complete before UI tickets start
3. **Each ticket** references specific spec files
4. **Each ticket** has a defined Verdict (test)

---

## Ticket 1: [Migration Title]

**Priority:** High
**Type:** Migration
**File:** `database/migrations/YYYY_MM_DD_create_[table]_table.php`

**Description:**
[What this migration creates/modifies]

**Acceptance Criteria:**
- [ ] Migration creates table with all columns from schema
- [ ] Indexes created for foreign keys
- [ ] Migration can rollback cleanly

**References:**
- Schema: `01-schema.sql`
- Infrastructure: [REUSE/EXTEND/NEW]

---

## Ticket 2: [Model Title]

**Priority:** High
**Type:** Model
**File:** `app/Models/[Model].php`

**Description:**
[What this model represents and its relationships]

**Acceptance Criteria:**
- [ ] Model extends base Model class
- [ ] $fillable array matches schema columns
- [ ] Relationships defined correctly
- [ ] Casts defined for special fields

**References:**
- Schema: `01-schema.sql`

---

## Ticket 3: [Controller Title]

**Priority:** Medium
**Type:** Controller
**File:** `app/Http/Controllers/[Resource]Controller.php`

**Description:**
[What endpoints this controller provides]

**Acceptance Criteria:**
- [ ] All endpoints from API contract implemented
- [ ] Request validation applied
- [ ] Proper HTTP status codes
- [ ] Error handling follows standards

**References:**
- API Contract: `02-api-contract.json`
- Fixtures: `03-fixtures.json`

---

## Ticket 4: [Route Title]

**Priority:** Medium
**Type:** Route
**File:** `routes/api.php`

**Description:**
[What routes are being added]

**Acceptance Criteria:**
- [ ] Routes match API contract paths
- [ ] Middleware applied correctly
- [ ] Route names follow conventions

**References:**
- API Contract: `02-api-contract.json`

---

## Ticket 5: [Component Title]

**Priority:** Low
**Type:** Component
**File:** `resources/js/Components/[Component].vue`

**Description:**
[What UI this component provides]

**Acceptance Criteria:**
- [ ] Component renders correctly
- [ ] Props match API response
- [ ] Events emitted properly
- [ ] Follows UI standards

**References:**
- UI Specs: `04-ui-specs.md`

---

## Execution Order

| Order | Ticket | Type | Depends On |
|-------|--------|------|------------|
| 1 | Ticket 1 | Migration | None |
| 2 | Ticket 2 | Model | Ticket 1 |
| 3 | Ticket 3 | Controller | Ticket 2 |
| 4 | Ticket 4 | Route | Ticket 3 |
| 5 | Ticket 5 | Component | Tickets 3, 4 |

---

## Executor Commands

```bash
python scripts/executor.py --list        # Preview all tickets
python scripts/executor.py               # Execute all tickets with sub-agents
python scripts/executor.py --ticket 1    # Execute specific ticket
python scripts/executor.py --status      # Check job status
```

---

## Approval Gate

**Status:** [ ] DRAFT  [ ] APPROVED

**All Tickets Atomic:** [ ] YES  [ ] NO

**Backend-Out Sequencing Verified:** [ ] YES  [ ] NO

**Approved By:**

**Date:**
