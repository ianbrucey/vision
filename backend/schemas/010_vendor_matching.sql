-- ============================================================================
-- Vision — Vendor Matching Migration v19
-- ============================================================================
-- Adds the `vendor_matches` table (ranked candidate vendors per solicitation)
-- plus matching/outreach-template columns on `solicitations`, and extends
-- `jobs.job_type` with 'vendor_matching'.
--
-- Design decisions:
--   - `vendor_matches.vendor_id` FKs to `vendors.id` (BIGSERIAL — that table
--     has no `external_id` column, per 009_vendors.sql). `solicitation_id`
--     FKs to `solicitations.id` (SERIAL/INTEGER).
--   - `UNIQUE (solicitation_id, vendor_id)` + CLAIM-08's delete-then-insert
--     re-run pattern (mirrors `_save_artifact_impl` in solicitation_triage.py)
--     means this constraint is a safety net, not the primary duplicate guard.
--   - `naics_match_type` records which tier of the candidate-pool SQL
--     surfaced this vendor (Brief §1 tiered strategy) — informational, shown
--     in the UI, not used for scoring.
--   - `match_score` is INTEGER 0-100, assigned by the ranking LLM — not a
--     deterministic SQL computation.
--   - `rank` is 1-25 (Brief §5: fixed cap, no dynamic threshold in v1).
--   - `matching_status` mirrors `triage_status`'s 4-state shape exactly
--     ('pending' | 'running' | 'complete' | 'failed'), same convention as
--     008_solicitation_triage.sql.
--   - `outreach_email_subject`/`outreach_email_body` are TEXT, nullable —
--     one shared template per solicitation (Brief §7: no per-vendor drafts).
--
-- Dependencies: 007_solicitations.sql, 008_solicitation_triage.sql
--   (solicitations table), 009_vendors.sql (vendors table)
-- ============================================================================

SET search_path TO vision, public;

-- ----------------------------------------------------------------------------
-- solicitations — matching status + shared outreach email template
-- ----------------------------------------------------------------------------
ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS matching_status TEXT
    NOT NULL DEFAULT 'pending'
    CHECK (matching_status IN ('pending', 'running', 'complete', 'failed'));

ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS matching_error TEXT;

ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS outreach_email_subject TEXT;
ALTER TABLE solicitations ADD COLUMN IF NOT EXISTS outreach_email_body TEXT;

CREATE INDEX IF NOT EXISTS idx_solicitations_matching_status ON solicitations (matching_status);

-- ----------------------------------------------------------------------------
-- vendor_matches — ranked candidate vendors for a solicitation
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vendor_matches (
    id                SERIAL PRIMARY KEY,
    external_id       UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,

    solicitation_id   INTEGER REFERENCES solicitations(id) ON DELETE CASCADE NOT NULL,
    vendor_id         BIGINT REFERENCES vendors(id) ON DELETE CASCADE NOT NULL,

    rank              INTEGER NOT NULL CHECK (rank BETWEEN 1 AND 25),
    match_score       INTEGER NOT NULL CHECK (match_score BETWEEN 0 AND 100),
    match_rationale   TEXT NOT NULL,

    -- Which candidate-pool tier surfaced this vendor (Brief §1) — informational.
    naics_match_type  TEXT NOT NULL
        CHECK (naics_match_type IN ('exact', 'family', 'capability_only')),

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (solicitation_id, vendor_id)
);

CREATE INDEX IF NOT EXISTS idx_vendor_matches_solicitation
    ON vendor_matches (solicitation_id, rank);
CREATE INDEX IF NOT EXISTS idx_vendor_matches_vendor
    ON vendor_matches (vendor_id);

CREATE OR REPLACE FUNCTION update_vendor_matches_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_vendor_matches_updated_at ON vendor_matches;
CREATE TRIGGER trg_vendor_matches_updated_at
    BEFORE UPDATE ON vendor_matches
    FOR EACH ROW
    EXECUTE FUNCTION update_vendor_matches_updated_at();

-- ----------------------------------------------------------------------------
-- jobs.job_type — add 'vendor_matching' for the unattended matching pipeline
-- ----------------------------------------------------------------------------
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_job_type_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_job_type_check
    CHECK (job_type IN ('ingest', 'ingest_pdf', 'ingest_docx', 'ingest_xlsx',
                         'analyze', 'export', 'ocr', 'embed', 'enrich',
                         'synthesize', 'profile_synthesis', 'capability_statement',
                         'sam_fetch', 'solicitation_triage', 'vendor_matching',
                         'other'));

-- ============================================================================
-- Migration Bookkeeping
-- ============================================================================
INSERT INTO schema_migrations (version, name) VALUES (19, 'add_vendor_matching')
ON CONFLICT (version) DO NOTHING;
