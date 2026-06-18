# PO Financing

## Purpose
Leverage a guaranteed government Purchase Order (PO) / contract award to obtain working capital financing — covering the sub's upfront costs (materials, labor) between contract start and first government payment. This is the primary mechanism for scaling without using your own cash.

## How PO Financing Works

1. TalentNyk wins a government contract (the "Purchase Order" in financing terms)
2. Financier advances 80-95% of the contract value upfront (or as needed)
3. TalentNyk uses the advance to pay subcontractors and cover costs
4. Government pays TalentNyk per contract terms (Day 15-30)
5. TalentNyk repays financier with the government payment
6. Financier deducts their fee (typically 1-3%) and releases the remainder

## The Key Insight

PO financiers lend against the **government's credit**, not TalentNyk's credit. The U.S. government has the lowest default risk on earth. This means:
- Startups and new entities can qualify (no long credit history needed)
- Rates are relatively low (1-3% vs. 15-30% for unsecured business loans)
- Approval is based on the contract, not the company's balance sheet

## Integration Workflow

### Pre-Award (Setup)
- Financier pre-approves TalentNyk as a client
- Standing agreement: when a contract is won, financing can be activated within 24-48 hours
- System stores: financier contact, rates, advance percentages, document requirements

### Post-Award (Activation)
1. Contract award uploaded to system
2. System exports: contract document, subcontractor payment schedule, total financing need
3. Export sent to financier (API or manual)
4. Financier reviews and approves within 24-48 hours
5. Financier wires advance to TalentNyk's operating account
6. System detects deposit, allocates to sub payments

### Repayment
1. Government pays TalentNyk
2. System detects deposit
3. System calculates: repayment = advance + fee
4. Auto-route repayment to financier
5. Record: PO financing transaction closed

## System Integration

```json
{
  "poFinancingRequest": {
    "contractNumber": "W912HN-24-C-0001",
    "agency": "DLA",
    "contractValue": 50000.00,
    "contractType": "FFP",
    "periodOfPerformance": "2026-10-01 to 2027-03-31",
    "subcontractorCosts": 30000.00,
    "financingRequired": 30000.00,
    "purpose": "Subcontractor raw materials for 1,000 first-aid pouches"
  }
}
```

## Dependencies
- [[../09-post-award/contract-activation]]
- [[../09-post-award/payment-tracking]]
- [[../13-integrations/payment-processor]]
- [[net-terms-management]]

## Key Rules & Compliance
- PO Financing is legal and common in GovCon
- Assignment of Claims (FAR 32.8): financier may require assignment of contract proceeds
- CO must acknowledge Assignment of Claims — it's a routine administrative action
- Financier's rights are subordinate to the government's rights (standard)
- Factoring vs. PO Financing: factoring is per-invoice; PO Financing is against the whole contract

## Open Questions
- Single PO financier partner (simpler) or multi-financier marketplace (competitive rates)?
- Should the system auto-recommend PO Financing when the cash gap exceeds a threshold?
