-- ============================================================================
-- Vision — DLA Batch Search Migration v34
-- ============================================================================
-- Enriched DIBBS solicitation data from the dibbs-enrich skill.
-- Loaded from enriched CSV output.
-- ============================================================================

SET search_path TO vision, public;

CREATE TABLE IF NOT EXISTS dla_batch_search (
    id                  BIGSERIAL PRIMARY KEY,
    nsn                 TEXT NOT NULL,
    fsc                 TEXT,
    niin                TEXT,
    nomenclature        TEXT,
    inc                 TEXT,
    sos                 TEXT,
    cancelled           TEXT,
    cancelled_niin      TEXT,
    amc                 TEXT,
    amsc                TEXT,
    aac                 TEXT,
    competable          TEXT,
    competability_notes TEXT,
    unit_price          NUMERIC,
    ui                  TEXT,
    slc                 TEXT,
    ciic                TEXT,
    dmil                TEXT,
    hmic                TEXT,
    hcc                 TEXT,
    crit_cd             TEXT,
    approved_cage       TEXT,
    approved_part       TEXT,
    cage_company        TEXT,
    cage_city           TEXT,
    cage_state          TEXT,
    cage_status         TEXT,
    vendor_name         TEXT,
    contact_name        TEXT,
    contact_email       TEXT,
    contact_phone       TEXT,
    website             TEXT,
    is_small_business   TEXT,
    is_woman_owned      TEXT,
    is_veteran_owned    TEXT,
    qty                 TEXT,
    solicitation        TEXT,
    purchase_request    TEXT,
    source_file         TEXT,
    search_vector       TSVECTOR,
    upload_batch_id     UUID DEFAULT gen_random_uuid(),
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Indexes for fast search/filter
CREATE INDEX IF NOT EXISTS idx_dla_nsn        ON dla_batch_search (nsn);
CREATE INDEX IF NOT EXISTS idx_dla_fsc        ON dla_batch_search (fsc);
CREATE INDEX IF NOT EXISTS idx_dla_competable ON dla_batch_search (competable);
CREATE INDEX IF NOT EXISTS idx_dla_solicitation ON dla_batch_search (solicitation);
CREATE INDEX IF NOT EXISTS idx_dla_vendor     ON dla_batch_search (vendor_name);
CREATE INDEX IF NOT EXISTS idx_dla_price      ON dla_batch_search (unit_price);
CREATE INDEX IF NOT EXISTS idx_dla_amc        ON dla_batch_search (amc);
CREATE INDEX IF NOT EXISTS idx_dla_niin       ON dla_batch_search (niin);
CREATE INDEX IF NOT EXISTS idx_dla_source     ON dla_batch_search (source_file);
CREATE INDEX IF NOT EXISTS idx_dla_search     ON dla_batch_search USING GIN (search_vector);

-- Auto-update search vector on insert/update
CREATE OR REPLACE FUNCTION dla_batch_search_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.nomenclature, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.nsn, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.vendor_name, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.cage_company, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.solicitation, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.fsc, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_dla_search ON dla_batch_search;
CREATE TRIGGER trg_dla_search
    BEFORE INSERT OR UPDATE ON dla_batch_search
    FOR EACH ROW EXECUTE FUNCTION dla_batch_search_update();

-- View: uniquified by NSN+solicitation (deduped)
CREATE OR REPLACE VIEW vision.dla_batch_unique AS
SELECT DISTINCT ON (nsn, solicitation) *
FROM vision.dla_batch_search
ORDER BY nsn, solicitation, unit_price DESC NULLS LAST;

INSERT INTO schema_migrations (version, name) VALUES (34, 'dla_batch_search')
ON CONFLICT (version) DO NOTHING;
