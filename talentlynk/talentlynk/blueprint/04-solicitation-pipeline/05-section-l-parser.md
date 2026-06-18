# Section L Parser

## Purpose
Extract and parse Section L — "Instructions, Conditions, and Notices to Offerors" — which tells bidders exactly how to format and submit their proposal. Violating Section L instructions = proposal thrown out as non-responsive. This is the "rulebook" for proposal assembly.

## Inputs
- Classified solicitation text (RFP, RFQ, Combined)
- Document section labeled "Section L" or containing FAR 52.212-1

## Outputs
- Structured proposal instructions
- Required volumes/sections with page limits
- Mandatory forms list (SF-1449, SF-30, etc.)
- Formatting requirements (font, spacing, page size)
- Submission instructions (due date, delivery method, copies required)
- Questions deadline and procedures

## Common Section L Requirements

### Proposal Volume Structure
Section L typically prescribes:
- **Volume 1:** Administrative / Business Proposal (forms, reps & certs, pricing)
- **Volume 2:** Technical Proposal (approach, staffing, past performance)
- **Volume 3:** Past Performance (if separate from technical)
- **Volume 4:** Price Proposal (detailed cost/price breakdown)

### Mandatory Forms
- **SF-1449:** Solicitation/Contract/Order for Commercial Items
- **SF-1442:** Solicitation, Offer, and Award (Construction)
- **SF-30:** Amendment of Solicitation/Modification of Contract
- **SF-LLL:** Disclosure of Lobbying Activities
- FAR 52.212-3: Offeror Representations and Certifications

### Page Limits & Formatting
- Maximum page counts per volume
- Font size and type requirements (often Times New Roman 12pt)
- Margin requirements
- Electronic submission requirements

## System Behavior

### Extraction
1. Isolate Section L text from solicitation
2. Parse into structured format:
```json
{
  "volumes": [
    {
      "number": 1,
      "title": "Administrative & Business Proposal",
      "pageLimit": 25,
      "requiredForms": ["SF-1449", "FAR 52.212-3"],
      "contentRequired": ["UEI", "CAGE", "Signed SF-1449", "Pricing Schedule"]
    },
    {
      "number": 2,
      "title": "Technical Proposal",
      "pageLimit": 35,
      "contentRequired": ["Technical Approach", "Staffing Plan", "Past Performance", "Key Personnel Resumes"]
    }
  ],
  "dueDate": "2026-08-15T14:00:00-05:00",
  "deliveryMethod": "email",
  "deliveryEmail": "contracting.officer@agency.gov",
  "questionsDeadline": "2026-07-20T17:00:00-05:00",
  "formattingRequirements": {
    "fontSize": 12,
    "fontFamily": "Times New Roman",
    "spacing": "single",
    "paperSize": "letter"
  }
}
```

### Form Flagging
- Identify every mandatory form referenced
- Cross-check against form library (does the system know how to fill this form?)
- Flag unfamiliar forms for manual handling

### Compliance Feed
- Structured Section L data feeds into [[../07-proposal-generation/multi-volume-assembler]]
- Page limit tracking during narrative generation
- Form requirement checklist for submission

## Dependencies
- [[classification-engine]]
- [[../07-proposal-generation/multi-volume-assembler]]
- [[../07-proposal-generation/compliance-checklist-generator]]

## Key Rules & Compliance
- Section L requirements are **mandatory** — not suggestions
- If Section L says "shall" or "must," the system must enforce it
- Page limits: exceeding them = pages may not be evaluated
- Wrong format (e.g., PDF when DOCX required) = non-responsive

## Open Questions
- How to handle Section L instructions that conflict with other sections?
- Should the system generate a "Section L compliance checklist" for manual review?
