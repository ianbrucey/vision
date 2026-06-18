# Subcontract Agreement

## Purpose
The post-award agreement that converts the Task-Specific Teaming Agreement into an active, legally binding subcontract — governing the actual performance of work, payment, and compliance after a contract is won.

## When This Executes

Trigger: Contract award notification received → system activates Subcontract Agreement generation.

The Subcontract Agreement takes the framework from the Task-Specific TA and expands it into a full, executable contract with the vendor.

## Required Provisions

### 1. Prime Contract Flow-Downs
All relevant FAR clauses that flow down from the Prime contract to the subcontractor, including:
- FAR 52.222-26: Equal Opportunity
- FAR 52.222-41: Service Contract Act (if applicable)
- FAR 52.222-4: Davis-Bacon Act (if applicable)
- FAR 52.222-50: Combating Trafficking in Persons
- FAR 52.203-13: Contractor Code of Business Ethics and Conduct
- FAR 52.204-21: Basic Safeguarding of Covered Contractor Information Systems
- Any contract-specific flow-downs from the prime award

### 2. Scope of Work
- Detailed description of the subcontracted work
- Deliverables and acceptance criteria
- Performance standards and metrics
- Government-furnished property or information (if any)

### 3. Period of Performance
- Start date (linked to prime contract start)
- End date (including option years)
- Key milestones and delivery dates

### 4. Price & Payment (The "Pay-When-Paid" Clause)
> **Pay-When-Paid Provision (FAR 52.232-40 Compliant)**
>
> Payment to Subcontractor is contingent upon Prime Contractor's receipt of payment from the Government for Subcontractor's work. Prime Contractor shall pay Subcontractor within [3-7] days after receipt of Government funds attributable to Subcontractor's work.
>
> This is a "pay-when-paid" provision, not a "pay-if-paid" provision. Prime Contractor's obligation to pay is not extinguished if Government non-payment is due to Prime Contractor's own actions or failures.

### 5. Compliance Obligations
- Sub must maintain all required licenses and certifications
- Sub must comply with SCA/Davis-Bacon wage requirements
- Sub must maintain required insurance
- Sub must cooperate with government audits and inspections

### 6. Performance Monitoring
- Progress reporting requirements
- Quality control standards
- Government site access and security requirements
- Deliverable acceptance process

### 7. Changes & Modifications
- Sub must execute any change orders required by the government
- Pricing adjustments for changed scope
- No unilateral changes by either party

### 8. Termination
- Termination for Convenience (mirroring prime contract T4C clause)
- Termination for Default/Cause
- Closeout procedures upon termination

### 9. Disputes
- Dispute resolution process
- Sponsorship of claims against the government (if sub's work is at issue)

## System Behavior

### Generation
- Pull: prime contract data, Task-Specific TA terms, vendor profile
- Auto-populate Subcontract Agreement with all flow-downs
- Route to both parties for execution

### Post-Execution Management
- Store executed agreement in contract repository
- Link to prime contract record
- Track sub's insurance and license expirations during performance
- Auto-alert if sub's certifications lapse during active contract

## Dependencies
- [[task-specific-teaming-agreement]]
- [[../09-post-award/contract-activation]]
- [[../09-post-award/accelerated-payment-routing]]

## Key Rules & Compliance
- FAR 52.232-40: Accelerated payments must flow down to subs within 3-7 days
- FAR 52.244-2: Consent to subcontract (some subcontracts require CO approval)
- All mandatory flow-down clauses must be included — omission = prime is in breach
- Subcontractor must be registered in SAM.gov for payment (if receiving direct government payment via Assignment of Claims)

## Open Questions
- Should subcontracts use a standard template or be customized per trade/industry?
- Disputes: arbitration, litigation, or government-sponsored dispute process?
