-- ============================================================================
-- Vision — Journal Schema
-- ============================================================================
-- Append-only journal for cross-session continuity. The agent writes entries
-- for session starts/ends, milestones, decisions, phase changes, and findings.
-- Entries are scoped to case_id and indexed for chronological + type queries.

SET search_path TO vision, public;

-- ----------------------------------------------------------------------------
-- journal_entries — Agent-written case journal
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS journal_entries (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    entry_type      TEXT NOT NULL CHECK (entry_type IN (
                        'session_start', 'session_end',
                        'milestone', 'decision', 'phase_change',
                        'finding', 'note'
                    )),
    title           TEXT,                                               -- optional one-line summary
    content         TEXT NOT NULL,                                      -- markdown body
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_journal_case ON journal_entries (case_id);
CREATE INDEX IF NOT EXISTS idx_journal_type ON journal_entries (case_id, entry_type);
CREATE INDEX IF NOT EXISTS idx_journal_created ON journal_entries (case_id, created_at DESC);

INSERT INTO schema_migrations (version, name) VALUES (13, 'add_journal_entries')
ON CONFLICT (version) DO NOTHING;
