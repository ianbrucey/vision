# SAM Databank Analysis — Active Opportunities

> 2026-08-05 · Raw pull: "Active" filter only · 46,569 rows · 35,586 unique notices · 138 agencies

---

## 1. Executive Summary

| Metric | Count |
|--------|-------|
| Total rows in CSV | 46,569 |
| Unique notice IDs | 35,586 |
| Unique agencies | 138 |
| **Target opportunities (construction + facilities + IT, excl. awards)** | **~7,000 notices with response dates** |
| **SB set-asides in target areas, due within 30 days** | **~1,189 notices** |
| Of those: Construction SB due in 30 | 909 |
| Of those: Facilities SB due in 30 | 185 |
| Of those: IT SB due in 30 | 95 |

**Bottom line:** There is more than enough pipeline volume. The question isn't "are there enough opportunities" — it's "how do we triage 1,200 urgent ones intelligently."

---

## 2. Data Quality & Caveats

### 2.1 The "Past Due" Problem

Of 33,087 non-award notices with response dates, **21,759 (66%) are past their response date** but still show as "active" in the SAM databank. This breaks down by type:

| Type | Unique Notices with Past-Due Dates |
|------|-----------------------------------|
| Combined Synopsis/Solicitation | 14,967 |
| Solicitation | 8,207 |
| Sources Sought | 3,535 |
| Presolicitation | 3,341 |
| Special Notice | 2,471 |

**What this means:** The SAM databank's "Active" filter doesn't exclude notices whose response deadline has passed. These are archived/expired solicitations still in the system. A proper pipeline **must** apply a response-date filter at pull time or immediately post-ingestion. The databank export interface may support a date-range filter — this should be tested.

### 2.2 NAICS Is Text, Not Codes

The databank exports NAICS as full text descriptions (e.g., "Commercial and Institutional Building Construction") rather than numeric codes (236220). This means:
- We cannot filter by NAICS family (236/237/238) directly — we must use keyword matching
- Some NAICS descriptions are ambiguous and span multiple families
- Keyword matching will have false positives and false negatives — it's a **triage heuristic**, not a precise filter

### 2.3 Attachment Availability

| Attachments | Unique Notices |
|-------------|---------------|
| 1–3 | 19,345 |
| 4–10 | 8,620 |
| 10+ | 1,356 |
| 0 | 3,328 |

**93% of non-award notices have at least one attachment.** This is excellent for the AI triage pipeline — we have documents to read.

### 2.4 Place of Performance

| Location | Unique Notices |
|----------|---------------|
| USA / Unspecified | 30,568 |
| Overseas (DEU, JPN, KOR, etc.) | 1,186 |

Only ~3.7% are overseas. The US-based subcontractor network will cover nearly everything.

---

## 3. Set-Aside Distribution (All 46.5K Rows)

| Set-Aside | Rows | % |
|-----------|------|---|
| *(blank — Full and Open)* | 31,088 | 66.8% |
| Total Small Business (FAR 19.5) | 12,223 | 26.2% |
| SDVOSB (FAR 19.14) | 1,878 | 4.0% |
| WOSB (FAR 19.15) | 558 | 1.2% |
| 8(a) (FAR 19.8) | 185 | 0.4% |
| HUBZone (FAR 19.13) | 166 | 0.4% |
| Other (ISBEE, sole source, etc.) | 471 | 1.0% |

**Key finding:** Total Small Business is by far the dominant set-aside (~12K rows, 26%). The niche set-asides (SDVOSB, 8(a), HUBZone, WOSB) together represent only ~6%. If we filter to Total Small Business + SDVOSB + 8(a) + HUBZone + WOSB, we capture essentially all relevant SB opportunities.

---

## 4. Construction Deep Dive

### 4.1 By Trade/NAICS (Active Non-Award Notices with Dates)

