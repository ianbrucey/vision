# License & Certification Tracker

## Purpose
Track all vendor licenses, professional certifications, and entity-level credentials with expiration monitoring. Many federal solicitations require active, current licenses — an expired license at time of proposal = disqualification.

## Inputs
- License/certification data from onboarding (type, number, state, expiration date)
- Scanned license documents (for verification)
- Auto-detected solicitation license requirements

## Outputs
- License database per vendor/specialist
- Expiration alerts (60, 30, 7 days)
- Solicitation-to-license matching: "Does this vendor hold the required license for this bid?"
- Compliance report for proposal package

## Data Model (per license entry)

```json
{
  "licenseId": "lic_001",
  "vendorId": "vnd_99218",
  "licenseType": "State Commercial Pesticide Applicator",
  "licenseNumber": "PST-4412",
  "issuingAuthority": "Georgia Department of Agriculture",
  "state": "GA",
  "issueDate": "2025-01-15",
  "expirationDate": "2027-12-31",
  "attachmentUrl": "s3://...",
  "verifiedBy": null,
  "verifiedDate": null
}
```

## System Behaviors

### Expiration Monitoring
- Daily cron: check all licenses within 60-day window
- Auto-email/SMS to vendor: "Your [license] expires on [date]. Renew now."
- Escalation at 30 days and 7 days
- Auto-flag vendor as "at risk" if license within 30 days of expiry

### Solicitation Matching
- When solicitation requires "State Commercial Pesticide Applicator License"
- System queries vendor database: who has this license, active, in the required state?
- Filters out vendors without required licenses

### Verification
- Manual verification step for Network Coordinator
- Flag: "unverified" vs "verified" vs "discrepancy found"
- Verification date and reviewer logged for audit

## Dependencies
- [[vendor-onboarding-wizard]]
- [[specialist-onboarding]]
- [[../12-platform-admin/notification-engine]]

## Key Rules & Compliance
- FAR 52.222-46: Evaluation of Professional Employee Compensation
- Some licenses are state-specific — must match contract performance location
- Expired license at proposal or performance = non-compliance

## Open Questions
- Integrate with state license databases for auto-verification?
- Should the system block a vendor from being matched if a key license is expired?
