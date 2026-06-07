"""
Vision — Job Queue (PostgreSQL-backed).

Lightweight job system using PostgreSQL SKIP LOCKED for concurrent workers.
No Redis/RabbitMQ needed — transactional, queryable, and visible via SQL.

Pattern:
    enqueue → worker claims with SKIP LOCKED → process → mark complete/failed
"""

from __future__ import annotations

import json
from typing import Any

import psycopg2.extras

# Support both package imports and direct script execution
try:
    from core.db import connect, tx
except (ImportError, ValueError):
    import sys
    from pathlib import Path
    _backend = Path(__file__).resolve().parents[1]
    if str(_backend) not in sys.path:
        sys.path.insert(0, str(_backend))
    from core.db import connect, tx  # type: ignore


# ---------------------------------------------------------------------------
# Enqueue
# ---------------------------------------------------------------------------

def enqueue(
    case_id: int,
    job_type: str,
    storage_ref: dict | None = None,
    metadata: dict | None = None,
) -> dict:
    """Create a new job. Returns the job record."""
    with tx() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO jobs (case_id, job_type, storage_ref, metadata)
                   VALUES (%s, %s, %s::jsonb, %s::jsonb)
                   RETURNING *""",
                (case_id, job_type,
                 json.dumps(storage_ref) if storage_ref else None,
                 json.dumps(metadata) if metadata else None),
            )
            return dict(cur.fetchone())


# ---------------------------------------------------------------------------
# Worker-side: claim + update
# ---------------------------------------------------------------------------

def claim_next(worker_id: str = "worker-1") -> dict | None:
    """Claim the next queued job using SKIP LOCKED.

    Multiple workers can call this concurrently without conflict.
    Returns None if no jobs are queued.
    """
    with tx() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE jobs SET status = 'processing',
                                   started_at = now(),
                                   attempts = attempts + 1,
                                   updated_at = now()
                   WHERE id = (
                       SELECT id FROM jobs
                       WHERE status = 'queued'
                       ORDER BY created_at
                       FOR UPDATE SKIP LOCKED
                       LIMIT 1
                   )
                   RETURNING *"""
            )
            row = cur.fetchone()
            return dict(row) if row else None


def mark_complete(job_id: int, document_id: int | None = None) -> None:
    """Mark a job as complete."""
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE jobs SET status = 'complete',
                                   progress_pct = 100,
                                   document_id = %s,
                                   completed_at = now(),
                                   updated_at = now()
                   WHERE id = %s""",
                (document_id, job_id),
            )


def mark_failed(job_id: int, error: str) -> None:
    """Mark a job as failed with an error message."""
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE jobs SET status = 'failed',
                                   error_message = %s,
                                   completed_at = now(),
                                   updated_at = now()
                   WHERE id = %s""",
                (error, job_id),
            )


def update_progress(job_id: int, pct: int) -> None:
    """Update the progress percentage of a running job."""
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET progress_pct = %s, updated_at = now() WHERE id = %s",
                (pct, job_id),
            )


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def get_job(job_id: int) -> dict | None:
    """Get a job by ID."""
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def list_jobs(case_id: int | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
    """List jobs, optionally filtered by case or status."""
    conn = connect()
    try:
        clauses = []
        params: list[Any] = []
        if case_id is not None:
            clauses.append("case_id = %s")
            params.append(case_id)
        if status:
            clauses.append("status = %s")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""SELECT * FROM jobs {where}
                    ORDER BY created_at DESC LIMIT %s""",
                tuple(params),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
