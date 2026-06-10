# GovCon Dashboard — Implementation Plan

## 1. Architecture: Where Everything Lives

```
┌─────────────────────────────────────────────────────────┐
│  DASHBOARD (/)                                           │
│                                                         │
│  ┌─────────────────────┐  ┌───────────────────────────┐ │
│  │ Company Profile     │  │ Cases / Matters           │ │
│  │ (account-level)     │  │                           │ │
│  │                     │  │ RFP Cases ──────────────┐ │ │
│  │ Vision Tech, LLC    │  │  ├─ HHS IT Modernization │ │ │
│  │ ┌─────────────────┐ │  │  ├─ DOD Cloud Migration  │ │ │
│  │ │ CAGE: 9ABCD     │ │  │  ├─ VA Healthcare RFP   │ │ │
│  │ │ UEI: FM8X...    │ │  │  └─ ...                 │ │ │
│  │ │ NAICS: 541511   │◄├──┤  (each references the    │ │ │
│  │ │ Certs: 8(a)...  │ │  │   company profile)       │ │ │
│  │ │ Past Perf: ...  │ │  └─────────────────────────┘ │ │
│  │ └─────────────────┘ │                               │ │
│  │ [Edit] [Re-synth]   │  Legal Cases                  │ │
│  └─────────────────────┘    ├─ Alhad v. Edmonds        │ │
│                             └─ ...                     │ │
│  [+ New Case]  [+ New Profile]                         │ │
└─────────────────────────────────────────────────────────┘
```

**Company Profile** is a top-level entity on the dashboard — one row below the app header, before cases. One click from anywhere. Not buried in settings.

**RFP Cases** reference a profile via FK. The case overview shows solicitation-specific fields (agency, due date, NAICS match, set-aside, status). The profile data feeds proposal generation.

**Legal Cases** don't reference a company profile. Different universe.

---

## 2. Module Breakdown

### Module A: Schema (30 min)

**New table: `company_profiles`**

