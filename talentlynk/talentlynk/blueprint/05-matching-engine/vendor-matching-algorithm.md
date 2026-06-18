# Vendor Matching Algorithm

## Purpose
Cross-reference extracted solicitation requirements (NAICS codes, capability tags, work elements) against the vendor database to surface the best-fit network partners for a given bid. This is the core "matching" function of the platform.

## Inputs
- Solicitation NAICS codes and capability tags (from solicitation pipeline)
- SOW work elements (from [[../04-solicitation-pipeline/sow-extraction]])
- Vendor profiles from database (NAICS, capability tags, pricing, past performance)
- Geographic service area of solicitation (Place of Performance)

## Outputs
- Ranked list of matching vendors
- Match score per vendor
- Match rationale (why this vendor matched)
- Gap flag: no vendor matched (missing capability)

## Matching Algorithm

### Layer 1: NAICS Code Match (Hard Filter)
```
IF vendor.primaryNaics == solicitation.primaryNaics → score += 40
IF vendor.secondaryNaics contains solicitation.primaryNaics → score += 25
IF vendor.naicsCodes intersects solicitation.naicsCodes → score += 15
ELSE → vendor filtered out (unless capability match is very strong)
```

### Layer 2: Capability Tag Overlap (Relevance)
```
Overlap = vendor.capabilityTags ∩ solicitation.requiredCapabilities
score += (overlap / requiredCapabilities) * 30
```

### Layer 3: Geographic Eligibility
```
IF vendor.serviceArea contains solicitation.placeOfPerformance → score += 15
ELSE → score += 0 (vendor can still be considered but flagged)
```

### Layer 4: Past Performance Relevance
```
score += relevanceScore(vendor.pastPerformance, solicitation.sowDescription) * 10
```
Past performance relevance scored via vector similarity between SOW description and past project descriptions.

### Layer 5: Licensing & Certification Gate
```
IF vendor lacks a mandatory license/certification → filtered out (or flagged as requiring remediation)
```

### Final Score Calculation
```
Total = NAICS Score (40) + Capability Score (30) + Geo Score (15) + Past Perf Score (10) + Certification Gate (5)
Max = 100
```

## Special Matching Logic

### Key Personnel Matching (Separate Query)
- Specialist matching runs in parallel using specialist profiles
- Scored on: role fit, experience match, certification match, clearance match

### Product Manufacturer Matching
- Triggered when solicitation is for supplies/products
- Additional filter: manufacturer flag (not dealer)
- NMR compliance check baked into matching

## System Behavior

### Surface Top-N
- Return top 3-5 matches with scores and rationale
- Each match includes: vendor name, NAICS match, capability overlap, relevant past performance snippets
- Proposal Manager selects from ranked list

### No-Match Handling
- Zero matches above threshold: system alerts Proposal Manager
- Suggests: expand geographic range, search for partial matches, or flag as "need to recruit"

### Conflict Check (Applied After Matching)
- Before presenting vendor as match: check exclusivity conflicts (see [[../08-review-submission/exclusivity-enforcement]])

## Dependencies
- [[../04-solicitation-pipeline/naics-extraction]]
- [[../04-solicitation-pipeline/sow-extraction]]
- [[../02-onboarding/vendor-profile-schema]]
- [[capability-scoring]]
- [[availability-check]]
- [[recommendation-ranking]]

## Key Rules & Compliance
- "Similarly Situated Entity" rule: sub must hold same socioeconomic certifications as prime for set-aside credit
- Vendor must be eligible (not debarred, not suspended) — SAM.gov exclusion check
- Matching is NOT automated selection — Proposal Manager makes the final call

## Open Questions
- Match score threshold: what minimum score justifies recommending a vendor?
- Should vendors see their own match scores?
- Weight tuning: should Proposal Managers be able to adjust layer weights?
