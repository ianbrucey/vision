# SBA Data Integration

## Purpose
Integrate with Small Business Administration data sources for size standards, certification verification, class waivers, and small business directory searches. SBA data is the backbone of set-aside compliance.

## Integration Points

### 1. Size Standards
- **Source:** SBA Table of Small Business Size Standards (13 CFR § 121.201)
- **Data:** For each NAICS code, the maximum size (employees or revenue) to qualify as "small"
- **Usage:** Before bidding on a set-aside, system checks: is the bidding entity "small" under this NAICS?
- **Update frequency:** SBA updates size standards periodically; system must track current version

### 2. Dynamic Small Business Search (DSBS)
- **Source:** SBA DSBS database (https://web.sba.gov/pro-net/search/dsp_dsbs.cfm)
- **Usage:** Search for small business manufacturers by NAICS, location, certification
- **Use case 1:** Manufacturer discovery for product acquisition directory
- **Use case 2:** NMR waiver research — proving no small manufacturer exists (search returned zero results)
- **Limitation:** DSBS is self-reported; entries may be outdated or inaccurate

### 3. Certification Verification
- **Source:** SBA certify.sba.gov (for WOSB, SDVOSB, 8a) or SAM.gov
- **Usage:** Verify that a vendor's claimed socioeconomic certification is real
- **Method:** API or manual lookup
- **Frequency:** At onboarding and periodically (certifications can lapse)

### 4. Class Waiver List
- **Source:** SBA Non-Manufacturer Rule Class Waivers page
- **Data:** NAICS codes with active class waivers, product descriptions, waiver expiration dates
- **Usage:** NMR compliance check (see [[../11-product-acquisition/non-manufacturer-rule]])
- **Update frequency:** Monthly sync recommended; waivers are added/removed periodically

### 5. SBA District Office Data
- **Source:** SBA district office directory
- **Usage:** Identify local SBA resources for partnerships, mentorship, and JV opportunities
- **Use case:** Find SBA-approved mentors or Protege firms for potential JV partnerships

## System Behaviors

### Size Standard Auto-Check
```
Solicitation NAICS: 561730 (Landscaping Services)
SBA Size Standard: $9.5M average annual revenue
Entity annual revenue: $2.1M
Result: MEETS size standard — eligible for small business set-aside
```

### Dynamic Size Standards
- NAICS 238160 (Roofing Contractors): $19M → effective Dec 2024
- NAICS 541511 (Custom Computer Programming): $34M → effective Dec 2024
- NAICS 541611 (Admin Management Consulting): $24.5M → effective Dec 2024
- System must track which size standard version is current

## Dependencies
- [[../01-corporate-foundation/sba-certifications]]
- [[../11-product-acquisition/non-manufacturer-rule]]
- [[../11-product-acquisition/class-waiver-database]]
- [[../11-product-acquisition/small-manufacturer-directory]]
- [[sam-gov-api]]

## Key Rules & Compliance
- 13 CFR § 121.201: Table of Small Business Size Standards
- Size is determined by the NAICS code assigned by the CO, not the offeror
- Size protests can be filed by competitors within 5 days of award notification
- SBA is the final authority on size determinations, not the CO

## Open Questions
- How much of SBA data is API-accessible vs. requiring manual/scraping integration?
- Should the system auto-challenge a competitor's size status if suspected misrepresentation?
