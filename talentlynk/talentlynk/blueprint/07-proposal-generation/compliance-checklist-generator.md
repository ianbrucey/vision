# Compliance Checklist Generator

## Purpose
Auto-generate a submission compliance checklist based on the solicitation's Section L instructions. This is the final gate before submission — every item must be checked off to confirm the proposal is complete and responsive.

## Inputs
- Section L instructions (parsed)
- All proposal volumes generated
- Section M evaluation criteria

## Outputs
- Compliance checklist with status per item
- Flagged non-compliance items (blockers)
- Final readiness determination: "Ready to Submit" or "Not Ready — X items outstanding"

## Checklist Categories

### Administrative Compliance
- [ ] SAM registration active for bidding entity
- [ ] UEI and CAGE code correct on all forms
- [ ] All mandatory forms (SF-1449, etc.) filled and signed
- [ ] Representations & Certifications (FAR 52.212-3) completed
- [ ] Bid bond included (if required)
- [ ] Signed amendments acknowledged (SF-30s)

### Technical Compliance
- [ ] SOW fully addressed (no work elements missed)
- [ ] All evaluation criteria addressed in narrative
- [ ] Key Personnel resumes included
- [ ] Letters of Commitment included for all Key Personnel
- [ ] Required certifications/license documentation included
- [ ] Past performance references included (required count)

### Format Compliance
- [ ] Page limits respected per volume
- [ ] Font and formatting compliant
- [ ] Page numbering correct
- [ ] Required markings (proprietary, solicitation number)
- [ ] Table of contents accurate

### Pricing Compliance
- [ ] All CLINs priced
- [ ] Pricing format matches solicitation requirement
- [ ] Total price clearly stated
- [ ] Discount terms noted (if applicable)

### Submission Compliance
- [ ] Due date: [DATE] — submission ready before deadline
- [ ] Delivery method: email / portal / physical
- [ ] File format and naming convention per instructions
- [ ] File size within limits

## System Behavior

### Pre-Submission Gate
- Checklist must be 100% complete (all items checked or waived with justification)
- Red items (blockers): cannot submit until resolved
- Yellow items (warnings): can submit but flagged for attention
- Green items: compliant

### Blockers (Red)
- Missing mandatory form
- Missing signature
- Page limit exceeded (may = pages not evaluated)
- Missing Key Personnel LOI
- SAM registration expired
- Bid bond missing (when required)

### Warnings (Yellow)
- Minor formatting deviation
- Past performance references older than 5 years
- Pricing slightly above IGE (if known)
- Font slightly off spec

### Submission Lock
- System can be configured to BLOCK submission if checklist has any red items
- Override: requires Proposal Manager + Compliance Officer dual approval

## Dependencies
- [[multi-volume-assembler]]
- [[../04-solicitation-pipeline/section-l-parser]]
- [[../04-solicitation-pipeline/certification-extraction]]
- [[../08-review-submission/digital-signature-routing]]
- [[../08-review-submission/internal-review-queue]]

## Key Rules & Compliance
- FAR 15.208: Submission, modification, revision, and withdrawal of proposals
- Late proposals are NOT accepted (with very narrow exceptions under FAR 52.212-1(f))
- Non-responsive proposals are rejected without evaluation — the checklist prevents this

## Open Questions
- Should checklist completion be enforced programmatically (hard block) or advisory (soft warning)?
- Should there be a "final compliance officer sign-off" step separate from the checklist?
