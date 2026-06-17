"""
Vision — ChatManager.

Manages the lifecycle of Agent SDK sessions for the chat interface.
One AgentSession per chat session — kept alive across turns for
conversation continuity. Bridges streaming responses to SSE events.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import AsyncIterator

import psycopg2.extras

from chat.prompt import VISION_SYSTEM_PROMPT
from chat.session_store import PostgresSessionStore
from chat.tools import create_vision_server
from chat.external_tools import create_external_tools_server
from core.db import connect, ensure_chat_schema

logger = logging.getLogger("vision.chat.manager")

_TMP_ROOT = Path(os.environ.get("VISION_SDK_TMP", "/tmp/vision/sdk"))


# ---------------------------------------------------------------------------
# AgentSession — a long-lived ClaudeSDKClient for one chat session
# ---------------------------------------------------------------------------


class AgentSession:
    """Wraps a persistent ClaudeSDKClient for a single chat session.

    Created on first message, stays alive until the chat session is archived.
    Each turn: client.query(user_message) → client.receive_response().
    """

    def __init__(self, session_id: int, case_id: int, system_prompt: str):
        self.session_id = session_id
        self.case_id = case_id
        self.system_prompt = system_prompt
        self._client = None
        self._connected = False

    async def _ensure_connected(self):
        """Connect the SDK client on first use."""
        if self._connected:
            return

        from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

        store = PostgresSessionStore(lambda: connect())
        sdk_workdir = _TMP_ROOT / f"case_{self.case_id}"
        sdk_workdir.mkdir(parents=True, exist_ok=True)

        # Create a per-session vision server — case_id is captured in
        # every tool handler's closure. The agent never sees a case_id.
        vision_server = create_vision_server(self.case_id)

        # External integration tools (research, court listener, legal brain)
        legal_hub = create_external_tools_server()

        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            mcp_servers={"vision": vision_server, "legal_hub": legal_hub},
            allowed_tools=["mcp__vision__*",
                           "mcp__legal_hub__*",
                           "Read", "Grep", "Write", "Edit",
                           "WebSearch", "WebFetch",
                           "Skill", "Agent"],
            skills="all",
            session_store=store,
            setting_sources=["project"],
            cwd=str(sdk_workdir),
            permission_mode="bypassPermissions",
            # DeepSeek uses reasoning_effort natively and rejects Anthropic's
            # thinking type parameter. Explicitly disable SDK thinking config.
            thinking=None,
            max_thinking_tokens=None,
        )

        self._client = ClaudeSDKClient(options=options)
        await self._client.connect()
        self._connected = True

    async def send_message(self, content: str):
        """Send a user message to the agent. Must be connected first."""
        await self._ensure_connected()
        await self._client.query(content)

    async def receive(self) -> AsyncIterator[dict]:
        """Yield SSE-ready event dicts from the agent's response stream.

        Yields until ResultMessage, then returns. Call send_message() again
        for the next turn.
        """
        from claude_agent_sdk.types import (
            AssistantMessage, UserMessage, ResultMessage, StreamEvent,
            TextBlock, ToolUseBlock, ToolResultBlock, ThinkingBlock,
        )

        streamed_text = False

        async for msg in self._client.receive_response():
            # --- StreamEvent: partial text deltas ---
            if isinstance(msg, StreamEvent):
                event = msg.event or {}
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        streamed_text = True
                        yield {"type": "assistant", "content": text}
                continue

            # --- AssistantMessage: final text + tool_use blocks ---
            if isinstance(msg, AssistantMessage):
                for block in (msg.content or []):
                    if isinstance(block, TextBlock):
                        text = block.text or ""
                        if text and not streamed_text:
                            yield {"type": "assistant", "content": text}
                    elif isinstance(block, ToolUseBlock):
                        name = block.name or ""
                        inp = block.input or {}
                        yield {"type": "tool_call", "name": name, "inputs": inp}
                    elif isinstance(block, ThinkingBlock):
                        pass  # internal reasoning — skip
                continue

            # --- UserMessage: tool results ---
            if isinstance(msg, UserMessage):
                blocks = msg.content if isinstance(msg.content, list) else []
                for block in blocks:
                    if isinstance(block, ToolResultBlock):
                        content_str = str(block.content)[:2000] if block.content else ""
                        yield {
                            "type": "tool_result",
                            "tool_use_id": block.tool_use_id or "",
                            "content": content_str,
                        }
                continue

            # --- ResultMessage: end of turn ---
            if isinstance(msg, ResultMessage):
                yield {
                    "type": "done",
                    "subtype": msg.subtype or "",
                    "session_id": getattr(msg, "session_id", None),
                    "cost": msg.total_cost_usd,
                }
                continue

    async def close(self):
        """Disconnect the SDK client."""
        if self._client and self._connected:
            try:
                await self._client.disconnect()
            except Exception:
                pass
        self._connected = False
        self._client = None


# ---------------------------------------------------------------------------
# ChatManager — session lifecycle + SSE streaming
# ---------------------------------------------------------------------------


class ChatManager:
    """Manages AgentSession instances and bridges to SSE events."""

    def __init__(self):
        _TMP_ROOT.mkdir(parents=True, exist_ok=True)
        ensure_chat_schema()
        self._sessions: dict[int, AgentSession] = {}

    def _conn_factory(self):
        return connect()

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    async def create_session(
        self, case_id: int, system_prompt: str | None = None
    ) -> dict:
        """Create a new chat session row. AgentSession is lazily created on first message."""
        prompt = system_prompt or VISION_SYSTEM_PROMPT
        project_key = f"case_{case_id}"

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
        """List active sessions for a case, with message counts."""
        conn = self._conn_factory()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT s.id, s.case_id, s.sdk_session_id, s.title, s.status,
                              s.context_summary, s.created_at, s.updated_at,
                              COALESCE(m.msg_count, 0) AS message_count
                       FROM chat_sessions s
                       LEFT JOIN (
                           SELECT session_id, COUNT(*) AS msg_count
                           FROM chat_messages
                           GROUP BY session_id
                       ) m ON m.session_id = s.id
                       WHERE s.case_id = %s AND s.status = 'active'
                       ORDER BY s.updated_at DESC""",
                    (case_id,),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    async def archive_session(self, session_id: int) -> bool:
        """Archive a session and close its agent."""
        # Close the agent if connected
        agent = self._sessions.pop(session_id, None)
        if agent:
            await agent.close()

        conn = self._conn_factory()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE chat_sessions
                       SET status = 'archived', updated_at = now()
                       WHERE id = %s""",
                    (session_id,),
                )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    async def update_session(
        self, session_id: int, title: str | None = None,
        context_summary: str | None = None,
    ) -> dict | None:
        """Update session metadata fields. Returns updated session or None."""
        updates = []
        params: list = []
        if title is not None:
            updates.append("title = %s")
            params.append(title)
        if context_summary is not None:
            updates.append("context_summary = %s")
            params.append(context_summary)

        if not updates:
            # Nothing to update — return current session
            return await self.get_session(session_id)

        updates.append("updated_at = now()")
        params.append(session_id)

        conn = self._conn_factory()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""UPDATE chat_sessions
                        SET {', '.join(updates)}
                        WHERE id = %s
                        RETURNING *""",
                    params,
                )
                row = cur.fetchone()
                if row:
                    conn.commit()
                    return dict(row)
                return None
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Message persistence
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
    ) -> tuple[int, int]:
        """Persist a message to the database. Returns (id, sequence)."""
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
                    (session_id, role, content,
                     tool_name,
                     json.dumps(tool_inputs) if tool_inputs else None,
                     json.dumps(tool_result) if tool_result else None,
                     json.dumps(citations) if citations else None,
                     seq),
                )
                msg_id = cur.fetchone()[0]
            conn.commit()
            return msg_id, seq
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
    # Streaming — the main event
    # ------------------------------------------------------------------

    async def stream_message(
        self, session_id: int, user_message: str
    ) -> AsyncIterator[str]:
        """Send a user message and stream the agent response as SSE events.

        Creates the AgentSession on first message, reuses it thereafter.
        Each SSE event includes the DB sequence number so the frontend
        can sort messages into correct chronological order.
        """
        session = await self.get_session(session_id)
        if not session:
            yield _sse("error", {"message": f"Session {session_id} not found"})
            return

        # Persist user message
        _user_id, user_seq = await self._save_message(session_id, "user", user_message)
        yield _sse("user_echo", {"sequence": user_seq, "content": user_message})

        # Get or create the persistent agent for this session
        agent = self._sessions.get(session_id)
        if agent is None:
            agent = AgentSession(
                session_id=session_id,
                case_id=session["case_id"],
                system_prompt=session["system_prompt"] or VISION_SYSTEM_PROMPT,
            )
            self._sessions[session_id] = agent

        try:
            await agent.send_message(user_message)

            # Accumulate assistant text across the turn — save once at the end
            assistant_text = ""

            async for event in agent.receive():
                event_type = event.get("type", "")

                if event_type == "assistant":
                    # Streaming delta — accumulate, emit immediately, save later
                    content = event.get("content", "")
                    if content:
                        assistant_text += content
                        yield _sse("assistant", {
                            "content": content,
                            "sequence": None,  # delta — sequence assigned on final save
                        })

                elif event_type == "tool_call":
                    _tid, tseq = await self._save_message(
                        session_id, "tool_call", "",
                        tool_name=event.get("name", ""),
                        tool_inputs=event.get("inputs"),
                    )
                    yield _sse("tool_call", {
                        "name": event.get("name", ""),
                        "inputs": event.get("inputs"),
                        "sequence": tseq,
                    })

                elif event_type == "tool_result":
                    _rid, rseq = await self._save_message(
                        session_id, "tool_result", event.get("content", ""),
                        tool_result=event,
                    )
                    yield _sse("tool_result", {
                        "tool_use_id": event.get("tool_use_id", ""),
                        "content": event.get("content", ""),
                        "sequence": rseq,
                    })

                elif event_type == "done":
                    # Save the accumulated assistant text as one row
                    if assistant_text:
                        _aid, aseq = await self._save_message(
                            session_id, "assistant", assistant_text,
                        )
                        yield _sse("assistant_final", {
                            "sequence": aseq,
                        })
                    await self._auto_title(session_id)
                    yield _sse("done", {
                        "subtype": event.get("subtype", ""),
                        "session_id": event.get("session_id"),
                        "cost": event.get("cost"),
                    })

        except Exception as exc:
            logger.exception("Agent SDK streaming failed")
            # Save whatever text we accumulated before the error
            if assistant_text:
                await self._save_message(session_id, "assistant", assistant_text)
            yield _sse("error", {"message": str(exc)})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sse(event_type: str, data: dict) -> str:
    """Format a dict as an SSE event string."""
    payload = json.dumps({"type": event_type, **data}, default=str)
    return f"data: {payload}\n\n"
