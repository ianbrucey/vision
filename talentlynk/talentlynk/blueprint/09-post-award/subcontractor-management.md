# Subcontractor Management

## Purpose
Ongoing management of active subcontractors during contract performance — performance monitoring, deliverable tracking, invoicing, compliance verification, and communication. This is the operational backbone of the post-award phase.

## Core Functions

### 1. Performance Monitoring
- Track subcontractor deliverables against the subcontract SOW
- Progress reporting cadence (weekly, monthly — per subcontract terms)
- Quality metrics: defect rates, rework, government acceptance rates
- Flag: late deliverables, quality issues, performance concerns

### 2. Deliverable Tracking
```
Deliverable: Monthly Grounds Maintenance Report
  Due: 5th of each month
  Status: Submitted (Sept), Submitted (Oct), Overdue (Nov)
  Action: Auto-escalate to PM + notify sub
```

### 3. Subcontractor Invoicing
- Sub submits invoice through vendor portal
- System validates: work performed matches deliverables
- System validates: invoice amount matches subcontract pricing
- Auto-approve or route for PM approval
- Approved invoices queued for payment

### 4. Compliance Monitoring
- License expiration during performance: auto-alert 60/30/7 days
- Insurance expiration: alert
- Certification renewal: alert
- Expired compliance item → flag sub as "at risk"

### 5. Communication
- Contract-related messaging (internal to platform, not email)
- Change order notifications
- Government feedback relay (CPARS, COR comments)
- Scheduled check-ins

### 6. Issue Management
- Track issues: performance, compliance, payment, communication
- Severity levels: Minor, Major, Critical
- Resolution tracking and escalation

## Subcontractor Scorecard

After each contract (or quarterly during long contracts), the system generates a subcontractor scorecard:

| Dimension | Weight | Score |
|-----------|--------|-------|
| Quality of Work | 30% | 4.2/5 |
| Timeliness | 25% | 4.5/5 |
| Compliance | 20% | 5.0/5 |
| Communication | 15% | 3.8/5 |
| Pricing Accuracy | 10% | 4.0/5 |
| **Composite** | | **4.3/5** |

Scorecard feeds back into [[../05-matching-engine/vendor-matching-algorithm]] — high-performing subs get ranked higher for future bids.

## Dependencies
- [[../05-matching-engine/vendor-matching-algorithm]]
- [[../02-onboarding/license-certification-tracker]]
- [[payment-tracking]]
- [[accelerated-payment-routing]]
- [[../12-platform-admin/vendor-portal]]

## Key Rules & Compliance
- Subcontractor performance directly affects prime's CPARS rating
- Prime is ultimately responsible for sub's work to the government
- Documentation is critical: if sub fails, prime needs evidence for disputes/termination
- Subcontractor must comply with all flow-down clauses from the prime contract

## Open Questions
- Should subs have a self-service portal for deliverable submission and invoicing?
- How to handle subcontractor disputes — built-in mediation workflow?
