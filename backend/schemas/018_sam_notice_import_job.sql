-- ============================================================================
-- Vision — SAM Notice Import Job Type Migration v27
-- ============================================================================
-- Adds 'sam_notice_import' to jobs.job_type CHECK constraint.
-- ============================================================================

SET search_path TO vision, public;

-- jobs.job_type — 'sam_notice_import' added here historically. The
-- jobs_job_type_check constraint is no longer redefined here; it is
-- consolidated into 033_smart_ingest_job_type.sql (see that file's header).

INSERT INTO schema_migrations (version, name) VALUES (27, 'sam_notice_import_job')
ON CONFLICT (version) DO NOTHING;
