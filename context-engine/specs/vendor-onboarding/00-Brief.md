# 00-Brief — Vendor Onboarding: Master Teaming Agreement (MTA) E-Signature

> State: APPROVED 2026-08-16 · Type: vendor portal / compliance · Ticket 0 of vendor-onboarding

## The Problem

Justice Quest (JQ) bids federal solicitations using subcontractor vendor experience, but the vendor portal contains **no legal mechanism** authorizing JQ to market on a vendor's behalf or use their past performance. Using vendor experience in proposals without written authorization is misrepresentation. The three-contract legal stack exists as templates (`context-engine/templates/vendor-contracts/`): MTA (evergreen, at registration), BSTA (per-bid, before formal offers), Subcontract (per-award).

## The Claim

Vendors execute a Master Teaming Agreement (Contract 1) in-portal before JQ may market on their behalf or use their capabilities/past performance. Quote requests are blocked until the MTA is executed.

## Success Verdict (how we know it worked)

1. `POST /api/vendors/mta/sign` with `consent=true` + typed name creates an executed `vendor_teaming_agreements` row with full audit trail (name, title, IP, UA, content hash, template version, timestamps).
2. A signed PDF artifact exists in the documents pipeline (MinIO + `documents` row, `case_id` NULL) and renders via the existing preview endpoint.
3. `require_mta` dependency returns 403 for vendors without an executed MTA; non-vendor roles pass.
4. Portal shows warning banner when unsigned, success banner + viewable signed PDF when executed. Persists across sessions.

## Decisions (locked)

- **E-signature: in-house typed name + explicit checkbox.** Valid under E-SIGN Act (15 U.S.C. §7001) + Georgia UETA (O.C.G.A. §10-12) — validity from intent + attribution + audit trail, not medium. No DocuSeal (free AGPL tier has no API; portal embedding requires paid Pro on-prem + $0.20/doc; AGPL restricts customization). No canvas (weakest evidence, mobile-hostile).
- **Scope: MTA signing flow only.** Onboarding doc uploads (license/bonding/insurance) = Ticket 2.
- **Gate derivation:** no `vendor_profiles.mta_executed_at` column; gate = executed `vendor_teaming_agreements` row (single source of truth, no drift).

## Out of Scope (this ticket)

- BSTA / Subcontract flows (same table, later tickets)
- Vendor compliance document uploads (Ticket 2)
- Quote requests (future; gated by `require_mta`)
- Email-based signing / DocuSeal
