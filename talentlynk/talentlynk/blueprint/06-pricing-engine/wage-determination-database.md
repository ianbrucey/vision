# Wage Determination Database

## Purpose
Maintain a local, searchable database of federal wage determinations (SCA and Davis-Bacon) that feeds into the cost estimation engine. Instead of manually looking up wage rates per solicitation, the system pre-ingests WDs and auto-applies them to bids.

## Inputs
- Wage determination data ingested from SAM.gov / WDOL (Wage Determinations OnLine)
- Solicitation-attached WD documents (parsed via [[../04-solicitation-pipeline/wage-determination-extraction]])
- Periodic updates: DOL publishes new WD revisions regularly

## Outputs
- Applicable wage rates by labor category, county, and WD number
- Health & Welfare fringe benefit rate
- Fully burdened hourly rates per labor category
- Audit trail: which WD was used for which bid, when it was retrieved

## Database Schema

```json
{
  "wageDetermination": {
    "wdNumber": "2015-4567",
    "revision": 17,
    "publishDate": "2026-01-15",
    "act": "SCA",
    "state": "GA",
    "county": "Fulton",
    "healthAndWelfareRate": 4.80,
    "vacationRate": null,
    "holidayRate": null,
    "expirationDate": "2027-01-15",
    "isActive": true,
    "occupations": [
      {
        "code": "11150",
        "title": "Groundskeeper",
        "wageRate": 15.40,
        "footnotes": ["Uniform allowance required"]
      }
    ]
  }
}
```

## Data Ingest Strategy

### Initial Load
- Bulk download from SAM.gov WD API or WDOL
- Parse and index all active WDs for target states/counties

### Incremental Updates
- Scheduled check: weekly or daily pull for new revisions
- Solicitation-triggered check: if a solicitation references a WD not in the database, pull it on-demand

### Versioning
- Track WD revisions over time
- When a solicitation is priced, snapshot which WD revision was used
- If WD is revised between proposal submission and award, the CO will apply the latest — system should alert

## Locality Resolution

When a solicitation is ingested:
1. Extract Place of Performance (county, state)
2. Query WD database for that county + applicable act (SCA or DBA)
3. If multiple WDs cover the same county (e.g., different construction types for DBA), select the correct one based on solicitation NAICS/SOW
4. Flag if Place of Performance spans multiple counties → use highest applicable rate

## Dependencies
- [[../04-solicitation-pipeline/wage-determination-extraction]]
- [[../13-integrations/wage-determination-api]]
- [[cost-estimation-formula]]
- [[fringe-benefit-calculator]]

## Key Rules & Compliance
- SCA: FAR 52.222-41 — Service Contract Labor Standards
- DBA: FAR 52.222-4 — Davis-Bacon Act
- WD at award governs, not the WD in the solicitation (if a new revision takes effect between proposal and award, the new rate applies)
- If WD is missing from a solicitation that requires one: the CO must provide it (request in Q&A)
- H&W rate: if employer provides qualifying benefits at or above the H&W rate, the cash H&W component does not need to be paid separately

## Open Questions
- Auto-pull WDs from SAM.gov API (real-time) vs. maintain local cache (faster, but must sync)?
- How far back to archive historical WDs for audit?
