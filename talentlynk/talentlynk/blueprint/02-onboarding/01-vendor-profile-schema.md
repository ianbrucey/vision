# Vendor Profile Schema

## Purpose
Master JSON schema for the vendor profile — the canonical data structure that represents every network partner in the system. This is the foundational data model that the matching engine, pricing engine, and proposal generator all query.

## Full Schema

```json
{
  "vendorId": "vnd_99218",
  "companyName": "Atlanta Commercial Landscaping LLC",
  "dba": "ACL Services",
  "entityType": "llc",
  "contactInfo": {
    "primaryContact": "John Doe",
    "title": "Owner",
    "email": "john@atlantacommercial.com",
    "phone": "404-555-0200",
    "address": {
      "street": "123 Main St",
      "city": "Atlanta",
      "state": "GA",
      "zip": "30301"
    }
  },
  "samRegistration": {
    "hasUei": true,
    "uei": "X123Y456Z789",
    "cageCode": "9A8B7",
    "samExpiration": "2027-03-15",
    "primaryNaics": "561730",
    "secondaryNaics": ["561210", "561710"]
  },
  "socioeconomicStatus": {
    "isSmallBusiness": true,
    "wosb": true,
    "sdvosb": false,
    "hubzone": false,
    "eightA": false,
    "certifications": [
      {
        "type": "wosb",
        "issuingAgency": "SBA",
        "certificationDate": "2025-01-01",
        "expirationDate": "2028-01-01",
        "documentUrl": "s3://..."
      }
    ]
  },
  "licensingMatrix": [
    {
      "licenseType": "State Commercial Pesticide Applicator",
      "licenseNumber": "PST-4412",
      "state": "GA",
      "expirationDate": "2027-12-31"
    }
  ],
  "insuranceInfo": {
    "generalLiability": { "amount": 2000000, "expiration": "2027-06-01" },
    "workersComp": { "amount": 500000, "expiration": "2027-06-01" }
  },
  "commercialPricingMatrix": {
    "unitType": "sq_ft",
    "baseRate": 0.12,
    "minProjectValue": 1500.00,
    "hourlyEmergencyRate": 75.00
  },
  "pastPerformanceSnippets": [
    {
      "clientId": "Fulton County Parks",
      "scopeOfWork": "Mowing, edging, and seasonal debris removal for 14 public parks.",
      "contractValue": 45000.00
    }
  ],
  "capabilityTags": [
    "landscaping", "grounds_maintenance", "mowing",
    "debris_removal", "pesticide_application"
  ],
  "serviceArea": ["GA", "AL", "TN"],
  "networkStatus": "standby",
  "agreements": {
    "mouSignedDate": "2026-06-01",
    "mouDocumentUrl": "s3://..."
  },
  "createdAt": "2026-06-01T12:00:00Z",
  "updatedAt": "2026-06-15T09:30:00Z"
}
```

## Status Lifecycle

```
Invited → Onboarding (profile incomplete) → Standby (MOU signed, ready) → Engaged (on active bid) → Active (on live contract) → Inactive
```

## Dependencies
- [[vendor-onboarding-wizard]]
- [[naics-auto-classifier]]
- [[pricing-matrix-schema]]
- [[past-performance-database]]
- [[license-certification-tracker]]

## Key Rules & Compliance
- Profile must be complete (all required fields) before vendor can be matched to bids
- SAM registration data must be verifiable
- Socioeconomic claims must match SBA certification records
- Network status transitions must be audit-logged

## Field-by-Field Data Source Analysis

What can be auto-pulled from APIs/scraping vs. what the vendor must manually enter. The ratio here directly impacts onboarding conversion — every field we can pre-fill is friction eliminated.

