# Vendor Portal — Registration, Profiles, and Roles

> **Purpose:** Onboard developers/agents to the vendor portal subsystem: vendor user role, vendor profiles, registration flow, and the /portal route separation.
> **Last Updated:** 2026-08-12

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
| `backend/core/vendor_profile.py` | `VendorProfileManager` CRUD |
| `backend/api/routes/vendor_profiles.py` | register / profile endpoints |
| `backend/auth/__init__.py` | `VALID_ROLES` set; `require_admin` dependency |
| `backend/api/routes/admin.py` | admin user CRUD (now supports vendor role) |
| `frontend/src/app/vendor-register/page.tsx` | self-service registration |
| `frontend/src/app/portal/page.tsx` | vendor dashboard |
| `frontend/src/app/settings/page.tsx` | admin user management (vendor role option) |
| `frontend/src/components/AuthProvider.tsx` | role-based route redirection |

---

## 6. Not Yet Built (Next Tickets)

- **Quote requests**: admin assigns solicitation → vendor; vendor responds from portal (extends `quotes` table with `vendor_user_id`).
- **Profile document uploads**: licenses, bonding, insurance docs via the documents pipeline.
- **Teaming agreements**: signed docs linked to vendors + solicitations (`vendor_teaming_agreements` junction table).
- **Capability integration**: pull vendor profile data into capability statements/proposals.
- **Portal quote submission UI**: vendor-facing quote form.
