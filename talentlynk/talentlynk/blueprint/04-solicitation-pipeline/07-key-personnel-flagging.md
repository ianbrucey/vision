# Key Personnel Flagging

## Purpose
Identify mandatory Key Personnel positions specified in the solicitation — the roles the government requires to be filled by named, committed individuals with specific qualifications. These positions require Letters of Commitment and resumes in the proposal. Missing or uncommitted Key Personnel = proposal disqualification.

## Inputs
- SOW and Section L extracted text
- Solicitation requirements parsed from full document

## Outputs
- List of mandatory Key Personnel roles
- Required qualifications per role
- Flagged: which roles have matching specialists in the network
- Flagged: which roles have NO matching specialists (gap alert)

## What Constitutes Key Personnel

The government typically designates Key Personnel with language like:
- "The contractor shall provide a Project Manager..."
- "Key Personnel include the following positions..."
- "The offeror shall submit Letters of Commitment for..."
- "Key Personnel may not be substituted without Contracting Officer approval..."
- "The following positions require a minimum of X years of experience in..."

Common Key Personnel roles in service contracts:
- **Project Manager:** Overall responsibility, main government POC
- **Site Supervisor:** On-site management for facilities/construction contracts
- **Quality Control Manager:** QC plan implementation
- **Safety Officer:** OSHA compliance, safety plan
- **Technical Lead:** Domain-specific technical expertise
- **Contract Administrator:** Invoicing, compliance, reporting

## Extraction Logic

### Pattern Matching
- Regex/keyword scan for "key personnel," "key positions," "staffing requirements"
- Look for: years of experience requirements, certification requirements, education requirements

### LLM Extraction
- Feed relevant sections to LLM
- Prompt: "Identify all Key Personnel positions in this solicitation. For each, extract: title, required years of experience, required certifications, required education, and whether a Letter of Commitment is required."

### Structured Output
```json
{
  "keyPersonnel": [
    {
      "positionTitle": "Project Manager",
      "requiredExperience": "5+ years managing federal contracts",
      "requiredCertifications": ["PMP"],
      "requiredEducation": "Bachelor's degree",
      "letterOfCommitmentRequired": true,
      "estimatedFTE": 0.5,
      "matchedSpecialists": ["spc_0042", "spc_0017"]
    }
  ],
  "gaps": [
    {
      "positionTitle": "Certified Industrial Hygienist",
      "reason": "No specialists in network with this certification"
    }
  ]
}
```

## System Behavior

### Gap Analysis
- Cross-reference required roles against specialist database
- If no match: alert Proposal Manager — time to recruit or partner
- If match found: surface top candidates with relevance score

### LOI Trigger
- When specialist is selected for a Key Personnel role → trigger LOI generation

### Post-Award Monitoring
- Track Key Personnel through contract performance
- Flag if Key Personnel leaves → alert: CO notification and substitution required

## Dependencies
- [[sow-extraction]]
- [[section-l-parser]]
- [[../05-matching-engine/]]
- [[../02-onboarding/specialist-onboarding]]
- [[../03-agreements/letter-of-commitment]]

## Key Rules & Compliance
- FAR 52.215-1: Instructions to Offerors — often requires Key Personnel LOIs
- Key Personnel substitution: CO must approve; system must track and flag
- False LOIs = procurement integrity violation
- Key Personnel resumes must be accurate and current at time of submission

## Open Questions
- Should the system auto-suggest specialist matches, or leave selection entirely to Proposal Manager?
- How to handle "desired but not required" personnel vs. truly mandatory Key Personnel?
