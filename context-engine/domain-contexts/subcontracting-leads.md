# Subcontracting Leads (USASpending.gov)

> **Purpose:** Identify primes who are contractually obligated to subcontract — then get on their team.
> **Last Updated:** 2026-08-05

---

## 1. Business Overview

### What This Domain Does

Finds IDV vehicles (IDIQ, MATOC, GWAC, BPA, BOA, FSS) from USASpending.gov where the prime contractor holds an active subcontracting plan (plan code F or G). These primes are legally required to subcontract a portion of their work to small businesses — and they're evaluated on doing so. The Subcontracting Leads module builds a ranked, enriched list of these primes so we can outreach to them and get on their subcontractor rosters.

### Why It Exists

The SAM databank tells us "what can we bid as prime." The USASpending data answers a different question: **"which primes are obligated to subcontract to companies like us?"** These are two completely different pipelines:

| Pipeline | Source | We are the... | Output |
|----------|--------|--------------|--------|
| SAM Databank → Solicitations | SAM.gov | Prime contractor | We bid, win, and sub out the work |
| USASpending → Subcontracting Leads | USASpending.gov | Subcontractor | We get on a prime's team, they win, we perform |

They converge: when we pull a prime's active SAM.gov solicitations during enrichment, those solicitations become bid opportunities where we're the sub, not the prime.

### Key Business Rules

- **FAR 19.702(a):** A subcontracting plan is required for contracts >$900K (>$2M for construction). Small business primes are exempt.
- **Plan F (Individual Subcontract Plan):** The prime negotiated specific SB subcontracting goals. Highest-value outreach targets.
- **Plan G (Commercial Subcontract Plan):** The prime sells commercial items and has a commercial sub plan. Valuable but lower priority than F.
- **Multi-award pools > single-award:** Primes in multi-award IDIQ/MATOC pools compete for every task order. More competition = more pressure to subcontract = warmer outreach targets.
- **SBLO (Small Business Liaison Officer):** Every large prime with a subcontracting plan has one. They are paid to talk to small businesses. This is the warmest door for outreach.

### User Stories

- As a BD analyst, I upload the monthly USASpending CSV and get a ranked list of primes with subcontracting obligations in our NAICS.
- As a BD analyst, I filter by construction primes with plan F who are in multi-award pools — these are our highest-probability outreach targets.
- As a BD analyst, I click "Compute Pools" to identify which primes share the same IDIQ vehicle — more awardees in a pool means more subcontracting pressure.

---

## 2. How to Use This Data (Operational Playbook)

### Step 1: Download

