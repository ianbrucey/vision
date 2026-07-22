-- ============================================================================
-- Vision — Vendor Outreach Tracking Migration v22
-- ============================================================================
-- Adds manual outreach status tracking to `vendor_matches` (T8). Tracks
-- whether a quote/response has been requested from and/or received from
-- each matched vendor, and optionally links the received response to a
-- row in `documents`.
--
-- Kept deliberately generic (no provider-specific columns) — automated
-- email capture (T10, possibly via Mailgun) is a later, separate decision.
-- When/if that lands, it becomes another writer of these same columns
-- (e.g. an inbound webhook calling the same update path as a manual
-- status change) rather than requiring new columns here.
--
-- See: backend/core/vendor_match.py::VendorMatchManager.update_outreach
-- Dependencies: 010_vendor_matching.sql (vendor_matches table),
--               001_core.sql (documents table)
-- ============================================================================

SET search_path TO vision, public;

ALTER TABLE vendor_matches ADD COLUMN IF NOT EXISTS outreach_status TEXT
    NOT NULL DEFAULT 'not_contacted';
ALTER TABLE vendor_matches DROP CONSTRAINT IF EXISTS vendor_matches_outreach_status_check;
ALTER TABLE vendor_matches ADD CONSTRAINT vendor_matches_outreach_status_check
    CHECK (outreach_status IN ('not_contacted', 'requested', 'received', 'declined'));

ALTER TABLE vendor_matches ADD COLUMN IF NOT EXISTS outreach_requested_at TIMESTAMPTZ;
ALTER TABLE vendor_matches ADD COLUMN IF NOT EXISTS outreach_received_at TIMESTAMPTZ;

ALTER TABLE vendor_matches ADD COLUMN IF NOT EXISTS outreach_doc_id INTEGER;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_vendor_matches_outreach_doc'
          AND conrelid = 'vendor_matches'::regclass
    ) THEN
        ALTER TABLE vendor_matches
            ADD CONSTRAINT fk_vendor_matches_outreach_doc
            FOREIGN KEY (outreach_doc_id) REFERENCES documents(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_vendor_matches_outreach_status
    ON vendor_matches (solicitation_id, outreach_status);

-- ============================================================================
-- Migration Bookkeeping
-- ============================================================================
INSERT INTO schema_migrations (version, name) VALUES (22, 'vendor_outreach_tracking')
ON CONFLICT (version) DO NOTHING;
