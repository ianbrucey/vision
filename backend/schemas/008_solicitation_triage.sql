-- ============================================================================
-- Vision — Solicitation Triage Pipeline Migration v18
-- ============================================================================
-- Adds unattended triage/deep-read output columns to `solicitations`:
--   - Triage classification + quick-kill result (internal-only).
--   - 5 partner-facing HTML artifacts, matching the external govcon Laravel
--     portal's `solicitations` table column names exactly (per
--     specs/vision-ai-brief.md), so a future sync job can copy them verbatim
--     with no re-shaping.
--
-- Design decisions:
--   - `triage_status` mirrors `ingestion_status`'s 4-state shape:
--     'pending' | 'running' | 'complete' | 'failed'. 'failed' is reserved for
--     the triage agent itself erroring out (e.g. can't classify at all) —
--     a quick-kill result is still `triage_status='complete'` with
--     `quick_kill=true`, not a failure.
--   - `has_partial_artifacts` mirrors `has_missing_docs`: true if 1+ of the
--     5 extractor agents failed but the run still finished (the other
--     artifacts are usable).
--   - Artifact columns are TEXT (HTML), nullable — absent until their
--     extractor completes. No default text; a NULL means "not generated yet"
--     vs. an extractor-produced "not found in solicitation" sentence.
--   - `notice_type` covers RFI/SSN/RFP/RFQ per the existing solicitation-
--     triage agent's classification step, plus 'other' for anything that
--     doesn't fit (state/local notices, unusual formats).
--
-- Dependencies: 007_solicitations.sql (solicitations, jobs tables must exist)
-- ============================================================================

SET search_path TO vision, public;

-- ----------------------------------------------------------------------------
-- solicitations — triage classification + quick-kill (internal-only)
-- ----------------------------------------------------------------------------
ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS triage_status TEXT
    NOT NULL DEFAULT 'pending'
    CHECK (triage_status IN ('pending', 'running', 'complete', 'failed'));

ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS triage_error TEXT;

ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS has_partial_artifacts
    BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS notice_type TEXT
    CHECK (notice_type IN ('rfi', 'sources_sought', 'rfp', 'rfq', 'other'));

ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS quick_kill BOOLEAN;

ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS quick_kill_reason TEXT;

-- ----------------------------------------------------------------------------
-- solicitations — 5 partner-facing HTML artifacts (external portal columns)
-- ----------------------------------------------------------------------------
ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS artifact_scope_of_work TEXT;
ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS artifact_technical_requirements TEXT;
ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS artifact_deliverables_timeline TEXT;
ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS artifact_evaluation_criteria TEXT;
ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS artifact_submission_checklist TEXT;

CREATE INDEX IF NOT EXISTS idx_solicitations_triage_status ON solicitations (triage_status);

-- ----------------------------------------------------------------------------
-- jobs.job_type — add 'solicitation_triage' for the unattended pipeline run
-- ----------------------------------------------------------------------------
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_job_type_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_job_type_check
    CHECK (job_type IN ('ingest', 'ingest_pdf', 'ingest_docx', 'ingest_xlsx',
                         'analyze', 'export', 'ocr', 'embed', 'enrich',
                         'synthesize', 'profile_synthesis', 'capability_statement',
                         'sam_fetch', 'solicitation_triage', 'vendor_matching', 'inbound_email', 'sam_notice_import', 'other'));

-- ============================================================================
-- Migration Bookkeeping
-- ============================================================================
INSERT INTO schema_migrations (version, name) VALUES (18, 'add_solicitation_triage')
ON CONFLICT (version) DO NOTHING;
