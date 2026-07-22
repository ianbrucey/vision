# Database Design Standards

> **Stack:** PostgreSQL 15+, `pgvector`, `pg_trgm`. No ORM — raw SQL via
> `psycopg2`. Schema files live in `backend/schemas/*.sql`. Access layer
> lives in `backend/core/db.py`.

## 1. Schemas

- `vision` — application tables (default `search_path`).
- `agent_work` — scratch space the agent can write to freely. Never put
  durable application data here.

## 2. Naming Conventions

- **Tables:** plural, snake_case (`cases`, `tasks`, `task_documents`).
- **Junction/many-to-many tables:** `<a>_<b>` (e.g. `task_documents`,
  `vault_documents`), composite `PRIMARY KEY (a_id, b_id)`, no surrogate id.
- **Columns:** snake_case. `id` is always `SERIAL PRIMARY KEY` unless the row
  needs a public-facing opaque reference, in which case add
  `external_id UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL` alongside it
  (see `cases`).
- **Foreign keys:** `<singular_table>_id` (`case_id`, `document_id`).
- **Indexes:** `idx_<table>_<column(s)>`.
- **Constraints:** named explicitly when they'll need `DROP CONSTRAINT IF
  EXISTS` later (see §5) — e.g. `jobs_job_type_check`, `fk_cases_owner`.

## 3. Standard Columns

Every table gets:
```sql
created_at TIMESTAMPTZ DEFAULT now(),
updated_at TIMESTAMPTZ DEFAULT now()
```
`updated_at` is set explicitly (`updated_at = now()`) in every `UPDATE` —
there is no trigger doing this automatically. If you add a table, add the
`SET updated_at = now()` line to its corresponding `update_X()` function.

Every table also gets a catch-all extensibility column:
```sql
metadata JSONB DEFAULT '{}'
```
Use `metadata` for anything that doesn't yet deserve a first-class column.
Promote fields out of `metadata` into real columns once they're queried
directly or need a `CHECK`/index.

## 4. Enums

We do **not** use native Postgres `ENUM` types (they're painful to alter).
Use `TEXT` + `CHECK (col IN (...))` instead:
```sql
status TEXT NOT NULL DEFAULT 'open'
       CHECK (status IN ('open', 'in_progress', 'blocked', 'complete')),
```

## 5. Migrations

Schema lives in numbered files under `backend/schemas/`: `001_core.sql`,
`002_strategy.sql`, `003_chat.sql`, `004_correspondence.sql`, `005_journal.sql`,
`006_*.sql`. Each is applied by a matching `ensure_X_schema()` function in
`core/db.py`, called from `api/main.py`'s startup event. **Files are
idempotent** — safe to re-run on every boot.

Rules:
1. **New table →** `CREATE TABLE IF NOT EXISTS`.
2. **New column on an existing table →** `ALTER TABLE x ADD COLUMN IF NOT
   EXISTS`.
3. **New/changed CHECK constraint →** `ALTER TABLE x DROP CONSTRAINT IF
   EXISTS x_col_check;` then `ADD CONSTRAINT x_col_check CHECK (...)`.
4. **New FK on an existing table (PG14-safe, no `ADD CONSTRAINT IF NOT
   EXISTS`)** — guard with a `pg_constraint` lookup:
   ```sql
   DO $$
   BEGIN
       IF NOT EXISTS (
           SELECT 1 FROM pg_constraint
           WHERE conname = 'fk_x_y' AND conrelid = 'x'::regclass
       ) THEN
           ALTER TABLE x ADD CONSTRAINT fk_x_y
               FOREIGN KEY (y_id) REFERENCES y(id) ON DELETE SET NULL;
       END IF;
   END $$;
   ```
5. **Record every migration** at the bottom of the file:
   ```sql
   INSERT INTO schema_migrations (version, name) VALUES (N, 'description')
   ON CONFLICT (version) DO NOTHING;
   ```
   Version numbers increment across the whole `001_core.sql` file — check
   the last one before adding a new block.
6. **Prefer additive migrations.** Never `DROP COLUMN`/`DROP TABLE` in a
   shared schema file without an explicit user decision — this is a Council
   (State 2) decision, not something the Builder decides mid-ticket.
7. **New domain that's big enough for its own concerns** (e.g. `partners`,
   outreach queue) → new numbered file (`007_partners.sql`), its own
   `ensure_partners_schema()`, wired into `api/main.py` startup — same
   pattern as `004_correspondence.sql`.

## 6. Relationships & Deletes

- **Owned child rows** (deleted when parent is deleted): `ON DELETE CASCADE`.
  Example: `parties`, `documents`, `tasks` all cascade from `cases`.
- **Optional references** (parent deletion shouldn't destroy history):
  `ON DELETE SET NULL`. Example: `events.actor_id → parties(id)`.
- **Referential integrity for append-only audit data:** `ON DELETE RESTRICT`
  (see `citations.block_id`) — don't let a block deletion silently orphan
  citation history.

## 7. Indexing

- Every FK column gets a plain B-tree index: `idx_<table>_<fk_column>`.
- Composite indexes for common filtered lookups: `idx_tasks_status ON tasks
  (case_id, status)`.
- Array columns (`TEXT[]`, `INTEGER[]`): GIN index — `idx_parties_roles ON
  parties USING GIN (roles)`.
- Fuzzy/autocomplete text: `pg_trgm` GIN index — `idx_sections_title_trgm`.
- Full-text search: generated `TSVECTOR` column + GIN index (see
  `blocks.text_tsv`, `sections.title_tsv`).
- Vector similarity: `ivfflat` index with `vector_cosine_ops` (see
  `sections.embedding`, `blocks.embedding`). Embedding dimension is fixed at
  1024 (Mistral embed) — don't introduce a second dimension without updating
  `search/embed.py`.

## 8. Data Access Layer (`core/db.py`)

No ORM. Two connection primitives:
- `connect()` — plain connection, caller must `conn.close()` in a `finally`.
  Use for reads.
- `tx()` — context manager: commits on clean exit, rolls back on exception,
  always closes. Use for every write.

CRUD function naming, one function per table (or logical entity):
- `insert_X(conn, ...) -> int` — returns the new row id.
- `get_X(conn, id) -> dict | None` — `RealDictCursor`, `None` if not found.
- `list_X(conn, ..., limit=N) -> list[dict]`.
- `update_X(conn, id, field=None, ...) -> dict | None` — every field
  defaults to `None`; build the `SET` clause only from non-`None` args;
  return `None` if nothing was provided; always append `updated_at = now()`;
  `RETURNING *`.
- `delete_X(conn, id) -> bool` — `cur.rowcount > 0`.

JSON columns: pass Python `dict`/`list`, serialize with the local `_j()`
helper (`json.dumps(d) if d else "{}"`), cast in SQL with `%s::jsonb`.

Add new functions to the `__all__` list at the bottom of `core/db.py`.
