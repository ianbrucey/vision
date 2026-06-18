# SOW Extraction

## Purpose
Isolate the Statement of Work (SOW) or Performance Work Statement (PWS) from the solicitation package. The SOW is the core of any federal proposal — it defines exactly what the government needs done, and every other pipeline component (matching, pricing, proposal narrative) depends on a correct SOW extraction.

## Inputs
- Full solicitation text (classified as RFQ, RFP, or Combined)
- Document structure (headings, sections)

## Outputs
- Isolated SOW/PWS text
- Extracted work elements (individual tasks, requirements, deliverables)
- Keywords, NAICS signals, and labor category hints
- Flagged requirements: mandatory certifications, security clearances, Key Personnel roles

## Extraction Approach

### 1. Section Identification
The SOW typically appears in Section C of the Uniform Contract Format (UCF). Common headings:
- "Statement of Work"
- "Performance Work Statement"
- "Scope of Work"
- "Requirements"
- "Specifications"
- "Section C — Description/Specifications/Statement of Work"

### 2. LLM-Based Parsing
1. Feed full document text to LLM
2. Prompt: "Extract the complete Statement of Work from this federal solicitation. Return the SOW text verbatim and identify all discrete work requirements."
3. LLM returns: SOW text + structured requirements list

### 3. Requirement Decomposition
Parse SOW into discrete work elements:
```json
{
  "sowSummary": "Provide all labor, materials, equipment, and supervision to perform grounds maintenance services at XYZ Federal Building...",
  "workElements": [
    {
      "id": "WE-001",
      "description": "Mowing all grass areas to 3-inch height, weekly during growing season",
      "category": "grounds_maintenance",
      "naicsSignal": "561730",
      "laborCategory": "Groundskeeper",
      "frequence": "weekly"
    },
    {
      "id": "WE-002",
      "description": "Seasonal debris removal including leaf collection and disposal",
      "category": "debris_removal",
      "naicsSignal": "561730",
      "laborCategory": "Laborer",
      "frequency": "seasonal"
    }
  ],
  "mandatoryRequirements": [
    "State Commercial Pesticide Applicator License",
    "OSHA 30 certification for site supervisor"
  ]
}
```

### 4. Flagged Items Extraction
- **Key Personnel:** Roles the government mandates (e.g., "Project Manager with minimum 5 years experience")
- **Certifications:** Required licenses/certs for personnel or company
- **Security:** Clearance requirements, facility access requirements
- **Equipment:** Government-furnished equipment vs. contractor-provided

## Dependencies
- [[classification-engine]]
- [[../05-matching-engine/vendor-matching-algorithm]]
- [[../07-proposal-generation/technical-narrative-templates]]

## Key Rules & Compliance
- SOW must be read against the Instructions to Offerors (Section L) — sometimes the SOW has performance requirements that differ from what's in Section L
- Ambiguities in the SOW must be flagged — they are Q&A opportunities or proposal risk items
- Don't assume: if the SOW is unclear, the government likely expects clarifying questions during Q&A period

## Open Questions
- Should the system auto-generate clarifying questions when the SOW is ambiguous?
- How to handle solicitations with multiple SOWs (e.g., IDIQ with sample task orders)?
