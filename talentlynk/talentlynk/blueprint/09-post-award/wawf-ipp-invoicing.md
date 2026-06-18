# WAWF/IPP Invoicing

## Purpose
Integrate with the government's electronic invoicing systems — Wide Area Workflow (WAWF) and Invoice Processing Platform (IPP) — to submit proper invoices and track acceptance. Government payment starts with a proper invoice, and the government's portals are the gatekeepers.

## WAWF (Wide Area Workflow)

- **Used by:** Department of Defense (DoD) and some civilian agencies
- **System:** Procurement Integrated Enterprise Environment (PIEE) — WAWF module
- **Document types:** Invoice, Receiving Report, Invoice and Receiving Report (Combo)
- **Key data:** Contract number, Delivery Order number, CLINs, Shipment Number, Acceptance

## IPP (Invoice Processing Platform)

- **Used by:** Treasury Bureau of the Fiscal Service — most civilian agencies
- **System:** Web-based invoice submission and tracking
- **Key data:** PO/Contract number, invoice amount, line items, period of performance

## System Integration

### Invoice Generation
- Pull: contract number, CLIN structure, period of performance, amounts
- Generate: proper invoice with all required fields
- Format: per WAWF or IPP specifications

### Invoice Submission
- **Option A (API Integration):** Submit directly via WAWF/IPP API (if available)
- **Option B (Assisted):** Generate invoice data; human reviews and submits via portal
- **Option C (RPA/Bot):** Automated form-filling bot that enters data into the web portal

### Acceptance Tracking
- Monitor WAWF/IPP for government acceptance signature
- Acceptance triggers: payment clock starts
- Government has 7 days to accept or reject goods/services (FAR 46.502)
- Rejection: flag immediately; route to PM for resolution

### Receiving Report (DD Form 250)
- Required for DoD supply contracts
- Government receiving officer signs to confirm delivery
- System tracks: shipped → delivered → accepted → invoiced

## Invoice Data Model

```json
{
  "invoice": {
    "invoiceNumber": "INV-2026-001",
    "contractNumber": "W912HN-24-C-0001",
    "deliveryOrderNumber": null,
    "issueDate": "2026-09-15",
    "periodOfPerformance": {
      "start": "2026-09-01",
      "end": "2026-09-30"
    },
    "lineItems": [
      {
        "clinNumber": "0001",
        "description": "Grounds Maintenance Services - September 2026",
        "quantity": 1,
        "unit": "month",
        "unitPrice": 85000.00,
        "amount": 85000.00
      }
    ],
    "totalAmount": 85000.00,
    "paymentTerms": "NET 30",
    "remittanceInfo": {
      "bankName": "...",
      "accountNumber": "...",
      "routingNumber": "..."
    }
  }
}
```

## Dependencies
- [[payment-tracking]]
- [[../10-financial-infrastructure/payment-splitting-engine]]
- [[../13-integrations/sam-gov-api]]

## Key Rules & Compliance
- Proper invoice requirements: FAR 52.212-4(g) or FAR 52.232-25
- Invoice must include: contract number, date, description, amount, remittance info
- Government can reject "improper" invoices within 7 days — must state why
- Payment clock starts at government acceptance (services) or receipt of proper invoice (goods)
- WAWF is MANDATORY for DoD contracts (DFARS 252.232-7003)

## Open Questions
- Does WAWF have a usable API, or is it portal-only?
- Should the system support RPA/bot-based portal automation if no API exists?
