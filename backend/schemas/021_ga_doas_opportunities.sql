-- ============================================================================
-- Vision — GA DOAS Opportunities Migration v30
-- ============================================================================
-- Georgia Department of Administrative Services procurement opportunities.
-- Parsed from rendered HTML tables at ssl.doas.state.ga.us/gpr.
-- ============================================================================

SET search_path TO vision, public;

CREATE TABLE IF NOT EXISTS ga_doas_opportunities (
    id                  SERIAL PRIMARY KEY,
    external_id         UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    event_id            TEXT NOT NULL,
    event_url           TEXT,
    title               TEXT NOT NULL DEFAULT '(no title)',
    government_entity   TEXT,
    start_date          TEXT,
    end_date            TEXT,
    ends_in             TEXT,
    status              TEXT,
    search_vector       TSVECTOR,
    source_file         TEXT,
    upload_batch_id     UUID,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ga_doas_event_id
    ON ga_doas_opportunities (event_id);
CREATE INDEX IF NOT EXISTS idx_ga_doas_entity
    ON ga_doas_opportunities (government_entity);
CREATE INDEX IF NOT EXISTS idx_ga_doas_status
    ON ga_doas_opportunities (status);
CREATE INDEX IF NOT EXISTS idx_ga_doas_search
    ON ga_doas_opportunities USING GIN (search_vector);

CREATE OR REPLACE FUNCTION ga_doas_search_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.government_entity, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.event_id, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ga_doas_search ON ga_doas_opportunities;
CREATE TRIGGER trg_ga_doas_search
    BEFORE INSERT OR UPDATE ON ga_doas_opportunities
    FOR EACH ROW EXECUTE FUNCTION ga_doas_search_update();

INSERT INTO schema_migrations (version, name) VALUES (31, 'ga_doas_opportunities')
ON CONFLICT (version) DO NOTHING;