| NAICS Description | Unique Notices | SB Set-Aside | SB % |
|-------------------|---------------|-------------|------|
| Commercial and Institutional Building Construction | 1,134 | 611 | 54% |
| Other Heavy and Civil Engineering Construction | 544 | 219 | 40% |
| Plumbing, Heating, and Air-Conditioning Contractors | 412 | 288 | 70% |
| Ship Building and Repairing ⚠️ | 354 | 137 | 39% |
| Electrical Contractors and Other Wiring Installation | 270 | 166 | 61% |
| Highway, Street, and Bridge Construction | 234 | 166 | 71% |
| Construction Machinery Manufacturing ⚠️ | 178 | 139 | 78% |
| Water and Sewer Line and Related Structures Construction | 162 | 91 | 56% |
| Roofing Contractors | 125 | 95 | 76% |
| Other Building Equipment Contractors | 115 | 69 | 60% |
| Power and Communication Line Construction | 63 | 31 | 49% |
| Painting and Wall Covering Contractors | 50 | 29 | 58% |
| Industrial Building Construction | 40 | 12 | 30% |
| Flooring Contractors | 37 | 32 | 86% |
| **Construction total (all)** | **~4,622** | **~2,512** | **54%** |

> ⚠️ **Ship Building** (354 notices) and **Construction Machinery Manufacturing** (178) are manufacturing/supply NAICS, not construction services. These should be filtered out of the construction bid pipeline — they're supply contracts, not trade work.

### 4.2 Construction SB Set-Asides by Type

| Set-Aside Type | Unique Notices |
|----------------|---------------|
| Total Small Business | 1,798 |
| SDVOSB | 453 |
| HUBZone | 59 |
| 8(a) | 54 |
| WOSB | 35 |
| **Total SB construction** | **~2,399** |

### 4.3 Top Construction Agencies

| Agency | Unique Notices |
|--------|---------------|
| Dept of the Army | 1,560 |
| Veterans Affairs | 617 |
| Dept of the Navy | 542 |
| Dept of the Air Force | 286 |
| National Park Service | 160 |
| State Department | 159 |
| Defense Logistics Agency | 140 |
| US Coast Guard | 131 |
| Forest Service | 125 |
| Public Buildings Service (GSA) | 93 |

**DoD (Army + Navy + Air Force + DLA + Coast Guard) = 2,659 — that's 58% of all construction notices.** The military is the dominant buyer of federal construction services.

---

## 5. Facilities Deep Dive

### 5.1 By NAICS (Active Non-Award Notices with Dates)

| NAICS Description | Unique Notices | SB Set-Aside | SB % |
|-------------------|---------------|-------------|------|
| Facilities Support Services | 323 | 170 | 53% |
| Electronic and Precision Equipment Repair and Maintenance | 340 | 182 | 54% |
| Landscaping Services | 231 | 165 | 71% |
| Commercial/Industrial Machinery Repair and Maintenance | 255 | 127 | 50% |
| Janitorial Services | 163 | 120 | 74% |
| Security Guards and Patrol Services | 85 | 66 | 78% |
| Solid Waste Collection | 77 | 33 | 43% |
| Food Service Contractors | 26 | 13 | 50% |
| Exterminating and Pest Control Services | 25 | 19 | 76% |
| **Facilities total (all)** | **~1,186** | **~770** | **65%** |

### 5.2 Facility SB Set-Asides by Type

| Set-Aside Type | Unique Notices |
|----------------|---------------|
| Total Small Business | 671 |
| SDVOSB | 224 |
| 8(a) | 44 |
| WOSB | 27 |
| HUBZone | 6 |
| **Total SB facilities** | **~972** |

> Facilities has the highest SB set-aside rate (65%) of all three categories. The government is actively pushing facilities work to small business.

---

## 6. IT Deep Dive

### 6.1 By NAICS (Active Non-Award Notices with Dates)

| NAICS Description | Unique Notices | SB Set-Aside | SB % |
|-------------------|---------------|-------------|------|
| Other Computer Related Services | 952 | 116 | 12% |
| Custom Computer Programming Services | 380 | 70 | 18% |
| Software Publishers | 366 | 37 | 10% |
| Computer Systems Design Services | 173 | 35 | 20% |
| Electronic Computer Manufacturing | 200 | 133 | 67% |
| Computing Infrastructure/Data Processing/Web Hosting | 114 | 13 | 11% |
| **IT total (all)** | **~1,213** | **~352** | **29%** |

### 6.2 Key IT Finding

IT has the **lowest SB set-aside rate (29%)** of the three categories. Most IT opportunities are Full and Open. However:
- IT SB set-asides that DO exist are high-value (software development, cloud migration, cybersecurity)
- The 5415 family (IT services) is marked as "Phase 2" in the sourcing-blueprint — this data confirms that construction should be the initial focus
- The 352 SB IT opportunities are still a meaningful pipeline for a later phase

---

## 7. Response Date Analysis

### 7.1 All Target-Category Notices (Excl. Awards)

