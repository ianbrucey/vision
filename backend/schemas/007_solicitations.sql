-- ============================================================================
-- Vision — Solicitation Ingestion Migration v17
-- ============================================================================
-- Adds the `solicitations` table (Option A: domain table backed by a `cases`
-- row via case_id). Extends `jobs.job_type` with 'sam_fetch' and
-- `documents.source` with 'sam_gov' for provenance tagging.
--
-- Design decisions:
--   - `solicitations.case_id` FKs to the generic `cases` container (Option A,
--     approved). Documents/OCR/chat/jobs all key off case_id unchanged.
--   - `notice_id TEXT UNIQUE` (nullable) — federal-only field. Postgres allows
--     multiple NULLs under a UNIQUE constraint, so state/local rows (no
--     notice_id) never collide with each other; only real duplicate SAM.gov
--     notice IDs are rejected (CLAIM-09).
--   - `ingestion_status` has 4 states, not 5: 'pending' | 'fetching' |
--     'complete' | 'failed'. Per CLAIM-05/06: a fetch with missing/failed
--     attachment downloads still completes (`has_missing_docs = true` carries
--     that signal) — 'failed' is reserved for the SAM.gov API call itself
--     failing (bad URL/invalid noticeId/API error). No separate 'partial'
--     status; avoids inventing an enum value no Claim tests.
--   - `point_of_contact` / `place_of_performance` stored as raw JSONB, not
--     first-class columns — SAM.gov v2's exact sub-object shape for these is
--     an open pre-mortem question (Brief §6) not yet confirmed against a real
--     fixture. Promote to typed columns once 03-fixtures.json is captured and
--     a real field is actually queried/filtered on (per database-design.md §3).
--   - `agency` (TEXT) maps to SAM.gov's `fullParentPathName`; `psc_code` maps
--     to `classificationCode`. Both are simple scalars, safe to type now.
--   - State/local rows: `notice_id`, `agency`, `naics_code`, `psc_code`,
--     `set_aside_type`, `set_aside_description`, `point_of_contact`,
--     `place_of_performance`, `response_deadline`, `posted_date` are all NULL
--     until a later AI-triage module (out of scope here) fills them in.
--
-- Dependencies: 001_core.sql (cases, documents, jobs tables must exist)
-- ============================================================================

SET search_path TO vision, public;

-- ----------------------------------------------------------------------------
-- solicitations — The domain entity. One row per opportunity being pursued.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitations (
    id                      SERIAL PRIMARY KEY,
    external_id             UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    case_id                 INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,

    source_type             TEXT NOT NULL CHECK (source_type IN (
                                'federal', 'state', 'local'
                            )),
    title                   TEXT NOT NULL,
    url                     TEXT NOT NULL,

    -- Federal-only idempotency key. NULL for state/local (CLAIM-09).
    notice_id               TEXT UNIQUE,

    ingestion_status        TEXT NOT NULL DEFAULT 'pending' CHECK (ingestion_status IN (
                                'pending', 'fetching', 'complete', 'failed'
                            )),
    has_missing_docs        BOOLEAN NOT NULL DEFAULT FALSE,
    error_message           TEXT,

    -- SAM.gov v2 metadata (federal only; NULL until sam_fetch job completes)
    agency                  TEXT,               -- fullParentPathName
    naics_code              TEXT,
    psc_code                TEXT,               -- classificationCode
    set_aside_type          TEXT,               -- typeOfSetAside
    set_aside_description   TEXT,               -- typeOfSetAsideDescription
    point_of_contact        JSONB,              -- raw pointOfContact[] — shape TBD (see fixture)
    place_of_performance    JSONB,              -- raw placeOfPerformance — shape TBD (see fixture)
    response_deadline       TIMESTAMPTZ,
    posted_date             DATE,

    metadata                JSONB DEFAULT '{}',
    created_at              TIMESTAMPTZ DEFAULT now(),
    updated_at              TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_solicitations_case ON solicitations (case_id);
CREATE INDEX IF NOT EXISTS idx_solicitations_source_type ON solicitations (source_type);
CREATE INDEX IF NOT EXISTS idx_solicitations_ingestion_status ON solicitations (ingestion_status);
CREATE INDEX IF NOT EXISTS idx_solicitations_deadline ON solicitations (response_deadline);

-- ----------------------------------------------------------------------------
-- jobs.job_type — add 'sam_fetch' for the async SAM.gov metadata+attachment pull
-- ----------------------------------------------------------------------------
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_job_type_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_job_type_check
    CHECK (job_type IN ('ingest', 'ingest_pdf', 'ingest_docx', 'ingest_xlsx',
                         'analyze', 'export', 'ocr', 'embed', 'enrich',
                         'synthesize', 'profile_synthesis', 'capability_statement',
                         'sam_fetch', 'solicitation_triage', 'vendor_matching', 'inbound_email', 'sam_notice_import', 'other'));

-- ----------------------------------------------------------------------------
-- documents.source — add 'sam_gov' to tag SAM-fetched attachments distinctly
-- from user uploads
-- ----------------------------------------------------------------------------
ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_source_check;
ALTER TABLE documents ADD CONSTRAINT documents_source_check
    CHECK (source IN ('user_upload', 'discovery', 'data_lab', 'email',
                       'portal', 'api', 'sam_gov', 'other'));

-- ============================================================================
-- Migration Bookkeeping
-- ============================================================================
INSERT INTO schema_migrations (version, name) VALUES (17, 'add_solicitations')
ON CONFLICT (version) DO NOTHING;
