# Cash Flow Forecasting

## Purpose
Model and predict cash inflows (government payments) and outflows (subcontractor payments, operating expenses) across all active and pipeline contracts. The goal: never be caught without cash to pay a subcontractor on time.

## Forecasting Dimensions

### Cash Inflows
- **Pipeline (probabilistic):** Expected contract wins × probability × expected payment timing
- **Awarded backlog:** Signed contracts with known payment schedules
- **Invoiced but unpaid:** Invoices submitted, awaiting government payment
- **Other:** Financing advances (PO Financing, AR Factoring)

### Cash Outflows
- **Subcontractor payments:** Tied to government payment receipt (pay-when-paid)
- **Payroll:** W-2 employees (Key Personnel activated on contracts)
- **Operating expenses:** Platform, office, compliance, professional services
- **Financing repayment:** PO Financing / AR Factoring repayment upon government receipt
- **Supplier payments:** Product acquisition orders on net terms

## Forecast Model

### Short-Term (Next 30 Days)
```json
{
  "forecastDate": "2026-10-01",
  "openingCash": 25000.00,
  "inflows": [
    {"source": "INV-2026-001 Gov Payment", "amount": 85000.00, "expectedDate": "2026-10-03", "probability": 0.95},
    {"source": "INV-2026-002 Gov Payment", "amount": 50000.00, "expectedDate": "2026-10-15", "probability": 0.90}
  ],
  "outflows": [
    {"destination": "Sub Payment - vnd_99218", "amount": 62000.00, "dueDate": "2026-10-10"},
    {"destination": "Supplier Payment - Uline", "amount": 12000.00, "dueDate": "2026-10-31"},
    {"destination": "Payroll", "amount": 8000.00, "dueDate": "2026-10-15"}
  ],
  "projectedClosingCash": 78000.00,
  "minimumCashThreshold": 15000.00,
  "cashGapRisk": "none"
}
```

### Medium-Term (30-90 Days)
- Roll up expected contract wins × probability from pipeline
- Layer in expected subcontractor draws

### Alerts
- **Cash Gap Warning:** Projected cash drops below threshold within 30 days
- **Sub Payment at Risk:** Inflow expected after sub payment due date
- **Opportunity:** Excess cash identified → could be deployed or reserved

## System Behaviors

### Auto-Generated Alerts
```
ALERT: Cash Gap Detected
  Date: Oct 10, 2026
  Issue: Sub payment of $62,000 due to vnd_99218 on Oct 10, 
         but government payment of $85,000 not expected until Oct 15.
  Gap: 5 days, $37,000 shortfall (after accounting for other cash)
  Recommended: PO Financing advance of $40,000 to cover gap.
  Cost of Financing: ~$400 (1% on $40,000)
```

### Rolling Forecast
- Updated daily or on each transaction
- As government payments come in and sub payments go out, forecast recalculates
- Pipeline probability adjustments as bids are won/lost

## Dependencies
- [[po-financing]]
- [[net-terms-management]]
- [[payment-splitting-engine]]
- [[../09-post-award/payment-tracking]]
- [[../08-review-submission/submission-tracking]] (pipeline data)

## Key Rules & Compliance
- Cash flow forecasting is internal — no government reporting requirement
- But: inability to pay subs = contract performance issue → government cares
- Subcontractor payment delays beyond 7 days = Prompt Payment Act violation

## Open Questions
- Should the system recommend specific financing actions based on forecast gaps?
- Cash reserve policy: what's the minimum safe cash balance?
