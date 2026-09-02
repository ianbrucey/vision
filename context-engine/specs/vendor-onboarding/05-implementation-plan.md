# 05-implementation-plan — Vendor Onboarding (Ticket 0 artifacts → Ticket 1 build)

> Sequencing: Backend-Out (DB → API → UI). Atomic tickets; each completes in isolation.

## Ticket 1 — MTA e-signature flow (THIS BUILD)

| Step | File(s) | Acceptance |
|---|---|---|
| 1. Migration | `backend/schemas/032_vendor_teaming_agreements.sql` | Idempotent; `documents.case_id` nullable; table + indexes + partial unique index |
| 2. Schema apply | `backend/core/db.py` — `ensure_vendor_agreements_schema()` + `__all__` | Applied at API startup with 030/031 |
| 3. Wiring | `backend/api/main.py` — `_apply_schemas()` call + router include | Startup applies 032; routes live |
| 4. Deps | `backend/requirements.txt` — `pymupdf>=1.24` | Declared (was runtime-only) |
| 5. Core | `backend/core/vendor_agreements.py` — `VendorAgreementManager` (render, sign, get_status, list) | Sign creates row + PDF; idempotent; consent enforced; audit fields populated |
| 6. Gate | `backend/auth/__init__.py` — `require_mta` | 403 unsigned vendor; staff pass |
| 7. Routes | `backend/api/routes/vendor_agreements.py` — GET/POST mta, admin list | Per 02-api-contract.json |
| 8. API client | `frontend/src/lib/api.ts` — MtaAgreement, getMyMtaStatus, signMyMta | Types match contract |
| 9. Modal | `frontend/src/components/MtaSigningModal.tsx` | Per 04-ui-specs |
| 10. Portal | `frontend/src/app/portal/page.tsx` — banners + wiring | State A/B per 04-ui-specs |
| 11. Docs | `context-engine/domain-contexts/vendor-portal.md` update | MTA section current |

Verdict: see Verification section of the master plan (`/Users/ianbruce/.claude/plans/frolicking-gliding-cherny.md`) — API-level curl flows 1–8 + frontend flow.

## Ticket 2 — Onboarding document uploads (NEXT)

- Vendor uploads license / bonding / insurance / certifications → `vendor_profiles.license_doc_id` etc. (documents rows now case-less — unblocked by 032)
- Admin review surface + `verified_at` write; status transition to active
- Requires: portal Profile card activation, upload UI (DocumentAttachButton pattern), admin verification UI

## Ticket 3 — BSTA flow (LATER)

- `vendor_teaming_agreements` rows `agreement_type='bsta'`; decision tree (solicitation type → BSTA required), LoS math (FAR 52.219-14 thresholds per contract type), similarly-situated computation (needs `is_small_business`/`sb_program_status[]` profile fields first — schema additions)

## Ticket 4 — Subcontract + quote requests (LATER)

- Subcontract rows on award; quote request assignment to vendors gated by `require_mta`
