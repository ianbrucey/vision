-- ============================================================================
-- Vision — DIBBS RFQ Opportunities Migration v32
-- ============================================================================
-- DLA Internet Bid Board System (DIBBS) RFQ search results.
-- Parsed from unified CSV export (dibbs_rfq_unified.csv).
-- ============================================================================

SET search_path TO vision, public;

CREATE TABLE IF NOT EXISTS dibbs_rfqs (
    id              SERIAL PRIMARY KEY,
    external_id     UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    row_num         INTEGER,
    nsn             TEXT,
    mil_spec        TEXT,
    nomenclature    TEXT,
    tech_docs       TEXT,
    solicitation    TEXT NOT NULL,
    status          TEXT,
    purchase_request TEXT,
    qty             INTEGER,
    issued          TEXT,
    return_by       TEXT,
    search_vector   TSVECTOR,
    fsc_code        TEXT,
    upload_batch_id UUID,
    source_file     TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dibbs_solicitation
    ON dibbs_rfqs (solicitation);
CREATE INDEX IF NOT EXISTS idx_dibbs_nsn ON dibbs_rfqs (nsn);
CREATE INDEX IF NOT EXISTS idx_dibbs_fsc ON dibbs_rfqs (fsc_code);
CREATE INDEX IF NOT EXISTS idx_dibbs_return_by ON dibbs_rfqs (return_by);
CREATE INDEX IF NOT EXISTS idx_dibbs_status ON dibbs_rfqs (status);
CREATE INDEX IF NOT EXISTS idx_dibbs_search ON dibbs_rfqs USING GIN (search_vector);

CREATE OR REPLACE FUNCTION dibbs_search_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.nomenclature, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.nsn, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.solicitation, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_dibbs_search ON dibbs_rfqs;
CREATE TRIGGER trg_dibbs_search
    BEFORE INSERT OR UPDATE ON dibbs_rfqs
    FOR EACH ROW EXECUTE FUNCTION dibbs_search_update();

INSERT INTO schema_migrations (version, name) VALUES (32, 'dibbs_rfqs')
ON CONFLICT (version) DO NOTHING;
