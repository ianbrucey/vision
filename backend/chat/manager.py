"""
Vision — ChatManager.

Manages the lifecycle of Agent SDK sessions for the chat interface.
One ChatManager per backend process. Creates and tracks ClaudeSDKClient
instances, bridges streaming responses to SSE events, and handles
session persistence via PostgresSessionStore.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import AsyncIterator

import psycopg2.extras

from chat.prompt import WAR_ROOM_SYSTEM_PROMPT
from chat.session_store import PostgresSessionStore
from core.db import connect, ensure_chat_schema

logger = logging.getLogger("vision.chat.manager")

# Temporary directory for SDK working files. The SDK writes local JSONL here
# (ephemeral) and mirrors to PostgresSessionStore (durable).
_TMP_ROOT = Path(os.environ.get("VISION_SDK_TMP", "/tmp/vision/sdk"))

# Agent CLI tool path — tells the agent how to invoke database operations
_VISION_CLI_PATH = (
    Path(__file__).resolve().parents[2] / "chat" / "cli.py"
)


class ChatManager:
    """Manages Agent SDK client instances and SSE streaming."""

    def __init__(self):
        _TMP_ROOT.mkdir(parents=True, exist_ok=True)
        ensure_chat_schema()  # apply 003_chat.sql if not already applied

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def _conn_factory(self):
        return connect()

    async def create_session(self, case_id: int, system_prompt: str | None = None) -> dict:
        """Create a new chat session for a case."""
        prompt = system_prompt or WAR_ROOM_SYSTEM_PROMPT
        project_key = f"case_{case_id}"
        sdk_workdir = _TMP_ROOT / project_key
        sdk_workdir.mkdir(parents=True, exist_ok=True)

        conn = self._conn_factory()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO chat_sessions (case_id, project_key, system_prompt, status)
                       VALUES (%s, %s, %s, 'active')
                       RETURNING id""",
                    (case_id, project_key, prompt),
                )
                session_id = cur.fetchone()["id"]
            conn.commit()
        finally:
            conn.close()

        return {
            "session_id": session_id,
            "case_id": case_id,
            "project_key": project_key,
            "system_prompt": prompt,
        }

    async def get_session(self, session_id: int) -> dict | None:
        """Get session metadata by ID."""
        conn = self._conn_factory()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM chat_sessions WHERE id = %s",
                    (session_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    async def list_sessions(self, case_id: int) -> list[dict]:
        """List active sessions for a case."""
        conn = self._conn_factory()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT id, case_id, sdk_session_id, title, status,
                              context_summary, created_at, updated_at
                       FROM chat_sessions
                       WHERE case_id = %s AND status = 'active'
                       ORDER BY updated_at DESC""",
                    (case_id,),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    async def archive_session(self, session_id: int) -> bool:
        """Archive a session."""
        conn = self._conn_factory()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE chat_sessions SET status = 'archived', updated_at = now() WHERE id = %s",
                    (session_id,),
                )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Message history
    # ------------------------------------------------------------------

    async def get_messages(self, session_id: int) -> list[dict]:
        """Get all messages for a session, ordered by sequence."""
        conn = self._conn_factory()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT id, role, content, tool_name, tool_inputs,
                              tool_result, citations, sequence, created_at
                       FROM chat_messages
                       WHERE session_id = %s
                       ORDER BY sequence""",
                    (session_id,),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    async def _save_message(
        self, session_id: int, role: str, content: str,
        tool_name: str | None = None, tool_inputs: dict | None = None,
        tool_result: dict | None = None, citations: list | None = None,
    ) -> int:
        """Save a message to the database. Fire-and-forget safe."""
        conn = self._conn_factory()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COALESCE(MAX(sequence), 0) + 1 FROM chat_messages WHERE session_id = %s",
                    (session_id,),
                )
                seq = cur.fetchone()[0]

                cur.execute(
                    """INSERT INTO chat_messages
                       (session_id, role, content, tool_name, tool_inputs,
                        tool_result, citations, sequence)
                       VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                       RETURNING id""",
                    (
                        session_id, role, content,
                        tool_name,
                        json.dumps(tool_inputs) if tool_inputs else None,
                        json.dumps(tool_result) if tool_result else None,
                        json.dumps(citations) if citations else None,
                        seq,
                    ),
                )
                conn.commit()
                return cur.fetchone()[0]
        finally:
            conn.close()

    async def _update_sdk_session_id(self, session_id: int, sdk_id: str):
        """Store the SDK session ID for later resumption."""
        conn = self._conn_factory()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE chat_sessions SET sdk_session_id = %s, updated_at = now() WHERE id = %s",
                    (sdk_id, session_id),
                )
            conn.commit()
        finally:
            conn.close()

    async def _auto_title(self, session_id: int):
        """Set session title from the first user message."""
        conn = self._conn_factory()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE chat_sessions
                       SET title = (
                           SELECT left(content, 80) FROM chat_messages
                           WHERE session_id = %s AND role = 'user'
                           ORDER BY sequence LIMIT 1
                       ), updated_at = now()
                       WHERE id = %s AND title IS NULL""",
                    (session_id, session_id),
                )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def stream_message(
        self, session_id: int, user_message: str
    ) -> AsyncIterator[str]:
        """Send a user message and stream the agent response as SSE events.

        Yields SSE-formatted strings:
            data: {"type":"assistant","content":"..."}
            data: {"type":"tool_call","name":"...","inputs":{...}}
            data: {"type":"tool_result","name":"...","result":{...}}
            data: {"type":"done","session_id":"...","cost":0.01}
            data: {"type":"error","message":"..."}
        """
        session = await self.get_session(session_id)
        if not session:
            yield _sse("error", {"message": f"Session {session_id} not found"})
            return

        # Save the user message
        await self._save_message(session_id, "user", user_message)

        # Build the prompt with CLI tool instructions and case context
        full_prompt = _build_prompt(user_message, session, _VISION_CLI_PATH)

        # Session store for durability — mirrors SDK writes to PostgreSQL
        store = PostgresSessionStore(lambda: connect())

        try:
            from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
        except ImportError:
            yield _sse("error", {
                "message": "claude-agent-sdk not installed. Run: pip install claude-agent-sdk"
            })
            return

        options = ClaudeAgentOptions(
            system_prompt=session["system_prompt"] or WAR_ROOM_SYSTEM_PROMPT,
            allowed_tools=["Bash", "Read", "Glob", "Grep", "Write", "Edit"],
            session_store=store,
            setting_sources=["project"],
        )

        sdk_session_id: str | None = session.get("sdk_session_id")

        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(full_prompt)

                async for sdk_msg in client.receive_response():
                    # Extract session ID from init messages
                    msg_type = getattr(sdk_msg, "type", "")

                    if msg_type == "system":
                        subtype = getattr(sdk_msg, "subtype", "")
                        if subtype == "init":
                            data = getattr(sdk_msg, "data", {}) or {}
                            if isinstance(data, dict):
                                sdk_session_id = data.get("session_id", sdk_session_id)
                            yield _sse("init", {"session_id": sdk_session_id})
                        else:
                            yield _sse("status", {"subtype": subtype})
                        continue

                    # Assistant message — may contain text + tool_use blocks
                    if msg_type == "assistant":
                        blocks = getattr(sdk_msg, "content", []) or []
                        for block in blocks:
                            bt = getattr(block, "type", "")
                            if bt == "text":
                                text = getattr(block, "text", "")
                                if text:
                                    await self._save_message(session_id, "assistant", text)
                                    yield _sse("assistant", {"content": text})
                            elif bt == "tool_use":
                                name = getattr(block, "name", "")
                                inp = getattr(block, "input", {})
                                await self._save_message(
                                    session_id, "tool_call", "",
                                    tool_name=name, tool_inputs=inp if isinstance(inp, dict) else {},
                                )
                                yield _sse("tool_call", {"name": name, "inputs": inp})
                        continue

                    # Tool results
                    if msg_type == "user":
                        blocks = getattr(sdk_msg, "content", []) or []
                        for block in blocks:
                            bt = getattr(block, "type", "")
                            if bt == "tool_result":
                                tid = getattr(block, "tool_use_id", "")
                                content = getattr(block, "content", "")
                                content_str = str(content)[:1000] if content else ""
                                await self._save_message(
                                    session_id, "tool_result", content_str,
                                    tool_result={"tool_use_id": tid, "summary": content_str},
                                )
                                yield _sse("tool_result", {
                                    "tool_use_id": tid,
                                    "content": content_str,
                                })
                        continue

                    # Final result
                    if msg_type == "result":
                        subtype = getattr(sdk_msg, "subtype", "")
                        cost = getattr(sdk_msg, "total_cost_usd", None)
                        yield _sse("done", {
                            "subtype": subtype,
                            "session_id": sdk_session_id,
                            "cost": cost,
                        })
                        continue

                # Persist SDK session ID for resumption
                if sdk_session_id:
                    await self._update_sdk_session_id(session_id, sdk_session_id)
                    await self._auto_title(session_id)

        except Exception as exc:
            logger.exception("Agent SDK streaming failed")
            yield _sse("error", {"message": str(exc)})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_prompt(user_message: str, session: dict, cli_path: Path) -> str:
    """Build the full prompt with CLI tool instructions and case context."""
    return f"""[Case ID: {session['case_id']}]

Database exploration tools (use Bash to run these):
  python3 {cli_path} list-cases [--status active] [--limit N]
  python3 {cli_path} get-case --case-id {session['case_id']}
  python3 {cli_path} search-blocks --case-id {session['case_id']} --query "text" [--document-id N] [--limit N]
  python3 {cli_path} get-document-structure --document-id N
  python3 {cli_path} get-block-context --block-id N [--window 3]
  python3 {cli_path} get-strategies --case-id {session['case_id']}
  python3 {cli_path} get-strategy-tree --strategy-id N

You are working on Case ID {session['case_id']}. Use the tools above to explore
the case before answering. All commands return JSON to stdout. If you need to
search the evidence store, use search-blocks. If you need case context, use
get-case. Always cite your sources when presenting findings.

{user_message}"""


def _sse(event_type: str, data: dict) -> str:
    """Format a dict as an SSE event string."""
    payload = json.dumps({"type": event_type, **data}, default=str)
    return f"data: {payload}\n\n"
