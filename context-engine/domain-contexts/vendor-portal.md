# Vendor Portal — Registration, Profiles, Roles, and Teaming Agreements

> **Purpose:** Onboard developers/agents to the vendor portal subsystem: vendor user role, vendor profiles, registration flow, the /portal route separation, and the Master Teaming Agreement (MTA) e-signature gate.
> **Last Updated:** 2026-08-16

---

## 1. Business Overview

### What This Domain Does

Vision acts as a **prime intermediary** — bidding on federal solicitations using the experience of subcontractor vendors. Vendors register (self-service or created internally by admin), build a business profile (licenses, bonding, capabilities), and will eventually receive quote requests for specific solicitations.

### Business Model

- **Vendor types** (3): `individual` (solo practitioner), `service` (construction/IT/consulting), `manufacturer` (product/equipment supplier). The type determines which profile fields matter (e.g., bonding capacity is irrelevant to manufacturers).
- **Vendor lifecycle**: `pending` (registered, awaiting review) → `active` (approved) / `suspended` / `inactive`.
- **Route separation**: vendors land on `/portal/*` and must never see internal pages (`/solicitations`, `/settings`, `/my-work`).

### User Stories This Supports

- As a subcontractor, I register from the landing page with my business name and vendor type, then sign in to my own portal.
- As an admin, I create vendor accounts internally from Settings and manage their role and status.
- (Future) As a vendor, I receive quote requests for solicitations and respond from my portal.

---

## 2. Data Model

### users.role — now three values

| Role | Landing route | Access |
|---|---|---|
| `user` | `/solicitations` | Internal: solicitations, cases, quotes tab, my-work |
| `vendor` | `/portal` | Vendor portal only |
| `admin` | `/solicitations` | Everything + `/settings` + `/api/admin/*` |

**Note:** The `users.role` CHECK constraint originally allowed only `user`/`admin`. Migration `031_fix_users_role_vendor.sql` drops and re-adds it with `vendor` included.

### Teaming agreements (schema 032) — MTA e-signature gate

- **`vendor_teaming_agreements`** table holds all three contract types (`mta`/`bsta`/`subcontract`); MTA rows have `solicitation_id` NULL, `status='executed'`, `executed_at`, `expires_at` (+2y, informational — MTA auto-renews per Art. 8.1; not gated this build).
- **E-signature**: in-portal typed name + explicit consent checkbox. Legal basis E-SIGN Act (15 U.S.C. §7001) + GA UETA (O.C.G.A. §10-12). The audit row (`signed_name`, `signed_title`, `signed_ip`, `signed_user_agent`, `content_hash`, `template_version`, `executed_at`) IS the legal evidence; the PDF image alone is not.
- **`content_hash`** = sha256 of render pass-1 bytes with the random trailer /ID stripped (signature block + Exhibit A included); the PDF then appends `Document SHA-256: {hash}` in pass 2. Verification = re-render pass 1 from stored inputs (profile, signer, `executed_at`→UTC) → strip /ID → sha256 must equal the stored hash (byte-exact; `executed_at` is derived in Python at sign time precisely for this).
- **Gate**: there is NO `vendor_profiles.mta_executed_at` column — the gate derives from an executed MTA row (single source of truth). `require_mta` dependency in `backend/auth/__init__.py` blocks vendors without one (403); JQ staff roles pass. Future vendor-facing quote endpoints use `Depends(require_mta)`.
- **Signed PDF storage**: `documents` rows with `case_id` NULL + `vendor_user_id` set (migration 032 relaxed `case_id NOT NULL` and extended `documents_owner_check` to `case_id | talent_id | vendor_user_id`). MinIO key `mta/signed/{uuid}/...pdf`; unsigned previews at `mta/unsigned/{user_id}.pdf` (regenerated per request, 1h presigned URL).
- **MTA template**: `context-engine/templates/vendor-contracts/01-master-teaming-agreement.md`, filled from `vendor_profiles` + users.email by `core/vendor_agreements.py`. `TEMPLATE_VERSION` constant — bump when the template changes. BSTA/subcontract templates exist (02/03) but their flows are not built yet.
- Registration now accepts `cage_code`, `tax_id`, `naics_codes` (optional) so the MTA party block is complete at first render.

### vendor_profiles table (schema 030)

One profile per vendor user (`user_id` UNIQUE):

