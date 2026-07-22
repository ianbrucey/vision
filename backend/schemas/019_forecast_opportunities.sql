-- ============================================================================
-- Vision — Acquisition Gateway Forecast Opportunities Migration v28
-- ============================================================================
-- Stores rows scraped from the Acquisition Gateway forecast tool. The data
-- source is rendered HTML (the site is an Angular SPA — no CSV export).
-- Fields match the Acquisition Gateway forecast card layout.
-- ============================================================================

SET search_path TO vision, public;

CREATE TABLE IF NOT EXISTS forecast_opportunities (
    id                      SERIAL PRIMARY KEY,
    external_id             UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,

    -- Core fields (from HTML parser)
    title                   TEXT NOT NULL DEFAULT '(no title)',
    description             TEXT,
    source_url              TEXT,

    -- Agency / office
    agency                  TEXT,
    office                  TEXT,

    -- Classification
    naics_code              TEXT,
    naics_description       TEXT,

    -- Set-aside
    set_aside               TEXT,

    -- Location / performance
    place_of_performance    TEXT,
    period_of_performance   TEXT,

    -- Value
    estimated_value_text    TEXT,

    -- Timeline
    fiscal_year             TEXT,
    created_date            TEXT,
    last_updated_date       TEXT,

    -- Full-text search
    search_vector           TSVECTOR,

    -- Metadata
    upload_batch_id         UUID,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_forecast_naics
    ON forecast_opportunities (naics_code);
CREATE INDEX IF NOT EXISTS idx_forecast_agency
    ON forecast_opportunities (agency);
CREATE INDEX IF NOT EXISTS idx_forecast_fiscal_year
    ON forecast_opportunities (fiscal_year);
CREATE INDEX IF NOT EXISTS idx_forecast_set_aside
    ON forecast_opportunities (set_aside);
CREATE INDEX IF NOT EXISTS idx_forecast_search
    ON forecast_opportunities USING GIN (search_vector);

-- Auto-update search vector
CREATE OR REPLACE FUNCTION forecast_search_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.agency, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.naics_code, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.naics_description, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.office, '')), 'D') ||
        setweight(to_tsvector('english', COALESCE(NEW.set_aside, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_forecast_search ON forecast_opportunities;
CREATE TRIGGER trg_forecast_search
    BEFORE INSERT OR UPDATE ON forecast_opportunities
    FOR EACH ROW EXECUTE FUNCTION forecast_search_update();

INSERT INTO schema_migrations (version, name) VALUES (28, 'forecast_opportunities')
ON CONFLICT (version) DO NOTHING;