```sql
CREATE TABLE company_profiles (
    id              SERIAL PRIMARY KEY,
    account_id      UUID NOT NULL,              -- FK to users or a new accounts concept
    name            TEXT NOT NULL,              -- "Vision Technologies, LLC"
    content         JSONB NOT NULL DEFAULT '{}', -- the profile fields
    source_docs     JSONB DEFAULT '[]',          -- [{document_id, document_name, fields_extracted}]
    status          TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'complete')),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

**content JSONB schema:**

```json
{
  "company_name": "Vision Technologies, LLC",
  "legal_name": "Vision Technologies LLC",
  "dba": null,
  "cage_code": "9ABCD",
  "uei": "FM8X...",
  "tax_id": null,
  "naics_codes": ["541511", "541512", "518210"],
  "psc_codes": [],
  "certifications": ["8(a)", "SDVOSB"],
  "capabilities_summary": "Vision is a Maryland-based small business...",
  "past_performance": [
    {
      "client": "State of Maryland",
      "contract_value": "$500K",
      "description": "Case management system...",
      "period_of_performance": "2024-2025"
    }
  ],
  "key_personnel": [
    {
      "name": "Ian Bruce",
      "title": "Principal",
      "years_experience": 15,
      "resume_document_id": 12,
      "clearance": null
    }
  ],
  "contact": {
    "address_line1": "1018 Prestwyck Ct",
    "city": "Alpharetta",
    "state": "GA",
    "zip": "30004",
    "phone": null,
    "email": null
  },
  "field_status": {
    "cage_code": "verified",       // verified | agent_filled | needs_input
    "uei": "agent_filled",
    "psc_codes": "needs_input",
    ...
  }
}
```

**Solicitation fields on `cases` (if case_type = rfp_response):**

Add a `solicitation JSONB` column to cases. Populated only for RFP cases:

```json
{
  "solicitation_number": "75A50323R0001",
  "agency": "HHS",
  "due_date": "2026-07-15",
  "set_aside": "8(a)",
  "naics_match": true,
  "status": "open",                // open | in_progress | submitted | awarded | lost
  "profile_id": 1                  // FK to company_profiles
}
```

Or: add `profile_id INTEGER REFERENCES company_profiles(id)` + `solicitation JSONB` to cases. The solicitation column is only populated for `rfp_response` cases.

### Module B: Company Profile Page (45 min)

A new page at `/profile` — accessible from the dashboard.

**Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  ← Dashboard                                            │
│                                                         │
│  Company Profile                    [Edit] [Re-synthesize]│
│                                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────────┐  │
│  │ Company Info │ │ Certs &     │ │ NAICS / PSC       │  │
│  │ ✓ CAGE       │ │ Codes       │ │ ✓ 541511          │  │
│  │ ✓ UEI        │ │ ✓ 8(a)      │ │ ✓ 541512          │  │
│  │ ? Tax ID     │ │ ✓ SDVOSB    │ │ ✗ PSC Codes       │  │
│  └─────────────┘ └─────────────┘ └───────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Past Performance                                 │   │
│  │ ✓ State of Maryland — $500K — CMS — 2024-2025  │   │
│  │ ✓ DOD — $200K — Cloud Migration — 2023-2024    │   │
│  │ [ + Add Reference ]                              │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Key Personnel                                    │   │
│  │ ✓ Ian Bruce — Principal — 15 yrs — resume.pdf   │   │
│  │ ? Jane Doe — Sr. Engineer — no resume uploaded   │   │
│  │ [ + Add Personnel ]                              │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  [Generate Capability Statement]                        │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Document Sources                                 │   │
│  │ capability-statement-2025.pdf — CAGE, UEI, NAICS │   │
│  │ sam-gov-printout.pdf — UEI, CAGE                 │   │
│  │ cert-8a.pdf — 8(a) certification                 │   │
│  │ [Upload more documents to re-synthesize...]       │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

**States per field:**
- `✓ verified` — manually confirmed by user (green check)
- `✓ agent_filled` — agent found it, not yet verified (gray check)
- `? uncertain` — agent found something but confidence is low (yellow)
- `✗ needs_input` — not found in any document (red, prompts user)

**Interactions:**
- Click any field to edit inline
- "Re-synthesize" button — re-runs agent extraction on all source docs. Only updates fields with `agent_filled` or `needs_input` status. Leaves `verified` fields alone.
- Upload new docs → agent processes the new doc → fills any matching fields it can
- "Generate Capability Statement" → agent creates a draft in the currently selected (or most recent) RFP case

### Module C: Profile Synthesis Agent (30 min)

Similar to the enricher — a background job triggered by upload or manual "Re-synthesize."

**Flow:**

```
User uploads docs for profile synthesis
  → saved to a "Company Profile" bucket (special case, or a profile-specific storage)
  → ingested normally (OCR, normalize, embed)
  → enqueue job(type='profile_synthesis', profile_id=X)
  → worker claims → spawn Agent SDK session
    → agent reads document content via tools
    → agent calls save_profile_fields(content_json)
  → profile.content updated
  → frontend polls → refreshed cards
```

**Agent tools:**
- `read_profile_documents` — reads all source docs attached to the profile
- `save_profile_fields` — writes the content JSONB with field_status tracking
- `generate_capability_statement` — creates a draft from the profile

**System prompt:** domain-specific — GovCon extraction. Knows what CAGE codes look like, how NAICS codes are formatted, what certifications are called, how to parse past performance references.

### Module D: RFP Case Creation + Overview (40 min)

**Create case flow (when case_type = rfp_response):**

```
1. Select "New RFP Response" from dashboard
2. Select company profile (or create one first)
3. Upload solicitation ZIP → ingested, documents appear
4. Case created → Overview shows:
   ┌────────────────────────────────────────────┐
   │ HHS IT Modernization RFP                   │
   │ Agency: HHS · Due: July 15, 2026 · 8(a)   │
   │                                            │
   │ Company Profile: Vision Tech, LLC          │
   │ ✓ CAGE ✓ UEI ✓ NAICS Match ✓ Certs       │
   │ [View Profile]                             │
   │                                            │
   │ Solicitation Docs: 12 documents            │
   │ Requirements extracted: 14                 │
   │ Compliance gaps: 3                         │
   │                                            │
   │ [Extract Requirements]  [Generate Proposal]│
   └────────────────────────────────────────────┘
