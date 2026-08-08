# GovCon Engine — Sourcing Subsystem Brief

> State 1 · DISCOVERY · 2026-08-05
> Produced by MCE after reading: blueprint, coffie, sourcing-blueprint, build-plan, and the existing Vision codebase.

---

## 1. What We're Building — The Sourcing Layer

The GovCon Engine is a prime contractor that wins federal construction set-asides and delivers through a network of small-business subcontractors. The **sourcing layer** is the intake — it must answer two questions every day:

| Question | Source | What it produces |
|----------|--------|------------------|
| "What can we bid right now?" | SAM.gov | Live bid feed — active solicitations filtered to construction NAICS, small-business set-asides, within response window |
| "Which primes are obligated to subcontract to us?" | USASpending.gov | Subcontracting leads — IDIQ/MATOC/GWAC vehicle holders with subcontracting plan obligations |

Everything downstream — AI triage, vendor matching, pricing requests, proposal drafting — consumes what sourcing produces. If sourcing is wrong or incomplete, nothing else works.

### The Two Pipelines (from sourcing-blueprint.md §2)

**Pipeline A — Live Bid Feed (SAM.gov)**
- Daily metadata pull: construction NAICS families 236/237/238, SB set-asides (SBA, SDVOSBC, HZC, 8A, WOSB), active with response-date window
- Async attachment retrieval + OCR (decoupled to respect rate limits)
- Feeds into AI triage → vendor matching → quoting → response

**Pipeline B — Subcontracting Leads (USASpending.gov)**
- Weekly/monthly sweep: IDV vehicles in construction NAICS awarded last 1–3 years
- Identify multi-award pools → build lead per prime (name, UEI, vehicle ID, NAICS, plan flag, sub volume)
- Enrichment: pull each target prime's active SAM.gov solicitations to extract concrete sub scope
- Feeds into prime outreach → subcontracting opportunity pipeline

### Key Regulatory Rules Encoded (from sourcing-blueprint.md §4)

- **FAR 19.702(a)**: Subcontracting plan required for contracts >$900K (>$2M for construction). Small business primes exempt.
- **FAR 52.219-14**: Limitations on subcontracting — construction primes must self-perform ≥15% (general) or ≥25% (specialty trade).
- **Plan flag filter**: `plan = F (Individual)` or `G (Commercial)` = highest-value outreach targets.

---

## 2. What Already Exists — Reuse Inventory

> This is a brownfield project. Vision already has production-ready infrastructure for federal solicitation processing. Below is what we reuse, extend, or replace.

### 2.1 REUSE — Take As-Is

| Component | Location | What it does for sourcing |
|-----------|----------|---------------------------|
| SAM.gov API client | `backend/ingestion/sam_client.py` | `fetch_notice()`, `fetch_description()`, `download_resource_link()` — production-tested against SAM.gov v2 API |
| SAM notices CSV import | `backend/api/routes/sam_notices.py` | Bulk CSV upload via PostgreSQL COPY (12K rows/sec), dynamic query with NAICS/set-aside/date filters, full-text search — this IS the databank approach from build-plan.md |
| Background job queue | `backend/ingestion/worker.py` | PostgreSQL-backed, `SKIP LOCKED` concurrency, job chaining (`sam_fetch` → `triage` → `vendor_matching`) |
| Document ingestion pipeline | `backend/ingestion/dispatcher.py` + `worker.py` | PDF/DOCX/XLSX → sections → blocks → pgvector embeddings — this IS the Pass 2 attachment OCR pipeline |
| AI agent pattern | Claude Agent SDK + custom MCP servers | Every LLM workflow in Vision uses this exact pattern — triage, enrichment, extraction, vendor matching |
| `solicitations` table + manager | `backend/core/solicitation.py` | Already has `notice_id` (UNIQUE), `naics_code`, `set_aside_type`, `response_deadline`, `agency`, `place_of_performance`, triage artifacts |
| `vendors` table (5.5M+ rows) | `backend/core/vendor.py` | NAICS-coded, socioeconomic flags, full-text search, trigram indexes — ready for subcontractor matching |
| FAR lookup | Chat tools | Authoritative FAR text by citation — useful for compliance verification |
| Vendor matching pipeline | `backend/core/vendor_match.py` + `backend/ingestion/vendor_matching.py` | Tiered SQL pooling (exact NAICS → family → capabilities FTS) + LLM ranking — adaptable for sub matching |
| Mailgun outreach | `backend/core/email_mailgun.py` + webhook routes | Reply-token correlation, per-vendor threads, inbound tracking |
| Dynamic views | `frontend/src/components/views/` | Tables, cards, charts from JSON envelopes — ready for opportunity dashboards |

### 2.2 EXTEND — Modify Existing

