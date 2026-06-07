# Conversation Infrastructure — Implementation Plan

## Research Findings

### Sessions

The Agent SDK persists sessions automatically as JSONL files:

```
~/.claude/projects/<encoded-cwd>/<session-id>.jsonl
```

Where `<encoded-cwd>` is the absolute working directory with non-alphanumeric chars replaced by `-`. The JSONL contains every prompt, tool call, tool result, and response.

**Two programming models:**

| Model | How | When |
|-------|-----|------|
| `ClaudeSDKClient` | Stateful client object. Call `client.query()` multiple times — it auto-continues the same session. No ID tracking | Multi-turn chat in a single process (this is us) |
| `query()` + `resume` | Stateless function. Capture `session_id` from `ResultMessage`, pass to next `query(resume=session_id)` | Process restarts, multi-user apps, resuming specific sessions |

**For our chat interface, `ClaudeSDKClient` is the right model.** The frontend opens a WebSocket or SSE connection. The backend creates a `ClaudeSDKClient` instance, calls `client.query(prompt)`, and streams `client.receive_response()` back to the frontend. Each subsequent user message calls `client.query()` again on the same client — session continues automatically.

**Session lifecycle we need to manage:**

```python
async with ClaudeSDKClient(options=...) as client:
    # User message 1
    await client.query("What documents are in this case?")
    async for msg in client.receive_response():
        yield msg  # stream to frontend
    
    # User message 2 (same session, full context)
    await client.query("Find all mentions of 'adhesion' in the operative report")
    async for msg in client.receive_response():
        yield msg
    
    # Session ID persists — save to DB for later resumption
    session_id = client.session_id
```

### System Prompts

**Four approaches, from least to most control:**

| Approach | What It Does | When |
|----------|-------------|------|
| Default (nothing set) | Minimal prompt — tool calling only, no Claude Code persona | Non-coding agents |
| `claude_code` preset | Full Claude Code prompt — tools, safety, style, conventions | Coding agents (not us) |
| `claude_code` preset + `append` | Preset plus your instructions tacked on the end | Coding agent with domain rules |
| Custom string | Complete control. You write everything. No built-in safety or tool guidance unless you include it | Agents with different identity, surface, or permission model |

**For the War Room, we want a custom system prompt.** Here's why:
- Different identity: "War Room Agent," not "Claude Code"
- Different surface: chat UI, not terminal
- Different permission model: autonomous DB exploration, not human-in-the-loop file editing
- Domain-specific: legal research, evidence analysis, strategy development — not software engineering

The custom prompt replaces everything. We are responsible for including tool guidance and safety rules. The `claude_code` preset's coding instructions would compete with — and dilute — our legal-domain instructions.

**CLAUDE.md still works.** It's injected as conversation context (not system prompt), so it works with any system prompt choice. Setting `setting_sources=["project"]` loads `CLAUDE.md` from the working directory. We can use this for case-specific context.

**For DeepSeek:** nothing changes. The system prompt is a standard API field. DeepSeek supports it fully.

### Database Tools

The agent needs read/write access to PostgreSQL. The Agent SDK's tool mechanism lets us register Python functions as tools:

```python
from claude_agent_sdk import tool

@tool
def search_blocks(query: str, case_id: int, limit: int = 20) -> list[dict]:
    """Full-text search across evidence store blocks for a case."""
    # SQL against blocks table with tsvector
    ...

@tool  
def get_case(case_id: int) -> dict:
    """Return full case with parties, allegations, documents."""
    ...

@tool
def get_strategy_tree(strategy_id: int) -> dict:
    """Return the full proposition tree for a strategy."""
    ...
```

The SDK handles tool call parsing, result formatting, and the tool loop. We just write the functions.

### DeepSeek Compatibility

Setting env vars (already configured):
```
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_API_KEY=<deepseek-key>
ANTHROPIC_MODEL=deepseek-v4-pro
```

