idt adg

# Strategy Execution Plan — Targeted Opportunity Sourcing

> **Status:** Living document — update as verticals and priorities evolve
> **Date:** July 22, 2026

---

## 1. The Playbook

Based on the strategy doc and attack plan, here's the complete sourcing playbook organized by priority, vertical, and data source.

### How to Read This

Each vertical has:

- **What to search for** — the exact queries the agent can run right now
- **Which data source** — forecasts (has value data), SAM notices (no value data, uses NAICS/text), or both
- **What to do with results** — next action after finding matching opportunities

---

## 2. Priority Verticals — Forecasts (Value Data Available)

Forecasts have `estimated_value_low` and `estimated_value_high` columns. You can filter by exact dollar thresholds. These are pre-solicitation — early engagement opportunities.

### P0: IT Projects — All Values

**Why:** Your core vertical. Software renewals (ServiceNow, Datadog, GitLab) are recurring, high-margin, and sourced through Carahsoft/EC America. Small IT projects are accessible entry points.

**Agent query:**

```
query_forecast_opportunities({
  q: "IT software license renewal computer services",
  order_by: "estimated_value_low",
  order_dir: "ASC"
})
```

Plus NAICS-specific:

```
query_forecast_opportunities({
  naics_code: "541519"
})  // Other Computer Related Services — 866 entries
query_forecast_opportunities({
  naics_code: "541512"
})  // Computer Systems Design — 160 entries  
query_forecast_opportunities({
  naics_code: "513210"
})  // Software Publishers — 95 entries
```

**Immediate targets:** The 271 entries under SAT in 541519 alone. Focus on software renewals and small IT services.

---

### P1: Total Small Business Set-Asides — Ascending by Value

**Why:** SB set-asides are your primary market. The SAT strategy applies: under $350K, you can subcontract 100%. Above $350K, you need similarly situated partners.

**Agent query:**

```
query_forecast_opportunities({
  set_aside: "Small Business",
  order_by: "estimated_value_low",
  order_dir: "ASC"
})
```

**Breakdown:**

- 795 SB set-asides under SAT ($350K) — these are direct targets
- 2,753 SB set-asides over SAT — need similarly situated partners (Four Points, etc.)

**Agency focus:** Interior (1,635 SB), Agriculture (1,379 SB), GSA (141 SB), VA (84 SB)

---

### P2: Unrestricted Under $500K — Ascending by Value

**Why:** These are rare (only 16 in forecasts) but valuable — unrestricted means you can compete as a small business without set-aside restrictions. The SAT subcontracting strategy applies.

**Agent query:**

```
query_forecast_opportunities({
  value_under: 500000,
  order_by: "estimated_value_low",
  order_dir: "ASC"
})
// Then manually filter out SB set-asides to find true unrestricted
```

**Reality check:** Only 16 unrestricted under $500K in the entire forecast database. The unrestricted-under-SAT play is thin. SB set-asides are the primary strategy.

---

### P3: Small-Value Vertical Report — Under $150K, Specific Industries

**Why:** These are the "easy wins" — small dollar, low complexity, accessible to any small business. The full list of 1,413 forecasts under $150K is too broad; this report narrows to specific verticals.

**Agent queries (run each separately or combine):**

```
// IT & Software
query_forecast_opportunities({
  value_under: 150000,
  q: "IT software computer license",
  order_by: "estimated_value_low"
})

// Office Supplies
query_forecast_opportunities({
  value_under: 150000,
  q: "office supplies paper furniture",
  naics_code: "423210"  // Office Supplies Merchant Wholesalers
})

// Cleaning Supplies
query_forecast_opportunities({
  value_under: 150000,
  q: "cleaning janitorial supplies",
  naics_code: "561720"  // Janitorial Services
})

// Medical Supplies (PRIORITY)
query_forecast_opportunities({
  value_under: 150000,
  q: "medical surgical supplies equipment",
  naics_code: "423450"  // Medical Equipment Merchant Wholesalers
})

// Lab Equipment
query_forecast_opportunities({
  value_under: 150000,
  q: "laboratory equipment analytical instruments",
  naics_code: "334516"  // Analytical Laboratory Instrument Manufacturing
})

// Small Motor Vehicles (ATVs, snowmobiles, motorcycles)
query_forecast_opportunities({
  value_under: 150000,
  q: "ATV snowmobile motorcycle vehicle",
  naics_code: "336999"  // All Other Transportation Equipment Manufacturing
})

// Appliances
query_forecast_opportunities({
  value_under: 150000,
  q: "appliances refrigerator microwave laundry",
  naics_code: "335220"  // Major Household Appliance Manufacturing
})

// Landscaping & Small Construction
query_forecast_opportunities({
  value_under: 150000,
  q: "landscaping grounds maintenance fencing small construction repair",
  naics_code: "561730"  // Landscaping Services
})
```

