-- ============================================================================
-- Vision — Correspondence Schema v5.0
-- ============================================================================
-- Lightweight correspondence tracker for legal professionals.
--
-- Two-entity design:
--   1. correspondence_threads — groups related correspondence items
--      (e.g., "Discovery letters to opposing counsel")
--   2. correspondence_items — individual correspondence within a thread,
--      referencing sender/receiver from the existing parties table
--   3. correspondence_attachments — junction linking items to documents
--
-- All FK references use existing tables: cases, parties, documents.
-- ============================================================================

SET search_path TO vision, agent_work, public;

-- ============================================================================
-- CORRESPONDENCE THREADS
-- ============================================================================
CREATE TABLE IF NOT EXISTS correspondence_threads (
    id         SERIAL PRIMARY KEY,
    case_id    INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    title      TEXT NOT NULL,
    status     TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_corr_threads_case
    ON correspondence_threads (case_id);
CREATE INDEX IF NOT EXISTS idx_corr_threads_status
    ON correspondence_threads (case_id, status);

-- ============================================================================
-- CORRESPONDENCE ITEMS
-- ============================================================================
CREATE TABLE IF NOT EXISTS correspondence_items (
    id                SERIAL PRIMARY KEY,
    thread_id         INTEGER REFERENCES correspondence_threads(id) ON DELETE CASCADE NOT NULL,
    sender_party_id   INTEGER REFERENCES parties(id) ON DELETE SET NULL,
    receiver_party_id INTEGER REFERENCES parties(id) ON DELETE SET NULL,
    direction         TEXT NOT NULL CHECK (direction IN ('sent', 'received')),
    notes             TEXT,
    date_sent         DATE,
    date_received     DATE,
    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_corr_items_thread
    ON correspondence_items (thread_id);
CREATE INDEX IF NOT EXISTS idx_corr_items_sender
    ON correspondence_items (sender_party_id);
CREATE INDEX IF NOT EXISTS idx_corr_items_receiver
    ON correspondence_items (receiver_party_id);

-- ============================================================================
-- CORRESPONDENCE ATTACHMENTS — Junction: items ↔ documents
-- ============================================================================
CREATE TABLE IF NOT EXISTS correspondence_attachments (
    id          SERIAL PRIMARY KEY,
    item_id     INTEGER REFERENCES correspondence_items(id) ON DELETE CASCADE NOT NULL,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    UNIQUE (item_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_corr_attachments_item
    ON correspondence_attachments (item_id);
CREATE INDEX IF NOT EXISTS idx_corr_attachments_document
    ON correspondence_attachments (document_id);

-- ============================================================================
-- MIGRATION RECORD
-- ============================================================================
INSERT INTO schema_migrations (version, name) VALUES (5, 'correspondence_tracker')
    ON CONFLICT (version) DO NOTHING;
