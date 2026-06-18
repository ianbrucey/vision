# Certification Extraction

## Purpose
Extract all mandatory certifications, clearances, and qualification requirements from a solicitation. These are pass/fail gates — if the bidding entity or its proposed team lacks a required certification, the proposal is non-responsive.

## Inputs
- Full solicitation text
- SOW, Section L, and any referenced clauses

## Outputs
- Required entity-level certifications
- Required personnel certifications/clearances
- Required insurance types and minimums
- Facility clearance requirements (if applicable)

## What to Extract

### Entity-Level Requirements
- Active SAM registration (universal requirement)
- Small business certification for set-asides
- Specific trade licenses (e.g., state contractor's license)
- Facility clearance (Secret, Top Secret) — rare but critical
- ISO certifications, quality standards
- Bonding requirements (bid bond, performance bond, payment bond)

### Personnel Requirements
- Professional certifications (PMP, PE, CISSP, etc.)
- Security clearances (Public Trust, Secret, TS/SCI)
- Trade certifications (Master Electrician, etc.)
- OSHA training (OSHA 10, OSHA 30)
- Citizenship requirements

### Insurance Requirements
- General Liability minimums
- Workers Compensation
- Professional Liability / E&O
- Auto Liability
- Umbrella/Excess

## Extraction Logic

### Pattern-Based
- Section I (Contract Clauses) and Section K (Representations, Certifications)
- FAR 52.222-46: Evaluation of Professional Employee Compensation
- FAR 52.204-7: SAM Registration
- FAR 52.228-1: Bid Guarantee
- DFARS clauses for DoD-specific requirements

### LLM Extraction
- Feed relevant sections to LLM
- Prompt: "Identify all mandatory certifications, clearances, licenses, and insurance requirements in this solicitation. Categorize as Entity-level, Personnel-level, or Insurance."

### Structured Output
```json
{
  "entityRequirements": [
    { "type": "sam_registration", "mandatory": true },
    { "type": "bid_bond", "amount": "20%", "mandatory": true },
    { "type": "performance_bond", "amount": "100%", "mandatory": true },
    { "type": "state_contractors_license", "state": "GA", "mandatory": true }
  ],
  "personnelRequirements": [
    { "role": "Project Manager", "requirement": "PMP", "mandatory": true },
    { "role": "Site Supervisor", "requirement": "OSHA 30", "mandatory": true }
  ],
  "clearanceRequirements": {
    "facilityClearance": null,
    "personnelClearance": "Public Trust",
    "citizenshipRequired": true
  },
  "insuranceRequirements": [
    { "type": "general_liability", "minimum": 2000000 },
    { "type": "workers_comp", "minimum": 500000 }
  ]
}
```

## Gap Analysis

Cross-reference against:
- Entity certifications in [[../01-corporate-foundation/sba-certifications]]
- Vendor licenses in [[../02-onboarding/license-certification-tracker]]
- Specialist certifications in [[../02-onboarding/specialist-onboarding]]

System flags: passed / gap (missing) / unknown (could not determine)

## Dependencies
- [[sow-extraction]]
- [[section-l-parser]]
- [[key-personnel-flagging]]
- [[../02-onboarding/license-certification-tracker]]

## Key Rules & Compliance
- Missing mandatory certification = proposal not responsive
- Facility clearance requirements often eliminate small businesses — critical to identify early
- Bonding requirements: bid bond due with proposal; performance/payment bonds due at award
- Insurance must be in place at time of performance, not necessarily at proposal submission

## Open Questions
- How to handle "equivalent certification" language (e.g., "PMP or equivalent")?
- Should the system auto-track bonding capacity limits per entity?
