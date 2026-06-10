-- =============================================================================
-- Drafting System — Schema
-- =============================================================================
-- Generated From: 00-Brief.md
-- Block types: section_heading, numbered_paragraph, list_item, signature
-- Document types: letter, pleading, contract, memo, other
-- Statuses: draft, review, final
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: drafts
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS drafts (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    name            TEXT NOT NULL,                                  -- display title
    document_type   TEXT NOT NULL DEFAULT 'letter'
                    CHECK (document_type IN (
                        'letter', 'pleading', 'contract',
                        'memo', 'other'
                    )),
    status          TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'review', 'final')),
    content         JSONB NOT NULL DEFAULT '[]',                   -- array of blocks
    created_by      TEXT NOT NULL DEFAULT 'agent'
                    CHECK (created_by IN ('agent', 'user')),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- INDEXES
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_drafts_case ON drafts (case_id);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts (case_id, status);
CREATE INDEX IF NOT EXISTS idx_drafts_updated ON drafts (case_id, updated_at DESC);

-- -----------------------------------------------------------------------------
-- VALIDATION: block structure (application-level, documented here)
-- -----------------------------------------------------------------------------
-- Each element in content[] must be:
-- {
--   "id": "uuid",            -- unique within the draft (generated on creation)
--   "type": "block_type",    -- section_heading | numbered_paragraph | list_item | signature
--   "content": "text"        -- the block's text content
-- }
--
-- Numbered paragraphs are auto-numbered at render time.
-- Block order in the array determines document order.
-- Each block must have a unique id for targeted updates.

-- -----------------------------------------------------------------------------
-- MIGRATION
-- -----------------------------------------------------------------------------
INSERT INTO schema_migrations (version, name) VALUES (4, 'add_drafts_table')
ON CONFLICT (version) DO NOTHING;
