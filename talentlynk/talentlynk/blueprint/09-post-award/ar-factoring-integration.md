# AR Factoring Integration

## Purpose
Provide API hooks and workflow for Accounts Receivable (AR) Factoring — selling government receivables to a financier at a small discount in exchange for immediate cash. This solves the working capital gap: sub needs to pay workers on Day 1-30, but government pays on Day 45+.

## When Factoring Is Triggered

- **Cash flow gap:** Sub needs payment before government pays TalentNyk
- **Large contract:** Sub's labor draw exceeds TalentNyk's available cash
- **Vendor request:** Sub explicitly requests early payment (factoring as a service)
- **Policy:** Per-contract decision or standing arrangement

## The Factoring Transaction

### Standard Flow
```
[Work Performed by Sub] → [Sub invoices TalentNyk] → [TalentNyk invoices Government]
    → [TalentNyk assigns receivable to Financier] → [Financier advances ~90% to TalentNyk]
    → [TalentNyk pays Sub] → [Government pays TalentNyk] → [TalentNyk repays Financier + fee]
    → [Remaining ~10% released to TalentNyk (minus factoring fee)]
```

### Factoring Rate
- Typically 1-3% of invoice value (varies by contract, agency, size)
- Financier's risk: government credit is extremely strong (virtually no default risk)
- System stores: factoring rate, financier contact, advance percentage

## System Integration Points

### Invoice Export
- When government invoice is generated, system can optionally:
  - Auto-notify financier of new invoice
  - Export invoice data to financier's portal/API
  - Attach supporting documents (government acceptance, invoice, contract)

### Advance Processing
- Financier advances funds to TalentNyk's operating account
- System detects advance, allocates to sub payment
- System tracks: total factoring debt outstanding, per-invoice

### Repayment
- Government pays → system detects deposit
- System auto-calculates: repayment amount (advance + fee) to financier
- System routes repayment to financier
- System records: factoring transaction closed

## API Hook Design

```json
{
  "factoringEvent": "invoice_generated",
  "invoice": {
    "invoiceNumber": "INV-2026-001",
    "contractNumber": "W912HN-24-C-0001",
    "agency": "DLA",
    "amount": 85000.00,
    "invoiceDate": "2026-09-15",
    "acceptanceDate": "2026-09-20",
    "expectedPaymentDate": "2026-10-20",
    "subcontractorAmount": 62000.00
  },
  "factoringRequest": {
    "advanceRequested": 62000.00,
    "financierId": "fin_001"
  }
}
```

## Dependencies
- [[payment-tracking]]
- [[../10-financial-infrastructure/po-financing]]
- [[../13-integrations/payment-processor]]

## Key Rules & Compliance
- Assignment of Claims (FAR Subpart 32.8): must notify CO if payments are assigned to financier
- Factoring is legal and common in GovCon — not a red flag
- Factoring fees should be priced into the contract (or absorbed as cost of doing business)
- Some government contracts prohibit assignment — system must check contract terms

## Open Questions
- Integrate with specific GovCon factoring companies (e.g., Parabilis, eCapital)?
- Should factoring be an automated decision (if cash gap > X) or always manual?
