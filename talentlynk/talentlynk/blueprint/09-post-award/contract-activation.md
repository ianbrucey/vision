# Contract Activation

## Purpose
The transition bridge from "We won!" to "Work is underway." Converts the awarded contract into an active operational state — activating subcontracts, onboarding Key Personnel as W-2 employees, and setting up all payment, compliance, and reporting infrastructure.

## Activation Triggers

- Government award notification received
- Contract document signed by both parties (TalentNyk + CO)
- Any required bonds (performance, payment) secured
- Insurance certificates submitted to CO

## Automated Activation Steps

### 1. Entity & Contract Setup
- Create contract record in system with all prime contract details
- Link to solicitation and proposal records
- Set Period of Performance dates
- Log all option years and expected exercise windows
- Store final executed contract document

### 2. Subcontract Activation
- Convert Task-Specific TA → Active Subcontract Agreement ([[../03-agreements/subcontract-agreement]])
- Route subcontract to vendor for execution
- Sub status: "Engaged" → "Active"

### 3. Key Personnel Activation
- Convert Contingent Offer Letters → Active W-2 Employment
- Trigger onboarding paperwork: W-4, I-9, benefits enrollment, direct deposit
- Notify specialists: "Contract awarded. Your employment begins [start date]."
- Specialist status: "Contingent" → "Active Employee"

### 4. Financial Setup
- Create contract budget in financial system
- Set up project accounts (if needed)
- Set up invoicing schedule
- If Assignment of Claims used: notify CO and set up payment routing
- If AR Factoring: notify financier of award

### 5. Compliance Setup
- Create compliance calendar with all reporting deadlines
- Set up deliverable tracking
- Log all mandatory government reporting requirements (monthly status reports, etc.)
- Set up insurance expiration monitoring

### 6. Kickoff
- Schedule internal kickoff meeting
- Schedule government kickoff meeting (post-award conference, if required)
- Distribute contract documents to all stakeholders
- Subcontractor receives: scope, schedule, deliverables, reporting requirements

## System State Transition

| Component | Pre-Award State | Post-Award State |
|-----------|----------------|------------------|
| Solicitation Record | Submitted / In Evaluation | Awarded |
| Contract Record | (doesn't exist) | Active |
| Vendor | Engaged (Task-Specific TA) | Active (Subcontract) |
| Specialist | Contingent Offer | Active W-2 Employee |
| Pricing | Bid Estimate | Contract Budget |
| Payment Setup | (not configured) | Active (payment tracking) |

## Dependencies
- [[../03-agreements/subcontract-agreement]]
- [[../08-review-submission/submission-tracking]]
- [[payment-tracking]]
- [[subcontractor-management]]

## Key Rules & Compliance
- Work cannot begin before the official Period of Performance start date
- Performance bond and payment bond must be in place before work begins (if required)
- Key Personnel must be in place on Day 1 — CO must be notified if substitution needed
- Post-award conference (FAR 42.503): contractor may be required to attend

## Open Questions
- How automated should activation be? Fully automated or stage-gated with human approval?
- Payroll provider integration for W-2 activation?
