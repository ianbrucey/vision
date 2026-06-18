# Vendor Portal

## Purpose
The external-facing interface where network vendors and specialists interact with TalentNyk. This is NOT the same as the internal dashboard — vendors see only their own data, assigned bids, agreements to sign, and post-award work.

## Vendor Features

### Profile Management
- View and update company/specialist profile
- Update pricing matrix
- Upload new licenses and certifications
- Add past performance references
- Manage service area and capacity

### Bid Participation
- View solicitations they've been matched to (after NDA/Task-Specific TA signed)
- Review proposal content that references their company
- Sign agreements digitally
- See bid status: Pending Review, Submitted, Won, Lost

### Post-Award
- View active subcontracts and deliverables
- Submit invoices
- Track payment status
- Submit performance reports
- View scorecard and performance feedback

### Document Vault
- All signed agreements accessible for download
- Proposal documents where they were named as sub
- Invoices and payment records

### Notifications
- "You've been matched to a new solicitation — review and sign the Task-Specific TA"
- "Your license [X] expires in 30 days — renew now"
- "Payment of $X has been sent for contract [Y]"
- "Please submit your monthly performance report for contract [Z]"

## Specialist Features

In addition to the above:
- Contingent offer letter review and acceptance
- Letter of Commitment signing
- Post-award: W-2 onboarding paperwork, time tracking

## Portal Access Control

- **Vendor Owner:** Full access to company profile and all bids
- **Vendor Staff (delegated):** Limited access per owner's settings
- **Specialist:** Access to own profile and assigned bids only
- **Manufacturer:** Same as vendor + product catalog management

## Authentication

- Email + password or SSO
- MFA for agreement signing
- Session management and timeout

## White-Label Consideration

Should the portal be:
- **TalentNyk-branded:** "Welcome to the TalentNyk Network"
- **Or white-label:** Vendors feel they're interacting directly with the Prime (not a platform)

## Dependencies
- [[../02-onboarding/]] (all onboarding wizards)
- [[../08-review-submission/digital-signature-routing]]
- [[../09-post-award/subcontractor-management]]
- [[internal-team-management]]
- [[notification-engine]]

## Key Rules & Compliance
- Vendor access to solicitation data is gated by NDA acceptance
- Vendor can only see bids they've been specifically matched to
- Multi-factor authentication for financial and legal actions

## Open Questions
- Mobile app or responsive web?
- Should vendors see their match scores relative to other vendors (transparency) or only their own status?