| What | What to add | Why |
|------|-------------|-----|
| `solicitations` table | `solicitation_type` column to distinguish: `live_bid` (SAM.gov opportunity) vs `sub_lead` (USASpending prime lead) | Current schema assumes all solicitations are bid targets; we need a second entity type for prime leads |
| `sam_notices` table | Add `source` column (`sam_api` vs `sam_databank`) | Current import assumes databank CSV; we want to track provenance |
| `vendors` table | Add `vendor_type` = `subcontractor` with trade/specialty fields, bonding capacity, license storage | Current vendors are potential subs for outreach; we need to model them as our own subcontractor network with credentials |
| `vendor_matches` table | Add `match_direction`: `we_need_them` (we're prime, need subs) vs `they_need_us` (they're prime, we're sub) | Current model assumes one direction (we're looking for vendors to help us); the subcontracting-lead pipeline reverses it |
| `jobs` table + worker | Add `usaspending_sweep` and `prime_enrichment` job types | New job types for Pipeline B |
| SAM databank CSV import | Add `current_set_aside` filter for "Total Small Business" vs "Full and Open" — the open question from build-plan.md | Need to test both and compare volume |
| Frontend case tabs | Add "Subcontracting Leads" tab and "Pipeline Dashboard" tab | New views for the two-pipeline model |

### 2.3 CREATE — Net New

| What | Purpose | Justification |
|------|---------|---------------|
| USASpending.gov API client | Pull IDV vehicles, awards, plan flags, sub-award data | Does not exist in codebase; SAM.gov client is the template to follow |
| `subcontracting_leads` table | Store prime leads: name, UEI, vehicle ID, NAICS scope, plan flag, sub volume, pool membership | Separate domain entity — NOT a solicitation |
| `idiq_pools` table | Store multi-award IDIQ/MATOC/GWAC pools: base contract, awardees, order window, NAICS scope | Needed for the "identify multi-award pools" step in sourcing-blueprint.md §5.3 |
| `subcontractor_credentials` table | Store vetted sub credentials: licenses, insurance, bonding, certifications | Net new domain — the subcontractor network from blueprint.md |
| Sourcing dashboard frontend | Live counters: opportunities in pipeline, by status, by trade, by deadline bucket | The "what success looks like" view from blueprint.md |
| USASpending sweep scheduler | Cron-like trigger for weekly IDV sweeps | Not an existing pattern in Vision (jobs are event-driven, not scheduled) |

---

## 3. Open Questions That Block Progress

These are the unknowns surfaced in build-plan.md that we must resolve before writing schema or code:

### 3.1 SAM.gov Databank: Volume & Filter Strategy

**The problem (from build-plan.md):** The SAM databank doesn't filter by NAICS code — only by designation (set-aside type) and a few other fields. A "Total Small Business" filter across all NAICS could return 2,000+ results. Full and Open could return 150,000.

**What we need to answer:**
1. How many active construction (236/237/238) SB set-aside solicitations are posted **per day**?
2. What is the volume difference between "Total Small Business" and individual set-aside types (SBA, SDVOSBC, HZC, 8A, WOSB)?
3. Can we get sufficient coverage with set-aside-filtered databank pulls + post-import NAICS filtering, or do we need the SAM.gov API for targeted queries?
4. What is the overlap between databank CSV results and SAM.gov API results for the same filters?

**How to answer:** Run one big databank pull (last 365 days, all SB set-asides), import through the existing `sam_notices` pipeline, then run NAICS-family distribution queries. This gives us empirical volume data in under an hour.

### 3.2 USASpending.gov: Data Model & Volume

**The problem (from build-plan.md):** "With the USA Spending, I'm not quite sure how that one is going to work yet." The sourcing-blueprint.md §3.2 confirms two hard limits: (a) construction sub-award reporting is thin (only 1 of top 40 primes reported any), and (b) required goal percentages are NOT in USASpending.

**What we need to answer:**
1. How many active IDV vehicles in construction NAICS (236/237/238) with subcontracting plan flags exist?
2. What fields does the USASpending API ACTUALLY return for an award/IDV endpoint? (The blueprint §3.1 lists expected fields — we need to verify against live API responses.)
3. How many unique primes hold these vehicles, and what's the overlap with vendors already in our `vendors` table?
4. How do we link a USASpending vehicle to that prime's active SAM.gov solicitations? (The enrichment step in sourcing-blueprint.md §5.4)

**How to answer:** Write a throwaway Python script that hits the USASpending API for construction NAICS awards, dumps raw JSON responses, and produces a field coverage report. Don't build the pipeline until we've seen the data.

### 3.3 IDIQ Pool Identification Heuristic

**The problem:** USASpending doesn't tag multi-award pools explicitly. The sourcing-blueprint.md §5.3 proposes: "same base contract + sequential awardee suffixes + identical order-window = one MATOC/IDIQ pool."

**What we need to answer:**
1. Does this heuristic hold against real data? (Test against known pools: FA442726G, W519TC26GA, 692M1526G.)
2. What's the false-positive rate?
3. Are there pools where the heuristic breaks (non-sequential suffixes, different order windows per awardee)?

**How to answer:** Pull the three known pools from USASpending, apply the heuristic manually, and validate.

### 3.4 Data Freshness & Cadence

**What we need to answer:**
1. How often does the SAM.gov databank refresh? (Hourly? Daily?)
2. What's the actual lag on USASpending award data vs. SAM.gov? (Blueprint says ~2–4 weeks — verify.)
3. What's the rate-limit behavior on both APIs?