| Group | Columns |
|---|---|
| Identity | `business_name` (NOT NULL), `vendor_type` (CHECK: individual/service/manufacturer), `uei`, `cage_code`, `tax_id` |
| Capabilities | `naics_codes` (text[]), `capabilities` (text), `website`, `phone` |
| Address | `address_line1/2`, `city`, `state`, `zip` |
| Compliance docs | `license_doc_id`, `bonding_doc_id`, `insurance_doc_id`, `certification_doc_ids` (integer[]) — all reference `documents(id)` |
| Financial | `bonding_capacity`, `annual_revenue`, `employee_count`, `years_in_business` |
| Status | `status` (pending/active/suspended/inactive), `verified_at` |

---

## 3. API Endpoints

```
POST   /api/vendors/register     — self-service: creates users row (role=vendor) + profile in one call
GET    /api/vendors/profile      — vendor's own profile (404 if none)
PATCH  /api/vendors/profile      — vendor updates own profile; only admin can change `status`
GET    /api/vendors/profiles     — list all (admin or internal `user` role; vendors get 403)
GET    /api/vendors/mta          — vendor MTA status; unsigned → presigned preview PDF URL
POST   /api/vendors/mta/sign     — execute MTA (typed name + title + consent=true); 201 new / 200 idempotent
GET    /api/vendors/mta-agreements — list all agreements (admin only)
```

Auth flow uses the existing JWT system (`auth/__init__.py`). `VALID_ROLES = {"user", "admin", "vendor"}` is enforced in `create_user()`.

---

## 4. Frontend Routes

| Route | Access | Purpose |
|---|---|---|
| `/vendor-register` | Public | Registration form: business name, vendor type (radio cards), username/password/email/phone |
| `/portal` | Vendor only | Blank dashboard: greets business name, shows type + status; placeholder cards (Profile, Quote Requests, History) |
| `/settings` | Admin only | User management — role dropdown now includes "Vendor" (blue badge) |

### Routing rules (AuthProvider)

- Authed vendor hitting `/` or `/login` → redirected to `/portal`
- Authed non-vendor hitting `/` or `/login` → redirected to `/solicitations`
- Non-vendor hitting `/portal` → bounced to `/solicitations`
- Unauthed hitting `/portal` → bounced to `/login`

---

## 5. Key Files

| File | What |
|---|---|
| `backend/schemas/030_vendor_profiles.sql` | vendor_profiles table |
| `backend/schemas/031_fix_users_role_vendor.sql` | role CHECK includes vendor |
| `backend/schemas/032_vendor_teaming_agreements.sql` | agreements table + documents owner model (`vendor_user_id`) |
| `backend/core/vendor_profile.py` | `VendorProfileManager` CRUD |
| `backend/core/vendor_agreements.py` | `VendorAgreementManager` — MTA render/sign/audit; `TEMPLATE_VERSION` |
| `backend/api/routes/vendor_profiles.py` | register / profile endpoints |
| `backend/api/routes/vendor_agreements.py` | MTA endpoints |
| `backend/auth/__init__.py` | `VALID_ROLES` set; `require_admin`, `require_mta` dependencies |
| `backend/api/routes/admin.py` | admin user CRUD (now supports vendor role) |
| `frontend/src/app/vendor-register/page.tsx` | self-service registration |
| `frontend/src/app/portal/page.tsx` | vendor dashboard + MTA banner (unsigned/signed) |
| `frontend/src/components/MtaSigningModal.tsx` | MTA review + e-signature (typed name, checkbox, PDF preview) |
| `frontend/src/components/DocumentPreviewModal.tsx` | signed-agreement PDF viewer (reused) |
| `frontend/src/app/settings/page.tsx` | admin user management (vendor role option) |
| `frontend/src/components/AuthProvider.tsx` | role-based route redirection |

---

## 6. Not Yet Built (Next Tickets)

- **Quote requests**: admin assigns solicitation → vendor; vendor responds from portal — gate with `require_mta` (done for MTA).
- **Profile document uploads**: licenses, bonding, insurance docs → `vendor_profiles.license_doc_id` etc. (documents rows can now be case-less with `vendor_user_id` — unblocked by 032). Includes admin review + `verified_at`.
- **BSTA flow**: per-bid addendum before formal offers (RFP/IFB) — decision tree, LoS math (FAR 52.219-14), similarly situated computation. Needs `is_small_business`/`sb_program_status[]` profile fields first. Reuses `vendor_teaming_agreements` (solicitation_id set).
- **Subcontract flow**: per-award rows prefilled from BSTA.
- **Capability integration**: pull vendor profile data into capability statements/proposals.
- **Portal quote submission UI**: vendor-facing quote form.
- **MTA lifecycle**: re-sign after termination (partial unique index supports it); SAM expiry + cert expiry alerts from contract-logic guide.