```

The RFP case overview is context-aware — shows solicitation-specific fields instead of the generic Overview layout.

### Module E: Agent-Derived Capability Statement (20 min)

The agent generates a capability statement as a **draft** in the context of an RFP case. It pulls data from:
1. The linked company profile (CAGE, NAICS, certs, past performance)
2. The solicitation requirements (extracted from the RFP documents)
3. The case narrative (any additional context the user provided)

This is an agent tool: `generate_capability_statement(profile_id, case_id?)` → creates a draft with `document_type: "capability_statement"`.

The draft is editable like any other draft. The user can refine it before exporting.

When no case is selected (from the Profile page), it generates a generic capability statement. When scoped to a case, it tailors the statement to the solicitation's requirements.

---

## 3. Implementation Sequence

| Phase | Tickets | Est. |
|-------|---------|------|
| **Phase 1: Foundation** | | 1.5 hr |
| | A1 — Schema: `company_profiles` table + `solicitation` JSONB on cases | 15 min |
| | A2 — DB helpers: CRUD for company_profiles | 15 min |
| | A3 — API: profile CRUD endpoints, profile doc upload | 25 min |
| | A4 — Frontend API client: profile types + functions | 10 min |
| **Phase 2: Profile UI** | | 1.5 hr |
| | B1 — Company Profile page (dashboard-level, `/profile`) | 45 min |
| | B2 — Profile card on dashboard (/), link to profile page | 20 min |
| | B3 — Editable field cards with status indicators | 30 min |
| **Phase 3: Synthesis** | | 1.5 hr |
| | C1 — `profile_synthesis` job type + worker handler | 15 min |
| | C2 — Synthesis agent: `read_profile_documents` + `save_profile_fields` tools | 30 min |
| | C3 — "Re-synthesize" button + upload-to-synthesize flow in profile UI | 20 min |
| | C4 — Field merge logic: agent doesn't overwrite `verified` fields | 15 min |
| **Phase 4: RFP Case** | | 1.5 hr |
| | D1 — Case creation flow for `rfp_response`: select profile, upload ZIP | 25 min |
| | D2 — RFP case overview: solicitation fields + profile card | 30 min |
| | D3 — Solicitation requirement extraction (extend synthesis agent) | 30 min |
| **Phase 5: Capability Statement** | | 45 min |
| | E1 — `generate_capability_statement` agent tool | 25 min |
| | E2 — "Generate Capability Statement" button in profile + RFP overview | 15 min |

**Total: ~6.5 hours**

---

## 4. What About Documents?

Documents uploaded for profile synthesis are stored in a dedicated "Company Profile" bucket — NOT in any specific RFP case. They're ingested and indexed normally (so the agent can search them), but they live at the profile level.

When the user uploads a solicitation ZIP for an RFP case, those docs live in the case's document bucket. The agent reads them to extract requirements, but they're scoped to that case.

**No document duplication.** The profile docs are reference material. Case docs are solicitation-specific. The agent can read both.

---

## 5. Open Questions

1. **Account vs. user scope:** Is a company profile per-account (shared by all users in the org) or per-user (personal)? For MVP, per-user (simple). Multi-user later.

2. **Multi-profile:** Can an account have multiple profiles? Yes — different company entities (the prime and a JV partner). The RFP case selects which profile to use.

3. **Profile docs storage:** Do we create a hidden "Company Profile" case for each profile? Or store doc references directly on the profile row? The hidden case approach reuses all existing document infrastructure. Recommended.

4. **Solicitation requirement extraction:** This is a separate synthesis agent that reads the solicitation docs and extracts structured requirements (similar to the parties/allegations extractor but for RFP elements). Scope it for Phase 4.
