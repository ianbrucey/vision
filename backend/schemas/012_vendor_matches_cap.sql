-- ============================================================================
-- Vision — Vendor Matches Cap Increase Migration v21
-- ============================================================================
-- Raises `vendor_matches.rank`'s hard cap from 25 to 30. Automated matching
-- (backend/ingestion/vendor_matching.py::_MAX_MATCHES) still only ever
-- produces up to 25 ranked candidates — the extra 5 slots (26-30) exist
-- solely so a user can manually add vendors (T7) on top of a full
-- automated result set, without needing to evict an existing match.
--
-- See: backend/core/vendor_match.py::VendorMatchManager.attach_manual_vendor
-- Dependencies: 010_vendor_matching.sql (vendor_matches table)
-- ============================================================================

SET search_path TO vision, public;

ALTER TABLE vendor_matches DROP CONSTRAINT IF EXISTS vendor_matches_rank_check;
ALTER TABLE vendor_matches ADD CONSTRAINT vendor_matches_rank_check
    CHECK (rank BETWEEN 1 AND 30);

-- ============================================================================
-- Migration Bookkeeping
-- ============================================================================
INSERT INTO schema_migrations (version, name) VALUES (21, 'vendor_matches_cap_30')
ON CONFLICT (version) DO NOTHING;