| Field | Source | Method | Confidence |
|-------|--------|--------|------------|
| `companyName` | SAM.gov API | UEI lookup → legal business name | High |
| `dba` | SAM.gov API | Sometimes present; often null | Low |
| `entityType` | State SOS registry | Scrape per state (fragmented, 50+ systems) | Medium |
| `contactInfo.email` | SAM.gov API | Electronic Business POC field | Medium (often stale) |
| `contactInfo.phone` | SAM.gov API | Electronic Business POC field | Medium (often stale) |
| `contactInfo.address` | SAM.gov API | Physical address from registration | High |
| `contactInfo.primaryContact` | Manual | Name of who we actually talk to | — |
| `samRegistration.uei` | Manual entry (key lookup field) | Vendor enters once → everything else unlocks | — |
| `samRegistration.cageCode` | SAM.gov API | Auto-returned from UEI lookup | High |
| `samRegistration.samExpiration` | SAM.gov API | Registration expiration date | High |
| `samRegistration.primaryNaics` | SAM.gov API | Primary NAICS from registration | High |
| `samRegistration.secondaryNaics` | SAM.gov API | All secondary NAICS on file | High |
| `socioeconomicStatus.*` | SAM.gov API + SBA certify.sba.gov | Verified certs from SAM; self-declared cross-checked | High |
| `licensingMatrix[*]` | Manual — no central API | 50+ state systems, few with public APIs. Upload + manual entry | — |
| `insuranceInfo.*` | Manual — no public API | Private between vendor and insurer. Certificate upload | — |
| `commercialPricingMatrix.*` | Manual — proprietary data | Vendor's own rates. Could suggest from industry averages | — |
| `pastPerformanceSnippets[*]` | Mixed | FPDS for federal contracts (API); CPARS for ratings; commercial = manual | Medium |
| `capabilityTags` | **Auto-generated** | Our NAICS auto-classifier from vendor's text description | System |
| `serviceArea` | Manual | Vendor tells us where they operate | — |

### The UEI as a Data Key

```
Vendor enters UEI → single SAM.gov API call returns:
  ├── Legal company name
  ├── Physical address
  ├── CAGE code
  ├── Primary + secondary NAICS codes
  ├── SAM registration status + expiration
  ├── Socioeconomic certifications (verified)
  └── POC names/emails/phones (Electronic Business, Government Business, Past Performance POCs)
```

**One field entered → 15+ fields auto-populated.** This is the biggest UX win in the onboarding flow.

### What We Could Scrape (Future)

| Source | What It Has | Feasibility |
|--------|-------------|-------------|
| State Secretary of State portals | Entity type, formation date, good standing | Fragmented — 50 states, different formats. Build per-state as needed. |
| State license boards | Trade licenses, expiration dates | Highly fragmented. Some states have lookup portals (no API). Scraping possible but fragile. |
| FPDS (Federal Procurement Data System) | All federal contracts a vendor has performed on | API-accessible. Can pull contract numbers, values, agencies, dates. |
| CPARS (Contractor Performance Assessment) | Federal past performance ratings | Limited public access. Vendor would need to share their CPARS report. |
| USASpending.gov | Federal award data | API available. Can cross-reference vendor as sub on known contracts. |
| Dun & Bradstreet | Business credit, size, years in business | Paid API. Could be worth it for vendor verification. |

### What's Always Manual

- **Proprietary pricing** — a vendor's rate sheet is their business; no public source exists
- **Insurance** — private contracts between vendor and insurer
- **Most trade licenses** — state-level, no central database, variable quality
- **Commercial past performance** — private client work only the vendor knows about
- **Service area** — business decision, not recorded anywhere public

### The Rough Split

| Category | % of Fields | Auto-Fill Potential |
|----------|-------------|---------------------|
| Entity identity & federal data | ~40% | Near 100% via UEI lookup |
| Pricing & capabilities | ~25% | 0% — pure manual |
| Licenses & insurance | ~20% | ~5% — mostly manual today, scrapers possible later |
| Past performance | ~10% | ~40% — federal work pullable, commercial work manual |
| Contact & preferences | ~5% | ~50% — SAM POCs as starting point, verify manually |

**Bottom line: ~40-45% of fields can be auto-filled with just the UEI. Another 10-15% could be scraped or pulled with additional integrations.** The vendor experience becomes: "Enter your UEI. Confirm what we found. Add your pricing and licenses."

## Open Questions
- Should profiles support "parent company / subsidiary" relationships?
- How to model vendors with multiple distinct business lines under one entity?
- Is the SAM.gov UEI lookup fast enough for a real-time onboarding wizard, or should we do it async and notify when ready?
- For vendors without a UEI (not SAM-registered), should we guide them through registration first or allow partial onboarding?
