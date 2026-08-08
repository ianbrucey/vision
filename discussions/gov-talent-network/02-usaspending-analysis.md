# USASpending Analysis — IDV Vehicles & Subcontracting Leads

> 2026-08-05 · Download: IDV types, NAICS 23/56/54/51 · 136,793 IDV rows · 48,572 unique primes

---

## 1. Executive Summary

| Metric | Count |
|--------|-------|
| Total IDV vehicles in download | 136,793 |
| Unique primes holding these vehicles | 48,572 |
| **Active vehicles with subcontracting plan F or G** | **~2,092** |
| Of those: Construction (236/237/238) | **507** |
| Of those: IT Services (5415) | **779** |
| Of those: Facilities/Janitorial/Security/Waste | **646** |
| **Identified multi-award construction MATOC/MACC pools** | **15+ pools with 9–17 awardees each** |

**Bottom line:** The download worked. We have 2,092 active IDV vehicles held by primes who are contractually obligated to subcontract (plan F = Individual Subcontract Plan, plan G = Commercial Subcontract Plan). We can identify the primes, their vehicles, and the multi-award pools they belong to — directly from the CSV, without per-award API enrichment.

---

## 2. What We Downloaded

### 2.1 Filters Applied

| Filter | Selection |
|--------|-----------|
| Award Type | GWAC, Multi-Agency Contract, Other IDC, Requirements, IDIQ, Definite Quantity, FSS, BOA, BPA |
| NAICS | 23 (Construction), 56 (Admin/Support/Waste), 54 (Professional/Scientific/Technical), 51 (Information) |
| Data | Awards + Subawards |

### 2.2 What's in the File

| Field | Content |
|-------|---------|
| `award_or_idv_flag` | All `IDV` — 100% vehicles, zero delivery orders (as expected from the IDV filter) |
| `idv_type` | 71,675 IDC, 41,211 BPA, 16,329 FSS, 4,317 GWAC, 3,261 BOA |
| `naics_code` | Numeric 6-digit codes — exactly what we need |
| `subcontracting_plan_code` | **PRESENT** — F, G, A, B, C, D, E, H values |
| `recipient_uei` / `recipient_name` | Prime identity |
| `potential_total_value_of_award` | Ceiling value (only populated for ~38K vehicles) |
| `ordering_period_end_date` | When the ordering window closes |
| `parent_award_id_piid` / `solicitation_identifier` | Pool grouping keys |

> **Key win:** The `subcontracting_plan` field is INCLUDED in the bulk download. The earlier research suggesting it was only available per-award was wrong for this export format. No per-award API enrichment needed.

---

## 3. Subcontracting Plan Distribution

| Code | Plan Type | Count | Our Interest |
|------|-----------|-------|-------------|
| B | Plan Not Required | 100,116 | ❌ Skip — no subcontracting obligation |
| *(blank)* | Not specified | 21,849 | ❌ Skip |
| C | Plan Required - Incentive Not Included | 4,062 | ⚠️ Maybe — plan exists but no incentive |
| A | Plan Not Included - No Subcontracting Possibilities | 6,068 | ❌ Skip — no subcontracting |
| **F** | **Individual Subcontract Plan** | **3,542** | ✅ **HIGH PRIORITY** — obligated to subcontract |
| **G** | **Commercial Subcontract Plan** | **639** | ✅ **PRIORITY** — obligated (commercial items) |
| D, E, H | Other (incentive, pre-2004, DOD comprehensive) | 517 | ⚠️ Lower priority |

**Total F + G plans: 4,181 vehicles** (3.1% of all IDVs in the download).

---

## 4. Active F/G Vehicles by NAICS Family

Filtered to vehicles with active ordering periods (end date ≥ today or open-ended):

| NAICS Family | Plan F | Plan G | Total | Unique Primes |
|-------------|--------|--------|-------|---------------|
| **IT Services (5415)** | 657 | 122 | **779** | 509 |
| **Construction (236/237/238)** | 499 | 8 | **507** | 252 |
| Janitorial/Landscaping (5617) | 181 | 19 | 200 | 134 |
| Waste/Remediation (562) | 149 | 20 | 169 | 93 |
| Facilities Support (5612) | 142 | 23 | 165 | 116 |
| Security (5616) | 99 | 13 | 112 | 64 |
| Other | 68 | 92 | 160 | 148 |
| **TOTAL** | **1,795** | **297** | **2,092** | — |

### 4.1 Construction Specifically

**507 active construction vehicles with subcontracting obligations across 252 unique primes.**

Top primes by vehicle count:

| Prime | Vehicles | Total Ceiling |
|-------|----------|---------------|
| Whiting-Turner Contracting Co. | 21 | $37.8B |
| Manson Construction Co. | 18 | $3.2B |
| M.A. Mortenson | 16 | $27.1B |
| RQ Construction LLC | 16 | $21.0B |
| BL Harbert International LLC | 15 | $34.7B |
| J&J Maintenance Inc. | 14 | $15.6B |
| Structsure Projects Inc. | 13 | $16.7B |
| Walsh Federal LLC | 12 | $30.9B |
| APTIM Federal Services LLC | 12 | $35.4B |
| Gilbane Federal | 11 | $30.5B |
| Korte Construction Co. | 11 | $21.7B |

