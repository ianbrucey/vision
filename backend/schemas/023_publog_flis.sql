-- ============================================================================
-- Vision — Publog FLIS Database Migration v33
-- ============================================================================
-- Full Federal Logistics Information System (FLIS) from DLA Publog DVD.
-- Extracted via Decomp.exe (Wine) from the July 2026 PUB LOG DVD.
-- ============================================================================

SET search_path TO vision, public;

-- ---------------------------------------------------------------------------
-- 1. FLIS NSN Master — every NSN in the federal catalog
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS publog_flis_nsn (
    id              BIGSERIAL PRIMARY KEY,
    fsc             TEXT NOT NULL,           -- Federal Supply Class (4 chars)
    niin            TEXT NOT NULL,           -- National Item Identification Number (9 chars)
    inc             TEXT,                    -- Item Name Code (5 chars)
    item_name       TEXT,                    -- Approved Item Name
    sos             TEXT,                    -- Source of Supply
    end_item_name   TEXT,                    -- End item application
    cancelled_niin  TEXT,                    -- Replacement NSN info
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_publog_nsn_niin
    ON publog_flis_nsn (niin);
CREATE INDEX IF NOT EXISTS idx_publog_nsn_fsc
    ON publog_flis_nsn (fsc);
CREATE INDEX IF NOT EXISTS idx_publog_nsn_inc
    ON publog_flis_nsn (inc);
CREATE INDEX IF NOT EXISTS idx_publog_nsn_item_name
    ON publog_flis_nsn USING gin (to_tsvector('english', COALESCE(item_name, '')));

-- ---------------------------------------------------------------------------
-- 2. FLIS Management — unit prices, MOE, AAC per NSN/service
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS publog_flis_management (
    id              BIGSERIAL PRIMARY KEY,
    niin            TEXT NOT NULL,           -- NIIN (9 chars)
    effective_date  TEXT,                    -- Date record became effective
    moe             TEXT,                    -- Major Organizational Entity (service code)
    aac             TEXT,                    -- Acquisition Advice Code
    sos             TEXT,                    -- Source of Supply
    sosm            TEXT,                    -- SOS modifier
    ui              TEXT,                    -- Unit of Issue
    ui_conv_fac     TEXT,                    -- UI conversion factor
    unit_price      TEXT,                    -- Unit price (may have embedded precision)
    qup             TEXT,                    -- Quantity per Unit Pack
    ciic            TEXT,                    -- Controlled Item Inventory Code
    slc             TEXT,                    -- Shelf Life Code
    rep_rec_code    TEXT,                    -- Repair/Recurring code
    mgmt_ctl        TEXT,                    -- Management control number
    rep_net_pr      TEXT,                    -- Replacement net price
    usc             TEXT,                    -- Using Service Code
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_publog_mgmt_niin
    ON publog_flis_management (niin);
CREATE INDEX IF NOT EXISTS idx_publog_mgmt_moe
    ON publog_flis_management (moe);
CREATE INDEX IF NOT EXISTS idx_publog_mgmt_aac
    ON publog_flis_management (aac);

-- ---------------------------------------------------------------------------
-- 3. FLIS Identification — DMIL, HMIC, criticality, IUID, etc.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS publog_flis_identification (
    id              BIGSERIAL PRIMARY KEY,
    niin            TEXT NOT NULL,           -- NIIN (9 chars)
    inc             TEXT,                    -- Item Name Code
    pinc            TEXT,                    -- Parent INC
    crit_cd         TEXT,                    -- Criticality Code
    ii              TEXT,                    -- Issue/Item type indicator
    rpd_mrc         TEXT,                    -- Reference/Partial Descriptive MRC
    dmil            TEXT,                    -- Demilitarization code
    dmil_int_cd     TEXT,                    -- Demil integrity code
    niin_asgmt      TEXT,                    -- NIIN assignment date
    pmic            TEXT,                    -- Precious Metals Indicator
    adp             TEXT,                    -- ADP equipment code
    esd_emi         TEXT,                    -- ESD/EMI code
    hmic            TEXT,                    -- Hazardous Material Indicator
    hcc             TEXT,                    -- Hazard Characteristic Code
    schedule_b      TEXT,                    -- Schedule B export code
    enac            TEXT,                    -- ENAC code
    iuid_indicator  TEXT,                    -- IUID indicator
    lst_kwn_sos     TEXT,                    -- Last known SOS
    fedmall         TEXT,                    -- FedMall indicator
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_publog_ident_niin
    ON publog_flis_identification (niin);
CREATE INDEX IF NOT EXISTS idx_publog_ident_dmil
    ON publog_flis_identification (dmil);
CREATE INDEX IF NOT EXISTS idx_publog_ident_hmic
    ON publog_flis_identification (hmic);

-- ---------------------------------------------------------------------------
-- 4. MOE Rule — AMC/AMSC acquisition method codes
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS publog_moe_rule (
    id              BIGSERIAL PRIMARY KEY,
    niin            TEXT NOT NULL,           -- NIIN (9 chars)
    moe_rl          TEXT,                    -- MOE Rule number
    moe_cd          TEXT,                    -- MOE Code
    amc             TEXT,                    -- Acquisition Method Code
    amsc            TEXT,                    -- Acquisition Method Suffix Code
    nimsc           TEXT,                    -- NIIN Item Management Code
    dt_asgnd        TEXT,                    -- Date assigned
    imc             TEXT,                    -- Item Management Code
    imca            TEXT,                    -- IMC Activity
    aac             TEXT,                    -- Acquisition Advice Code
    pica            TEXT,                    -- Primary Inventory Control Activity
    pica_loa        TEXT,                    -- PICA Level of Authority
    sica            TEXT,                    -- Secondary Inventory Control Activity
    sica_loa        TEXT,                    -- SICA Level of Authority
    auth_collab     TEXT,                    -- Authorized Collaborator
    supp_collab     TEXT,                    -- Supporting Collaborator
    dsor            TEXT,                    -- Depot Source of Repair
    fmr_moe_rl      TEXT,                    -- Former MOE Rule
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_publog_moe_niin
    ON publog_moe_rule (niin);
CREATE INDEX IF NOT EXISTS idx_publog_moe_amc
    ON publog_moe_rule (amc);

-- ---------------------------------------------------------------------------
-- 5. CAGE — Commercial and Government Entity codes
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS publog_cage (
    id              BIGSERIAL PRIMARY KEY,
    cage_code       TEXT NOT NULL,           -- CAGE code (5 chars)
    cage_status     TEXT,                    -- Status (A=Active, etc.)
    type            TEXT,                    -- Entity type (A=US, F=Foreign, etc.)
    cao             TEXT,                    -- Contract Administration Office
    company         TEXT,                    -- Company name
    city            TEXT,                    -- City
    state_province  TEXT,                    -- State or Province
    zip_postal_zone TEXT,                    -- ZIP/Postal code
    country         TEXT,                    -- Country
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_publog_cage_code
    ON publog_cage (cage_code);
CREATE INDEX IF NOT EXISTS idx_publog_cage_company
    ON publog_cage USING gin (to_tsvector('english', COALESCE(company, '')));

-- ---------------------------------------------------------------------------
-- 6. FLIS Part — Part number to NSN cross-reference
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS publog_flis_part (
    id              BIGSERIAL PRIMARY KEY,
    niin            TEXT NOT NULL,           -- NIIN (9 chars)
    part_number     TEXT,                    -- Reference/part number
    cage_code       TEXT,                    -- CAGE code for manufacturer
    cage_status     TEXT,                    -- CAGE status
    rncc            TEXT,                    -- Reference Number Category Code
    rnvc            TEXT,                    -- Reference Number Variation Code
    dac             TEXT,                    -- Document Availability Code
    rnaac           TEXT,                    -- Reference Number Action Activity Code
    rnfc            TEXT,                    -- Reference Number Format Code
    rnsc            TEXT,                    -- Reference Number Status Code
    rnjc            TEXT,                    -- Reference Number Justification Code
    sadc            TEXT,                    -- Source Approval Data Code
    hcc             TEXT,                    -- Hazard Characteristic Code
    msds            TEXT,                    -- MSDS ID
    medals          TEXT,                    -- Medals indicator
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_publog_part_niin
    ON publog_flis_part (niin);
CREATE INDEX IF NOT EXISTS idx_publog_part_cage
    ON publog_flis_part (cage_code);
CREATE INDEX IF NOT EXISTS idx_publog_part_number
    ON publog_flis_part (part_number);
CREATE INDEX IF NOT EXISTS idx_publog_part_rncc
    ON publog_flis_part (rncc);

INSERT INTO schema_migrations (version, name) VALUES (33, 'publog_flis_tables')
ON CONFLICT (version) DO NOTHING;
