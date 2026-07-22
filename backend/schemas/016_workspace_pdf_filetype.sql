-- ============================================================================
-- Vision — Workspace PDF File Type Migration v25
-- ============================================================================
-- Adds 'pdf' to the drafts.file_type CHECK constraint so filled forms and
-- other PDF documents can be referenced from workspace items.
-- ============================================================================

SET search_path TO vision, public;

ALTER TABLE drafts DROP CONSTRAINT IF EXISTS drafts_file_type_check;
ALTER TABLE drafts ADD CONSTRAINT drafts_file_type_check
    CHECK (file_type IN ('markdown', 'structured_draft', 'html', 'json_view', 'pdf'));

INSERT INTO schema_migrations (version, name) VALUES (25, 'workspace_pdf_filetype')
ON CONFLICT (version) DO NOTHING;
