# Availability Check

## Purpose
Check whether a matched vendor has the capacity to take on a new project and whether they have any existing conflicts that would block them from this solicitation.

## Inputs
- Vendor profile (capacity limits, active engagements)
- Vendor's current active subcontracts and active bids
- Solicitation timeline (period of performance, estimated hours)

## Outputs
- Availability status: Available / Limited Capacity / Unavailable
- Conflict flags: active exclusivity on competing bids
- Capacity overlap analysis: can they handle this plus existing commitments?

## Check Dimensions

### 1. Exclusivity Conflicts
- Is vendor already committed to another prime for THIS solicitation number?
- Is vendor bidding as Prime on THIS solicitation number?
- If yes → BLOCK (see [[../08-review-submission/exclusivity-enforcement]])

### 2. Capacity Limits
- Vendor's stated max project capacity ($)
- Vendor's max concurrent projects
- Current active subcontract volume
- Does this solicitation push them over capacity?
- If near limit → flag as "Limited Capacity"

### 3. Timeline Overlap
- Solicitation period of performance vs. vendor's existing commitments
- Key Personnel availability during the performance period
- Seasonal considerations (e.g., landscaping vendor fully booked in spring)

### 4. Geographic Feasibility
- Solicitation Place of Performance within vendor's service area?
- Distance/logistics: can they reasonably serve this location?

## Output Structure

```json
{
  "vendorId": "vnd_99218",
  "solicitationNumber": "W912HN-24-R-0001",
  "availability": "available",
  "conflicts": [],
  "capacityDetails": {
    "maxProjectValue": 500000,
    "currentCommitments": 120000,
    "estimatedNewProjectValue": 85000,
    "remainingCapacity": 380000,
    "utilizationPercent": 24
  },
  "warnings": []
}
```

## Dependencies
- [[vendor-matching-algorithm]]
- [[../08-review-submission/exclusivity-enforcement]]
- [[../02-onboarding/vendor-profile-schema]]

## Key Rules & Compliance
- Vendor must not be debarred or suspended (check SAM.gov exclusions)
- Exclusivity for one solicitation does NOT prevent vendor from working on other solicitations

## Open Questions
- Should vendors self-report current capacity/availability on a regular cadence?
- At what utilization threshold should the system auto-flag "Limited Capacity"?
