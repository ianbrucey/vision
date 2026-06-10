# Task Tracker — Design

> **Status:** Planned
> **Date:** 2026-06-09

---

## Model

```
tasks
├── id
├── case_id          → cases(id)
├── title            TEXT NOT NULL
├── notes            TEXT
├── status           CHECK (open, in_progress, blocked, complete)
├── priority         CHECK (low, medium, high, urgent) DEFAULT medium
├── assignee_id      → users(id) NULLABLE (NULL = unassigned)
├── deadline         DATE NULLABLE
├── completed_at     TIMESTAMPTZ NULLABLE
├── created_by       → users(id)
├── created_at
├── updated_at

task_documents
├── task_id          → tasks(id) ON DELETE CASCADE
├── document_id      → documents(id) ON DELETE CASCADE
├── attached_at
├── PRIMARY KEY (task_id, document_id)
```

**Why not a generic "attachments" table?** Because the only attachment type is documents — and they must be from the case's document bucket. A junction table enforces referential integrity. New documents uploaded via the task get ingested normally and appear in the case's document list too.

**Why assignee over "doer"?** "Assignee" is standard task terminology. Defaults to the user creating the task. NULL means unassigned — someone has to claim it.

---

## API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/cases/{id}/tasks` | List tasks for case. Query params: `status`, `assignee_id`, `sort` |
| `POST` | `/api/cases/{id}/tasks` | Create task. Body: title, notes, assignee_id, deadline, document_ids[] |
| `GET` | `/api/tasks/{id}` | Single task with documents |
| `PATCH` | `/api/tasks/{id}` | Update fields including status |
| `POST` | `/api/tasks/{id}/documents` | Attach documents. Body: `{ document_ids: [] }` |
| `DELETE` | `/api/tasks/{id}/documents/{doc_id}` | Detach a document |
| `DELETE` | `/api/tasks/{id}` | Delete task |

No `POST /api/tasks/{id}/upload` — the existing `POST /api/cases/{id}/ingest` handles file upload + ingestion. The frontend calls ingest, gets the `job_id`, polls for the `document_id`, then attaches it via `POST /api/tasks/{id}/documents`.

---

## Agent Tools

Two tools added to `create_vision_server()`:

**`list_tasks`** — List tasks with filters. Agent can check what's pending.
**`create_task`** — Create a task. Agent can assign follow-ups after analysis.
**`update_task`** — Update task status/notes. Agent can close tasks.

All closure-scoped to case_id. The agent never sees other cases' tasks.

---

## Frontend

### Overview Card (compact)

```
┌─────────────────────────────────────────────┐
│  Tasks                           [View all →]│
│                                             │
│  ● Draft response to RFP                    │
│    Due Jun 12 · Ian Bruce                   │
│                                             │
│  ○ Review medical records for A02           │
│    No deadline · Unassigned                 │
│                                             │
│  ● Follow up on missing lab results         │
│    Overdue · Ian Bruce                      │
│                                             │
│  + 3 more tasks                             │
└─────────────────────────────────────────────┘
```

Shows up to 3 most urgent tasks (overdue first, then nearest deadline). "View all" opens the task list modal. If 0 tasks, card shows "No tasks yet" with a create prompt.

### Task List Modal / Page

Opens from the Overview card. Full-screen on mobile, large modal on desktop.

```
┌──────────────────────────────────────────────────────┐
│  Tasks                                    [+ New]    │
│                                                      │
│  Filter: [All ▾] [All priorities ▾] [All assignees ▾]│
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │ ● Draft RFP response              Due Jun 12   │  │
│  │   Ian Bruce · 2 docs attached                  │  │
│  │                                                │  │
│  │ ○ Review medical records          No deadline  │  │
│  │   Unassigned                                    │  │
│  │  ...                                           │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### Task Detail (inline expansion or side panel)

Click a task → expands to show notes, document attachments, status controls.

Document attachment area:
- "Attach document" button → opens document picker (search existing) OR upload button
- Upload → uses existing ingest flow, polls for completion, attaches resulting doc
- Each attached doc shows name + page count, clickable to preview

Status control: dropdown or button group — Open / In Progress / Blocked / Complete

---

## Implementation Sequence

| Ticket | What | Time |
|--------|------|------|
| T1 | Schema — `tasks` + `task_documents` tables, migration v5 | 10 min |
| T2 | DB helpers — `insert_task`, `update_task`, `list_tasks`, etc. | 15 min |
| T3 | API — CRUD endpoints for tasks + document attachment | 25 min |
| T4 | Agent tools — `list_tasks`, `create_task`, `update_task` | 15 min |
| T5 | Frontend API client — task types + functions | 10 min |
| T6 | TaskListModal component — list + filters + task detail panel | 45 min |
| T7 | Overview card — compact task summary, wires to modal | 20 min |
| T8 | Prompt update — add TASKS section | 5 min |

**Estimated: ~2.5 hours**

---

## Open Questions

1. **Does the agent auto-create tasks from synthesis?** E.g., after extracting allegations, create follow-up tasks. Defer until protocols are built.
2. **Task notifications?** Browser push or email when a deadline approaches. Defer.
3. **Task comments/activity log?** Could add a `task_events` table for status changes. Defer — notes field covers 80% of use case.