**These 11 primes alone hold 159 construction vehicles with ~$240B combined ceiling.**

---

## 5. Multi-Award Construction MATOC/MACC Pools

Identified via shared `solicitation_identifier` (multiple primes awarded off the same RFP):

| Solicitation | Awardees | Likely Program |
|-------------|----------|----------------|
| 6FEC-E6-030292-B | **17** | AFCEC vertical construction SATOC |
| 47PG0220R0003 | **13** | GSA construction IDIQ |
| N6247319R1237 | **12** | NAVFAC Southwest large construction MACC |
| W912EP18R0029 | **11** | USACE dredging MATOC |
| W9128A22R0003 | **11** | USACE Pacific construction MATOC |
| N6247824R4053 | **11** | NAVFAC Hawaii MACC |
| FA890324R0023 | **11** | AFCEC heavy construction MATOC |
| W912DY21R0014 | **10** | USACE medical facilities IDIQ |
| W912DY21R0005 | **10** | USACE energy/resilience IDIQ |
| N6945020R0097 | **10** | NAVFAC Southeast MACC |
| N6247817R4032 | **10** | NAVFAC Pacific MACC |
| W912QR23R0048 | **9** | USACE large construction MATOC |
| W912HY21R0012 | **9** | USACE civil works MATOC |
| W9127815R0021 | **9** | USACE healthcare facilities |
| N6274224R1327 | **9** | NAVFAC Marianas MACC |

**These 15 pools alone contain 164 prime vehicle positions.** Most awardees appear across multiple pools — Whiting-Turner, Hensel Phelps, BL Harbert, Korte, and Mortenson show up repeatedly.

---

## 6. Subawards Data

The subaward CSV (13,813 rows) connects primes to their actual subcontractors:

| Field | Purpose |
|-------|---------|
| `prime_awardee_name` / `prime_awardee_uei` | Who let the subcontract |
| `subawardee_name` / `subawardee_uei` | Who got the subcontract |
| `subaward_amount` | Dollar value |
| `subaward_description` | What the work was |
| `prime_award_naics_code` | NAICS of the prime contract |

**However**, per the sourcing-blueprint, construction primes severely under-report subawards to FSRS. The subaward data should be treated as a bonus signal, not a reliable measure of subcontracting activity.

---

## 7. Answers to the Open Questions

### 7.1 Is `subcontracting_plan` available in the bulk download?

**Yes.** Columns 118–119 contain `subcontracting_plan_code` and `subcontracting_plan`. The earlier concern (from sourcing-blueprint §3.2) that it was only available per-award was incorrect for this export format. No per-award API enrichment needed for the plan flag.

### 7.2 How many active construction IDVs with subcontracting obligations?

**507 vehicles across 252 primes.** That's the outreach target list.

### 7.3 Can we identify multi-award pools?

**Yes** — via `solicitation_identifier`. 15+ construction MATOC/MACC pools identified with 9–17 awardees each. The `parent_award_id_piid` approach didn't work well for construction (those are mostly FSS schedules), but `solicitation_identifier` grouping works cleanly.

### 7.4 What's the value of these vehicles?

Ceiling values are only populated for ~38K of 136K rows. For the 507 active construction F/G vehicles, many show multi-billion-dollar ceilings. But IDV ceilings are often aspirational — the actual obligated dollars come from task orders, which aren't in this download.

---

## 8. Next Steps

### 8.1 Build the Subcontracting Lead Schema

From this data, a subcontracting lead is:

```
prime_name, prime_uei, vehicle_piid, vehicle_type,
naics_codes, plan_type (F/G), ceiling_value,
ordering_period_end, solicitation_identifier,
pool_id (if multi-award), pool_awardee_count
```

### 8.2 Prioritize Outreach

Sort primes by:
1. Plan type (F > G)
2. Number of active vehicles
3. Membership in known multi-award pools (more awardees = more subcontracting pressure)
4. Total ceiling value

### 8.3 Enrichment: Pull Active SAM.gov Solicitations per Prime

For the top ~50 primes, search SAM.gov for active solicitations where the prime is the awardee (using their UEI). This is the "what do they actually need from subs right now?" layer from sourcing-blueprint §5.4.

### 8.4 Cross-Reference with SAM Databank

Match the primes' names/UEIs against the `sam_notices` vendor fields to find solicitations they're bidding on or have won. This closes the loop between "who has an obligation" and "what are they buying."

---

> Generated from: `Contracts_PrimeAwardSummaries_2026-08-05_H05M16S04_1.csv` (136,793 rows, 232MB)
> SQLite DB: `usaspending.db`
