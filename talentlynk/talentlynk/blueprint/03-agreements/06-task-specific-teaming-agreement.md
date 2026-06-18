# Task-Specific Teaming Agreement

## Purpose
The binding, solicitation-specific agreement that locks in a vendor for a particular bid. Unlike the Master MOU (which is non-exclusive and non-binding), the Task-Specific TA creates real legal obligations: the vendor commits to serve as subcontractor for this specific solicitation and is barred from bidding against TalentNyk as a Prime for this specific opportunity.

## Key Characteristics

- **Solicitation-specific:** Tied to one solicitation number
- **Exclusive:** Vendor cannot bid as Prime or sub to another Prime for this solicitation
- **Binding pricing:** Vendor's quoted price is locked (subject to final review and sign-off)
- **Temporary:** Expires if bid is lost; converts to Subcontract if won

## Required Provisions

### 1. Identification of the Opportunity
- Solicitation number
- Agency name
- Project title/description
- NAICS code(s)
- Proposal due date

### 2. Exclusivity Clause (Critical)
> "For Solicitation Number [X], Subcontractor agrees to participate exclusively as a subcontractor to [TalentNyk Entity]. Subcontractor shall not submit a competing prime bid, nor serve as subcontractor to any other prime contractor, for this specific solicitation."

**This clause is what prevents the dual-bidding "gotcha" and FAR 52.203-2 (Certificate of Independent Price Determination) violations.**

### 3. Pricing & Scope
- The specific scope of work the vendor will perform
- The vendor's quoted price or rate for this specific solicitation
- Price validity period (must survive through the government's evaluation timeline)
- Any assumptions or exclusions

### 4. Proposal Participation
- Vendor authorizes TalentNyk to name them in the proposal
- Vendor authorizes inclusion of their past performance and capabilities
- Vendor will provide any additional documentation needed for the proposal
- Vendor will review and sign the final proposal package before submission

### 5. Post-Award Conversion
- If award is won: parties will execute a detailed Subcontract Agreement within X days
- Subcontract terms will be based on the scope and pricing in this TA
- If award is lost: this TA automatically terminates with no liability to either party

### 6. Confidentiality
- All solicitation and pricing information is confidential
- Vendor may not discuss the bid with any other prime or competitor
- Vendor may not disclose TalentNyk's pricing or technical approach

### 7. Representations
- Vendor represents that their pricing was independently determined
- Vendor represents they have no conflicts of interest
- Vendor represents their licenses and certifications are current

## System Behavior

### Generation Trigger
- Proposal Manager selects a vendor from the matching engine recommendations for a specific solicitation
- System auto-generates Task-Specific TA with solicitation data + vendor profile data

### Routing & Sign-Off
- TA is sent to vendor for digital signature
- System blocks proposal submission until vendor signs
- **This is the mandatory review step — not optional under FAR rules**

### Conflict Check (Before Generation)
- System checks: is this vendor already committed to another prime for this solicitation?
- System checks: is this vendor submitting their own prime bid for this solicitation?
- If conflict detected: block matching, flag for Proposal Manager

### Expiration
- If proposal due date passes without submission: TA auto-expires (configurable)
- If award is lost: TA auto-terminates

## Dependencies
- [[master-teaming-agreement]]
- [[exclusivity-clause]]
- [[subcontract-agreement]]
- [[../08-review-submission/digital-signature-routing]]
- [[../08-review-submission/exclusivity-enforcement]]

## Key Rules & Compliance
- **FAR 52.203-2 (Certificate of Independent Price Determination):** By submitting a proposal, TalentNyk certifies pricing was independently determined without collusion. The exclusivity clause + vendor sign-off protects against allegations of collusion with network members.
- **FAR 15.408:** The vendor named as sub must have reviewed the final solicitation-specific proposal and signed a task-specific agreement — this is a legal requirement, not optional.
- **GAO Protest Risk:** If a competing vendor in your network bids as Prime on the same solicitation without exclusivity enforcement, a protest for bid-rigging is almost certain.

## Open Questions
- What's the penalty if a vendor breaches exclusivity? Liquidated damages clause?
- Should the TA include a "right of first refusal" for option years or follow-on contracts?
