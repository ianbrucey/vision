-- ============================================================================
-- Vision — SAM Notice Import Job Type Migration v27
-- ============================================================================
-- Adds 'sam_notice_import' to jobs.job_type CHECK constraint.
-- ============================================================================

SET search_path TO vision, public;

ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_job_type_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_job_type_check
    CHECK (job_type IN ('ingest', 'ingest_pdf', 'ingest_docx', 'ingest_xlsx',
                         'analyze', 'export', 'ocr', 'embed', 'enrich',
                         'synthesize', 'profile_synthesis', 'capability_statement',
                         'sam_fetch', 'solicitation_triage', 'vendor_matching',
                         'inbound_email', 'sam_notice_import', 'other'));

INSERT INTO schema_migrations (version, name) VALUES (27, 'sam_notice_import_job')
ON CONFLICT (version) DO NOTHING;
