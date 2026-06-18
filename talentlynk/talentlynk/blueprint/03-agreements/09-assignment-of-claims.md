# Assignment of Claims

## Purpose
Legal mechanism under FAR Subpart 32.8 that redirects government contract payments to a third party — typically a financing institution or directly to a subcontractor's bank. This is how TalentNyk eliminates the upfront capital burden: the subcontractor's bank finances raw materials against the guaranteed government receivable.

## How It Works

The Assignment of Claims Act allows a government contractor to assign its right to receive payment to a bank, trust company, or other financing institution. The assignment is legally binding on the government once acknowledged by the Contracting Officer.

### The Typical Transaction

1. TalentNyk wins a product supply contract
2. Manufacturer needs $30,000 for raw materials to produce the goods
3. TalentNyk and Manufacturer execute an Assignment of Claims
4. The assignment redirects government payments to a designated project account (or directly to the manufacturer's bank)
5. The manufacturer's bank now has collateral (the guaranteed government receivable) and can extend short-term financing
6. **Cost to TalentNyk: $0 — the bank finances against the government's credit, not TalentNyk's**

## Required Elements

### Assignment Instrument
- Prime contract number
- Assignor (TalentNyk entity)
- Assignee (financing institution or designated account)
- Specific contract payments being assigned (may be all or a portion)
- Banking information of the assignee
- Signature of authorized TalentNyk representative
- Acknowledgment by the Contracting Officer

### Notice to Government
- Formal written notice to the Contracting Officer
- Copy of the assignment instrument
- CO acknowledgment (required for the assignment to be binding on the government)

## System Behavior

### Generation
- Trigger: Post-award, when subcontractor financing is needed
- System generates Assignment of Claims instrument
- Pulls: prime contract data, subcontractor banking info
- Routes for signatures (TalentNyk → CO acknowledgment)

### Tracking
- Status: Draft → Signed → Submitted to CO → Acknowledged → Active
- Track which contract payments are assigned
- Auto-calculate amounts to be directed to assignee vs. retained

### Payment Routing
- On government payment receipt: system splits payment per assignment
- Assigned portion → assignee account
- Unassigned portion → TalentNyk operating account
- Full audit trail maintained

## Dependencies
- [[../10-financial-infrastructure/po-financing]]
- [[../09-post-award/contract-activation]]
- [[../09-post-award/payment-tracking]]

## Key Rules & Compliance
- FAR Subpart 32.8: Assignment of Claims
- Assignment is only valid for payment — the contractor still holds the contract and all performance obligations
- Assignment must be to a "bank, trust company, or other financing institution" (not to an individual)
- The government is only required to honor one assignment at a time per contract
- Assignment does not relieve the contractor of any contract obligations

## Open Questions
- Will this be a standard option on all product contracts, or only for specific financing scenarios?
- Relationship with AR Factoring integration?
