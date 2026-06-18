# Contingent Offer Letter

## Purpose
The formal W-2 job offer issued to individual specialists that is explicitly conditional on a specific federal contract being awarded. This is the legal instrument that lets TalentNyk claim Key Personnel without spending a dollar upfront.

## How It Works

The Contingent Offer Letter contains explicit conditional language that makes the employment offer legally binding **only if** all conditions are met:

1. The federal government awards Contract X to TalentNyk (or the bidding entity)
2. The Contracting Officer (CO) approves the individual as Key Personnel
3. The Period of Performance actually begins

If the contract is lost, the offer expires — neither party owes the other anything.

## Required Legal Provisions

### Conditions Precedent
- Award of the specific contract (identified by solicitation number)
- CO approval of the individual as Key Personnel
- Start of the Period of Performance
- Individual maintaining required certifications/clearances through award date

### Offer Terms (Effective Only Upon Conditions Being Met)
- Position title and role description
- Salary or hourly rate
- Benefits package
- Work location
- Reporting structure
- Duration: tied to the contract's Period of Performance (including option years)

### Expiration Clause
- Offer automatically expires if contract is not awarded
- Offer expires if individual is not approved as Key Personnel
- No severance, no compensation owed upon expiration
- Explicit: "This is not a guarantee of employment"

## System Behavior

### Generation
- Pull specialist profile data (name, role, compensation expectations)
- Pull solicitation data (solicitation number, contract title, period of performance)
- Generate PDF with all fields populated
- Route to specialist for digital signature

### Storage & Tracking
- Store signed offer letter in document repository
- Status: "Contingent — Pending Award"
- Link to solicitation record
- Link to specialist profile

### Activation
- On contract award: system triggers conversion to active W-2 status
- If award lost: system marks offer as "Expired" and notifies specialist

## Dependencies
- [[letter-of-commitment]]
- [[../02-onboarding/specialist-onboarding]]
- [[../13-integrations/docusign-integration]]

## Key Rules & Compliance
- Must be unequivocally conditional — no ambiguity about "maybe" employment
- Cannot obligate the individual to accept other work in the interim (restraint of trade issues)
- Individual must be free to pursue other opportunities until conditions are met
- The offer is for a specific role on a specific contract — not a general employment offer

## Open Questions
- Should offers include a "good until" date beyond which they auto-expire even if award is pending?
- Benefits: include specifics or reference "standard company benefits package"?
