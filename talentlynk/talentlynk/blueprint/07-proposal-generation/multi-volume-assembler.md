# Multi-Volume Assembler

## Purpose
Assemble the complete proposal package by bundling Volume 1 (government forms — filled by AcroForm/CV pipeline) and Volume 2 (technical narrative + past performance) into a single, submission-ready package that complies with Section L instructions.

## Inputs
- Volume 1: Filled government forms (from [[acroform-filler]] and/or [[computer-vision-form-filler]])
- Volume 2: Technical narrative (from [[technical-narrative-templates]])
- Volume 3: Past performance (from [[past-performance-compiler]]) — if separate
- Volume 4: Price proposal (from pricing engine) — if separate from Volume 1
- Section L instructions: required volumes, page limits, formatting

## Outputs
- Complete proposal package (single PDF or multi-file, per instructions)
- Table of contents
- Cover letter (if required)
- Compliance checklist
- Submission metadata

## Assembly Logic

### Volume Structure Per Section L

The assembler reads the parsed Section L volume requirements and builds accordingly:

```
Proposal Package:
├── Cover Letter (if required)
├── Volume 1: Administrative & Business
│   ├── SF-1449 (filled, signed)
│   ├── FAR 52.212-3 Representations & Certifications
│   ├── Pricing Schedule (if included in Vol 1)
│   └── Other required administrative forms
├── Volume 2: Technical Proposal (max 35 pages)
│   ├── Executive Summary
│   ├── Technical Approach
│   ├── Management & Staffing Plan
│   ├── Key Personnel Resumes
│   └── Quality Control Plan
├── Volume 3: Past Performance (max 15 pages)
│   ├── Past Performance Summary Table
│   └── Detailed Reference Narratives
└── Volume 4: Price Proposal (if separate)
    └── Detailed Cost/Price Breakdown
```

### Page Limit Tracking
- System tracks page count per volume during assembly
- Wraps/truncates content at page limits if automatic (with flag for manual review)
- Page count verified against Section L limits

### Formatting Enforcement
- Font: Times New Roman 12pt (or per Section L)
- Margins: 1 inch all sides (standard)
- Page numbering: Per volume or continuous
- Headers/Footers: Solicitation number, company name, proprietary marking

## Quality Checks

### Completeness
- All required forms present
- All required signatures applied
- All evaluation criteria addressed in technical narrative
- All mandatory sections included

### Formatting
- Page limits respected
- Font and formatting compliant
- No broken cross-references
- Table of contents accurate

### Marking
- Proprietary/confidential markings applied where needed
- Solicitation number on every page
- Company identification consistent

## Submission Formats

The assembler must support:
- **Single PDF:** Most common for electronic submission
- **Multi-file:** Some portals (e.g., PIEE) require separate file uploads per volume
- **Physical:** Generate print-ready files if hard copy submission required (rare now)
- **Email:** File size limits (often 10-20MB); system compresses if needed

## Dependencies
- [[pdf-form-detection]]
- [[acroform-filler]]
- [[computer-vision-form-filler]]
- [[technical-narrative-templates]]
- [[past-performance-compiler]]
- [[compliance-checklist-generator]]
- [[../04-solicitation-pipeline/section-l-parser]]
- [[../08-review-submission/digital-signature-routing]]

## Key Rules & Compliance
- Section L format requirements are MANDATORY — wrong format = non-responsive
- Each volume must be clearly labeled
- Page limits are HARD limits; pages over the limit may not be evaluated
- Electronic submission: follow portal instructions exactly (file naming, format, size)

## Open Questions
- Should the assembler auto-generate a "readiness score" before allowing submission?
- Should the system maintain version history of each proposal iteration?
