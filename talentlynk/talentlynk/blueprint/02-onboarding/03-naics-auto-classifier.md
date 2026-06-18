# NAICS Auto-Classifier

## Purpose
Automatically map free-text business descriptions to proper NAICS codes using an LLM embedding matrix. Most local trade businesses don't know their NAICS codes — this bridges the gap.

## Inputs
- Free-text business description from vendor onboarding
- Example: "We fix commercial flat roofs, handle leak patches, and clean gutters."
- Vendor's stated services and capabilities

## Outputs
- Primary NAICS code recommendation
- Secondary NAICS code suggestions
- Confidence score per recommendation
- Mapped wage determination category (SCA or Davis-Bacon)

## How It Works

### 1. Text Embedding
- Convert vendor description to vector embedding
- Compare against NAICS code descriptions in vector space
- Surface top-N matches by cosine similarity

### 2. LLM Verification
- Pass top matches to LLM with vendor description
- LLM validates or overrides based on semantic understanding
- Returns explanation for audit trail

### 3. Wage Category Linkage
- Map NAICS code to applicable wage law:
  - Construction NAICS → Davis-Bacon Act
  - Service NAICS → Service Contract Act
  - Supply NAICS → Neither (product acquisition rules apply)

### Example
- **Input:** "We fix commercial flat roofs, handle leak patches, and clean gutters."
- **Primary:** NAICS 238160 (Roofing Contractors)
- **Wage Category:** Davis-Bacon — Roofer
- **Confidence:** 0.94

## Dependencies
- [[vendor-profile-schema]]
- [[../06-pricing-engine/wage-determination-database]]

## Key Rules & Compliance
- NAICS code selection affects which wage laws apply
- Some solicitations require specific NAICS codes — auto-classification is a starting point, not final
- Vendor can override auto-classification with manual selection

## Open Questions
- Which embedding model?
- Should the system also suggest PSC (Product Service Codes)?
- How to handle businesses that span multiple NAICS?
