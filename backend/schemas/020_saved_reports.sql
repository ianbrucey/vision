-- ============================================================================
-- Vision — Saved Reports Migration v29
-- ============================================================================
-- Persists named filter presets for the Forecasts and Sam Notices tabs.
-- A report stores the query_filters JSONB that can be passed directly to
-- query_forecast_opportunities or query_sam_notices — no transformation needed.
-- ============================================================================

SET search_path TO vision, public;

CREATE TABLE IF NOT EXISTS saved_reports (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    name            TEXT NOT NULL,
    data_source     TEXT NOT NULL CHECK (data_source IN ('forecasts', 'sam_notices')),
    query_filters   JSONB NOT NULL DEFAULT '{}',
    sort_by         TEXT,
    sort_dir        TEXT DEFAULT 'ASC' CHECK (sort_dir IN ('ASC', 'DESC')),
    created_by      TEXT DEFAULT 'agent' CHECK (created_by IN ('agent', 'user')),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_saved_reports_case_source
    ON saved_reports (case_id, data_source);

INSERT INTO schema_migrations (version, name) VALUES (29, 'saved_reports')
ON CONFLICT (version) DO NOTHING;
