# Backend Project Structure

> **Stack:** Python 3.12+, FastAPI, psycopg2 (no ORM).

## 1. Directory Layout (`backend/`)

```
backend/
├── api/
│   ├── main.py          # FastAPI app, startup schema hooks, inline routes
│   │                     # for the oldest domains (cases/parties/allegations)
│   └── routes/           # One file per domain, APIRouter, included in main.py
│       ├── tasks.py
│       ├── chat.py
│       ├── profiles.py
│       ├── correspondence.py
│       ├── calendar.py
│       ├── drafts.py
│       ├── vault.py
│       └── workspace.py
├── auth/                 # JWT + bcrypt auth, get_current_user dependency
├── core/
│   ├── db.py             # Connection primitives + ALL CRUD functions
│   └── case.py            # CaseManager — case/party/allegation business logic
├── ingestion/             # Upload → OCR → normalize → embed pipeline
│   ├── dispatcher.py, enricher.py, jobs.py, storage.py, synthesizer.py, worker.py
├── chat/                  # Agent chat: manager, tools, prompt, streaming
├── search/                # Embedding + retrieval (embed.py)
├── strategy/              # Strategy engine (doctrine trees, gauntlet) — sparse so far
├── schemas/               # Numbered .sql migration files + view_envelope validator
├── scripts/                # One-off ingestion/pipeline CLI entry points
└── tests/                  # pytest + a couple of standalone smoke-test scripts
```

## 2. Layering — Where New Code Goes

1. **Route handler (`api/routes/<domain>.py`)** — HTTP concerns only: parse
   request body (Pydantic model), call into `core/db.py` (or a manager class
   for a rich domain), map results/errors to HTTP responses. No SQL here.
2. **Data access (`core/db.py`)** — all SQL lives here as plain functions
   (see `02-BACKEND-STANDARDS/database-design.md` §8 for the CRUD naming
   convention). No FastAPI imports here — this module must be importable
   from CLI scripts and workers without pulling in the web framework.
3. **Manager classes (`core/case.py`-style)** — used when a domain has
   several related entities and non-trivial cross-entity logic (e.g.
   `CaseManager` covers cases + parties + allegations). Optional — most
   domains (tasks, profiles, correspondence) skip this layer and call
   `core/db.py` functions directly from the route file. Add a manager class
   only when a route file would otherwise duplicate multi-step logic across
   handlers.
4. **No repository pattern, no service-layer interfaces, no dependency
   injection framework.** This is a small, single-team codebase — the two
   layers above (routes → db functions, with optional manager classes) are
   sufficient. Don't introduce abstraction the codebase doesn't need yet.

## 3. Adding a New Domain (e.g. `partners`)

Follow the `tasks.py` / `correspondence.py` pattern exactly:
1. Schema: new numbered file `backend/schemas/00N_partners.sql` (see
   `database-design.md` §5) + `ensure_partners_schema()` in `core/db.py`,
   called from `api/main.py`'s `_apply_schemas()`.
2. CRUD functions in `core/db.py`: `insert_partner`, `get_partner`,
   `list_partners`, `update_partner`, `delete_partner` — add to `__all__`.
3. Route file `api/routes/partners.py`: `APIRouter(prefix="/api",
   tags=["partners"])`, Pydantic request models (`CreatePartnerRequest`,
   `UpdatePartnerRequest`), one handler per CRUD op, `Depends(get_current_user)`
   on every route.
4. Register the router in `api/main.py`: `app.include_router(partners.router)`.
5. Frontend client functions + TypeScript interfaces in `frontend/src/lib/api.ts`
   (see `01-FRONTEND-STANDARDS/component-patterns.md` §11).

## 4. Naming Conventions

