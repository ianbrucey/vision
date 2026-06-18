# Payment Tracking

## Purpose
Monitor government payments — receipt, amount, timing — and track against contractual payment milestones and Prompt Payment Act deadlines. This is the heartbeat of the post-award financial engine.

## Payment Tracking Dimensions

### Government Payments Received
- Invoice number and date
- Amount invoiced
- Amount received
- Receipt date and time (critical for Prompt Payment Act timing)
- Days to pay (from invoice date or acceptance date)
- Payment method (ACH, check)
- Payment reference number

### Subcontractor Payments Owed
- Amount owed to each sub
- Trigger: government payment received
- Deadline: within 3-7 days of government receipt (Prompt Payment Act acceleration)
- Payment status: Pending / Processing / Sent / Confirmed

### Retention of Prime Margin
- Total received - total owed to subs = prime margin retained
- Reconciliation against expected margin

## System Behavior

### Payment Detection
- Monitor operating bank account for ACH deposits from Treasury
- Match deposit to outstanding invoice
- Auto-record: amount, date, time, reference

### Payment Allocation
- Split government payment per subcontract terms
- Calculate: sub's share, prime's share
- Generate payment instructions for each sub

### Aging & Alerts
- Days since invoice submitted
- Days since government acceptance (if goods/services accepted but invoice not submitted)
- Alert if payment exceeds Prompt Payment Act timeline (30 days standard, 15 days accelerated for small business)
- Alert if sub hasn't been paid within 3 days of government receipt

### Payment Ledger
```
Invoice INV-2026-001 | Submitted: 2026-09-15 | Amount: $85,000
  Gov Acceptance: 2026-09-20
  Gov Payment Received: 2026-10-03 (13 days from acceptance ✓)
  Sub Payment Due: 2026-10-10 (7 days from receipt)
  Sub Payment Sent: 2026-10-05 ($62,000 to Atlanta Commercial Landscaping LLC)
  Prime Margin Retained: $23,000
```

## Dependencies
- [[accelerated-payment-routing]]
- [[../10-financial-infrastructure/payment-splitting-engine]]
- [[../13-integrations/payment-processor]]

## Key Rules & Compliance
- Prompt Payment Act (FAR 52.232-25): Government must pay within 30 days of proper invoice (15 days for small business accelerated)
- FAR 52.232-40: Prime must pass accelerated payments to subs within 3 days
- Interest penalties: Government owes interest on late payments (automatically calculated)
- Improper invoice: government may reject — system must track rejections and resubmissions

## Open Questions
- Bank integration: Plaid, direct bank API, or manual reconciliation?
- Should the system auto-generate late payment interest claims to the government?