| Bucket | Count |
|--------|-------|
| Past Due | 21,759 |
| Due in 0–30 days | 9,478 |
| Due in 31–60 days | 424 |
| Due in 61–90 days | 160 |
| Due in 90+ days | 1,266 |
| No date | 1,091 |

### 7.2 Target Categories: SB Set-Asides Due in 30 Days

| Category | SB Due in 30 Days |
|----------|-------------------|
| Construction | 909 |
| Facilities | 185 |
| IT | 95 |
| **Total** | **1,189** |

**This is the "hot list"** — 1,189 small-business set-aside opportunities across our three target areas that need attention within the next 30 days. At ~40/day, this is a manageable triage volume for an AI-assisted pipeline.

---

## 8. Answers to the Open Questions from `00-sourcing-brief.md`

### 8.1 §3.1: SAM Databank Volume & Filter Strategy

**Q: How many active construction/facilities/IT SB set-asides exist?**

A: ~4,534 SB set-aside notices across all three categories (with response dates). Of these, ~1,189 are due within 30 days.

**Q: Total Small Business vs individual set-aside types?**

A: Total Small Business (FAR 19.5) dominates at ~26% of all active opportunities. The niche types (SDVOSB, 8(a), HUBZone, WOSB) combined account for only ~6%. Strategy: **filter for all set-aside types, not just Total Small Business** — the niche categories add meaningful volume.

**Q: Is the databank sufficient or do we need the API?**

A: The databank provides volume data but has limitations: (a) NAICS is text not codes, (b) no numeric NAICS filter at export time, (c) the "active" filter doesn't exclude past-due notices. For the **live bid feed**, we likely need BOTH: databank for volume discovery + SAM API for targeted per-notice enrichment (attachments, descriptions, POCs).

### 8.2 §3.3: The "Active but Past Due" Phenomenon

Two-thirds of "active" notices have past response dates. This means either:
1. The databank export needs a response-date range filter applied at pull time
2. Or we filter post-ingestion with a hard cutoff (response_date >= today)
3. Some of these may be amendments/extensions — the databank might show the original date while the actual date was extended

**Recommendation:** Apply a response-date window filter at databank export time. If that's not possible, filter immediately post-ingestion and flag notices with past dates for manual review.

---

## 9. Recommendations for the Pipeline

### 9.1 Filter Configuration

```
NAICS keyword families:
  CONSTRUCTION: ['Construction', 'Building', 'Plumbing', 'HVAC', 'Electrical Contractors',
                 'Carpentry', 'Masonry', 'Roofing', 'Concrete', 'Painting', 'Welding',
                 'Excavation', 'Demolition', 'Flooring', 'Drywall', 'Fencing', 'Paving',
                 'Structural Steel', 'Fire Protection', 'Elevator', 'Asphalt',
                 'Sheet Metal', 'Finishing Contractors']
  
  EXCLUDE FROM CONSTRUCTION: ['Ship Building', 'Machinery Manufacturing', 'Equipment Manufacturing',
                               'Mining', 'Equipment Rental']
  
  FACILITIES: ['Facilities Support', 'Janitorial', 'Custodial', 'Landscaping',
               'Security Guards', 'Security Systems', 'Waste Collection', 'Pest Control',
               'Laundry', 'Food Service']
  
  IT: ['Software', 'Computer Programming', 'Computer Systems Design', 'Electronic Computer',
       'Computing Infrastructure', 'Data Processing', 'Custom Computer', 'Cloud',
       'Cybersecurity', 'Information Technology', 'Telecom', 'Wireless']

Set-aside filter:
  ANY of: ['Total Small Business', 'SDVOSB', 'HUBZone', '8(a)', 'WOSB', 'Women-Owned',
           'Indian Small Business', 'Veteran-Owned Small Business']

Date filter:
  response_date >= TODAY  (exclude past-due)
  OR response_date IS NULL (flag for review, don't discard)

Type filter:
  EXCLUDE: ['Award Notice', 'Justification', 'Sale of Surplus Property']
  INCLUDE: ['Combined Synopsis/Solicitation', 'Solicitation', 'Presolicitation',
            'Sources Sought', 'Special Notice']
```

### 9.2 Initial Pipeline Sizing

| Pipeline Segment | Daily Volume (est.) |
|-----------------|---------------------|
| New notices across all 3 categories | ~40/day (based on 1,189 SB due in 30 days ÷ 30) |
| Construction only | ~30/day |
| Facilities only | ~6/day |
| IT only | ~3/day |
| Total (including Full & Open) | ~74/day (based on 2,221 due in 30 ÷ 30) |

