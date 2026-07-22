-- ============================================================================
-- Vision — SAM.gov Databank Notices Migration v26
-- ============================================================================
-- Stores rows from the SAM.gov databank CSV export (Contract_Notice_Details.csv
-- and similar bulk extracts). Supports free-text search via tsvector and
-- dynamic filtering via JSONB condition objects.
-- ============================================================================

SET search_path TO vision, public;

CREATE TABLE IF NOT EXISTS sam_notices (
    id                      SERIAL PRIMARY KEY,
    external_id             UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,

    -- Core notice fields
    notice_id               TEXT,
    opportunity_title       TEXT NOT NULL,
    contract_opportunity_type TEXT,
    description             TEXT,
    status                  TEXT,

    -- Dates
    current_response_date   TIMESTAMPTZ,
    last_published_date     TIMESTAMPTZ,
    inactive_date           TIMESTAMPTZ,
    last_updated_date       TIMESTAMPTZ,

    -- Classification
    naics_code              TEXT,
    naics_description       TEXT,
    psc_code                TEXT,
    current_set_aside       TEXT,
    current_set_aside_code  TEXT,
    initiative              TEXT,

    -- Agency
    contracting_office      TEXT,
    procurement_aac_code    TEXT,
    sub_tier_code           TEXT,
    sub_tier_name           TEXT,

    -- Place of performance
    pop_country             TEXT,
    pop_zip                 TEXT,
    pop_city                TEXT,
    pop_state               TEXT,

    -- POC
    poc_name                TEXT,
    poc_email               TEXT,

    -- Vendor / awardee (populated on award notices)
    awardee_uei             TEXT,
    awardee_name            TEXT,

    -- Attachments
    attachment_count        INTEGER,
    ivl_enabled             BOOLEAN,

    -- Full-text search
    search_vector           TSVECTOR,

    -- Metadata
    upload_batch_id         UUID,
    source_csv              TEXT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sam_notices_naics
    ON sam_notices (naics_code);
CREATE INDEX IF NOT EXISTS idx_sam_notices_set_aside
    ON sam_notices (current_set_aside_code);
CREATE INDEX IF NOT EXISTS idx_sam_notices_type
    ON sam_notices (contract_opportunity_type);
CREATE INDEX IF NOT EXISTS idx_sam_notices_status
    ON sam_notices (status);
CREATE INDEX IF NOT EXISTS idx_sam_notices_agency
    ON sam_notices (sub_tier_name);
CREATE INDEX IF NOT EXISTS idx_sam_notices_response_date
    ON sam_notices (current_response_date);
CREATE INDEX IF NOT EXISTS idx_sam_notices_pop_state
    ON sam_notices (pop_state);
CREATE INDEX IF NOT EXISTS idx_sam_notices_search
    ON sam_notices USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_sam_notices_upload_batch
    ON sam_notices (upload_batch_id);

-- Trigger to keep search_vector updated
CREATE OR REPLACE FUNCTION sam_notices_search_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.opportunity_title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.naics_code, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.naics_description, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.sub_tier_name, '')), 'D') ||
        setweight(to_tsvector('english', COALESCE(NEW.contracting_office, '')), 'D') ||
        setweight(to_tsvector('english', COALESCE(NEW.poc_name, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sam_notices_search ON sam_notices;
CREATE TRIGGER trg_sam_notices_search
    BEFORE INSERT OR UPDATE ON sam_notices
    FOR EACH ROW EXECUTE FUNCTION sam_notices_search_update();

INSERT INTO schema_migrations (version, name) VALUES (26, 'sam_notices')
ON CONFLICT (version) DO NOTHING;
