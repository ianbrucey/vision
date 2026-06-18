# Agreement Generation Engine

## Purpose
The backend engine that auto-generates all legal agreement documents on the platform. This is the "document assembly line" — it takes templates + data from vendor profiles, solicitation records, and contract records, then produces populated, ready-to-sign PDFs.

## Inputs
- **Template:** Agreement template with merge fields (from template library)
- **Entity Data:** Bidding entity info (UEI, CAGE, legal name, address)
- **Vendor Data:** Vendor profile JSON, pricing matrix, licenses
- **Solicitation Data:** Solicitation number, NAICS, SOW, due date, agency
- **Contract Data:** Post-award contract number, POP, awarded price, flow-downs
- **Specialist Data:** Specialist profile, resume, compensation expectations

## Outputs
- Populated agreement PDF (ready for digital signature)
- Audit record: template version, data sources, generation timestamp
- Agreement metadata: type, parties, dates, status

## Supported Agreement Types

| Agreement | Trigger | Data Sources |
|-----------|---------|-------------|
| NDA | Onboarding | Vendor profile |
| Master MOU | Onboarding completion | Vendor profile, entity data |
| Contingent Offer Letter | Specialist onboarding | Specialist profile, entity data |
| Letter of Commitment | Specialist matched to bid | Specialist profile, solicitation data |
| Task-Specific TA | Vendor selected for bid | Vendor profile, solicitation data, pricing |
| Exclusivity Clause | Embedded in Task-Specific TA | Solicitation number |
| JV Agreement | Set-aside requiring non-held cert | Partner profile, entity data, solicitation |
| Subcontract Agreement | Contract award | TA terms, prime contract data, flow-downs |
| Assignment of Claims | Post-award financing | Contract data, banking info |

## System Architecture

### Template Engine
- Each agreement type has a master template with merge fields
- Templates stored with version control
- Merge fields use a standard syntax: `{{vendor.companyName}}`, `{{solicitation.number}}`
- Templates are configurable by Compliance Officer (not hardcoded)

### Data Resolution
- Engine resolves all merge fields by querying the relevant data sources
- Missed fields flagged for manual review before generation
- Data validation: required fields must be present before PDF generation

### PDF Generation
- Generate fillable PDF from populated template
- Apply digital signature fields at designated locations
- Store in document repository with metadata

### Status Tracking
```
Draft → Generated → Sent for Signature → Partially Signed → Fully Executed → Expired/Superseded
```

## Dependencies
- Every agreement document in this domain (03-agreements)
- [[../02-onboarding/vendor-profile-schema]]
- [[../04-solicitation-pipeline/]] (all components)
- [[../13-integrations/docusign-integration]]

## Key Rules & Compliance
- Each agreement type must track its template version for audit purposes
- Generated agreements must be immutable once signed (no editing after execution)
- Agreement data must be stored in a way that survives vendor deactivation (compliance retention)
- Template changes must be logged and approved (who changed what, when, why)

## Open Questions
- PDF generation library: server-side (LaTeX, HTML-to-PDF, or direct PDF manipulation)?
- Should templates be stored as code (version-controlled) or in a database (admin-editable)?
- Internationalization: Spanish-language versions for certain vendors?
