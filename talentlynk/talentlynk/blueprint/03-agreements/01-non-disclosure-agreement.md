# Non-Disclosure Agreement (NDA)

## Purpose
Binds vendors and specialists to confidentiality before they are given access to solicitation data, bid strategies, pricing, or any proprietary TalentNyk information. Signed during onboarding as part of the Master MOU execution.

## When It's Required

- **Vendor onboarding:** Signed alongside Master MOU before vendor sees any solicitation data
- **Specialist onboarding:** Signed before receiving contingent offer details or solicitation information
- **Ad-hoc:** For any third party who needs access to bid-related information

## Required Provisions

### 1. Definition of Confidential Information
Includes but not limited to:
- All federal solicitation documents shared with the recipient
- TalentNyk's bid strategies, pricing methodologies, and technical approaches
- TalentNyk's vendor database, matching algorithms, and platform technology
- The identities of other vendors in the TalentNyk network
- Any government-furnished information marked as procurement-sensitive
- The existence of any specific bid TalentNyk is pursuing (unless publicly posted)

### 2. Obligations of Recipient
- Use confidential information solely for the purpose of the specific bid
- Do not disclose to any third party
- Do not use for personal benefit or to compete with TalentNyk
- Implement reasonable security measures to protect the information
- Return or destroy confidential information upon request

### 3. Exclusions
Confidential information does NOT include:
- Information already in the public domain (e.g., published on SAM.gov)
- Information independently developed by the recipient
- Information rightfully received from a third party without restriction
- Information required to be disclosed by law or court order

### 4. Term
- Survives termination of the Master MOU or any other agreement
- Typically 3-5 years from date of disclosure
- Trade secrets protected indefinitely

### 5. Remedies
- Injunctive relief (money damages inadequate)
- Actual damages
- Attorney's fees to prevailing party
- No waiver of other legal remedies

## System Behavior

### Onboarding Integration
- NDA is presented during vendor/specialist onboarding
- Must be digitally signed before onboarding is complete
- Signed NDA is stored in document repository

### Enforcement Tracking
- System logs who has accessed which solicitation data
- NDA status checked before granting access to solicitation details
- Expired NDA = blocked from new bid access until renewed

## Dependencies
- [[../02-onboarding/vendor-onboarding-wizard]]
- [[../02-onboarding/specialist-onboarding]]
- [[../13-integrations/docusign-integration]]

## Key Rules & Compliance
- FAR 3.104: Procurement Integrity — prohibits disclosure of procurement-sensitive information
- Trade Secrets Act (18 U.S.C. § 1905): criminalizes unauthorized disclosure of confidential government information
- NDA must not restrict whistleblower rights or mandatory reporting of fraud/waste/abuse

## Open Questions
- Should the NDA include a non-solicitation clause (can't poach other network members)?
- Should there be different NDA tiers (standard vendor vs. high-security bids)?
