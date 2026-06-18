# Past Performance Compiler

## Purpose
Aggregate, format, and present relevant past performance references for inclusion in the proposal. This component selects which past projects to feature, writes the relevance narrative, and formats them per the solicitation's instructions.

## Inputs
- Solicitation SOW and evaluation criteria
- Section L instructions (past performance format requirements)
- Selected vendor's past performance snippets (from [[../02-onboarding/past-performance-database]])
- Selected specialist past performance entries
- TalentNyk's own past performance (if any)

## Outputs
- Past performance volume or section
- Selected references with relevance narratives
- Formatted per solicitation requirements (may be a table, narrative, or both)
- POC contact information (redacted or included per instructions)

## Selection Logic

### Which References to Include

1. **Relevance scoring:** Vector similarity between SOW and each past project description
2. **Recency filter:** Prioritize last 3 years; 5+ year projects only if highly relevant
3. **Value comparability:** Similar dollar value projects preferred (not too small, not too large)
4. **Performance quality:** Prioritize projects with excellent outcomes (CPARS "Exceptional" or "Very Good")
5. **Client diversity:** Mix of federal agencies preferred over all from one agency
6. **Number:** Typically 3-5 most relevant references (or per Section L instructions)

### Reference Format (Typical)

Each reference includes:
- **Project Title/Name**
- **Customer/Agency:** Name, address
- **POC:** Name, phone, email (included per solicitation instructions — some restrict POC info)
- **Contract Number and Type**
- **Period of Performance:** Start and end dates
- **Contract Value:** Total and annual
- **Scope:** Description of work performed
- **Relevance Narrative:** Paragraph explaining why this project is relevant to the current SOW
- **Performance Outcome:** Completed on time/budget, CPARS rating if available

## Compilation

```json
{
  "selectedReferences": [
    {
      "vendor": "Atlanta Commercial Landscaping LLC",
      "project": "Fulton County Parks Grounds Maintenance",
      "relevanceScore": 0.91,
      "relevanceNarrative": "This project is directly relevant as it involved weekly mowing, edging, and seasonal debris removal across 14 public park locations — essentially identical to the grounds maintenance requirements in this solicitation's SOW Section C.3.2.",
      "contractValue": 45000,
      "solicitationValue": 85000,
      "valueComparison": "comparable"
    }
  ]
}
```

## Formatting Per Solicitation

### Table Format
Some solicitations require past performance in a specific table format:
| Project | Agency | Value | POP | Scope | POC |
|---------|--------|-------|-----|-------|-----|

### Narrative Format
Others allow or require a narrative format with each reference as a subsection.

### Combined Format
Some want both: a summary table followed by detailed narratives for the top references.

## Dependencies
- [[../02-onboarding/past-performance-database]]
- [[../04-solicitation-pipeline/sow-extraction]]
- [[../04-solicitation-pipeline/section-l-parser]]
- [[technical-narrative-templates]]
- [[multi-volume-assembler]]

## Key Rules & Compliance
- FAR 15.305(a)(2): Past performance evaluation — recency, relevancy, and quality
- POC contact information: follow solicitation instructions (some say "do not include POC contact info in the proposal")
- Government may contact references directly — references must be willing and available
- False or misleading past performance references = False Claims Act liability

## Open Questions
- Should POCs be notified when they're listed as a reference for an active bid?
- How to handle the case where the vendor has no federal past performance (only commercial)?
