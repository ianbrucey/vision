# NAICS Extraction

## Purpose
Extract the NAICS code(s) from a federal solicitation. The NAICS code is the primary matching key between a solicitation and the vendor network — it determines which vendors are eligible and which wage determination rules apply.

## Inputs
- Classified solicitation text
- Solicitation metadata (SF-1449 block 10, or similar)

## Outputs
- Primary NAICS code
- NAICS code description
- Size standard (employees or revenue)
- Secondary/referenced NAICS codes (if any)
- Determined wage law: SCA, DBA, or Neither

## Where NAICS Appears

| Solicitation Type | NAICS Location |
|-------------------|----------------|
| SF-1449 (Commercial) | Block 10 |
| SF-1442 (Construction) | Block 10 |
| FedBizOpps/SAM.gov posting | Classification section |
| Combined Synopsis | "This requirement is set aside under NAICS code..." |
| Section L / Instructions | May reference applicable NAICS |

## Extraction Logic

### 1. Form-Based Detection
- If SF-1449 or SF-1442: extract from Block 10 directly
- Parse NAICS code (6 digits) and size standard

### 2. Text Pattern Matching
- Regex: `NAICS [Cc]ode:?\s*(\d{6})`
- Regex: `(\d{6})\s*[-–]\s*.*[Ss]ize [Ss]tandard`
- Common NAICS prefixes: 23 (construction), 54 (professional services), 56 (admin/support)

### 3. LLM Extraction
- Feed document context around NAICS mentions
- LLM returns: primary NAICS, secondary NAICS, and corresponding descriptions

### 4. Validation
- Validate NAICS exists in official NAICS taxonomy (2022 or current version)
- Validate size standard matches SBA Table of Size Standards
- Cross-check: NAICS code should be consistent with the SOW (roofing SOW + IT NAICS = flag for review)

## Wage Law Linkage

| NAICS Sector | Wage Law |
|--------------|----------|
| 23 — Construction | Davis-Bacon Act (DBA) |
| 56 — Administrative & Support | Service Contract Act (SCA) |
| 54 — Professional Services | SCA (some exemptions) |
| 31-33 — Manufacturing | Neither (product acquisition rules) |
| Other | Check solicitation for wage determination attachment |

## Dependencies
- [[classification-engine]]
- [[wage-determination-extraction]]
- [[../02-onboarding/naics-auto-classifier]]
- [[../05-matching-engine/vendor-matching-algorithm]]

## Key Rules & Compliance
- NAICS code match is the primary eligibility filter for set-asides
- Size standard varies by NAICS — vendor must be "small" under that specific standard
- Multiple NAICS codes may apply to one solicitation (rare but possible)
- NAICS manual is updated every 5 years; system must track current version

## Open Questions
- Should the system maintain a local copy of the full NAICS taxonomy + size standards?
- Auto-flag when solicitation NAICS seems inconsistent with SOW content?
