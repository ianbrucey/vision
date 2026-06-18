# Master Teaming Agreement (MOU)

## Purpose
The non-exclusive, baseline agreement that brings a vendor into the TalentNyk standby network. It creates the legal framework for future collaboration but does not obligate either party to any specific work. Think of it as the "we're in business together when there's business to be had" agreement.

## Key Characteristics

- **Non-exclusive:** Vendor can pursue other work independently
- **No financial obligation:** Either party can walk away from any specific opportunity
- **No corporate entanglements:** Does not create a partnership, JV, or shared ownership
- **Standing agreement:** Remains in effect until terminated (with notice period)
- **Framework only:** Specific work requires a Task-Specific Teaming Agreement

## Required Provisions

### 1. Purpose & Scope
- Establishes framework for collaborating on federal contract opportunities
- TalentNyk as Prime, Vendor as Subcontractor
- Covers all or specified categories of work

### 2. Roles & Responsibilities
- **TalentNyk:** Prime contractor — proposal writing, compliance, contract management, payment administration
- **Vendor:** Subcontractor — physical execution of the work, maintaining licenses, providing pricing

### 3. Non-Exclusivity
- Vendor may pursue other prime and subcontract opportunities independently
- TalentNyk may work with other vendors in the same trade
- Only a signed Task-Specific TA creates exclusivity for a specific bid

### 4. Pricing Protocol
- Vendor provides baseline commercial pricing
- Vendor agrees to provide solicitation-specific quotes within X business days of request
- Pricing is confidential and protected

### 5. Proposal Protocol
- TalentNyk has the right to include Vendor's past performance and capabilities in proposals
- Vendor must be identified as a proposed subcontractor in any proposal where they are included
- Vendor has the right to review and approve any proposal naming them before submission

### 6. Post-Award Terms (Framework)
- If award is won: parties will execute a detailed Subcontract Agreement
- Subcontract will include: scope, price, period of performance, payment terms
- "Pay-When-Paid" clause will govern payment timing

### 7. Term & Termination
- Initial term (e.g., 2 years) with auto-renewal
- Either party may terminate with X days written notice
- Termination does not affect existing Task-Specific Agreements or active subcontracts

### 8. Confidentiality
- All solicitation data, pricing, and proposal content is confidential
- Vendor may not share bid information with competitors
- Survives termination of the MOU

### 9. Governing Law & Disputes
- Governing state law
- Dispute resolution process
- No mandatory arbitration unless desired

## System Behavior

### Generation
- Trigger: vendor completes onboarding wizard
- Pull vendor profile data → populate MOU template
- Present for digital signature
- Signed MOU → vendor status changes to "Standby"

### Storage
- Stored in document repository
- Linked to vendor profile
- Expiration date tracked
- Version history maintained

## Dependencies
- [[task-specific-teaming-agreement]]
- [[../02-onboarding/vendor-onboarding-wizard]]
- [[../13-integrations/docusign-integration]]
- [[non-disclosure-agreement]]

## Key Rules & Compliance
- MOU must NOT create an ostensible subcontractor relationship (SBA affiliation risk)
- Similarly Situated Entity rule: subcontracting to certified small businesses counts as prime performance
- MOU alone does not authorize TalentNyk to submit a proposal naming the vendor — a Task-Specific TA is required

## Open Questions
- Should the MOU include a non-solicitation clause (vendor can't poach TalentNyk staff)?
- Automatic renewal or manual re-confirmation?
