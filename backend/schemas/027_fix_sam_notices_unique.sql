-- ============================================================================
-- Vision — Fix sam_notices notice_id index · Migration 37
-- ============================================================================
-- The sam_notices table is a raw CSV dump. The SAM.gov databank CSV contains
-- duplicate notice_id values because a single notice can appear with multiple
-- NAICS/PSC codes. A UNIQUE index on notice_id was added outside of migrations
-- and causes COPY failures on legitimate data.
--
-- This migration drops the unique index (if present) and creates a regular
-- non-unique index for query performance. The unique constraint belongs on
-- the solicitations table (007_solicitations.sql), not the raw import table.
-- ============================================================================

SET search_path TO vision, public;

-- Drop the incorrectly-added unique index
DROP INDEX IF EXISTS idx_sam_notices_notice_id;

-- Create a regular (non-unique) index for query performance
CREATE INDEX IF NOT EXISTS idx_sam_notices_notice_id
    ON sam_notices (notice_id);

INSERT INTO schema_migrations (version, name) VALUES (37, 'fix_sam_notices_unique')
ON CONFLICT (version) DO NOTHING;