**What works:** Standard tool_use/tool_result, streaming, system prompts, thinking
**What doesn't:** Prompt caching (cache_control ignored), image/document content, MCP-specific content types

The Agent SDK uses standard tool_use — so database tools and MCP tools (which the SDK discovers client-side and presents as standard tools) should work.

**One risk to validate:** The Agent SDK may use Anthropic-specific API features (like `mcp_servers` in the request body or extended thinking with `budget_tokens`). DeepSeek ignores these. We need to test that the SDK → DeepSeek pipeline actually works end-to-end before committing to this architecture.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                        │
│                                                             │
│  ChatTab.tsx                                                │
│    │ WebSocket or SSE to /api/chat/{session_id}             │
│    │ Displays streaming messages, tool calls, citations     │
│    │ User types prompt → sent to backend → response streams │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 BACKEND (FastAPI + Agent SDK)                │
│                                                             │
│  /api/chat/sessions          POST   create new session      │
│  /api/chat/sessions/{id}     GET    get session history     │
│  /api/chat/sessions/{id}     DELETE end/archive session     │
│  /api/chat/sessions/{id}/messages  POST   send message      │
│                              GET    stream response (SSE)   │
│                                                             │
│  ChatManager:                                                │
│    - Maps session_id → ClaudeSDKClient instance             │
│    - Manages client lifecycle (create, resume, cleanup)     │
│    - Bridges SSE → client.receive_response()                │
│                                                             │
│  Tools (registered with Agent SDK):                         │
│    - DB read: cases, parties, documents, blocks, strategies │
│    - DB write: strategy_propositions, facts, mappings       │
│    - MCP bridge: legal research, knowledge graph            │
│    - File ops: read/write within case workspace             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    POSTGRESQL                                │
│                                                             │
│  chat_sessions  — NEW TABLE (see below)                     │
│  chat_messages  — NEW TABLE (see below)                     │
│  cases, parties, documents, blocks... (existing)            │
│  strategies, strategy_propositions... (migration ready)     │
└─────────────────────────────────────────────────────────────┘
```

---

## Session Storage: PostgresSessionStore (NOT JSONL files)

### The SDK's SessionStore Interface

The Agent SDK has a `SessionStore` protocol. You implement two methods, and the SDK calls them instead of writing JSONL to `~/.claude/projects/`:

```python
# claude_agent_sdk SessionStore protocol (Python)
class SessionStore(Protocol):
    async def append(self, key: SessionKey, entries: list[SessionStoreEntry]) -> None
    async def load(self, key: SessionKey) -> list[SessionStoreEntry] | None
    # Optional:
    async def list_sessions(self, project_key: str) -> list[SessionStoreListEntry]
    async def delete(self, key: SessionKey) -> None
    async def list_subkeys(self, key: SessionListSubkeysKey) -> list[str]
```

`SessionKey` has three fields:
- `project_key` — stable encoding of the working directory (e.g. `-Users-me-code-war_room`)
- `session_id` — session UUID
- `subpath` — for subagent transcripts (optional)

### Our Implementation: PostgresSessionStore

We write a Python class that implements `SessionStore` backed by a PostgreSQL table. The TypeScript SDK repo has a [reference Postgres adapter](https://github.com/anthropics/claude-agent-sdk-typescript/tree/main/examples/session-stores/postgres) we port to Python.

**Architecture:**

```
ClaudeSDKClient
    │
    │ writes entries via SessionStore.append()
    ▼
PostgresSessionStore
    │
    │ INSERT INTO session_store_entries
    ▼
PostgreSQL (single source of truth for all session data)
    │
    │ Frontend reads via API → chat_messages view
    ▼
