# Vendor Onboarding Wizard

## Purpose
Self-service intake flow for local service businesses (landscapers, roofers, janitorial, logistics, etc.) to join the TalentNyk network. Captures everything needed to map them to federal solicitations and generate compliant proposals.

## Wizard Steps

### Step 1: Company Basics
- Legal business name, DBA if applicable
- Physical address (must be U.S.-based)
- Years in business
- Website (optional)

### Step 2: Federal Identity
- UEI number (if already SAM-registered)
- CAGE code (if available)
- Current SAM.gov registration status
- If not SAM-registered: flag for assistance

### Step 3: Classification & Capability
- **Free-text description of services** → Backend LLM auto-maps to NAICS codes
- Manual NAICS code selection (searchable) as override
- Service categories (checkbox: landscaping, roofing, janitorial, HVAC, etc.)
- Geographic service area (radius from home base)

### Step 4: Socioeconomic Status
- Self-declare: Small Business, WOSB, SDVOSB, HUBZone, 8(a)
- Upload verification documents
- **Note:** System flags self-declared statuses for compliance officer verification

### Step 5: Licensing & Certifications
- Dynamic form: add licenses one by one
- Fields: License type, number, issuing authority, state, expiration date
- Upload license document
- System auto-tracks expiration

### Step 6: Commercial Pricing Matrix
- Unit types: per sq ft, per hour, per project, per acre, etc.
- Base rates
- Minimum project value
- Emergency/after-hours rates
- Geographic pricing variations (if any)

### Step 7: Past Performance
- Add past projects one by one
- Fields: Client name, scope of work (free text), contract value, completion date
- System uses these snippets in proposals

### Step 8: Agreement Execution
- Present Master Teaming Agreement for digital signature
- Present NDA for digital signature
- Both must be signed to complete onboarding

## Dependencies
- [[vendor-profile-schema]]
- [[naics-auto-classifier]]
- [[license-certification-tracker]]
- [[pricing-matrix-schema]]
- [[past-performance-database]]
- [[../03-agreements/master-teaming-agreement]]
- [[../03-agreements/non-disclosure-agreement]]
- [[../13-integrations/docusign-integration]]

## Key Rules & Compliance
- Vendors must be U.S.-based (no foreign subs for set-asides)
- Self-declared socioeconomic statuses must be verified against SAM.gov
- Pricing data is confidential — protected by NDA
- "Similarly Situated Entity" rule requires subs to hold same certifications as prime for set-aside credit

## Open Questions
- Wizard UX: single page, multi-step, or conversational?
- How to handle vendors who are not yet SAM-registered?
- Pricing matrix: how many unit types to support?
