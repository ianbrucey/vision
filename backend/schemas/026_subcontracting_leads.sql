-- ============================================================================
-- Vision — Subcontracting Leads · Migration 36
-- ============================================================================
-- Stores IDV vehicles from USASpending.gov that represent subcontracting
-- opportunities: primes who hold active vehicles and are contractually
-- obligated to subcontract (plan F or G).
--
-- Dedup key: (award_id_piid, recipient_uei) — a prime can hold each
-- vehicle only once. Monthly re-imports UPDATE existing rows and INSERT
-- new ones via ON CONFLICT.
-- ============================================================================

SET search_path TO vision, public;

CREATE TABLE IF NOT EXISTS subcontracting_leads (
    id                      SERIAL PRIMARY KEY,
    external_id             UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,

    -- Vehicle identity
    award_id_piid           TEXT NOT NULL,
    parent_award_id_piid    TEXT,
    solicitation_identifier TEXT,
    idv_type                TEXT,
    multiple_or_single_award TEXT,

    -- Prime identity
    recipient_uei           TEXT NOT NULL,
    recipient_name          TEXT NOT NULL,
    recipient_parent_name   TEXT,
    recipient_city          TEXT,
    recipient_state         TEXT,

    -- Scope
    naics_code              TEXT,
    naics_description       TEXT,
    psc_code                TEXT,
    psc_description         TEXT,

    -- Value
    potential_value         NUMERIC,
    current_value           NUMERIC,

    -- Dates
    base_action_date        DATE,
    ordering_period_end     DATE,
    pop_current_end         DATE,
    pop_potential_end       DATE,

    -- Subcontracting obligation
    subcontracting_plan_code TEXT,
    subcontracting_plan     TEXT,

    -- Agency
    awarding_agency         TEXT,
    awarding_sub_agency     TEXT,

    -- Set-aside
    set_aside_type          TEXT,

    -- Pool intelligence (computed post-import)
    pool_id                 TEXT,
    pool_awardee_count      INTEGER,

    -- Prime socioeconomic flags
    is_woman_owned          BOOLEAN,
    is_sdvosb               BOOLEAN,
    is_hubzone              BOOLEAN,
    is_8a                   BOOLEAN,
    is_small_disadvantaged  BOOLEAN,
    is_minority_owned       BOOLEAN,

    -- Pipeline processing
    pipeline_status         TEXT DEFAULT 'new',
    -- new, triaged, enriched, in_outreach, responded, on_roster, declined, expired, archived
    pipeline_category       TEXT,
    -- construction, facilities, it, other
    pipeline_priority       TEXT,
    -- high, medium, low
    pipeline_priority_score INTEGER,
    -- 0–100 computed score
    pipeline_notes          TEXT,
    -- analyst notes from triage

    -- Enrichment
    last_enriched_at        TIMESTAMPTZ,
    enrichment_data         JSONB,

    -- Outreach tracking
    outreach_status         TEXT DEFAULT 'not_started',
    -- not_started, researching, drafting, sent, responded, meeting_scheduled, on_roster, declined
    outreach_last_contact   TIMESTAMPTZ,
    outreach_notes          TEXT,

    -- Source tracking
    upload_batch_id         UUID,
    source_csv              TEXT,
    usaspending_permalink   TEXT,

    created_at              TIMESTAMPTZ DEFAULT now(),
    updated_at              TIMESTAMPTZ DEFAULT now(),

    -- Dedup: a prime can hold a given vehicle only once
    UNIQUE (award_id_piid, recipient_uei)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sub_leads_status
    ON subcontracting_leads (pipeline_status);
CREATE INDEX IF NOT EXISTS idx_sub_leads_category
    ON subcontracting_leads (pipeline_category);
CREATE INDEX IF NOT EXISTS idx_sub_leads_priority
    ON subcontracting_leads (pipeline_priority);
CREATE INDEX IF NOT EXISTS idx_sub_leads_plan
    ON subcontracting_leads (subcontracting_plan_code);
CREATE INDEX IF NOT EXISTS idx_sub_leads_uei
    ON subcontracting_leads (recipient_uei);
CREATE INDEX IF NOT EXISTS idx_sub_leads_ordering
    ON subcontracting_leads (ordering_period_end);
CREATE INDEX IF NOT EXISTS idx_sub_leads_pool
    ON subcontracting_leads (pool_id);
CREATE INDEX IF NOT EXISTS idx_sub_leads_naics
    ON subcontracting_leads (naics_code);
CREATE INDEX IF NOT EXISTS idx_sub_leads_upload_batch
    ON subcontracting_leads (upload_batch_id);

INSERT INTO schema_migrations (version, name) VALUES (36, 'subcontracting_leads')
ON CONFLICT (version) DO NOTHING;