---

## 4. Concrete Next Steps — Ordered by Dependency

### Phase 0: Data Exploration (This Week — No Code, Just Scripts)

| Step | Action | Output | Time |
|------|--------|--------|------|
| 0.1 | Run SAM databank pull: last 365 days, all SB set-asides. Import via existing `sam_notices` pipeline. | Row counts by NAICS family, set-aside type, posting date. Answers §3.1. | 1 hour |
| 0.2 | Write a throwaway Python script to hit USASpending API for construction NAICS IDV awards (2023–2026). Dump raw JSON. | Field coverage report. Answers §3.2. | 2 hours |
| 0.3 | Validate the pool-identification heuristic against the 3 known IDIQ pools. | Confirmed or refined heuristic. Answers §3.3. | 1 hour |
| 0.4 | Compare SAM databank CSV results vs. SAM API results for same filter criteria. | Overlap analysis. Informs whether we need API or databank is sufficient. | 1 hour |

### Phase 1: Schema & API Contracts (After Phase 0 Answers Are In)

| Step | Action | Depends On |
|------|--------|------------|
| 1.1 | Write `01-sourcing-schema.sql`: `subcontracting_leads`, `idiq_pools`, `subcontractor_credentials` tables + extensions to `solicitations`, `vendors`, `vendor_matches` | Phase 0 complete |
| 1.2 | Write USASpending API client (`backend/ingestion/usaspending_client.py`) following the `sam_client.py` pattern | 1.1 |
| 1.3 | Write `02-sourcing-api-contract.json`: endpoints for lead list/query, pool view, sweep trigger | 1.1 |
| 1.4 | Write `03-sourcing-fixtures.json`: real SAM notices (from databank), real USASpending award rows, real IDIQ pool data | Phase 0 data |

### Phase 2: Pipeline Wiring

| Step | Action | Depends On |
|------|--------|------------|
| 2.1 | Add `usaspending_sweep` and `prime_enrichment` job types to worker | 1.2 |
| 2.2 | Wire SAM databank → opportunity pipeline (pass-through to existing triage) | 1.1 |
| 2.3 | Wire USASpending → subcontracting leads pipeline (new path) | 2.1 |
| 2.4 | Build sourcing dashboard frontend (live counters, pipeline view) | 1.1, 1.3 |

---

## 5. The Risk Nobody's Talking About

**Construction sub-award reporting is nearly nonexistent.** The sourcing-blueprint.md §3.2(a) found that of the top-40 construction awards by value, only 1 prime reported any sub-awards. Dragados ($3.1B), Hensel Phelps ($760M), Whiting-Turner ($400M), Kiewit ($515M) all report zero.

This means the `subaward_count` and `total_subaward_amount` fields in USASpending are **not reliable signals** for construction. We cannot use "reported sub-awards" as a filter criterion. The plan flag (`F` or `G`) is the primary signal — it tells us the prime HAS a subcontracting obligation, even if they haven't reported against it.

**Mitigation:** Weight the plan flag heavily. Treat sub-award dollar amounts as a bonus signal only. The enrichment step (pulling the prime's active SAM.gov solicitations) is where we actually find the concrete subcontracting opportunities.

---

## 6. What We're NOT Building (Yet)

Per sourcing-blueprint.md §7:
- **DLA/DIBBS** — No modern REST API; high engineering overhead for low relative margin. HELD.
- **Municipal/state portals** — Defer until federal pipeline is stable. Phase 2+.
- **USASpending as live bid source** — It's a historical award database, not a solicitation feed. Never treat it as one.

---

## 7. Success Verdict — How We Know Sourcing Works

- [ ] **V-01:** SAM.gov pipeline produces ≥200 active construction SB set-aside solicitations per week, with full metadata (NAICS, agency, deadline, set-aside type, attachments).
- [ ] **V-02:** USASpending pipeline identifies ≥50 primes holding active IDIQ/MATOC/GWAC vehicles in construction NAICS with subcontracting plan obligations.
- [ ] **V-03:** IDIQ pool identification heuristic correctly groups ≥90% of known multi-award vehicles.
- [ ] **V-04:** Enrichment pass successfully links ≥80% of target primes to their active SAM.gov solicitations.
- [ ] **V-05:** Sourcing dashboard shows live counters for both pipelines — opportunities in queue, by status, by trade, by deadline bucket.
- [ ] **V-06:** Daily ingestion runs without manual intervention. New opportunities appear within 24 hours of SAM.gov posting.

---

## 8. Approval Gate

**Status:** [ ] DRAFT  [ ] APPROVED

**Approved By:**

**Date:**

---

> ⚠️ **NEXT:** This Brief must be Approved before entering State 1.5 (Archaeology — formal infrastructure scan) or State 2 (Architecture — schema/API specs). The Phase 0 data exploration scripts can run in parallel with approval.
>
> Once approved, the Council phase produces: `01-sourcing-schema.sql`, `02-sourcing-api-contract.json`, `03-sourcing-fixtures.json`.
