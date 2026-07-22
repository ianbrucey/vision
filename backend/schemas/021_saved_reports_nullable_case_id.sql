-- 021_saved_reports_nullable_case_id.sql
-- Make case_id nullable so reports can be global (not tied to a single case).
-- SAM Notices, Forecasts, and Vendors are case-agnostic reference data;
-- reports saved from those views should not require a case context.
ALTER TABLE vision.saved_reports ALTER COLUMN case_id DROP NOT NULL;

INSERT INTO vision.schema_migrations (version, name)
VALUES (30, 'saved_reports_nullable_case_id');
