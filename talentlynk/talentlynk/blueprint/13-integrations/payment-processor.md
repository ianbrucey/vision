# Payment Processor Integration

## Purpose
Integrate with payment processing and banking APIs to automate ACH and wire transfers to subcontractors when government payments are received. This is the execution layer of the payment routing engine.

## Integration Scope

### Outbound Payments (TalentNyk → Subcontractors)
- ACH transfers (standard: 1-2 business days, same-day: within hours)
- Wire transfers (same day, for large/urgent payments)
- Check issuance (fallback for vendors without electronic banking)

### Inbound Payment Monitoring (Government → TalentNyk)
- Monitor operating bank account for incoming ACH deposits
- Match deposits to outstanding government invoices
- Trigger payment split calculation

## Provider Options

### Option A: Bank API Direct
- Major commercial banks offer APIs (JPMorgan Chase, Bank of America, etc.)
- Higher integration effort per bank
- Lower per-transaction costs
- Full control over payment execution

### Option B: Payment Platform
- Fintech platforms: Stripe Treasury, Modern Treasury, Dwolla, Plaid Transfer
- Faster integration, standardized APIs
- May have transaction limits or compliance restrictions
- Stripe/Moov.io: built for marketplace/platform models (good fit)

### Option C: Hybrid
- Banking relationship for primary accounts
- Payment platform for outbound automation
- Plaid for account verification and balance monitoring

## Core Capabilities

### Account Verification
- Verify subcontractor banking details before first payment
- Plaid Auth or micro-deposit verification
- Store tokenized banking information (PCI compliance)

### Payment Initiation
```json
{
  "payment": {
    "recipient": {
      "vendorId": "vnd_99218",
      "bankToken": "btok_xxx",
      "accountLast4": "1234"
    },
    "amount": 62000.00,
    "method": "ach_standard",
    "reference": "Contract W912HN-24-C-0001",
    "scheduleDate": "2026-10-05"
  }
}
```

### Balance Monitoring
- Check operating account balance (sufficient for upcoming payments?)
- Alert if balance insufficient for scheduled payments
- Link to cash flow forecasting

### Reconciliation
- Match sent payments to bank statement entries
- Flag unmatched transactions
- Generate reconciliation reports

## System Behaviors

### Payment Batch Processing
- Multiple sub payments due on same day → batch for efficiency
- Payment window: 3 days from government receipt
- System can hold payments and batch-submit on Day 3 to maximize float while staying compliant

### Failed Payment Handling
- Insufficient funds → halt, alert Financial Controller immediately
- Invalid account details → notify sub, request updated banking info
- Bank rejection → retry with corrected details or fall back to check

## Dependencies
- [[../10-financial-infrastructure/payment-splitting-engine]]
- [[../09-post-award/payment-tracking]]
- [[../09-post-award/accelerated-payment-routing]]
- [[../01-corporate-foundation/bank-accounts]]

## Key Rules & Compliance
- ACH rules: NACHA operating guidelines
- OFAC compliance: all payment recipients must be screened against sanctions lists
- Prompt Payment Act: sub payments within 3 days of government receipt
- PCI DSS if storing banking information
- Privacy: banking details must be encrypted at rest

## Open Questions
- Which bank will TalentNyk use? (Start with their API capabilities in mind)
- Platform payment provider preference?
- Should the system support international wire transfers for foreign manufacturers (TAA-compliant)?
