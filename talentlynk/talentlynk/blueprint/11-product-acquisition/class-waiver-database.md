# Class Waiver Database

## Purpose
Maintain a current, searchable copy of the SBA's Non-Manufacturer Rule Class Waiver list — products by NAICS code that the SBA has determined have no domestic small business manufacturers. When a solicitation matches a waived product, TalentNyk can source from large corporate suppliers without violating the NMR.

## What Is a Class Waiver?

The SBA periodically reviews NAICS product codes and determines which ones have zero small business manufacturers in the U.S. For these items, the SBA issues a "class waiver" — a blanket exemption from the NMR for that specific product class.

**Practical effect:** If the SBA has waived NAICS 339113 (Surgical Appliance and Supplies Manufacturing), TalentNyk can buy surgical supplies from a large corporation like Medline or McKesson and sell them under a small business set-aside. The SBA has acknowledged that no small business makes these items, so the NMR restriction is lifted.

## Database Schema

```json
{
  "classWaiver": {
    "naicsCode": "339113",
    "naicsDescription": "Surgical Appliance and Supplies Manufacturing",
    "productDescription": "Surgical staplers and associated staple cartridges",
    "waiverNumber": "CW-2024-001",
    "issueDate": "2024-03-15",
    "expirationDate": "2029-03-15",
    "sbaFederalRegisterNotice": "89 FR 12345",
    "isActive": true,
    "notes": "Waiver applies to surgical staplers only, not all NAICS 339113 products"
  }
}
```

## Data Ingest

### Initial Load
- Scrape/download the full SBA Class Waiver list from SBA.gov
- Parse into structured database
- Index by NAICS code for fast lookup

### Updates
- SBA updates the list periodically (new waivers added, expired waivers removed)
- System should check for updates monthly
- Auto-flag: is this waiver still current? (some waivers have expiration dates)
- CO may issue solicitation-specific waivers — these should also be tracked

## Lookup Integration

### Solicitation-Time Check
```
Solicitation NAICS: 339113
  → Query class waiver database
  → Result: WAIVER FOUND (CW-2024-001, active until 2029)
  → Action: GREEN LIGHT — can source from any supplier (large or small)
```

### Bid-Time Warning
```
Solicitation NAICS: 337214 (Office Furniture, non-wood)
  → Query class waiver database
  → Result: NO WAIVER FOUND
  → Next Check: Do we have a small manufacturer?
  → If NO: WARNING — cannot bid as small business set-aside unless NMR waiver obtained
```

## Dependencies
- [[non-manufacturer-rule]]
- [[product-set-aside-logic]]
- [[../13-integrations/sba-data-integration]]

## Key Rules & Compliance
- SBA Class Waiver list: https://www.sba.gov/document/support-non-manufacturer-rule-class-waivers
- Waivers are item-specific within a NAICS — read the scope carefully
- Some waivers cover the ENTIRE NAICS code; others cover only specific items
- Waivers expire (typically 5 years) — system must track expiration
- Just because a waiver exists today doesn't mean it will exist when the contract is awarded

## Open Questions
- Auto-sync: scrape SBA.gov weekly, monthly, or on-demand per solicitation?
- Should the system alert when a frequently-used waiver is approaching expiration?
