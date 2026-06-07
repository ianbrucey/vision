"""
Vision — PostgresSessionStore.

Implements the claude_agent_sdk SessionStore protocol backed by PostgreSQL.
Replaces the default JSONL filesystem storage so sessions survive backend
restarts, work across multiple hosts, and are queryable via SQL.

Multi-tenancy: project_key isolates cases from each other.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("vision.chat.session_store")


class PostgresSessionStore:
    """SessionStore backed by the session_store_entries table.

    Implements the claude_agent_sdk.SessionStore protocol:
      - append(key, entries)  → INSERT rows
      - load(key)             → SELECT rows in order, return list or None
      - list_sessions(key)    → SELECT DISTINCT session_id with mtime
      - delete(key)           → DELETE rows for session

    The SDK calls these methods during query(), resume(), listSessions(),
    and deleteSession(). Entries are treated as opaque JSON — we store
    them as jsonb and return them in insertion order.
    """

    def __init__(self, conn_factory):
        """conn_factory: callable returning a psycopg2 connection.

        Example:
            store = PostgresSessionStore(lambda: psycopg2.connect(...))
        """
        self._conn_factory = conn_factory

    # ------------------------------------------------------------------
    # Required by SessionStore protocol
    # ------------------------------------------------------------------

    async def append(self, key: dict, entries: list[dict]) -> None:
        """Persist transcript entries for a session.

        Called by the SDK after each batch of local writes.
        key has: project_key, session_id, subpath (optional).
        """
        conn = self._conn_factory()
        try:
            with conn.cursor() as cur:
                for entry in entries:
                    cur.execute(
                        """INSERT INTO session_store_entries
                           (project_key, session_id, subpath, entry)
                           VALUES (%s, %s, %s, %s::jsonb)""",
                        (
                            key.get("project_key", ""),
                            key.get("session_id", ""),
                            key.get("subpath"),
                            json.dumps(entry),
                        ),
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("PostgresSessionStore.append failed — continuing (best-effort mirror)")
        finally:
            conn.close()

    async def load(self, key: dict) -> list[dict] | None:
        """Load transcript entries for a session. Returns None if not found.

        Called by the SDK before spawning the subprocess when resume is set.
        Entries must be returned in insertion order.
        """
        conn = self._conn_factory()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT entry FROM session_store_entries
                       WHERE project_key = %s
                         AND session_id = %s
                         AND subpath IS NOT DISTINCT FROM %s
                       ORDER BY id""",
                    (
                        key.get("project_key", ""),
                        key.get("session_id", ""),
                        key.get("subpath"),
                    ),
                )
                rows = cur.fetchall()
                if not rows:
                    return None
                return [row[0] for row in rows]
        except Exception:
            logger.exception("PostgresSessionStore.load failed")
            return None
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Optional — enables listSessions() and deleteSession()
    # ------------------------------------------------------------------

    async def list_sessions(
        self, project_key: str
    ) -> list[dict]:
        """Return list of {session_id, mtime} for a project.

        Called by listSessions() and continue: true logic.
        """
        conn = self._conn_factory()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT session_id,
                              EXTRACT(EPOCH FROM max(created_at))::bigint AS mtime
                       FROM session_store_entries
                       WHERE project_key = %s
                         AND subpath IS NULL
                       GROUP BY session_id
                       ORDER BY mtime DESC""",
                    (project_key,),
                )
                return [
                    {"session_id": row[0], "mtime": int(row[1])}
                    for row in cur.fetchall()
                ]
        except Exception:
            logger.exception("PostgresSessionStore.list_sessions failed")
            return []
        finally:
            conn.close()

    async def delete(self, key: dict) -> None:
        """Delete all entries for a session (cascades subpaths)."""
        conn = self._conn_factory()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """DELETE FROM session_store_entries
                       WHERE project_key = %s
                         AND session_id = %s""",
                    (key.get("project_key", ""), key.get("session_id", "")),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("PostgresSessionStore.delete failed")
        finally:
            conn.close()

    async def list_subkeys(self, key: dict) -> list[str]:
        """Return subpaths for a session (subagent transcripts)."""
        conn = self._conn_factory()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT DISTINCT subpath
                       FROM session_store_entries
                       WHERE project_key = %s
                         AND session_id = %s
                         AND subpath IS NOT NULL""",
                    (key.get("project_key", ""), key.get("session_id", "")),
                )
                return [row[0] for row in cur.fetchall()]
        except Exception:
            logger.exception("PostgresSessionStore.list_subkeys failed")
            return []
        finally:
            conn.close()