---

## 3. Priority Verticals — SAM Notices (No Value Data)

SAM notices don't have dollar values in the databank CSV. Strategy: use NAICS codes, full-text search, and set-aside filters to approximate. Value data would require downloading and parsing each solicitation's attachments.

### IT Projects

```
query_sam_notices({
  q: "IT software license computer services renewal",
  status: "active",
  current_set_aside_code: "SBA"  // SB set-asides only
})
```

Plus NAICS-specific:

```
query_sam_notices({
  naics_code: "541519",
  status: "active"
})
```

### Office / Cleaning / Janitorial

```
query_sam_notices({
  q: "office supplies cleaning janitorial",
  status: "active"
})
```

### Medical Supplies

```
query_sam_notices({
  q: "medical surgical supplies equipment",
  status: "active",
  current_set_aside_code: "SBA"
})
```

### Lab Equipment

```
query_sam_notices({
  q: "laboratory equipment analytical instruments",
  status: "active"
})
```

### Small Vehicles / Appliances

```
query_sam_notices({
  q: "ATV snowmobile motorcycle appliance refrigerator",
  status: "active"
})
```

### Landscaping / Small Construction

```
query_sam_notices({
  q: "landscaping grounds maintenance fencing small construction repair",
  status: "active"
})
```

---

## 4. SAM.gov Live API — Gap Detection

Your databank CSV is a snapshot. New opportunities appear daily. Use the live API to find what you're missing:

```
search_sam_opportunities({
  q: "IT services software",
  notice_type: "solicitation",
  posted_days: 7,  // last week only
  limit: 50
})
```

Cross-reference results with your local `sam_notices` table by `notice_id`. Any notice_id in the API response that's NOT in your database is a new opportunity you haven't seen yet.

---

## 5. Agency-Specific Plays

### Department of Veterans Affairs (VA)

