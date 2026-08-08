-- ============================================================================
-- Vision — Pipeline Processing Columns on sam_notices · Migration 35
-- ============================================================================
-- Adds processing-status columns to sam_notices so the databank processor can
-- track which rows have been fed into the solicitation pipeline without
-- creating a separate processing-log table.
-- ============================================================================

SET search_path TO vision, public;

ALTER TABLE sam_notices ADD COLUMN IF NOT EXISTS pipeline_status TEXT;
-- NULL  = unprocessed
-- 'queued'    = sent to solicitation pipeline (sam_fetch enqueued)
-- 'skipped'   = did not pass filters (see pipeline_skip_reason)
-- 'duplicate' = notice_id already exists in solicitations table
-- 'error'     = processing failed

ALTER TABLE sam_notices ADD COLUMN IF NOT EXISTS pipeline_category TEXT;
-- 'construction', 'facilities', 'it', 'other'

ALTER TABLE sam_notices ADD COLUMN IF NOT EXISTS pipeline_urgency TEXT;
-- 'red'     = 0-7 days until deadline (or Sources Sought)
-- 'yellow'  = 8-14 days
-- 'green'   = 15+ days
-- 'unknown' = no response date
-- 'past_due' = before today (normally skipped, except recent Sources Sought)

ALTER TABLE sam_notices ADD COLUMN IF NOT EXISTS pipeline_skip_reason TEXT;
-- e.g. 'past_due', 'wrong_naics', 'excluded_type', 'full_and_open',
--      'invalid_notice_id', 'partial_set_aside'

ALTER TABLE sam_notices ADD COLUMN IF NOT EXISTS pipeline_solicitation_id INTEGER;
-- FK to solicitations.id — the created solicitation row, if queued

ALTER TABLE sam_notices ADD COLUMN IF NOT EXISTS pipeline_processed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_sam_notices_pipeline_status
    ON sam_notices (pipeline_status);
CREATE INDEX IF NOT EXISTS idx_sam_notices_pipeline_category
    ON sam_notices (pipeline_category);
CREATE INDEX IF NOT EXISTS idx_sam_notices_pipeline_urgency
    ON sam_notices (pipeline_urgency);

INSERT INTO schema_migrations (version, name) VALUES (35, 'pipeline_processing')
ON CONFLICT (version) DO NOTHING;
