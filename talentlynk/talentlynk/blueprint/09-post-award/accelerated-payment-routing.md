# Accelerated Payment Routing

## Purpose
Enforce the FAR 52.232-40 requirement that accelerated payments received by a small business Prime must be passed down to subcontractors within 3-7 days. This is a hard compliance requirement — failure to route payments on time = contract breach.

## The Legal Requirement

Under FAR 52.232-40 (Providing Accelerated Payments to Small Business Subcontractors):
- When the government accelerates payments to a small business prime (within 15 days)
- The prime **must** pass accelerated payments to its subcontractors "to the maximum extent practicable"
- Industry standard and DOD policy: within **3 days** of government payment receipt
- "Accelerated" means faster than the standard 30-day payment cycle

## Payment Routing Pipeline

```
[Government ACH Deposit Detected]
          │
          ▼
[Payment Allocation: Calculate sub vs. prime shares]
          │
          ▼
[Prime Margin: Retain in operating account]
          │
          ▼
[Sub Payment: Initiate ACH/wire to subcontractor]
          │
          ▼
[Timing Check: Was sub paid within 3-7 days?]
          │
    ┌─────┴─────┐
    ▼           ▼
 [YES]       [NO → ALERT: Compliance breach]
    │
    ▼
[Payment Confirmation: Track sub's receipt]
          │
          ▼
[Audit Log: Complete paper trail]
```

## Routing Logic

### Payment Split Calculation
```
For each subcontract on the contract:
  SubAmount = GovernmentPayment × (SubcontractValue / TotalContractValue)
  OR
  SubAmount = SubInvoiceAmount (if sub invoiced separately for specific work)
  OR
  SubAmount = ContractSpecificAllocation (per subcontract payment schedule)
```

### Payment Method
- ACH (preferred: fast, traceable)
- Wire (urgent or large amounts)
- Check (fallback only — slow, untraceable)

### Timing Enforcement
- System clock starts at government ACH deposit timestamp
- Sub payment must be initiated within:
  - 3 business days (accelerated / best practice)
  - 7 calendar days (maximum acceptable)
- System prevents sub payment initiation beyond 7 days without Compliance Officer override
- Override requires written justification (logged)

## Compliance Monitoring

### Real-Time Dashboard
- Payment status per contract
- Days since government receipt
- Countdown to sub payment deadline
- Green: within timeline / Yellow: approaching deadline / Red: past deadline

### Compliance Reporting
- Monthly/quarterly: report on all Prompt Payment Act transactions
- Audit trail: government receipt → sub payment → confirmation
- Available for DCAA audit, CO review, or small business compliance verification

## Dependencies
- [[payment-tracking]]
- [[../10-financial-infrastructure/payment-splitting-engine]]
- [[../13-integrations/payment-processor]]

## Key Rules & Compliance
- FAR 52.232-40: Mandatory accelerated payment flow-down
- DOD Class Deviation 2018-O0015: Accelerated payments to small business subs
- "Pay-when-paid" not "pay-if-paid" — sub must be paid if government pays, even if late
- Payment delays caused by TalentNyk (not government) → TalentNyk still owes sub (not excused by pay-when-paid clause)

## Open Questions
- What's the penalty structure if TalentNyk misses the 3-day window?
- Should subs have visibility into the payment tracking dashboard for their contracts?
