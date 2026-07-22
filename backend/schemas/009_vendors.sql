-- 009_vendors: Unified small business vendor registry
-- Sources: GSA Schedule holders + SBA certification database
-- Merged by UEI with SBA profile data taking priority

BEGIN;

CREATE TABLE IF NOT EXISTS vendors (
    id              BIGSERIAL PRIMARY KEY,
    vendor_name     TEXT NOT NULL,
    trade_name      TEXT,
    source          TEXT NOT NULL DEFAULT 'unknown',  -- 'sba', 'gsa', 'both'
    uei             TEXT,                           -- Unique Entity Identifier (not unique — vendor may have multiple contracts)
    cage_code       TEXT,

    -- Contact
    contact_name    TEXT,
    contact_email   TEXT,
    contact_phone   TEXT,
    website         TEXT,

    -- Location
    address_line1   TEXT,
    address_line2   TEXT,
    city            TEXT,
    state           TEXT,       -- 2-letter abbreviation preferred
    zipcode         TEXT,
    country         TEXT DEFAULT 'USA',
    county          TEXT,

    -- Business profile
    legal_structure         TEXT,
    business_types          TEXT,   -- comma-separated self-certifications
    sba_certifications      TEXT,   -- active SBA certs (VOSB, SDVOSB, WOSB, 8a, HUBZone, etc.)
    naics_codes_all         TEXT,   -- all NAICS codes, comma-separated
    naics_code_primary      TEXT,   -- primary NAICS code
    certifications_other    TEXT,   -- other relevant certifications
    capabilities            TEXT,   -- capabilities narrative (free text)
    year_established        TEXT,
    congressional_district  TEXT,
    principals              TEXT,   -- owner/principal names
    sba_profile_url         TEXT,

    -- GSA contract vehicle
    gsa_contract_number     TEXT,
    gsa_large_category      TEXT,
    gsa_sub_category        TEXT,
    gsa_source              TEXT,   -- MAS, OASIS, etc.
    gsa_closed_for_new      TEXT,
    gsa_option_end_date     TEXT,
    gsa_ultimate_end_date   TEXT,
    gsa_catalog_url         TEXT,

    -- Normalized socioeconomic flags
    is_small_business       BOOLEAN NOT NULL DEFAULT FALSE,
    is_woman_owned          BOOLEAN NOT NULL DEFAULT FALSE,
    is_veteran_owned        BOOLEAN NOT NULL DEFAULT FALSE,
    is_sdvosb               BOOLEAN NOT NULL DEFAULT FALSE,
    is_hubzone              BOOLEAN NOT NULL DEFAULT FALSE,
    is_8a                   BOOLEAN NOT NULL DEFAULT FALSE,

    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------
-- Indexes
-- ------------------------------------------------------------------

-- Lookup by UEI (primary join key)
CREATE INDEX IF NOT EXISTS idx_vendors_uei ON vendors (uei);

-- Lookup by primary NAICS
CREATE INDEX IF NOT EXISTS idx_vendors_naics_primary ON vendors (naics_code_primary);

-- B-tree on vendor name for ORDER BY (critical — avoids seq scan + sort)
CREATE INDEX IF NOT EXISTS idx_vendors_name_btree ON vendors (vendor_name);

-- Full-text search on business name + capabilities
CREATE INDEX IF NOT EXISTS idx_vendors_fts
    ON vendors
    USING GIN (to_tsvector('english', coalesce(vendor_name, '') || ' ' || coalesce(capabilities, '')));

-- GIN trigram index for LIKE/ILIKE on vendor name
CREATE INDEX IF NOT EXISTS idx_vendors_name_trgm
    ON vendors
    USING GIN (vendor_name gin_trgm_ops);

-- GIN trigram index for LIKE/ILIKE on capabilities (large text field)
CREATE INDEX IF NOT EXISTS idx_vendors_capabilities_trgm
    ON vendors
    USING GIN (capabilities gin_trgm_ops);

-- NAICS array-style search: "find all vendors with NAICS 541511"
-- Use: WHERE naics_codes_all LIKE '%541511%' (simple) or
--      WHERE string_to_array(naics_codes_all, ', ') @> ARRAY['541511']
CREATE INDEX IF NOT EXISTS idx_vendors_naics_trgm
    ON vendors
    USING GIN (naics_codes_all gin_trgm_ops);

-- Filter indexes for common opportunity-matching queries
CREATE INDEX IF NOT EXISTS idx_vendors_small_business ON vendors (is_small_business) WHERE is_small_business;
CREATE INDEX IF NOT EXISTS idx_vendors_woman_owned ON vendors (is_woman_owned) WHERE is_woman_owned;
CREATE INDEX IF NOT EXISTS idx_vendors_sdvosb ON vendors (is_sdvosb) WHERE is_sdvosb;
CREATE INDEX IF NOT EXISTS idx_vendors_hubzone ON vendors (is_hubzone) WHERE is_hubzone;
CREATE INDEX IF NOT EXISTS idx_vendors_8a ON vendors (is_8a) WHERE is_8a;

-- Location filter indexes
CREATE INDEX IF NOT EXISTS idx_vendors_state ON vendors (state);
CREATE INDEX IF NOT EXISTS idx_vendors_state_setaside ON vendors (state, is_small_business) WHERE is_small_business;

-- Source tracking
CREATE INDEX IF NOT EXISTS idx_vendors_source ON vendors (source);

-- ------------------------------------------------------------------
-- Trigger: auto-update updated_at
-- ------------------------------------------------------------------

CREATE OR REPLACE FUNCTION update_vendors_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_vendors_updated_at ON vendors;
CREATE TRIGGER trg_vendors_updated_at
    BEFORE UPDATE ON vendors
    FOR EACH ROW
    EXECUTE FUNCTION update_vendors_updated_at();

COMMIT;
