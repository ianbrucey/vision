-- ============================================================================
-- Vision — Manual Vendor Matches Migration v20
-- ============================================================================
-- Extends `vendor_matches.naics_match_type` to allow 'manual' — vendors
-- added directly by the user via VendorMatchesTab (T7 — inline vendor
-- creation), bypassing the automated candidate-pool/ranking pipeline.
--
-- See: backend/core/vendor_match.py::VendorMatchManager.attach_manual_vendor
-- Dependencies: 010_vendor_matching.sql (vendor_matches table)
-- ============================================================================

SET search_path TO vision, public;

ALTER TABLE vendor_matches DROP CONSTRAINT IF EXISTS vendor_matches_naics_match_type_check;
ALTER TABLE vendor_matches ADD CONSTRAINT vendor_matches_naics_match_type_check
    CHECK (naics_match_type IN ('exact', 'family', 'capability_only', 'manual'));

-- ============================================================================
-- Migration Bookkeeping
-- ============================================================================
INSERT INTO schema_migrations (version, name) VALUES (20, 'vendor_matches_manual_type')
ON CONFLICT (version) DO NOTHING;
