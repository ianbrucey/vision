# Architecture Diagram

## Purpose
High-level visual and conceptual map of the entire TalentNyk platform — how the major subsystems connect and data flows between them.

## The Core Pipeline

```
[Federal Solicitation Drop]
         │
         ▼
[04-Solicitation Pipeline: Ingestion → Classification → Extraction]
         │
         ▼
[05-Matching Engine: NAICS/Code Cross-Reference → Vendor Ranking]
         │
         ▼
[06-Pricing Engine: Wage Determination Overlay → Cost Calculation]
         │
         ▼
[08-Review & Submission: Mandatory Sub Digital Sign-Off]
         │
         ▼
[07-Proposal Generation: Form Filling + Technical Narrative → Compilation]
         │
         ▼
[Submit to SAM.gov / eBuy]
         │
         ▼
[09-Post-Award: Activation → Payment Tracking → Sub Routing]
```

## Supporting Systems

- **02-Onboarding** feeds the vendor/specialist/manufacturer database that **05-Matching** queries
- **03-Agreements** generates the legal documents used throughout the pipeline
- **10-Financial Infrastructure** sits behind **09-Post-Award** for cash flow and factoring
- **11-Product Acquisition** is a parallel track with its own compliance rules
- **12-Platform Admin** wraps the entire system for user management
- **13-Integrations** connects to external services (SAM.gov, SBA, DocuSign, payments)

## System Boundaries

- **Internal-facing:** Admin dashboard, team workflows, review queues
- **External-facing:** Vendor portal (onboarding, document sign-off, invoice submission)

## Dependencies
None — this is the top-level overview.

## Key Rules & Compliance
N/A — overview document.

## Open Questions
- Cloud provider (AWS assumed based on S3 mention)?
- Monolith vs. microservices?
- Web app, mobile app, or both?
