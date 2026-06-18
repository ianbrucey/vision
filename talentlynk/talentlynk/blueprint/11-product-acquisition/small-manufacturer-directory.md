# Small Manufacturer Directory

## Purpose
Build and maintain a proprietary directory of domestic small business manufacturers — the "American Alibaba" layer. This is the strategic asset that enables compliant product acquisition under small business set-asides. Every entry represents a verified U.S. factory that can supply products to the government through TalentNyk.

## Why This Matters

The Non-Manufacturer Rule means TalentNyk can ONLY source from small domestic manufacturers for set-aside product contracts. Large suppliers like Uline, Grainger, and Quill are off-limits for set-asides unless a waiver exists. The manufacturer directory IS the product-side supply chain.

## Discovery Methods

### 1. Active Recruitment
- Search SBA Dynamic Small Business Search (DSBS) by manufacturing NAICS
- Attend industry trade shows (manufacturing, defense, textiles)
- LinkedIn outreach to small U.S. manufacturers
- Manufacturing extension partnerships (MEP centers in each state)
- State economic development databases

### 2. Passive / Inbound
- Manufacturers find TalentNyk through marketing
- Referral from existing network partners
- SBA.gov / SAM.gov presence

### 3. Automated Discovery
- Web scraping of U.S. manufacturer directories
- NAICS-based database queries
- ThomasNet, IndustryNet, Maker's Row

## Directory Data Model

```json
{
  "manufacturerId": "mfr_0047",
  "companyName": "TexShield Fabrics",
  "isVerifiedManufacturer": true,
  "verificationMethod": "site_visit",
  "verificationDate": "2026-03-15",
  "facilityInfo": {
    "address": "123 Industrial Dr, Austin, TX 78701",
    "squareFeet": 25000,
    "employees": 35,
    "yearsInOperation": 12,
    "equipment": ["Industrial sewing machines", "RF welding", "Cutting tables"]
  },
  "productCatalog": [
    {
      "productId": "prd_001",
      "name": "Ruggedized First-Aid Pouch",
      "description": "MOLLE-compatible, 1000D Cordura, 4 internal pockets",
      "category": "tactical_gear",
      "naicsCodes": ["314910", "315990"],
      "unitCost": 30.00,
      "minOrderQuantity": 500,
      "leadTimeDays": 45,
      "buyAmericanCompliant": true,
      "berryCompliant": true,
      "countryOfOrigin": "USA"
    }
  ],
  "certifications": [
    {"type": "small_business", "status": "certified"},
    {"type": "iso_9001", "status": "certified"},
    {"type": "berry_amendment", "status": "compliant"}
  ],
  "pastContracts": [
    {
      "agency": "DLA",
      "product": "Custom medical pouches",
      "value": 50000.00,
      "year": 2025
    }
  ],
  "onboardingStatus": "active",
  "networkAgreements": {
    "mouSigned": "2026-03-15",
    "ndaSigned": "2026-03-15"
  }
}
```

## Manufacturer vs. Dealer Verification

### Verification Methods
1. **Self-declaration:** Manufacturer attests they make the products (lowest confidence)
2. **Document evidence:** Equipment lists, facility photos, raw material purchase orders
3. **Third-party verification:** D&B report, industry certification, ISO audit
4. **Site visit:** In-person or virtual tour of the manufacturing facility (highest confidence)

### Red Flags (Potential Dealers, Not Manufacturers)
- No manufacturing facility address (only office/PO box)
- Product catalog matches large corporate catalogs exactly
- Can't provide evidence of equipment or raw material purchasing
- Lead times inconsistent with manufacturing (too fast = drop-shipping)
- Reluctance to allow facility visit

## Search & Matching

When a product solicitation is ingested:
1. Extract product requirements from SOW
2. Search directory by: product category, NAICS code, BAA compliance, Berry compliance
3. Rank manufacturers by: relevance, capacity, past performance, pricing
4. Surface matches for Proposal Manager

## Dependencies
- [[../02-onboarding/manufacturer-onboarding]]
- [[non-manufacturer-rule]]
- [[buy-american-act]]
- [[product-set-aside-logic]]

## Key Rules & Compliance
- Must be actual manufacturers, not dealers (NMR compliance)
- SBA size standard: manufacturer must be small under their NAICS (generally ≤500 employees, but varies)
- Buy American Act: certain products must be U.S.-origin manufactured
- Berry Amendment: DoD textiles, food, and specialty metals must be 100% U.S. origin
- Manufacturer claims should be verifiable if challenged by CO or competitor

## Open Questions
- Directory size goal: how many manufacturers in the first year?
- Should directory include "pending verification" manufacturers or only verified entries?
- Geo-prioritization: should the system favor manufacturers near the delivery destination?
