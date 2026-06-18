# Specialist Onboarding

## Purpose
Intake flow for individual professionals (project managers, IT leads, compliance experts, construction managers) who will serve as contingent W-2 Key Personnel on proposals.

## How This Differs from Vendor Onboarding

Specialists are individuals, not companies. They are onboarded via **Contingent Offer Letters** — a formal job offer that only activates if a specific contract is won. This costs $0 upfront and satisfies the government's Key Personnel requirements.

## Wizard Steps

### Step 1: Personal Information
- Full legal name
- Contact information
- Citizenship/work authorization status
- Security clearance (if any): level, issuing agency, expiration

### Step 2: Professional Profile
- Current title/role
- Years of experience
- Industry domains (construction management, IT, logistics, etc.)
- Upload resume (PDF/DOCX)

### Step 3: Skills & Certifications
- Professional certifications (PMP, CISSP, PE license, etc.)
- Certification numbers and expiration dates
- System auto-tracks expirations

### Step 4: Past Performance Snippets
- Projects managed (name, scope, value, outcome)
- Role on each project
- These are used in proposals as "Key Personnel past performance"

### Step 5: Compensation Expectations
- Desired salary range (for contingent offer)
- Hourly rate range
- Willingness to work on-site vs. remote
- Geographic preferences/restrictions

### Step 6: Contingent Framework Execution
- System generates **Contingent Offer Letter** based on profile
- System generates **Letter of Commitment** template
- Specialist signs both digitally
- **Legal effect:** "I commit to joining TalentNyk as a W-2 employee IF AND ONLY IF Contract X is awarded"

## Activation Trigger

When a contract is won and this specialist was named as Key Personnel:
1. Contingent offer auto-activates
2. Specialist is onboarded as W-2 employee on Day 1 of performance
3. Payroll begins from government contract funding

## Dependencies
- [[../03-agreements/contingent-offer-letter]]
- [[../03-agreements/letter-of-commitment]]
- [[../13-integrations/docusign-integration]]

## Key Rules & Compliance
- Contingent offer must state: award of Contract X, CO approval of Key Personnel, and Period of Performance start date as conditions precedent
- Letter of Commitment: unequivocal commitment language — "I hereby make an unequivocal commitment to fulfill the duty of [Role] for the duration of the contract"
- If contract is lost: offer expires, neither party owes anything
- Key Personnel substitution after award requires CO approval — system must flag this

## Open Questions
- How to handle specialists with active security clearances?
- Background check integration?
- Payroll provider integration for activation?
