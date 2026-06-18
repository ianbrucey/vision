# Letter of Commitment (LOI)

## Purpose
The document signed by a Key Personnel candidate that is submitted alongside the proposal to prove to the government that the proposed team is real and committed. Required by many solicitations — without it, resumes are treated as "we hope to find someone" rather than "this person is on our team."

## How It Differs from the Contingent Offer Letter

| Aspect | Contingent Offer Letter | Letter of Commitment |
|--------|------------------------|----------------------|
| **Who issues** | TalentNyk (employer → employee) | Individual (employee → government) |
| **Direction** | "We offer you a job if we win" | "I commit to doing this job if you win" |
| **Audience** | Internal (specialist) | External (Contracting Officer) |
| **Submitted with proposal?** | No (internal document) | Yes (part of proposal package) |
| **Legal effect** | Employment conditional offer | Government-facing commitment |

## Required Language

The Letter of Commitment must contain unequivocal commitment language:

> "In the event of a contract award to [TalentNyk Entity] for Solicitation Number [X], I hereby make an unequivocal commitment to fulfill the duties of [Position Title] for the duration of the contract's Period of Performance, including all option years."

## Required Elements

- Solicitation number and title
- Individual's full name and proposed role
- TalentNyk entity name
- Statement of unequivocal commitment
- Acknowledgment that the commitment is binding if contract is awarded
- Individual's signature and date
- Individual's contact information

## System Behavior

### Generation
- Trigger: specialist is selected for a specific bid
- Pull solicitation data and specialist profile
- Generate LOI PDF
- Route to specialist for signature
- Signed LOI is bundled into the proposal package (Volume 1 or Key Personnel section)

### Revocation Handling
- If specialist withdraws before proposal submission: system alerts Proposal Manager
- If specialist withdraws after award: triggers Key Personnel substitution workflow (requires CO approval)
- System must flag that LOI revocation after proposal submission may constitute a procurement issue

## Dependencies
- [[contingent-offer-letter]]
- [[../02-onboarding/specialist-onboarding]]
- [[../07-proposal-generation/multi-volume-assembler]]
- [[../13-integrations/docusign-integration]]

## Key Rules & Compliance
- FAR 52.215-1: Instructions to Offerors often requires Letters of Commitment
- False or misleading commitments = potential procurement integrity violation
- Key Personnel substitution after award requires CO notification and approval
- The government evaluates LOIs to confirm the team is "available and committed" — weak language ("I am interested in...") will be scored lower

## Open Questions
- Should the LOI include compensation terms, or is that only in the Contingent Offer Letter?
- How to handle specialists committed to multiple simultaneous bids (capacity conflict)?
