# Phase 3 — USASpending Subcontracting Lead Pipeline

> Pipeline artifact · 2026-08-05 · Status: DRAFT

---

## 1. What This Pipeline Produces

A ranked, enriched list of primes who are contractually obligated to subcontract — with enough intelligence to start a conversation, not just a name and UEI.

**End goal:** Get our company on their subcontractor roster so when task orders drop, we're the ones they call.

---

## 2. How This Is Different From SAM

| Dimension | SAM Pipeline | USASpending Pipeline |
|-----------|-------------|---------------------|
| **We are the...** | Prime | Subcontractor |
| **We are responding to...** | The government's solicitation | The prime's subcontracting needs |
| **The output is...** | A proposal/bid | A capability statement / teaming conversation |
| **Success is...** | Winning the contract as prime | Getting on the prime's approved sub list |
| **The deadline is...** | The response date on the solicitation | No deadline — it's relationship-building. But earlier is better. |
| **The data source...** | SAM.gov databank (active solicitations) | USASpending.gov (awarded IDV vehicles) |
| **Volume...** | ~80/day active bids | ~2,000 total leads, ~50–100 priority targets |

---

## 3. The Table: `subcontracting_leads`

### 3.1 Schema

```sql
CREATE TABLE subcontracting_leads (
    id                  SERIAL PRIMARY KEY,
    external_id         UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,

    -- Vehicle identity
    award_id_piid       TEXT NOT NULL,          -- The IDV PIID (e.g. W912DY21R0014)
    parent_award_id_piid TEXT,                  -- Parent IDV if this is a child
    solicitation_identifier TEXT,               -- The RFP that created this pool
    idv_type            TEXT,                   -- IDC, BPA, FSS, GWAC, BOA
    multiple_or_single_award TEXT,              -- MULTIPLE AWARD or SINGLE AWARD

    -- Prime identity
    recipient_uei       TEXT NOT NULL,          -- UEI of the prime
    recipient_name      TEXT NOT NULL,          -- Legal name of the prime
    recipient_parent_name TEXT,                 -- Parent company
    recipient_city      TEXT,
    recipient_state     TEXT,

    -- Scope
    naics_code          TEXT,                   -- Primary NAICS
    naics_description   TEXT,
    psc_code            TEXT,
    psc_description     TEXT,

    -- Value
    potential_value     NUMERIC,                -- Ceiling value
    current_value       NUMERIC,                -- Obligated to date (usually $0 for IDVs)

    -- Dates
    base_action_date    DATE,                   -- When vehicle was awarded
    ordering_period_end DATE,                   -- When ordering window closes
    pop_current_end     DATE,                   -- Current period of performance end
    pop_potential_end   DATE,                   -- Maximum POP end

    -- Subcontracting obligation
    subcontracting_plan_code TEXT,              -- F or G
    subcontracting_plan TEXT,                   -- Human-readable

    -- Agency
    awarding_agency     TEXT,
    awarding_sub_agency TEXT,

    -- Set-aside
    set_aside_type      TEXT,

    -- Pool intelligence
    pool_id             TEXT,                   -- Derived: groups vehicles from same solicitation
    pool_awardee_count  INTEGER,                -- How many primes share this pool
    pool_rank           INTEGER,                -- Our rank within the pool (by value or recency)

    -- Socioeconomic flags on the prime
    is_woman_owned      BOOLEAN,
    is_sdvosb           BOOLEAN,
    is_hubzone          BOOLEAN,
    is_8a               BOOLEAN,
    is_small_disadvantaged BOOLEAN,
    is_minority_owned   BOOLEAN,

    -- Processing metadata
    pipeline_status     TEXT DEFAULT 'new',     -- new, triaged, enriched, in_outreach, responded, archived
    pipeline_category   TEXT,                   -- construction, facilities, it, other
    pipeline_priority   TEXT,                   -- high, medium, low
    pipeline_notes      TEXT,                   -- Analyst notes from triage
    last_enriched_at    TIMESTAMPTZ,            -- When we last pulled their active SAM solicitations
    enrichment_data     JSONB,                  -- Cached enrichment results

    -- Outreach tracking
    outreach_status     TEXT,                   -- not_started, researching, drafting, sent, responded, meeting_scheduled, on_roster, declined
    outreach_last_contact TIMESTAMPTZ,
    outreach_notes      TEXT,

    -- Source tracking
    upload_batch_id     UUID,
    source_csv          TEXT,
    usaspending_permalink TEXT,

    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    -- Dedup: a prime can hold a vehicle only once
    UNIQUE (award_id_piid, recipient_uei)
);

CREATE INDEX idx_sub_leads_status ON subcontracting_leads (pipeline_status);
CREATE INDEX idx_sub_leads_category ON subcontracting_leads (pipeline_category);
CREATE INDEX idx_sub_leads_priority ON subcontracting_leads (pipeline_priority);
CREATE INDEX idx_sub_leads_plan ON subcontracting_leads (subcontracting_plan_code);
CREATE INDEX idx_sub_leads_uei ON subcontracting_leads (recipient_uei);
CREATE INDEX idx_sub_leads_ordering ON subcontracting_leads (ordering_period_end);
CREATE INDEX idx_sub_leads_pool ON subcontracting_leads (pool_id);
CREATE INDEX idx_sub_leads_value ON subcontracting_leads (potential_value);
```