- **Forecasts:** 697 entries, 203 under SAT, 84 SB
- **SAM notices:** 192 active, 85 SDVOSB (the #1 SDVOSB buyer)
- **Top NAICS:** IT services (166), building construction (65), computer systems design (37), medical instruments (27)
- **Play:** If you have SDVOSB status, VA is your #1 target. If not, target the 84 SB set-asides. Medical supplies (PSC 6515) is a VA specialty — Medline/Cardinal Health sourcing applies.

### Department of the Interior

- **Forecasts:** 3,101 entries, 1,301 under SAT (the MOST under-SAT of any agency)
- **SAM notices:** 163 across Forest Service, NPS, BLM, Bureau of Reclamation, FWS
- **Top NAICS:** IT services (315), forestry support (222), highway construction (202), environmental consulting (98)
- **Play:** Bureau of Reclamation (885) and Fish & Wildlife (710) are the top buying offices. Construction and environmental services are the SB sweet spots. IT services is the largest single NAICS.

### Department of Agriculture

- **Forecasts:** 2,317 entries, 60% SB rate (highest), only 137 under SAT
- **SAM notices:** 59 across ARS, AMS, APHIS, Forest Service
- **Top NAICS:** Food manufacturing (cheese, fruit/veg, meat, poultry) — 918 entries, 90%+ SB
- **Play:** Food procurement is recurring, stable, and almost entirely SB. If you can source food commodities, this is steady work. IT services (173 entries) is the #1 non-food NAICS.

### General Services Administration (GSA)

- **Forecasts:** 324 entries, 44% SB, 51 under SAT
- **SAM notices:** 38 across PBS and FAS
- **Top NAICS:** Highway construction (38), building construction (37), building leasing (29), facilities support (26)
- **Play:** Facilities-heavy. PBS manages 8,700 federal buildings. Construction, maintenance, janitorial, leasing.

### Bureau of Prisons (BOP)

- **Forecasts:** 0 entries (not in forecast data)
- **SAM notices:** 27 active, 30% SB
- **Top NAICS:** Roofing (3), IT services (2), plumbing/HVAC (2), building construction (2)
- **Play:** Small volume, secondary target. Individual prison facilities contracts are accessible but low-dollar.

---

## 6. Operational Workflow

### Daily Rhythm (Track A — Transactional Quoting)

1. **Morning:** Agent runs all saved reports, checks for new deadlines in next 7 days
2. **Triage:** Danielle/Zamaya review results, flag 5-10 that match sourcing capabilities
3. **Quote:** Agent drafts outreach emails to Carahsoft/Medline/Grainger for flagged opportunities
4. **Submit:** Agent auto-fills SF-1449 with quote data, uploads to workspace
5. **Review:** Human reviews filled form, approves, submits

### Weekly Rhythm (Track B — Strategic Teaming)

1. **Monday:** Agent runs forecast reports filtered to $1M+ SB set-asides
2. **Partner Search:** Agent searches vendor database for similarly situated businesses in matching NAICS
3. **Outreach:** Agent drafts teaming inquiry emails
4. **Pipeline Review:** Human reviews forecast pipeline, updates Go/No-Go decisions

---

## 7. What The Agent Can Do Right Now

These all work with existing tools — no new code needed:

| You say                                                      | Agent does                                                                                                           |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| "Find all IT forecast opportunities under $150K"             | `query_forecast_opportunities({q: "IT software", value_under: 150000})`                                            |
| "Show me SB set-asides in Interior, ascending by value"      | `query_forecast_opportunities({set_aside: "Small Business", agency: "Interior", order_by: "estimated_value_low"})` |
| "What active SAM notices are for medical supplies?"          | `query_sam_notices({q: "medical supplies", status: "active"})`                                                     |
| "Break down forecasts by agency for SB set-asides under SAT" | `summarize_forecasts({group_by: "agency"})` then filter                                                            |
| "Check SAM.gov for new IT opportunities this week"           | `search_sam_opportunities({q: "IT", posted_days: 7})`                                                              |
| "Are there any new SAM notices I don't have locally?"        | Cross-reference`search_sam_opportunities` results with `query_sam_notices` by `notice_id`                      |
| "Summarize what Interior is buying under SAT"                | `summarize_forecasts({group_by: "naics_code", agency: "Interior"})` + value_under filter                           |

---

## 8. What Needs Building

| Feature                          | Why                                                       | Priority |
| -------------------------------- | --------------------------------------------------------- | -------- |
| Saved Reports (see design doc)   | Persist these queries as named, revisitable reports       | P0       |
| SAM.gov live API gap detection   | Find opportunities not in your CSV snapshot               | P1       |
| Value estimation for SAM notices | Parse solicitation attachments to estimate contract value | P2       |
| Automated daily report refresh   | Agent runs reports on schedule, flags new matches         | P2       |
| Cross-source unified view        | Single report spanning forecasts + SAM notices            | P3       |

---

## Appendix A: Key NAICS Codes by Vertical

| Vertical             | Primary NAICS | Description                                      |
| -------------------- | ------------- | ------------------------------------------------ |
| IT Services          | 541519        | Other Computer Related Services                  |
| IT Services          | 541512        | Computer Systems Design Services                 |
| Software             | 513210        | Software Publishers                              |
| Medical Supplies     | 423450        | Medical Equipment Merchant Wholesalers           |
| Medical Supplies     | 339112        | Surgical/Medical Instrument Manufacturing        |
| Office Supplies      | 423210        | Furniture Merchant Wholesalers                   |
| Office Supplies      | 424120        | Office Supplies Merchant Wholesalers             |
| Cleaning/Janitorial  | 561720        | Janitorial Services                              |
| Cleaning Supplies    | 325612        | Polish/Sanitation Good Manufacturing             |
| Lab Equipment        | 334516        | Analytical Laboratory Instrument Manufacturing   |
| Vehicles (small)     | 336999        | All Other Transportation Equipment Manufacturing |
| Appliances           | 335220        | Major Household Appliance Manufacturing          |
| Landscaping          | 561730        | Landscaping Services                             |
| Construction (small) | 236220        | Commercial Building Construction                 |
| Construction (small) | 238220        | Plumbing/HVAC Contractors                        |
| Construction (small) | 238160        | Roofing Contractors                              |
| Construction (small) | 238210        | Electrical Contractors                           |

## Appendix B: Sourcing Partners by Vertical

| Vertical             | Wholesale Source                          |
| -------------------- | ----------------------------------------- |
| IT Software          | Carahsoft (Master Aggregator), EC America |
| Medical Supplies     | Medline, Cardinal Health                  |
| Facilities/MRO       | W.W. Grainger                             |
| Aviation Electronics | Mouser, Digi-Key                          |