ChatTab UI
```

The SDK dual-writes: local disk first (can be temp), then mirrors to our store. We point `CLAUDE_CONFIG_DIR` at `/tmp` so local writes are ephemeral. The database IS the durable store.

### Database Tables

```sql
-- Raw SDK transcript entries. One row per JSONL line.
-- This replaces ~/.claude/projects/<project_key>/<session_id>.jsonl
CREATE TABLE session_store_entries (
    id              BIGSERIAL PRIMARY KEY,               -- preserves insertion order
    project_key     TEXT NOT NULL,                       -- encoded working directory
    session_id      TEXT NOT NULL,                       -- SDK session UUID
    subpath         TEXT,                                -- NULL for main, "subagents/agent-<id>" for subagents
    entry           JSONB NOT NULL,                      -- the SessionStoreEntry (opaque JSON)
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_session_store_lookup 
    ON session_store_entries (project_key, session_id, subpath, id);
CREATE INDEX idx_session_store_list 
    ON session_store_entries (project_key, session_id);

-- Application-level chat sessions. Maps our internal session ID to the SDK's.
-- Multi-tenancy: each session belongs to a case. Cases belong to users (future FK).
CREATE TABLE chat_sessions (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    sdk_session_id  TEXT,                                -- Agent SDK session UUID
    project_key     TEXT,                                -- derived from case_id: "case_<id>"
    title           TEXT,                                -- auto-generated or user-set
    status          TEXT DEFAULT 'active' CHECK (status IN (
                        'active',     -- conversation in progress
                        'archived'    -- done
                    )),
    system_prompt   TEXT,                                -- custom prompt for this session
    context_summary TEXT,                                -- brief auto-generated summary
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chat_sessions_case ON chat_sessions (case_id);
CREATE INDEX idx_chat_sessions_sdk ON chat_sessions (sdk_session_id);

-- UI-facing messages. Derived from session_store_entries but structured for
-- frontend rendering. Populated by our backend as it streams SDK responses.
CREATE TABLE chat_messages (
    id              SERIAL PRIMARY KEY,
    session_id      INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE NOT NULL,
    role            TEXT NOT NULL CHECK (role IN (
                        'user',         -- human message
                        'assistant',    -- agent text response
                        'tool_call',    -- agent invoked a tool
                        'tool_result',  -- tool returned data
                        'system'        -- session lifecycle events
                    )),
    content         TEXT NOT NULL,
    tool_name       TEXT,
    tool_inputs     JSONB,
    tool_result     JSONB,
    citations       JSONB,                               -- block references
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chat_messages_session ON chat_messages (session_id);
CREATE INDEX idx_chat_messages_created ON chat_messages (session_id, created_at);
```

### Multi-Tenancy: How It Works

1. **Each case gets its own `project_key`.** When creating a chat session for `case_id=42`, we set `project_key = "case_42"` and spawn the Agent SDK with `cwd` pointing to a case-specific directory (`/tmp/vision/case_42/`). The SDK encodes `cwd` → `project_key`. Different cases = different project keys = isolated session storage.

2. **User isolation is at the case level.** `cases` table will eventually have a `user_id` FK. `chat_sessions.case_id` → `cases.id` → `cases.user_id`. Users can only access sessions belonging to their cases.

3. **Resumption across restarts.** `chat_sessions` stores `sdk_session_id` and `project_key`. After backend restart, we instantiate `PostgresSessionStore`, look up the session, and pass `resume=sdk_session_id` to a new `ClaudeSDKClient` — the SDK calls `store.load()` and gets the full transcript.

### PostgresSessionStore Implementation (Python)

```python
# backend/chat/session_store.py

from claude_agent_sdk import SessionStore, SessionKey, SessionStoreEntry, SessionStoreListEntry
import psycopg2
import json

class PostgresSessionStore:
    """SessionStore backed by PostgreSQL. One row per transcript entry."""
    
    def __init__(self, conn_factory):
        self._conn = conn_factory  # callable returning a psycopg2 connection
    
    async def append(self, key: SessionKey, entries: list[SessionStoreEntry]) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                for entry in entries:
                    cur.execute(
                        """INSERT INTO session_store_entries 
                           (project_key, session_id, subpath, entry)
                           VALUES (%s, %s, %s, %s::jsonb)""",
                        (key["project_key"], key["session_id"], 
                         key.get("subpath"), json.dumps(entry)),
                    )
            conn.commit()
        finally:
            conn.close()
    
    async def load(self, key: SessionKey) -> list[SessionStoreEntry] | None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT entry FROM session_store_entries
                       WHERE project_key = %s AND session_id = %s
                         AND subpath IS NOT DISTINCT FROM %s
                       ORDER BY id""",
                    (key["project_key"], key["session_id"], key.get("subpath")),
                )
                rows = cur.fetchall()
                if not rows:
                    return None
                return [row[0] for row in rows]
        finally:
            conn.close()
    
    async def list_sessions(
        self, project_key: str
    ) -> list[SessionStoreListEntry]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT session_id, 
                              EXTRACT(EPOCH FROM max(created_at))::bigint as mtime
                       FROM session_store_entries
                       WHERE project_key = %s AND subpath IS NULL
                       GROUP BY session_id
                       ORDER BY mtime DESC""",
                    (project_key,),
                )
                return [
                    {"session_id": row[0], "mtime": row[1]}
                    for row in cur.fetchall()
                ]
        finally:
            conn.close()
    
    async def delete(self, key: SessionKey) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """DELETE FROM session_store_entries
                       WHERE project_key = %s AND session_id = %s""",
                    (key["project_key"], key["session_id"]),
                )
            conn.commit()
        finally:
            conn.close()
```

---

## System Prompt

Custom system prompt for the War Room Agent, stored as a constant in the backend and written to `chat_sessions.system_prompt` at session creation:

```python
WAR_ROOM_SYSTEM_PROMPT = """You are the War Room Agent — an AI legal intelligence system.

IDENTITY:
You serve a litigation attorney. Your job is to research evidence, analyze 
legal claims, map facts to doctrine, assess adversarial vulnerabilities, and 
draft legal documents. You are not a chatbot. You are an intelligence layer 
that operates on a fully indexed case corpus.

CAPABILITIES:
- Search the evidence store: documents, sections, blocks — full-text + vector
- Read case facts, parties, allegations, and timelines from the database
- Research case law via CourtListener and legal research tools
- Build and analyze strategy trees (claims → elements → facts → authorities)
- Run adversarial analysis on legal propositions
- Draft legal documents with citation-anchored factual claims

RULES (NON-NEGOTIABLE):
1. Every factual claim MUST cite a source. Say "According to page 117 of the 
   medical record (block /page/116/Text/6)..." not "The record shows..."
2. Every legal citation MUST be verified. Use the legal research tools to 
   confirm that a case exists and stands for what you claim. Never invent 
   citations. Never write holdings from memory.
3. If you don't know something, say so. Do not guess. Offer to research it.
4. Absence of evidence IS evidence of absence in certain contexts. If you 
   search for something and it's not in the record, say so explicitly.
5. Be precise about what you found vs. what you concluded. "The pathology 
   report states X" is a finding. "This supports the allegation" is a 
   conclusion. Keep them distinct.
6. When asked to analyze strategy, build the doctrine tree FIRST from 
   controlling law, THEN map facts. Never start with facts.

COMMUNICATION STYLE:
- Professional, direct, citation-backed
- Prefer structured output when analyzing (tables, trees, lists)
- When citing evidence, include the page number and block reference
- When citing law, include the full citation and operative quotation
- Flag gaps and uncertainties explicitly

You have direct read access to the case database and evidence store. 
Use your tools to explore before answering. Do not ask permission to 
search — just search."""
```

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `backend/requirements.txt` | Modify | Add `claude-agent-sdk` |
| `backend/chat/__init__.py` | Create | Chat module init |
| `backend/chat/manager.py` | Create | `ChatManager` — maps sessions to `ClaudeSDKClient` instances, lifecycle management |
| `backend/chat/tools.py` | Create | Database tools registered with Agent SDK (`search_blocks`, `get_case`, `get_document_structure`, `get_strategy_tree`, etc.) |
| `backend/chat/prompt.py` | Create | System prompt constant |
| `backend/chat/stream.py` | Create | SSE bridge — `client.receive_response()` → SSE events |
| `backend/api/routes/chat.py` | Create | FastAPI routes for chat CRUD + SSE streaming |
| `backend/api/main.py` | Modify | Register chat routes |
| `schemas/003_chat.sql` | Create | `chat_sessions` + `chat_messages` tables |
| `frontend/src/lib/api.ts` | Modify | Add chat API client functions |
| `frontend/src/app/cases/[id]/tabs/ChatTab.tsx` | Modify | Wire up real chat with SSE streaming |

---

## Implementation Phases

### Phase 1: Agent SDK Smoke Test (verify DeepSeek compatibility)

Before building infrastructure, verify the Agent SDK works with DeepSeek:

```python
# test_agent_sdk.py — run standalone to verify DeepSeek compatibility
import os, asyncio
os.environ["ANTHROPIC_BASE_URL"] = "https://api.deepseek.com/anthropic"
os.environ["ANTHROPIC_API_KEY"] = os.environ.get("DEEPSEEK_API_KEY")  # from .env
os.environ["ANTHROPIC_MODEL"] = "deepseek-v4-pro"

from claude_agent_sdk import query, ClaudeAgentOptions

async def test():
    async for msg in query(
        prompt="Say hello and confirm you can read the current directory",
        options=ClaudeAgentOptions(allowed_tools=["Bash", "Read"]),
    ):
        print(msg)

asyncio.run(test())
```

**Pass criteria:** Agent responds, can use Bash to list directory, streaming works.

### Phase 2: Database Tools + System Prompt

- Write `backend/chat/prompt.py` with the custom system prompt
- Write `backend/chat/tools.py` with initial database tools (read-only first: `list_cases`, `get_case`, `search_blocks`, `get_document_structure`)
- Verify agent can answer questions about a case by querying the database

### Phase 3: Session Infrastructure

- Create `chat_sessions` and `chat_messages` tables
- Write `ChatManager` that manages `ClaudeSDKClient` instances
- Write SSE bridge for streaming
- Write FastAPI routes

### Phase 4: Frontend Integration

- Update ChatTab to use real API instead of mock
- Implement SSE streaming in the chat component
- Display tool calls/citations in a structured way

### Phase 5: Write Tools + Strategy Integration

- Add write tools for strategy tables
- Enable the agent to build doctrine trees, map facts, etc. from conversation

---

## Open Risks

1. **Agent SDK + DeepSeek compatibility not yet tested.** The SDK may use API features DeepSeek doesn't support. Phase 1 is a smoke test — if it fails, we fall back to direct `anthropic` Python SDK (or `openai` SDK pointed at DeepSeek) with a custom tool loop.

2. **ClaudeSDKClient in a web server.** The SDK is designed for local processes. Running `ClaudeSDKClient` inside FastAPI requires managing client lifecycle per-session: create on first message, keep alive across messages, timeout/cleanup on inactivity. The `ChatManager` handles this but needs careful implementation.

3. **Session JSONL persistence across restarts.** If the backend restarts, the JSONL files survive (they're on disk), and `ClaudeSDKClient` can resume via `resume=sdk_session_id`. But if the backend runs in a container with ephemeral storage, the JSONL is lost. For production: mount a persistent volume for `~/.claude/projects/`.

4. **DeepSeek rate limits.** No prompt caching means every request sends the full context. Long conversations will have large system+message payloads. DeepSeek rate limits may constrain throughput. Mitigation: summarize long conversations and start fresh sessions periodically.
