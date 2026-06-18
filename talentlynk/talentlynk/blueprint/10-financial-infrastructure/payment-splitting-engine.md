# Payment Splitting Engine

## Purpose
Automatically calculate and execute the split of every government payment between TalentNyk's prime margin and subcontractor payments. This is the transaction-level engine that ensures subs get paid exactly what they're owed, exactly when they're owed it.

## Inputs
- Government payment received (amount, contract, invoice reference)
- Active subcontract(s) for that contract
- Subcontract payment terms (fixed price, T&M, instalment schedule)
- Subcontractor invoices (if subs invoice TalentNyk separately)
- Any outstanding advances (PO Financing, AR Factoring)

## Outputs
- Split instructions: how much to each sub, how much retained
- Payment initiation: actual ACH/wire to subs
- Journal entries for accounting
- Audit trail for compliance

## Split Calculation Logic

### Fixed Price Subcontract
```
SubAmount = PREDEFINED_AMOUNT (already agreed in subcontract)
PrimeAmount = TotalReceived - SubAmount
```

### Percentage-Based Split
```
SubAmount = TotalReceived × SubPercentage
PrimeAmount = TotalReceived × PrimePercentage
```

### Reimbursable / Cost-Plus
```
SubAmount = SubActualCosts + SubFee
PrimeAmount = TotalReceived - SubAmount
```

### Multiple Subcontractors
```
For a contract with 3 subs:
  Sub1_Amount = Sub1ContractShare × TotalReceived
  Sub2_Amount = Sub2ContractShare × TotalReceived
  Sub3_Amount = Sub3ContractShare × TotalReceived
  PrimeAmount = TotalReceived - (Sub1 + Sub2 + Sub3)
```

### With Financing Repayment
```
If PO Financing active on this contract:
  FinancierRepayment = FinancingAdvance + FinancingFee
  SubAmount = Per subcontract terms
  PrimeAmount = TotalReceived - FinancierRepayment - SubAmount
```

## Execution Flow

```
1. Government ACH detected in operating account
2. System matches payment to contract/invoice
3. System retrieves active subcontracts and payment terms
4. System calculates split: Sub A = $X, Sub B = $Y, Prime Retain = $Z
5. Split presented for review (auto-approved if within configured thresholds)
6. Payment instructions sent to bank/payment processor
7. Sub payments initiated within 3-day window
8. Prime margin retained in operating account
9. Complete transaction recorded in ledger
10. Subs notified: "Payment of $X sent for contract W912HN-24-C-0001"
```

## Payment Methods

| Method | Best For | Speed | Cost |
|--------|----------|-------|------|
| ACH | Standard sub payments | 1-2 business days | Low (~$0.25-1.00) |
| Same-Day ACH | Urgent (within timeline) | Same day | Medium (~$5-10) |
| Wire | Large amounts, urgent | Same day | High (~$15-30) |
| Check | Backup only | 5-7 days | Low |

System auto-selects method based on amount, urgency, and cost.

## Audit Trail

Every split generates:
- Transaction ID
- Timestamp
- Government payment reference
- Contract number
- Calculated split amounts
- Actual payment amounts
- Payment method and confirmation
- User who reviewed/approved (or "auto-approved")
- Link to subcontract documentation

## Dependencies
- [[../09-post-award/payment-tracking]]
- [[../09-post-award/accelerated-payment-routing]]
- [[../13-integrations/payment-processor]]
- [[cash-flow-forecasting]]

## Key Rules & Compliance
- Prompt Payment Act (FAR 52.232-40): subs paid within 3 days
- Payment must match subcontract terms — overpayment = loss; underpayment = breach
- Bank reconciliation: system payments must match bank statements
- All splits must be auditable (for DCAA, financial audit, or subcontractor dispute)

## Open Questions
- Should subs see the split calculation (transparency) or just the payment (simplicity)?
- Automated approval threshold: below what dollar amount are splits auto-approved?