### 3.2 Deduplication

**Natural key:** `(award_id_piid, recipient_uei)` — a prime can hold the same IDV vehicle only once.

**On re-import (monthly sweep):**
- New `(award_id_piid, recipient_uei)` → INSERT as `pipeline_status = 'new'`
- Existing key, but dates or values changed → UPDATE, set `pipeline_status = 'updated'`, preserve outreach history
- Existing key, nothing changed → skip (no-op)
- Vehicle no longer in the new download → mark `pipeline_status = 'expired'` (the ordering period ended)

This means the monthly sweep both adds new leads AND maintains the freshness of existing ones.

---

## 4. The Triage Workflow

Triage for a subcontracting lead answers different questions than solicitation triage:

### 4.1 Triage Questions

| Question | Data Source | What We're Looking For |
|----------|------------|----------------------|
| Is the vehicle still active? | `ordering_period_end` | Must be ≥ today or open-ended |
| Are they obligated to subcontract? | `subcontracting_plan_code` | F or G only |
| What do they buy? | `naics_code`, `psc_code` | Overlap with our capabilities? |
| How big is the vehicle? | `potential_value` | Larger = more sub opportunities |
| Are they in a multi-award pool? | `pool_id`, `pool_awardee_count` | Multi-award = more task order competition = more sub pressure |
| Are they a small business themselves? | Socioeconomic flags | If the prime IS a small business, FAR 52.219-14 applies — they can only sub out 50–85% |
| Have we worked with them before? | Our internal CRM / past performance | Existing relationship = warmer outreach |
| Are they actively buying right now? | Enrichment (SAM.gov solicitations) | Active task order solicitations = immediate opportunities |

### 4.2 Priority Scoring

```
Score 0–100:

+30  Plan F (Individual Subcontract Plan — strongest obligation)
+15  Plan G (Commercial Subcontract Plan)
+20  Multi-award pool with 5+ awardees (more TO competition)
+10  Potential value > $1B
+10  Ordering period ends after 2028 (long runway)
+5   NAICS matches our core capabilities exactly
+5   Prime not marked as small business (fewer self-performance limits)
+5   Active SAM.gov solicitations found during enrichment (buying NOW)
---
100  MAX
```

### 4.3 Triage Outputs

| Priority | Score | Action |
|----------|-------|--------|
| **High** | 70–100 | Enrich immediately, research the prime, draft outreach within 48 hours |
| **Medium** | 40–69 | Batch enrich, add to CRM watchlist, outreach when capacity allows |
| **Low** | <40 | Archive. Re-evaluate on next monthly sweep if anything changed. |

---

## 5. Enrichment: What Are They Buying Right Now?

This is the step that turns a lead into an opportunity. For each high-priority prime, pull their active SAM.gov solicitations:

### 5.1 Enrichment Sources

| Source | What It Tells Us |
|--------|-----------------|
| SAM.gov API (search by UEI) | Active task order solicitations under their vehicles |
| Their website / GSA eLibrary | Capability statements, past performance, sub opportunities page |
| FPDS / USASpending task order search | What they've actually bought recently (task orders under the IDV) |
| SBA Dynamic Small Business Search | Their small business status, certs, contact info |

### 5.2 What Enrichment Produces

For each high-priority prime, we build a one-page brief:

```
PRIME: Whiting-Turner Contracting Co.
UEI: VEP4UN7LDMK5
Active Vehicles: 21 (all IDCs, $37.8B ceiling)
Multi-Award Pools: 8+ MATOC/MACC pools
Active SAM Solicitations Right Now: 3 task orders seeking subs
Primary NAICS: 236220 (Commercial Building Construction)
Known Subcontracting Needs: Electrical, HVAC, plumbing, fire protection
Contact: [from research]
Our Fit: We have 4 qualified electrical subs in their regions
Recommended Approach: Capability statement + call to their small business liaison
```

---

## 6. Acting on the Leads: The Outreach Funnel

This is different from the SAM pipeline. We're not submitting a bid — we're building a relationship.

### 6.1 The Funnel

```
Lead identified (2,092)
    ↓ triage filters
Priority targets (~200)
    ↓ enrichment
Enriched with context (~200)
    ↓ research + prep
Outreach drafted (~100)
    ↓ sent
Outreach sent (~100)
    ↓ response received
Prime responded (~30–50)
    ↓ meeting / capability review
On their subcontractor roster (~15–25)
    ↓ task order opportunity
Asked to quote on a task order (~5–10)
    ↓ we price + submit
Subcontract won (~2–5)
```

### 6.2 Outreach Methods

| Method | When to Use | Success Rate |
|--------|------------|-------------|
| Capability statement via email | Cold outreach to primes we've never worked with | Low (but scalable) |
| Response to their active SAM solicitation | When they have a live task order seeking subs | Medium — they're actively looking |
| Small Business Liaison Officer (SBLO) call | Every large prime has one — they're PAID to talk to small businesses | High — this is literally their job |
| Industry day / pre-proposal conference | When they host one for an upcoming task order | High — face-to-face |
| Teaming agreement | When we've established rapport and a specific opportunity exists | This is the goal |

