-- ============================================================================
-- Vision — Chat Infrastructure Schema v3.0
-- ============================================================================
-- Session storage and message tables for the conversational agent interface.
--
-- Two-layer design:
--   1. session_store_entries — raw SDK transcript (replaces JSONL files).
--      The PostgresSessionStore adapter reads/writes this table. One row
--      per JSONL line, ordered by BIGSERIAL for append-order fidelity.
--   2. chat_sessions + chat_messages — application-level session management
--      and UI-facing message rendering. Populated by the backend as it
--      streams Agent SDK responses.
--
-- Multi-tenancy:
--   - Each case gets its own project_key (derived from working directory).
--   - session_store_entries is keyed by (project_key, session_id, subpath).
--   - chat_sessions links to cases. User isolation via cases.user_id (future FK).
-- ============================================================================

SET search_path TO vision, agent_work, public;

-- ============================================================================
-- SESSION STORE — Raw SDK transcript storage.
-- ============================================================================
-- Replaces ~/.claude/projects/<project_key>/<session_id>.jsonl.
-- The PostgresSessionStore adapter writes every transcript entry as a row.
-- BIGSERIAL preserves insertion order for faithful replay.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS session_store_entries (
    id              BIGSERIAL PRIMARY KEY,
    project_key     TEXT NOT NULL,                       -- encoded working directory (e.g. "case_42")
    session_id      TEXT NOT NULL,                       -- SDK session UUID
    subpath         TEXT,                                -- NULL for main transcript;
                                                        -- "subagents/agent-<id>" for subagent transcripts
    entry           JSONB NOT NULL,                      -- opaque SessionStoreEntry from the SDK
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Primary lookup: load a specific transcript in order
CREATE INDEX IF NOT EXISTS idx_session_store_lookup
    ON session_store_entries (project_key, session_id, subpath, id);

-- List sessions for a project
CREATE INDEX IF NOT EXISTS idx_session_store_list
    ON session_store_entries (project_key, session_id);

-- ============================================================================
-- CHAT SESSIONS — Application-level session management.
-- ============================================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    workspace_id    INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
    sdk_session_id  TEXT,                                -- Agent SDK session UUID for resumption
    project_key     TEXT NOT NULL,                       -- derived from case_id: "case_<id>"
    title           TEXT,                                -- auto-generated from first prompt or set by user
    status          TEXT DEFAULT 'active' CHECK (status IN (
                        'active',     -- conversation in progress
                        'archived'    -- done, kept for reference
                    )),
    system_prompt   TEXT,                                -- the custom system prompt used for this session
    context_summary TEXT,                                -- brief auto-generated summary for session list display
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_case ON chat_sessions (case_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_workspace ON chat_sessions (workspace_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_sdk ON chat_sessions (sdk_session_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_status ON chat_sessions (case_id, status);

-- ============================================================================
-- CHAT MESSAGES — UI-facing structured message history.
-- ============================================================================
-- Derived from the SDK stream as messages arrive. Structured for frontend
-- rendering: markdown content, expandable tool calls, citation badges.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_messages (
    id              SERIAL PRIMARY KEY,
    session_id      INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE NOT NULL,

    -- Message role
    role            TEXT NOT NULL CHECK (role IN (
                        'user',         -- human message
                        'assistant',    -- agent text response (markdown)
                        'tool_call',    -- agent invoked a tool (name + inputs)
                        'tool_result',  -- tool returned data
                        'system'        -- session lifecycle (init, error, status)
                    )),

    -- Content (markdown for assistant, plain for tool results)
    content         TEXT NOT NULL,

    -- Tool metadata (for tool_call / tool_result)
    tool_name       TEXT,
    tool_inputs     JSONB,
    tool_result     JSONB,

    -- Citation badges extracted from the message
    citations       JSONB,                               -- [{block_id, page, quote}, ...]

    -- Sequence within the session
    sequence        INTEGER DEFAULT 0,

    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages (session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_sequence ON chat_messages (session_id, sequence);
CREATE INDEX IF NOT EXISTS idx_chat_messages_role ON chat_messages (session_id, role);

-- ============================================================================
-- MIGRATION RECORD
-- ============================================================================
INSERT INTO schema_migrations (version, name) VALUES (3, 'chat_infrastructure')
    ON CONFLICT (version) DO NOTHING;
