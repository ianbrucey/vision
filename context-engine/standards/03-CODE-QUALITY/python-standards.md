# Python Coding Standards

> **Stack:** Python 3.12+ (see `__pycache__/*.cpython-313*` — running on 3.13
> in practice; 3.12+ is the floor). FastAPI + psycopg2, no ORM.

## 1. Style

- **Module header:** every module-level file starts with a triple-quoted
  docstring: `"""\nVision — <Module Name>.\n\n<1-3 sentence description.>\n"""`
  (see `core/case.py`, `auth/__init__.py`, `ingestion/jobs.py`).
- **`from __future__ import annotations`** as the first import in every
  module — enables modern `X | None` syntax on all supported versions.
- **Type hints on every function signature** — parameters and return type.
  Use `dict`, `list`, `X | None` (PEP 604), not `Optional[X]`/`Dict[str, Any]`
  from `typing` unless the shape genuinely needs `typing.Any`.
- **Section dividers** for readability in larger files — a comment banner:
  ```python
  # ---------------------------------------------------------------------------
  # Section Name
  # ---------------------------------------------------------------------------
  ```
  Used consistently in `db.py`, `main.py`, route files to separate CRUD
  groups / route groups.
- **Docstrings on public functions**, one-line summary minimum; multi-line
  with `Usage:` example for anything non-obvious (see `jobs.py`, `db.py`).
- **f-strings** for interpolation. **Never** build SQL with f-strings —
  always parameterized queries (`%s` placeholders via psycopg2).

## 2. Static Analysis & Linting

**Currently no linter or type checker is configured** (no `pyproject.toml`,
`ruff.toml`, `mypy.ini`, or `.flake8` exist in the repo as of this writing).
This is a gap, not a decision — if/when it's addressed, this section should
be updated to name the actual tool and config. Until then: match the
existing style in the file you're editing (type hints, docstrings, section
banners as above) rather than introducing a new personal style.

## 3. Error Handling

- **Route handlers raise `HTTPException`** directly — no custom exception
  hierarchy. `status_code` + `detail` string:
  ```python
  raise HTTPException(status_code=404, detail="Task not found")
  ```
- **404** for "entity not found by id". **400** for "bad/empty request
  payload" (e.g. an update with no fields set, an attach with an empty id
  list). **409** for uniqueness conflicts (see `create_user`'s
  `UniqueViolation` handling).
- **Known DB errors are caught and translated** at the point they occur
  (e.g. `except psycopg2.errors.UniqueViolation:` inside `create_user`) —
  don't let raw psycopg2 exceptions bubble to the client.
- **Silent failure is acceptable only for non-critical background paths**
  (e.g. `useReminderPolling`'s network errors are swallowed client-side
  because the next poll retries) — never swallow errors in a write path or
  a route handler.

## 4. Database Access Rules

See `02-BACKEND-STANDARDS/database-design.md` §8 for the full CRUD
convention. Key rules that are about *code quality*, not schema:
- **Always use `RealDictCursor`** for reads that return to the API layer —
  `psycopg2.extras.RealDictCursor` — so rows come back as `dict`, not tuples.
- **Always parameterize** — `cur.execute("... WHERE id = %s", (id,))`, never
  string-format a value into SQL.
- **Close every connection.** `connect()` calls need `try/finally:
  conn.close()`. `tx()` handles this automatically — prefer `tx()` for any
  write.
- **JSON columns:** serialize with `json.dumps(d) if d else "{}"` (or the
  local `_j()` helper where one exists) and cast with `%s::jsonb` in the
  query — see `jobs.py`'s `enqueue`.

## 5. Security

- **Passwords:** bcrypt via `bcrypt.hashpw`/`bcrypt.checkpw` — never store
  or log plaintext.
- **JWT:** `PyJWT`, `HS256`, secret from `VISION_JWT_SECRET` env var (dev
  fallback exists in `auth/__init__.py` — **must** be overridden via env in
  any non-local deployment).
- **Auth dependency on every protected route:** `user: dict =
  Depends(get_current_user)` — see `02-BACKEND-STANDARDS/laravel-structure.md`
  §5 for the route skeleton. Only `/api/auth/register` and `/api/auth/login`
  are unauthenticated.
- **CORS is currently `allow_origins=["*"]`** in `api/main.py` — flagged
  in-code as "tightened in production." Do not widen further; narrow this
  when deployment topology is decided.
- **Secrets via `.env`**, loaded by `core/db._load_dotenv()` — never commit
  `.env`, never hardcode credentials in source.

## 6. Performance

- **N+1 avoidance:** batch-fetch related rows in one query with a `WHERE id
  = ANY(%s)` or a join, rather than looping and querying per-row. (No
  current examples of this failing, but watch for it as `partners`/matching
  queries are added — matching a solicitation against N partners should be
  one query, not N.)
- **Connection reuse within a request:** open one connection per request
  (via `connect()` or `tx()`), pass it through helper functions — don't open
  multiple connections in a single route handler.
- **Vector/FTS queries:** use the existing indexes (`ivfflat`, `GIN` — see
  `database-design.md` §7) rather than filtering in Python after a broad
  `SELECT *`.
