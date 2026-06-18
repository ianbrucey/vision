# Exclusivity Enforcement

## Purpose
Programmatically enforce the conflict-of-interest rules that prevent dual-bidding and collusion. Before a vendor is selected for a solicitation, the system checks for conflicts. This is the automated guard against the FAR 52.203-2 "gotcha" that could get both TalentNyk and the vendor disqualified and referred to the DOJ.

## The Problem

A vendor in TalentNyk's network could:
- Submit their own Prime bid on the same solicitation
- Serve as a sub to another Prime bidding on the same solicitation
- Share TalentNyk's pricing data with another bidder

Any of these = potential bid-rigging allegation.

## Enforcement Logic

### Phase 1: Network Phase (Master MOU Only — Non-Exclusive)
- Vendor can pursue any work independently
- Vendor can work with other primes
- No restrictions
- Status: "Standby"

### Phase 2: Engagement Phase (Task-Specific TA Signed — Exclusive)
- Upon signing Task-Specific TA for Solicitation X:
  - Vendor is flagged as "Engaged" for Solicitation X
  - Vendor CANNOT be matched to another Prime for Solicitation X
  - System checks: is vendor already flagged as Prime bidder for Solicitation X? → If yes, BLOCK and ALERT
  - System alerts: "Vendor V is now exclusive to TalentNyk for Solicitation X"

### Pre-Match Conflict Check (Runs BEFORE Vendor Selection)

```
For each vendor being considered for Solicitation S:

1. CHECK: Is vendor already listed as Engaged to another Prime for Solicitation S?
   → If YES: EXCLUDE from matching

2. CHECK: Is vendor flagged as preparing their own Prime bid for Solicitation S?
   → If YES: EXCLUDE from matching

3. CHECK: Has vendor already signed an exclusivity clause with another Prime for Solicitation S?
   → If YES: EXCLUDE from matching (contractual breach if we proceed)
```

### Conflict Resolution

| Conflict Type | System Action |
|---------------|---------------|
| Vendor already sub to another Prime for S | Block match; flag for Proposal Manager |
| Vendor bidding as Prime for S | Block match; flag for Proposal Manager |
| Vendor refuses to sign exclusivity | Flag as conflict; bar vendor from seeing any S-specific data |
| Vendor signed exclusivity but backs out | Legal breach; flag for legal counsel; log for potential protest defense |

## Self-Reporting Mechanism

Vendors should be prompted (during onboarding and periodically):
- "Are you currently preparing a Prime bid for any active federal solicitations? If yes, list solicitation numbers."
- This data feeds into the conflict check engine.

## Dependencies
- [[../03-agreements/exclusivity-clause]]
- [[../03-agreements/task-specific-teaming-agreement]]
- [[../05-matching-engine/vendor-matching-algorithm]]
- [[../05-matching-engine/availability-check]]

## Key Rules & Compliance
- FAR 52.203-2: Certificate of Independent Price Determination — certifying no collusion
- FAR 3.104: Procurement Integrity Act — prohibits disclosure of procurement-sensitive information to competitors
- 18 U.S.C. § 1001: False Statements — criminal for false certifications
- Sherman Antitrust Act: bid-rigging is a felony

## Open Questions
- Should the system cross-reference vendors against SAM.gov / FPDS to see if they've bid independently on the same solicitation?
- What's the process if a vendor breaches exclusivity — automated legal hold, manual escalation?
