# Joint Venture Agreement

## Purpose
SBA-compliant Joint Venture (JV) agreement used when TalentNyk needs to bid on a specialized socioeconomic set-aside (WOSB, SDVOSB, 8a) but does not itself hold the required certification. A network partner who holds the certification becomes the Managing Venturer (51%), and TalentNyk serves as the Administrative Member (49%).

## When This Is Triggered

The system triggers JV workflow when:
1. A solicitation is a specialized socioeconomic set-aside (e.g., WOSB, SDVOSB, 8a)
2. The bidding entity (Justice Quest / FunLink) does NOT hold that specific certification
3. A network partner DOES hold the certification
4. The contract value and strategic fit justify JV formation

## SBA JV Requirements (13 CFR § 121.103(h))

### Ownership Split
- **Managing Venturer (certified partner):** Minimum 51% ownership
- **Administrative Member (TalentNyk):** Maximum 49% ownership
- Ownership must reflect the work share and contributions of each party

### Work Share
- The certified Managing Venturer must perform at least 40% of the work
- Administrative Member performs the remaining work
- Work share is calculated based on labor costs (not just revenue split)

### Control & Governance
- Managing Venturer controls day-to-day operations
- Administrative Member provides administrative, compliance, and proposal support
- Major decisions may require unanimous consent (defined in JV agreement)

### Separate Legal Entity
- JV must be registered as a separate legal entity
- JV must obtain its own UEI and SAM.gov registration
- JV must have its own bank account
- JV must file its own tax returns

## Required Provisions

### 1. Purpose & Scope
- Formed solely for the purpose of bidding on and performing Solicitation [X]
- May cover related follow-on work (option years, IDIQ task orders)

### 2. Ownership & Capital Contribution
- Managing Venturer: 51% ownership, contributes [specific resources]
- Administrative Member: 49% ownership, contributes [administrative systems, proposal writing, compliance]

### 3. Work Share Breakdown
- Specific work elements assigned to each party
- Labor cost breakdown demonstrating 40%+ Managing Venturer performance
- Administrative services (proposal, compliance, billing) assigned to TalentNyk

### 4. Profit & Loss Distribution
- Profits distributed per ownership percentage
- Losses allocated per ownership percentage
- Cash calls: how additional funding is handled if needed

### 5. Management & Control
- Managing Venturer: day-to-day operations, technical direction
- Administrative Member: contract administration, invoicing, compliance
- Governing Board: one representative from each party; certain decisions require unanimous approval

### 6. Term & Dissolution
- Term: duration of the contract plus closeout period
- Dissolution upon: contract completion, mutual agreement, or material breach
- Wind-down procedures and asset distribution

## System Behavior

### Auto-Generation
- System pulls certified partner profile + solicitation data
- Generates JV agreement with calculated work share percentages
- Routes to both parties for legal review and signature

### JV Entity Onboarding
- System tracks JV entity formation checklist
- SAM.gov registration for JV
- Bank account setup
- Insurance requirements

### Post-Award Management
- System tracks JV-specific invoicing
- Work share compliance monitoring
- Profit distribution calculations

## Dependencies
- [[../01-corporate-foundation/entity-structure]]
- [[../01-corporate-foundation/sba-certifications]]
- [[../13-integrations/sba-data-integration]]

## Key Rules & Compliance
- 13 CFR § 121.103(h): SBA JV regulations
- 13 CFR § 125.8: Similarly Situated Entity rule
- Managing Venturer must be the certified small business AND must perform at least 40% of the work
- JV must not be a "sham" — both parties must contribute substantive resources
- Each JV typically covers one contract (or related group) — not a permanent entity

## Open Questions
- Will JV formation be routine (every relevant set-aside) or strategic (only high-value opportunities)?
- Legal counsel review required before JV execution, or can it be fully automated?
- How many simultaneous JVs can be practically managed?
