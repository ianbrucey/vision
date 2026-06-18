# Audit Log

## Purpose
Maintain a comprehensive, immutable audit trail of all significant actions within the platform. This is critical for FAR compliance, protest defense, DCAA audit readiness, and internal accountability.

## What Gets Logged

### User Actions
- Login/logout (timestamp, IP, user agent)
- All agreement signatures (who, what, when, IP)
- Proposal creation, editing, approval, submission
- Vendor selection for bids
- Pricing changes and approvals
- Manual overrides of system recommendations (with justification)
- User permission changes

### System Actions
- Solicitation ingestion (source, timestamp)
- Automated matching results (which vendors surfaced)
- Automated pricing calculations (inputs and output)
- Document generation (which template, which data sources)
- Payment receipt and routing
- Agreement status changes

### Data Changes
- Any modification to vendor profile, pricing matrix, licenses
- Any modification to entity data (SAM registration, NAICS, certifications)
- Agreement template changes (who changed what, before/after)
- System configuration changes

## Log Entry Format

```json
{
  "logId": "log_20261015_0042",
  "timestamp": "2026-10-15T14:32:00Z",
  "actor": {
    "userId": "usr_0012",
    "name": "Jane Smith",
    "role": "proposal_manager",
    "ip": "192.168.1.100"
  },
  "action": "proposal_submitted",
  "target": {
    "type": "proposal",
    "id": "bid_0192",
    "solicitationNumber": "W912HN-24-R-0001"
  },
  "details": {
    "submissionMethod": "email",
    "submissionEmail": "contracting.officer@agency.gov",
    "vendorSelected": "vnd_99218",
    "bidPrice": 58993.00,
    "complianceChecklist": "all_green"
  },
  "result": "success"
}
```

## Retention & Access

- **Retention:** Minimum 6 years (matches government contract document retention requirements under FAR 4.805)
- **Immutability:** Once written, log entries cannot be modified or deleted
- **Access:** Compliance Officer and Administrator roles; read-only
- **Export:** Must be exportable for DCAA audit, legal discovery, or protest response

## Audit Reports

The system should generate:
- **User Activity Report:** All actions by a specific user in a date range
- **Proposal Audit Trail:** Every action taken on a specific proposal from ingestion to award
- **Payment Audit Trail:** Government receipt → split calculation → sub payment → confirmation
- **Agreement Audit Trail:** Generation → routing → signature → expiration
- **Compliance Events:** All compliance-related alerts and resolutions

## Dependencies
- [[internal-team-management]]
- [[../08-review-submission/submission-tracking]]
- [[../09-post-award/payment-tracking]]

## Key Rules & Compliance
- FAR 4.805: Contract files retention — 6 years after final payment
- DCAA audit: Defense Contract Audit Agency may audit any cost-reimbursement or T&M contract
- FAR 3.104: Procurement integrity — audit trail proves no improper disclosure
- Legal hold: audit logs must be preserved during any protest or litigation

## Open Questions
- Log storage: dedicated audit database, append-only ledger, or cloud logging service?
- Should the system support "legal hold" functionality to freeze logs related to specific contracts?
