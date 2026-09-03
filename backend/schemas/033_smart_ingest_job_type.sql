-- ============================================================================
-- Vision — Smart Ingest Job Type Migration v38
-- ============================================================================
-- Adds 'smart_ingest' to jobs.job_type CHECK constraint.
--
-- CANONICAL SOURCE OF TRUTH for jobs_job_type_check on existing databases.
-- Previously this constraint was redefined piecemeal across 001_core.sql
-- (legacy v2/v3 DO blocks), 007_solicitations.sql, 008_solicitation_triage.sql,
-- 010_vendor_matching.sql, 014_vendor_outreach_email.sql, and
-- 018_sam_notice_import_job.sql — each with its own copy of the allowed
-- values list. Because ensure_smart_ingest_job_type_schema() runs LAST in
-- api/main.py::_apply_schemas() (highest migration number), those redundant
-- copies have been removed; this is now the only file that alters
-- jobs_job_type_check after table creation.
--
-- To add a new job_type going forward:
--   1. Add it to the CHECK list below AND to the CREATE TABLE jobs definition
--      in 001_core.sql (keeps fresh installs and upgraded installs in sync).
--   2. Do NOT add another ALTER TABLE ... DROP/ADD CONSTRAINT block anywhere
--      else — edit this file only.
-- ============================================================================

SET search_path TO vision, public;

ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_job_type_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_job_type_check
    CHECK (job_type IN ('ingest', 'ingest_pdf', 'ingest_docx', 'ingest_xlsx',
                         'analyze', 'export', 'ocr', 'embed', 'enrich',
                         'synthesize', 'profile_synthesis', 'capability_statement',
                         'sam_fetch', 'solicitation_triage', 'vendor_matching',
                         'inbound_email', 'sam_notice_import', 'smart_ingest', 'other'));

INSERT INTO schema_migrations (version, name) VALUES (38, 'smart_ingest_job_type')
ON CONFLICT (version) DO NOTHING;