### 6.3 The SBLO Angle

Every large prime with a subcontracting plan has a Small Business Liaison Officer. Their job is to find qualified small businesses. They're evaluated on how much they subcontract to SB. This is the warmest door.

The outreach isn't "Can we bid your work?" — it's "We're a qualified small business in your NAICS. We see you hold vehicles X, Y, Z with subcontracting obligations. Here's our capability statement. Can we schedule 15 minutes with your SBLO?"

---

## 7. Full Workflow Summary

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: INGEST                                            │
│                                                             │
│  USASpending download → subcontracting_leads table          │
│  Dedup key: (award_id_piid, recipient_uei)                  │
│  Monthly sweep cadence                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  PHASE 2: FILTER & TAG                                      │
│                                                             │
│  - Tag NAICS family (construction/facilities/IT)            │
│  - Filter: plan F or G only                                 │
│  - Filter: ordering_period_end ≥ today                      │
│  - Compute pool_id from solicitation_identifier             │
│  - Compute pool_awardee_count                               │
│  - Score priority (0–100)                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  PHASE 3: TRIAGE                                            │
│                                                             │
│  For each lead:                                             │
│  - Does NAICS overlap with our capabilities?                │
│  - How big is the vehicle?                                  │
│  - Multi-award → more sub pressure?                         │
│  - Are they small business → self-performance limits?       │
│  Output: priority ranking + analyst notes                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  PHASE 4: ENRICH (top ~50–100 high-priority leads)          │
│                                                             │
│  - Pull active SAM.gov solicitations for each prime         │
│  - Find active task orders under their vehicles             │
│  - Research SBLO contact info                               │
│  - Cross-reference with our vendor/sub database             │
│  Output: one-page prime brief with concrete opportunities   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  PHASE 5: OUTREACH                                          │
│                                                             │
│  - Draft capability statement / intro email                 │
│  - Contact SBLO (warm door)                                 │
│  - Respond to their active SAM solicitations (if any)       │
│  - Track status: sent → responded → meeting → on roster     │
│  - Follow up monthly until response or decline              │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  PHASE 6: SUBCONTRACT WON                                   │
│                                                             │
│  - On roster → task order RFQ received → we price → we win  │
│  - Link subcontract back to the lead record                 │
│  - Track performance → past performance → more work         │
│  - The Coffie flywheel: line item → cash flow → credibility │
│    → past performance → partnerships → contracts            │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Integration with the SAM Pipeline

The two pipelines converge at enrichment:

```
SAM databank                    USASpending
     │                               │
     ▼                               ▼
sam_notices                   subcontracting_leads
     │                               │
     ▼                               ▼
Processor filters             Processor filters
→ solicitations               → priority leads
     │                               │
     ▼                               ▼
sam_fetch (API metadata)      Enrichment (SAM API by UEI)
     │                               │
     ▼                               ▼
AI Triage (solicitation)      Prime Brief (manual + AI)
     │                               │
     ▼                               ▼
Vendor Matching               Outreach (email/call/SBLO)
(sub matching)                      │
     │                               ▼
     ▼                          On Roster
Proposal Drafting                    │
     │                               ▼
     ▼                          Subcontract Quote
Submit Bid                           │
     │                               ▼
     ▼                          Subcontract Won
Contract Won
```

**They feed each other:** When we find a prime through USASpending and then pull their active SAM solicitations, those solicitations go into the SAM pipeline as bid opportunities — but with a different strategy (sub bid, not prime bid). And when we're triaging a SAM solicitation and see a known prime as the incumbent, we cross-reference our USASpending leads to check if they have subcontracting obligations.

---

## 9. Build Sequence

| Step | What | Dependencies |
|------|------|-------------|
| 1 | `subcontracting_leads` table + migration | None |
| 2 | CSV import endpoint (modeled on sam_notices upload) | Step 1 |
| 3 | Processor: filter, tag, pool-group, priority-score | Step 2 |
| 4 | Triage UI: list leads, filter by priority/category, add analyst notes | Step 3 |
| 5 | Enrichment: SAM API by UEI → active solicitations | Step 4 |
| 6 | Outreach tracking: status, contact log, follow-up reminders | Step 4 |
| 7 | Dashboard: pipeline metrics (leads → enriched → in outreach → on roster → won) | Step 6 |

Steps 1–3 are code. Steps 4–7 are code + UI + workflow.

---

## 10. Exit Condition

**Complete when:**
- [ ] `subcontracting_leads` table exists with dedup constraint
- [ ] CSV import processes the 136K-row USASpending file and produces correct counts
- [ ] Processor correctly tags NAICS families, filters for F/G plans, groups pools
- [ ] Priority scoring produces a ranked list that passes a human sanity check
- [ ] Enrichment pulls active SAM solicitations for at least one prime
- [ ] Outreach funnel is defined and trackable
