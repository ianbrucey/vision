-- ============================================================================
-- Vision — NAICS Code Lookup Table Migration v28
-- ============================================================================
-- Adds a static reference table of 2022 NAICS codes (6-digit level) with
-- titles, for display labels and filtering on solicitations. The table is
-- seeded from the U.S. Census Bureau's official 2022 NAICS list.
--
-- Design decisions:
--   - 6-digit codes only (1012 rows) — SAM.gov always returns 6-digit NAICS.
--   - `code` is TEXT PRIMARY KEY (e.g., "517810"), not INTEGER, because NAICS
--     codes have leading zeros in some representations (though not at 6-digit).
--   - This is pure reference data — no FKs reference it. It exists solely for
--     JOINs in SELECT queries.
--   - The seed data is loaded by 028's companion Python seed script, not
--     inline in this SQL file (the data comes from an Excel file).
--
-- Dependencies: none (standalone reference table)
-- ============================================================================

SET search_path TO vision, public;

CREATE TABLE IF NOT EXISTS naics_codes (
    code  TEXT PRIMARY KEY,
    title TEXT NOT NULL
);

-- ============================================================================
-- Migration Bookkeeping
-- ============================================================================
INSERT INTO schema_migrations (version, name) VALUES (28, 'add_naics_codes')
ON CONFLICT (version) DO NOTHING;
