# Submission Tracking

## Purpose
Track the status of every proposal submission — confirmation of receipt, government acknowledgment, amendments during evaluation, and final award/decline notification. The proposal doesn't end at "submit" — evaluation is a multi-month process that must be monitored.

## Submission Lifecycle

```
[Not Yet Submitted] → [Submitted] → [Received/Acknowledged] → [In Evaluation]
    → [Clarifications/Discussions (if any)] → [Award Notice] OR [Not Awarded]
    → [Post-Award Debrief]
```

## Tracking States

| State | Meaning |
|-------|---------|
| **Draft** | Proposal in preparation |
| **Ready to Submit** | Approved, compliance-checked, awaiting submission |
| **Submitted** | Sent to government (email, portal, physical) |
| **Received** | Government confirmed receipt (auto-reply, portal status) |
| **In Evaluation** | Government evaluating proposals |
| **Clarifications** | Government requested clarifications or discussions |
| **Awarded** | Contract awarded to TalentNyk |
| **Not Awarded** | Contract awarded to another bidder |
| **Protested** | Award protested (by TalentNyk or by competitor) |
| **Cancelled** | Solicitation cancelled by government |

## System Behaviors

### Submission Confirmation
- If submitted via email: system monitors inbox for auto-confirmation reply; flags if no confirmation within X hours
- If submitted via portal (SAM.gov, eBuy, PIEE): system logs portal confirmation
- If physical: tracking number logged
- No confirmation within 24 hours → alert Proposal Manager to follow up

### Evaluation Timeline Monitoring
- Track expected award date (from solicitation or estimated)
- Flag if no update within X days past expected date
- Track government Q&A or clarification requests

### Amendment Monitoring
- System monitors SAM.gov for amendments to submitted solicitations
- If amendment is issued after submission: alert immediately
- Amendment may require revised proposal (see [[amendment-handling]])

### Award/Decline
- Award: trigger post-award workflow ([[../09-post-award/contract-activation]])
- Not awarded: schedule debrief request; capture lessons learned
- Protest window: track 10-day GAO protest window post-award

## Dashboard Integration

- Pipeline dashboard: all proposals by status, value, probability
- Win rate tracking per vendor, per NAICS, per agency
- Days-in-status aging

## Dependencies
- [[../12-platform-admin/dashboard-analytics]]
- [[../12-platform-admin/notification-engine]]
- [[amendment-handling]]
- [[../09-post-award/contract-activation]]

## Key Rules & Compliance
- Late proposals: not accepted (FAR 52.212-1(f)). System must enforce submission BEFORE deadline.
- GAO protest: must be filed within 10 days of award or debrief (whichever is later)
- Debrief: entitled to a debrief upon request after award decision (FAR 15.506)

## Open Questions
- Should the system proactively poll SAM.gov/eBuy for status updates?
- Automated GAO protest deadline tracking?
