# Wage Determination API Integration

## Purpose
Automatically retrieve current SCA and Davis-Bacon wage determinations from the Department of Labor's WDOL (Wage Determinations OnLine) system or SAM.gov. Ensures pricing is always based on current, legally binding wage rates.

## Data Sources

### Primary: SAM.gov Wage Determination API
- SCA wage determinations: by WD number, state, county
- DBA wage determinations: by General Decision number, construction type, county
- Returns: wage rates, fringe rates, effective dates, revision history

### Secondary: DOL WDOL Website
- If API is unavailable, system can parse WD from solicitation attachments
- See [[../04-solicitation-pipeline/wage-determination-extraction]]

## Integration Workflow

### 1. Ingestion
- When solicitation is ingested, extract WD number or location data
- Query API for the specific WD
- If WD found: parse, store, and use for pricing
- If WD not found (new WD, API issue): flag for manual entry

### 2. Ongoing Refresh
- Weekly check: any of our actively-used WDs have new revisions?
- If yes: alert — "WD 2015-4567 Revision 18 is now available. Revision 17 was used for active bids."
- For submitted proposals: CO will apply the WD in effect at award, not the one in the solicitation
- For active contracts: option years may trigger new wage rates

### 3. Locality Resolution
When a solicitation doesn't specify a WD number but specifies a Place of Performance:
- System queries: SCA or DBA WD for [County, State] × [Construction Type if DBA]
- Returns: most current applicable WD

## API Model

```json
{
  "request": {
    "type": "SCA",
    "state": "GA",
    "county": "Fulton"
  },
  "response": {
    "wdNumber": "2015-4567",
    "revision": 17,
    "effectiveDate": "2026-01-15",
    "occupations": [
      {
        "code": "11150",
        "title": "Groundskeeper",
        "wageRate": 15.40,
        "fringeRate": 4.80
      }
    ]
  }
}
```

## System Behaviors

### WD Version Tracking
- Every bid records: which WD number + revision was used for pricing
- If WD is updated between submission and award: alert PM — pricing may need adjustment
- If contract has option years: system flags WD anniversary for rate adjustments

### WD Gap Detection
- Solicitation requires SCA compliance but no WD attached?
- System searches for applicable WD by location
- If still not found → flag: "Request WD from CO during Q&A period"

## Dependencies
- [[../06-pricing-engine/wage-determination-database]]
- [[../04-solicitation-pipeline/wage-determination-extraction]]
- [[sam-gov-api]]

## Key Rules & Compliance
- SCA: FAR 52.222-41 — contractor must pay at least the rates in the WD
- DBA: FAR 52.222-4 — same for construction
- WD at award governs — if WD is revised between submission and award, the new revision applies
- WD must be physically included in the solicitation by the CO — if missing, request during Q&A

## Open Questions
- SAM.gov API vs. direct DOL API — which is more reliable for automated queries?
- Should the system maintain a full offline copy of all WDs for faster access?
