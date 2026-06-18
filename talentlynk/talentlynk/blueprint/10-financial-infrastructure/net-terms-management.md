# Net Terms Management

## Purpose
Track and manage commercial credit terms with suppliers (Net 30, Net 60, etc.) that create a natural cash flow buffer — TalentNyk can sell products to the government on 15-day payment terms while paying suppliers on 30-60 day terms. This "float" is free working capital.

## The Float Strategy

```
Timeline:
Day 0:   TalentNyk orders from supplier on Net 30 terms
Day 7:   Supplier ships to government
Day 10:  Government accepts delivery
Day 10:  TalentNyk invoices government (15-day accelerated payment)
Day 25:  Government pays TalentNyk ($50K)
Day 30:  TalentNyk pays supplier ($30K)
         → $20K profit retained, ZERO own cash used
```

The 5-day gap between government payment and supplier payment is a natural, cost-free float.

## Tracking Data

### Per-Supplier Credit Profile
```json
{
  "supplierId": "sup_001",
  "supplierName": "Uline",
  "creditTerms": {
    "standardNetTerms": "net_30",
    "creditLimit": 50000.00,
    "currentBalance": 12000.00,
    "availableCredit": 38000.00,
    "lastCreditReview": "2026-01-15",
    "paymentHistory": "excellent"
  },
  "contactInfo": {
    "creditManager": "Jane Smith",
    "email": "credit@uline.com",
    "phone": "800-555-0100"
  }
}
```

### Per-Order Tracking
```json
{
  "orderId": "PO-2026-0042",
  "supplierId": "sup_001",
  "orderDate": "2026-10-01",
  "orderAmount": 12000.00,
  "terms": "net_30",
  "paymentDueDate": "2026-10-31",
  "govContractLinked": "W912HN-24-C-0001",
  "govPaymentExpected": "2026-10-20",
  "floatDays": 11,
  "status": "paid_on_time"
}
```

## System Behaviors

### Credit Limit Monitoring
- Track total outstanding against each supplier's credit limit
- Alert when approaching limit (80% utilization)
- Alert when credit review is due

### Payment Scheduling
- Auto-schedule supplier payments based on due dates
- Optimize: pay as late as possible without damaging credit (maximize float)
- Early payment discount: if supplier offers 2% Net 10 vs. Net 30, system calculates whether discount beats float

### Float Optimization
- For a given government contract + supplier order, calculate:
  - Expected government payment date
  - Supplier payment due date
  - Float days = supplier due date - government payment date
  - Positive float = free working capital
  - Negative float = cash gap (may need PO Financing)

## Dependencies
- [[po-financing]]
- [[cash-flow-forecasting]]
- [[../09-post-award/payment-tracking]]

## Key Rules & Compliance
- Building commercial credit takes time — track payment history to demonstrate creditworthiness
- Late payments damage credit ratings (Dun & Bradstreet) — system prevents missed payments
- Some government contracts prohibit purchasing from debarred suppliers — check SAM.gov exclusions
- Net terms are a commercial agreement, not a government requirement — no FAR constraints

## Open Questions
- Should the system auto-negotiate Net 60 terms for high-volume suppliers?
- Track supplier diversity for potential small business subcontracting credit?
