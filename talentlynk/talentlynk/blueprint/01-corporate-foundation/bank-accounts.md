# Bank Accounts & Payment Routing

## Purpose
Define the banking and financial account architecture for receiving government payments and routing funds to subcontractors.

## Account Structure

### Operating Account (Per Entity)
- Receives all government ACH payments
- Primary operating funds
- Used for prime management margin retention

### Project-Specific Accounts (Optional, for Large Contracts)
- Segregated per large contract if required by solicitation
- Used for Assignment of Claims setup (FAR Subpart 32.8)
- Provides subcontractors' banks with collateral visibility

### Subcontractor Payment Account
- Dedicated account for rapid sub payment routing
- Funds flow: Government → Operating → Sub Payment → Subcontractors
- Must execute payments within 3-7 days of government receipt (Prompt Payment Act acceleration)

## Payment Flow

```
[Government ACH Deposit]
         │
         ▼
[Operating Account: Full Contract Payment]
         │
         ├──► [Prime Margin Retained]
         │
         └──► [Sub Payment Account]
                    │
                    ▼
              [Subcontractor ACH/Wire within 3 days]
```

## System Responsibilities

- **Payment Detection:** Monitor operating account for government deposits
- **Payment Splitting:** Auto-calculate prime/sub split based on subcontract terms
- **Accelerated Payment Trigger:** Within 3 days of receipt, initiate sub payment
- **Compliance Timestamp:** Log receipt time and payment time for audit
- **AR Factoring Hook:** If factoring is active, route payment to financier first

## Dependencies
- [[../10-financial-infrastructure/payment-splitting-engine]]
- [[../09-post-award/payment-tracking]]
- [[../09-post-award/accelerated-payment-routing]]
- [[../13-integrations/payment-processor]]

## Key Rules & Compliance
- FAR 52.232-40: Prompt Payment Act — accelerated payments to small business subs
- Prime must pass accelerated payments to subs within 3 days of receipt
- Assignment of Claims: FAR Subpart 32.8
- Maintain clear audit trail of all payment receipts and disbursements

## Open Questions
- Which bank(s) will be used?
- Will project accounts be created manually or programmatically?
- What payment processor/API will be used for ACH?