Go to [usaspending.gov/search](https://www.usaspending.gov/search) → Award Search → Download. Filters:
- **Award Type:** GWAC, Multi-Agency Contract, Other IDC, Requirements, IDIQ, Definite Quantity, FSS, BOA, BPA
- **NAICS:** 23 (Construction), 56 (Admin/Support/Waste), 54 (Professional/Scientific/Technical), 51 (Information)
- **Data:** Awards + Subawards

This produces a ~232MB CSV with 136K+ rows.

### Step 2: Upload

Go to `/subcontracting-leads` → Upload CSV. The upload applies four filter gates:
1. Only plan F or G vehicles
2. Only active ordering periods (not expired)
3. Only target NAICS (236/237/238, 5415, 5612/5616/5617, 562, 5112/5182)
4. Valid keys (award_id_piid + recipient_uei)

From 136K rows, ~2,000 qualify as actionable leads.

### Step 3: Compute Pools

Click "Compute Pools" to group leads by `solicitation_identifier`. This identifies multi-award MATOC/MACC pools and boosts priority scores (+20 for 5+ awardee pools, +10 for 2–4).

### Step 4: Triage

Filter by `priority = high`. These are primes with:
- Plan F (individual subcontracting plan)
- Multi-award pool membership
- Large ceiling values
- Long ordering periods (runway)

For each high-priority lead, research:
- What does this prime actually build? (NAICS, past awards)
- Are they actively buying right now? (Check SAM.gov for active task orders under their vehicles)
- Who is their SBLO? (Google "[company] small business liaison officer")
- Are they a small business themselves? (If yes, FAR 52.219-14 limits how much they can sub out)

### Step 5: Outreach

Contact the SBLO. The pitch is NOT "can we bid your work?" — it's:

> *"We're a qualified [construction/facilities/IT] small business. We see you hold [X vehicles] with subcontracting obligations under FAR 19.7. Here's our capability statement. Can we schedule 15 minutes to discuss how we can help you meet your subcontracting goals?"*

Track status through the pipeline: `not_started → researching → drafting → sent → responded → meeting_scheduled → on_roster → declined`.

### Step 6: Enrich (Coming)

The enrichment step pulls each target prime's active SAM.gov solicitations by UEI. When a prime has an active task order solicitation seeking subs, that goes into the SAM pipeline as a sub-bid opportunity — we respond to THEIR solicitation as a subcontractor.

### The Funnel

```
2,092 active leads (plan F/G, active ordering periods)
    ↓ filter high priority
~200 priority targets
    ↓ enrichment + research  
~100 ready for outreach
    ↓ contact SBLO
~30–50 responses
    ↓ capability review
~15–25 on roster
    ↓ task order RFQ received
~5–10 asked to quote
    ↓ price + submit
~2–5 subcontracts won
```

### The Coffie Flywheel

> Line item → cash flow → credibility → past performance → partnerships → contracts

Each subcontract won is a line item. Each line item is past performance for the next bid — as prime or as sub.

---

## 3. Data Model

### Table: `subcontracting_leads` (migration v36)

```sql
subcontracting_leads
├── id                        SERIAL PK
├── external_id               UUID UNIQUE
├── award_id_piid             TEXT NOT NULL (vehicle ID)
├── parent_award_id_piid      TEXT
├── solicitation_identifier   TEXT (RFP that created the pool)
├── idv_type                  TEXT (IDC, BPA, FSS, GWAC, BOA)
├── multiple_or_single_award   TEXT
├── recipient_uei             TEXT NOT NULL (prime UEI)
├── recipient_name            TEXT NOT NULL
├── recipient_parent_name     TEXT
├── recipient_city/state      TEXT
├── naics_code                TEXT (indexed)
├── naics_description         TEXT
├── psc_code/description      TEXT
├── potential_value           NUMERIC (ceiling)
├── current_value             NUMERIC (obligated — usually $0 for IDVs)
├── base_action_date          DATE
├── ordering_period_end       DATE (indexed)
├── pop_current_end           DATE
├── pop_potential_end         DATE
├── subcontracting_plan_code  TEXT (F or G — indexed)
├── subcontracting_plan       TEXT
├── awarding_agency           TEXT
├── awarding_sub_agency       TEXT
├── set_aside_type            TEXT
├── pool_id                   TEXT (computed — indexed)
├── pool_awardee_count        INTEGER (computed)
├── is_woman_owned            BOOLEAN
├── is_sdvosb                 BOOLEAN
├── is_hubzone                BOOLEAN
├── is_8a                     BOOLEAN
├── is_small_disadvantaged    BOOLEAN
├── is_minority_owned         BOOLEAN
├── pipeline_status           TEXT DEFAULT 'new' (indexed)
├── pipeline_category         TEXT (construction/facilities/it — indexed)
├── pipeline_priority         TEXT (high/medium/low — indexed)
├── pipeline_priority_score   INTEGER (0–100)
├── pipeline_notes            TEXT
├── last_enriched_at          TIMESTAMPTZ
├── enrichment_data           JSONB
├── outreach_status           TEXT DEFAULT 'not_started'
├── outreach_last_contact     TIMESTAMPTZ
├── outreach_notes            TEXT
├── upload_batch_id           UUID (indexed)
├── source_csv                TEXT
├── usaspending_permalink     TEXT
├── created_at                TIMESTAMPTZ
└── updated_at                TIMESTAMPTZ

UNIQUE (award_id_piid, recipient_uei)
```

**Dedup:** `UNIQUE (award_id_piid, recipient_uei)` — a prime can hold each vehicle only once. Monthly re-uploads UPDATE existing rows (refreshing dates, values, plan status) and INSERT new ones. Outreach history is preserved across updates.

### Priority Score Formula

```
Base score (0–70 during upload):
  +30  Plan F (Individual Subcontract Plan)
  +15  Plan G (Commercial Subcontract Plan)
  +10  Construction NAICS (our primary wedge)
  +5   Facilities or IT NAICS
  +10  Potential value > $1B
  +7   Potential value > $100M
  +3   Potential value > $10M
  +10  Ordering period ends after 2028

Pool boost (post-upload via /process-pools):
  +20  5+ awardees in pool
  +10  2–4 awardees in pool

Final (after enrichment, coming):
  +10  Active SAM.gov solicitations found for this prime
  ---
  100  MAX
```

### Pipeline Statuses

| Status | Meaning |
|--------|---------|
| `new` | Freshly uploaded, not yet triaged |
| `triaged` | Analyst has reviewed and set priority/notes |
| `enriched` | SAM.gov enrichment data pulled |
| `in_outreach` | Outreach email/call has been sent |
| `responded` | Prime responded |
| `on_roster` | We're on their approved subcontractor list |
| `declined` | Prime declined or not a fit |
| `expired` | Ordering period ended, vehicle inactive |
| `archived` | Not pursuing |

---

## 4. Code Navigation

### Entry Points

| If you want to... | Start at... |
|-------------------|-------------|
| Understand the data model | `backend/schemas/026_subcontracting_leads.sql` |
| See the API endpoints | `backend/api/routes/subcontracting_leads.py` |
| Trace the upload/filter logic | `backend/api/routes/subcontracting_leads.py` → `upload_subcontracting_leads_csv()` |
| See the pool computation | `backend/api/routes/subcontracting_leads.py` → `process_pools()` |
| Query leads from the frontend | `frontend/src/lib/api.ts` → `querySubcontractingLeads()`, `uploadSubLeadsCsv()` |
| See the UI | `frontend/src/app/subcontracting-leads/page.tsx` |
| Understand the analysis that produced the filter rules | `discussions/gov-talent-network/02-usaspending-analysis.md` |

### Key Files

| File | Purpose |
|------|---------|
| `backend/schemas/026_subcontracting_leads.sql` | Table schema + indexes + unique constraint |
| `backend/api/routes/subcontracting_leads.py` | Upload, query, triage update, pool processing, batch management |
| `frontend/src/lib/api.ts` (SubcontractingLead type + API functions) | Type definitions + direct-fetch upload (bypasses JSON-only fetchAPI) |
| `frontend/src/app/subcontracting-leads/page.tsx` | Full page: upload button, filters, scored table, expandable rows, pagination |
| `frontend/src/components/ReferenceNav.tsx` | Nav link labeled "Sub Leads" |
| `discussions/gov-talent-network/02-usaspending-analysis.md` | Raw data analysis: 136K IDVs → 2,092 active F/G leads |

---

## 5. API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/subcontracting-leads/upload` | Upload CSV with inline filtering. Returns inserted/updated/skipped counts. |
| `POST` | `/api/subcontracting-leads/query` | Dynamic filtered query with pagination. |
| `GET` | `/api/subcontracting-leads/{id}` | Single lead detail. |
| `POST` | `/api/subcontracting-leads/{id}/triage` | Update priority, notes, status. |
| `POST` | `/api/subcontracting-leads/process-pools` | Post-upload: group by solicitation_identifier, compute awardee counts, boost scores. |
| `GET` | `/api/subcontracting-leads/batches` | List upload history with row counts. |

All endpoints require Bearer token.

---

## 6. Upload Filter Logic

Applied during CSV processing (not post-hoc). Four gates in order:

```
CSV row (136K+)
  ↓
Gate 1: Plan F or G?        → NO → skipped: no_plan (~130K)
  ↓ YES
Gate 2: Active ordering?     → NO → skipped: not_active (~2K)
  ↓ YES
Gate 3: Target NAICS?        → NO → skipped: wrong_naics (~500)
  ↓ YES
Gate 4: Valid keys?          → NO → skipped: invalid_key (~few)
  ↓ YES
INSERT with ON CONFLICT UPDATE → ~2,000 leads
```

NAICS families accepted: `236xxx, 237xxx, 238xxx` (Construction), `5415xx` (IT Services), `5612xx, 5616xx, 5617xx` (Facilities/Security/Janitorial), `562xxx` (Waste/Remediation), `5112xx, 5182xx` (Software/Data).

---

## 7. Related Domains

| Domain | Relationship |
|--------|-------------|
| [SAM Notices Databank](sam-notices-databank.md) | Raw SAM.gov CSV data — feeds the solicitation pipeline (bid as prime) |
| [Solicitation Pipeline](solicitation-pipeline.md) | Full pipeline from SAM.gov URL → triage → vendor matching → outreach |
| [Forecast Opportunities](forecast-opportunities.md) | Acquisition Gateway forecasts — longer-horizon opportunities |

---

## 8. Known Issues & Planned Work

- [ ] **Enrichment not yet built:** Pulling active SAM.gov solicitations by prime UEI is spec'd but not implemented. This is the bridge between the two pipelines.
- [ ] **Outreach tracking is manual:** Status updates are done via the API, not through a CRM-style UI yet.
- [ ] **Subaward data not loaded:** The subawards CSV (13K rows) is available but not imported. Construction subaward reporting is thin — not a priority for v1.
- [ ] **Priority scoring is static:** Pool computation boosts scores, but there's no ongoing score refresh. Monthly re-uploads update vehicle data but scores are only recalculated on fresh upload.

---

> ⚠️ **When working in this domain:** The upload uses direct `fetch()` (not `fetchAPI`) because `fetchAPI` forces `Content-Type: application/json` which corrupts FormData uploads. If you need to add a new FormData-based endpoint, follow the `uploadSubLeadsCsv` / `uploadSamNoticesCsv` pattern, not the `fetchAPI` pattern.
