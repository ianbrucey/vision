# Exclusivity Clause

## Purpose
The specific contractual language within the Task-Specific Teaming Agreement that legally bars a vendor from competing against TalentNyk on a given solicitation. This is the mechanism that resolves the "dual-bidding gotcha" — when a network vendor and TalentNyk both want to bid as Prime on the same opportunity.

## The Problem It Solves

Under standard commercial procurement, a subcontractor can give quotes to multiple competing Primes and even submit their own Prime bid. But under **FAR 52.203-2 (Certificate of Independent Price Determination)**, a Prime certifies that its pricing was "arrived at independently, without communication or consultation with other competitors regarding prices or methods of calculating prices."

If TalentNyk has active visibility into a network vendor's pricing matrices through the platform, and that vendor also bids as a Prime, a losing competitor can file a protest alleging **collusion or bid-rigging**. The result: both companies disqualified and referred to the Department of Justice.

## The Solution: Task-Specific Exclusivity

The network operates in two legal phases:

- **Phase 1 (Master MOU / Standby):** Non-exclusive. Vendors look at other work; TalentNyk looks at other vendors.
- **Phase 2 (Task-Specific TA):** The moment a vendor is selected for a specific solicitation, they sign an exclusivity clause. For *this specific solicitation number*, they are barred from submitting a competing Prime bid or quoting another Prime.

## Required Clause Language

> **Exclusivity of Representation**
>
> For Solicitation Number [SOLICITATION_NUMBER] ("the Solicitation"), Subcontractor agrees to participate exclusively as a proposed subcontractor to [TALENTNYK ENTITY] ("Prime Contractor").
>
> Subcontractor expressly agrees that, for the duration of this Agreement:
> a) Subcontractor shall not submit, or participate in the preparation of, a competing prime bid or offer in response to the Solicitation;
> b) Subcontractor shall not serve as a subcontractor, teaming partner, or consultant to any other entity submitting a prime bid or offer in response to the Solicitation;
> c) Subcontractor shall not disclose any pricing, technical approach, or proprietary information related to the Solicitation to any third party.
>
> This exclusivity obligation applies only to the Solicitation identified above and does not restrict Subcontractor's ability to pursue any other contracting opportunities independently.

## System Enforcement

### Pre-Generation Check
Before generating a Task-Specific TA for Vendor V on Solicitation S:
1. Query: Is Vendor V already listed as a sub for another prime on Solicitation S?
2. Query: Is Vendor V preparing their own Prime bid on Solicitation S?
3. If yes to either: block matching, flag conflict

### Refusal Handling
If a vendor refuses to sign the exclusivity clause:
- System flags them as a conflict of interest for this specific bid
- Vendor is barred from seeing any details of this solicitation
- Vendor remains in good standing for other solicitations
- The refusal is logged for audit

## Dependencies
- [[task-specific-teaming-agreement]]
- [[../08-review-submission/exclusivity-enforcement]]

## Key Rules & Compliance
- FAR 52.203-2: Certificate of Independent Price Determination
- FAR 3.104: Procurement Integrity Act
- 18 U.S.C. § 1001: False Statements (criminal liability for false certifications)
- Antitrust laws: bid-rigging and collusion are criminal offenses

## Open Questions
- Should exclusivity survive for a period after the TA expires (e.g., 6-month tail)?
- What documentation should the system generate to prove independent pricing to auditors?
