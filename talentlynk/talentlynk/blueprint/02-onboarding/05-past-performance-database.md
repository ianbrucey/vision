# Past Performance Database

## Purpose
Store, index, and retrieve vendor and specialist past performance snippets. These are the primary currency of federal proposal evaluation — the government evaluates "what have you done before that's relevant to what we need now?"

## Inputs
- Vendor reference projects (client, scope, value, dates, POC)
- Specialist project contributions (role, agency, outcome)
- Contract closeout data (post-award capture)
- Uploaded CPARS (Contractor Performance Assessment Reports) if available

## Outputs
- Searchable past performance database
- Relevance-ranked snippets for a given solicitation
- Past performance volume content for proposals
- Performance scoring for vendor ranking

## Data Model

### Vendor Past Performance Entry
```json
{
  "performanceId": "pp_vnd_001",
  "vendorId": "vnd_99218",
  "clientName": "Fulton County Parks",
  "clientType": "local_government",
  "scopeOfWork": "Mowing, edging, and seasonal debris removal for 14 public parks.",
  "contractValue": 45000.00,
  "periodOfPerformance": {
    "start": "2024-03-01",
    "end": "2025-02-28"
  },
  "naicsCodes": ["561730"],
  "relevanceTags": ["landscaping", "grounds_maintenance", "public_parks"],
  "pocName": "Jane Smith",
  "pocPhone": "404-555-0100",
  "pocEmail": "jsmith@fultoncounty.gov",
  "outcome": "completed_on_time"
}
```

### Specialist Past Performance Entry
```json
{
  "performanceId": "pp_spc_001",
  "specialistId": "spc_0042",
  "role": "Senior Construction Manager",
  "agency": "General Services Administration",
  "projectName": "Federal Building Renovation - Phase II",
  "contractValue": 2200000.00,
  "description": "Managed 12 subcontractors across electrical, HVAC, and structural trades for a 90,000 sq ft federal building renovation.",
  "outcome": "completed_under_budget"
}
```

## System Behaviors

### Relevance Scoring
When a solicitation is parsed:
1. Extract SOW keywords and NAICS codes
2. Vector-search past performance database
3. Rank snippets by relevance (scope similarity, value similarity, recency)
4. Surface top-N for proposal inclusion

### Proposal Compilation
- Auto-generate past performance volume
- Format per solicitation instructions
- Include required elements: client, scope, value, dates, POC, outcome

### Post-Award Capture
- On contract closeout, capture performance data for future use
- Track CPARS ratings when available

## Dependencies
- [[vendor-profile-schema]]
- [[../07-proposal-generation/past-performance-compiler]]
- [[../05-matching-engine/capability-scoring]]

## Key Rules & Compliance
- Past performance must be relevant to the solicitation's scope
- References must be verifiable — fake references = fraud
- CPARS data has privacy/access restrictions
- Recency matters: government typically weighs last 3-5 years most heavily

## Open Questions
- Should POCs be auto-contacted for verification during onboarding?
- How to handle vendors with no federal past performance (first-time contractors)?