- **Modules/files:** snake_case (`profiles.py`, `view_envelope.py`).
- **Classes:** PascalCase, noun (`CaseManager`, `ChatManager`).
- **Functions:** snake_case, verb-first (`create_task`, `list_partners`).
- **Route handler functions:** `<verb>_<entity>[_endpoint]` —
  `list_tasks_endpoint`, `create_task_endpoint` — suffixed with `_endpoint`
  only when the plain name collides with an imported `core.db` function of
  the same name (compare `tasks.py`'s `list_tasks_endpoint` vs. the
  imported `list_tasks as _list_tasks` pattern). If no collision, omit the
  suffix (see `profiles.py`'s `list_profiles`).
- **Private/internal DB imports in route files:** alias with a leading
  underscore to avoid shadowing the endpoint function name:
  `from core.db import get_task as _get_task`.
- **Pydantic request models:** `<Verb><Entity>Request` —
  `CreateTaskRequest`, `UpdateTaskRequest`, `AttachDocumentsRequest`.

## 5. Route File Skeleton

```python
"""
Vision — <Domain> API Routes.

<One-line description.>
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from core.db import (
    connect, tx,
    list_x as _list_x,
    get_x as _get_x,
    insert_x,
    update_x as _update_x,
    delete_x as _delete_x,
)

router = APIRouter(prefix="/api", tags=["x"])


class CreateXRequest(BaseModel):
    ...


class UpdateXRequest(BaseModel):
    ...  # every field optional, defaults to None


@router.get("/x")
def list_x_endpoint(user: dict = Depends(get_current_user)):
    conn = connect()
    try:
        return {"items": _list_x(conn)}
    finally:
        conn.close()


@router.post("/x")
def create_x_endpoint(body: CreateXRequest, user: dict = Depends(get_current_user)):
    with tx() as conn:
        item_id = insert_x(conn, **body.model_dump())
        item = _get_x(conn, item_id)
    return {"item": item}


@router.patch("/x/{x_id}")
def update_x_endpoint(x_id: int, body: UpdateXRequest, user: dict = Depends(get_current_user)):
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    with tx() as conn:
        updated = _update_x(conn, x_id, **kwargs)
    if not updated:
        raise HTTPException(status_code=404, detail="X not found")
    return {"item": updated}


@router.delete("/x/{x_id}")
def delete_x_endpoint(x_id: int, user: dict = Depends(get_current_user)):
    with tx() as conn:
        ok = _delete_x(conn, x_id)
    if not ok:
        raise HTTPException(status_code=404, detail="X not found")
    return {"deleted": True}
```

**Rules:**
- **Reads** (`list`/`get`) use `connect()` + `try/finally: conn.close()`.
- **Writes** (`insert`/`update`/`delete`) use `with tx() as conn:` — commits
  on success, rolls back on exception, always closes.
- **Every route** takes `user: dict = Depends(get_current_user)` unless it's
  `auth/*` (register/login) — no unauthenticated endpoints otherwise.
- **404 vs 400:** entity not found → 404; empty/invalid update payload → 400.
- **Response envelope:** wrap the single/list resource in a named key
  (`{"task": ...}`, `{"tasks": [...]}`, `{"deleted": true}`) — never return
  a bare list or bare object at the top level (matches every existing route
  file).

## 6. Streaming / Long-Running Work

- **SSE streaming** (agent chat): `StreamingResponse` yielding `data: {json}\n\n`
  chunks — see `chat.py` + `frontend/src/lib/api.ts`'s `streamChatMessage`.
- **Background/async work** (document ingestion, synthesis): the Postgres-
  backed job queue in `ingestion/jobs.py` (`enqueue` / `claim_next` /
  `mark_complete` / `mark_failed`, using `FOR UPDATE SKIP LOCKED`). Do not
  introduce Celery/Redis/RabbitMQ — this pattern is the standard for any new
  async job type (e.g. future outreach email sending, SAM.gov polling).
- **Frontend polls** `getJob(id)` on an interval until `status` is
  `complete`/`failed` (see `TaskListModal.tsx`'s `handleUploadAndAttach` for
  the reference polling loop, and `01-FRONTEND-STANDARDS/component-patterns.md`
  §5 for the loading-state conventions around it).
