# Closeout Procedures

## Purpose
Manage the formal contract closeout process — final payment, performance evaluation capture, document archiving, and vendor scorecard generation. Closeout is a FAR-required process that converts a completed contract into captured past performance for future bids.

## Closeout Triggers

- Contract Period of Performance ended
- All deliverables accepted
- Final invoice submitted and paid
- Government issues final acceptance / DD 1594 (DoD) or equivalent

## Closeout Checklist

### Financial Closeout
- [ ] All invoices submitted
- [ ] All government payments received
- [ ] All subcontractor payments made
- [ ] Final payment reconciliation: did sub receive everything owed?
- [ ] Prime margin vs. actuals reconciliation
- [ ] Assignment of Claims released (if used)
- [ ] AR Factoring repaid (if used)
- [ ] Final indirect cost rates settled (for cost-reimbursement contracts)
- [ ] Refund any excess funds to government (if applicable)

### Administrative Closeout
- [ ] All deliverables submitted and accepted
- [ ] Government property returned (if any)
- [ ] Security clearances / facility access terminated
- [ ] Subcontracts formally closed
- [ ] Final report submitted (if required)
- [ ] Contractor Performance Assessment (CPARS) requested
- [ ] Past performance data captured for future proposals
- [ ] All contract documents archived (retention: typically 6 years)

### Vendor Closeout
- [ ] Final subcontractor payment confirmed
- [ ] Subcontractor scorecard generated (see [[subcontractor-management]])
- [ ] Past performance snippets captured from this contract
- [ ] Vendor returned to "Standby" status (or "Inactive" if performance was poor)
- [ ] Vendor license/certification status updated

### Specialist Closeout
- [ ] Specialist W-2 employment ended (if tied to contract POP)
- [ ] Final payroll processed
- [ ] Specialist returned to "Available" status for future opportunities
- [ ] CO notified of Key Personnel departure (if applicable)

## Past Performance Capture

This is strategically critical — the output of every contract feeds the input of future proposals:

```json
{
  "contractCloseout": {
    "contractNumber": "W912HN-24-C-0001",
    "agency": "Department of the Army",
    "scopeOfWork": "Grounds maintenance services at Fort Benning, GA...",
    "contractValue": {
      "awarded": 85000.00,
      "finalWithModifications": 92000.00
    },
    "periodOfPerformance": {
      "start": "2026-10-01",
      "end": "2027-09-30"
    },
    "performanceOutcome": "completed_on_time",
    "cparsRatings": {
      "technical": "very_good",
      "schedule": "excellent",
      "management": "very_good",
      "cost": "excellent",
      "overall": "very_good"
    },
    "subcontractors": ["vnd_99218"],
    "lessonsLearned": ["..."
  }
}
```

## Dependencies
- [[subcontractor-management]]
- [[payment-tracking]]
- [[../02-onboarding/past-performance-database]]
- [[../02-onboarding/vendor-profile-schema]]

## Key Rules & Compliance
- FAR 4.804: Closeout of contract files
- Contract closeout timeline: 6 months for FFP contracts, 36 months for cost-reimbursement
- Document retention: 6 years after final payment (FAR 4.805)
- CPARS: must be requested; government has 120 days to complete evaluation
- Contractor can comment on and rebut CPARS evaluations

## Open Questions
- Should closeout be a fully guided workflow (checklist wizard) or automated as much as possible?
- Should the system auto-request CPARS at closeout?
