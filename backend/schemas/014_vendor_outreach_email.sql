-- ============================================================================
-- Vision — Vendor Outreach Email Migration v23
-- ============================================================================
-- Adds Mailgun send/reply-correlation columns to vendor_matches (T10a/b).
-- outreach_message_id: Mailgun's returned Message-Id for the sent email —
--   informational/debugging only, never required for correctness.
-- outreach_reply_token: random token embedded in the Reply-To address used
--   to correlate an inbound webhook back to this row. SECURITY: never
--   include this column in any SELECT reachable by a public API route —
--   see core/vendor_match.py::find_by_reply_token, which is the only
--   permitted reader, used exclusively by the webhook handler.
-- Also extends jobs.job_type with 'inbound_email' for the async ingest path.
--
-- Dependencies: 013_vendor_outreach.sql (vendor_matches outreach columns)
-- ============================================================================

SET search_path TO vision, public;

ALTER TABLE vendor_matches ADD COLUMN IF NOT EXISTS outreach_message_id TEXT;
ALTER TABLE vendor_matches ADD COLUMN IF NOT EXISTS outreach_reply_token TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_vendor_matches_reply_token
    ON vendor_matches (outreach_reply_token) WHERE outreach_reply_token IS NOT NULL;

ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_job_type_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_job_type_check
    CHECK (job_type IN ('ingest', 'ingest_pdf', 'ingest_docx', 'ingest_xlsx',
                         'analyze', 'export', 'ocr', 'embed', 'enrich',
                         'synthesize', 'profile_synthesis', 'capability_statement',
                         'sam_fetch', 'solicitation_triage', 'vendor_matching',
                         'inbound_email', 'other'));

INSERT INTO schema_migrations (version, name) VALUES (23, 'vendor_outreach_email')
ON CONFLICT (version) DO NOTHING;