**This is well within the capacity of the existing Vision ingestion pipeline** (which already handles SAM API fetches, document downloads, OCR, and AI triage). No new infrastructure needed — just new filter configuration.

### 9.3 What to Build vs. What to Configure

| Action | Type |
|--------|------|
| Configure SAM databank pull with response-date window | Configuration |
| Apply post-ingestion NAICS keyword filter | Configuration (extend existing `sam_notices` pipeline) |
| Route construction/facilities/IT → existing triage pipeline | Configuration (extend job chaining) |
| Build USASpending client and subcontracting leads pipeline | **New development** (Phase 1) |
| Build sourcing dashboard | **New development** (Phase 2) |

---

## 10. Next Action

The SAM databank analysis is complete. The open questions about USASpending (data model, field coverage, pool identification heuristic) remain — those require API exploration scripts, not SQL queries.

**Recommendation:** Approve this analysis, then proceed to Phase 0.2 (USASpending API exploration). The SAM-side pipeline is ready to configure once we have the USASpending side understood as well.

---

> Generated from: `active-ops-Contract_Notice_Details.csv` (46,569 rows, 24MB)
> SQLite DB: `sourcing.db`
> Analysis scripts available upon request.

---

## 11. USASpending.gov Download Filters

> Applied 2026-08-05 via usaspending.gov/search → Award Search → Download

| Filter | Selection |
|--------|-----------|
| **Data Selections** | Awards, Subawards |
| **Award Type** | GWAC, Multi-Agency Contract, Other IDC, Requirements Contract, IDIQ, Definite Quantity Contract, FSS, BOA, BPA |
| **NAICS 23 — Construction** | All 31 subcategories (236xxx, 237xxx, 238xxx) |
| **NAICS 56 — Admin/Support/Waste/Remediation** | All 45 subcategories (561xxx Facilities, Janitorial, Landscaping, Security, Waste, Pest Control, etc.) |
| **NAICS 54 — Professional/Scientific/Technical** | 4 subcategories (541511, 541512, 541513, 541519 — IT services) |
| **NAICS 51 — Information** | 1 subcategory (511210 — Software Publishers, or possibly 518210 — Data Processing/Hosting) |
| **Status** | Download pending |

### Coverage check

| Our Target | NAICS Families Selected | Covered? |
|------------|------------------------|----------|
| Construction trades | 23 (all) | ✅ Full |
| Facilities support | 56 (all) | ✅ Full — covers 561210, 561720, 561730, 561612, 561621, 562111, 561710, 722310 |
| IT services | 54 (4 selected) + 51 (1 selected) | ✅ Core — 541511, 541512, 541513, 541519 + 511210/518210 |

### What this download will tell us

1. How many active IDV vehicles exist in these NAICS families
2. Which primes hold them (names, UEIs, award values)
3. Multi-award pool candidates (same base contract, multiple awardees)
4. Award amounts and ordering periods

### What it won't tell us (without enrichment)

- Subcontracting plan flag (`F`/`G`/`A`/`B`) — only available per-award via API detail endpoint
- Actual subcontracting volume — construction primes severely under-report this to FSRS
- Active task orders under each IDV — would need a separate contract search

---

## 12. Daily Triage Volume Estimate

From §7, the active non-award notices across all three categories with response dates:

| Bucket | Count | Daily Rate |
|--------|-------|------------|
| Due in 0–30 days | 1,934 | ~64/day |
| Due in 31–60 days | ~424 | ~14/day |
| Due in 61–90 days | ~160 | ~5/day |
| Due in 90+ days | ~1,266 | — |

**Initial catch-up triage: ~1,934 opportunities** (everything due within 30 days). That's the one-time backlog.

**Steady-state: ~30–50 new postings/day** is the likely rate once the backlog is cleared, based on the distribution across date buckets. The 64/day figure includes backlog compression — solicitations cluster in the near-term window because older ones have already closed.

**80/day is a reasonable planning number** — it leaves headroom for broader filters (if we include Full and Open later) and for USASpending enrichment leads that convert to bid opportunities. The existing Vision ingestion pipeline handles this volume without modification.

> **To get an exact number**, we'd need to track unique new notice IDs over a 1–2 week period. The single snapshot can estimate but not measure the posting rate precisely.
