-- ============================================================================
-- Vision — Calendar System Migration v15
-- ============================================================================
-- Adds calendar events and reminders tables. Each is case-scoped.
--
-- Design decisions:
--   - Named `calendar_events` to avoid collision with existing `events` table
--     (which stores historical case timeline facts, not future calendar items)
--   - All times stored as TIMESTAMPTZ — PostgreSQL handles timezone conversion
--   - All-day events use all_day boolean; date queries use start_time::DATE
--     (expression index on (case_id, (start_time::DATE)) handles date filtering)
--   - Reminders link to events via nullable FK (standalone reminders have NULL event_id)
--   - ON DELETE CASCADE on event_id: deleting an event silently deletes its reminders
--   - created_by uses TEXT CHECK pattern (matching drafts and business_vault):
--     'user' for human-created, 'agent' for agent-created via chat tools
--   - workspace_id included as nullable FK for future workspace scoping (matching
--     the pattern on drafts and events tables — deferred but schema-supported)
--   - Follows the same patterns as `tasks` table (CHECK constraints, indexes, metadata JSONB)
--
-- Dependencies: 001_core.sql (cases, workspaces tables must exist)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Calendar Events
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS calendar_events (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    workspace_id    INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,  -- deferred: scope to sub-matter

    -- Core fields
    title           TEXT NOT NULL,
    description     TEXT,

    -- Time: start is required; end is optional (for point-in-time events)
    -- All-day events set start_time to midnight of the event date.
    -- Date-only queries use start_time::DATE — see expression index below.
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ,                -- NULL = point-in-time / unspecified duration
    all_day         BOOLEAN NOT NULL DEFAULT FALSE,

    -- Classification
    -- ⚠️ SYNC: If you change these values, also update the CHECK on `reminders.category`.
    category        TEXT NOT NULL DEFAULT 'other'
                    CHECK (category IN (
                        'hearing',
                        'deposition',
                        'deadline',
                        'meeting',
                        'other'
                    )),

    -- Optional location (Zoom link, courtroom number, address)
    location        TEXT,

    -- Provenance
    -- 'user' = created by human via UI; 'agent' = created by agent via chat tool.
    -- Follows the same TEXT CHECK pattern as drafts.created_by.
    created_by      TEXT NOT NULL DEFAULT 'user'
                    CHECK (created_by IN ('user', 'agent')),
    metadata        JSONB DEFAULT '{}',

    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_calendar_events_case
    ON calendar_events (case_id);

CREATE INDEX IF NOT EXISTS idx_calendar_events_time
    ON calendar_events (case_id, start_time, end_time);

-- Expression index: enables efficient date-range queries without a denormalized event_date column
CREATE INDEX IF NOT EXISTS idx_calendar_events_date
    ON calendar_events (case_id, (start_time::DATE));

CREATE INDEX IF NOT EXISTS idx_calendar_events_category
    ON calendar_events (case_id, category);

CREATE INDEX IF NOT EXISTS idx_calendar_events_workspace
    ON calendar_events (workspace_id);

-- ----------------------------------------------------------------------------
-- Reminders
-- ----------------------------------------------------------------------------
-- Reminders can be standalone (event_id IS NULL) or attached to a calendar event.
-- The remind_at column stores an absolute time. When the user (or agent) says
-- "remind me 48 hours before the hearing", the agent computes the absolute
-- remind_at value from the event's start_time. The schema never stores intervals.
--
-- ON DELETE CASCADE on event_id: deleting a calendar event silently deletes
-- all reminders attached to it. Standalone reminders (event_id IS NULL) are
-- unaffected by event deletion.
CREATE TABLE IF NOT EXISTS reminders (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    event_id        INTEGER REFERENCES calendar_events(id) ON DELETE CASCADE,  -- NULL = standalone reminder

    -- Core fields
    title           TEXT NOT NULL,
    description     TEXT,

    -- When the reminder should fire (absolute time, agent-computed from interval input)
    remind_at       TIMESTAMPTZ NOT NULL,

    -- Classification
    -- ⚠️ SYNC: If you change these values, also update the CHECK on `calendar_events.category`.
    category        TEXT NOT NULL DEFAULT 'other'
                    CHECK (category IN (
                        'hearing',
                        'deposition',
                        'deadline',
                        'meeting',
                        'other'
                    )),

    -- Lifecycle
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN (
                        'pending',      -- scheduled, not yet due
                        'fired',        -- reminder time arrived, notification sent
                        'dismissed'     -- user dismissed manually
                    )),

    -- Provenance (same TEXT CHECK pattern as calendar_events)
    created_by      TEXT NOT NULL DEFAULT 'user'
                    CHECK (created_by IN ('user', 'agent')),
    metadata        JSONB DEFAULT '{}',

    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_reminders_case
    ON reminders (case_id);

CREATE INDEX IF NOT EXISTS idx_reminders_event
    ON reminders (event_id);

-- Partial index: only pending reminders — the query the polling hook runs
CREATE INDEX IF NOT EXISTS idx_reminders_due
    ON reminders (case_id, status, remind_at)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_reminders_category
    ON reminders (case_id, category);

-- ============================================================================
-- Migration Bookkeeping
-- ============================================================================
INSERT INTO schema_migrations (version, name) VALUES (15, 'add_calendar_tables')
ON CONFLICT (version) DO NOTHING;
