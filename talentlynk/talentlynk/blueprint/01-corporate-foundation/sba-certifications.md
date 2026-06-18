# SBA Certifications

## Purpose
Track SBA socioeconomic certifications across all entities and key network partners to enable set-aside bidding and Joint Venture formation.

## Certification Types

### Entity-Level Certifications (Owned by You)
| Certification | Status | Held By |
|---------------|--------|---------|
| Small Business | [ ] | [Entity] |
| WOSB (Women-Owned Small Business) | [ ] | [Entity] |
| SDVOSB (Service-Disabled Veteran-Owned) | [ ] | [Entity] |
| 8(a) Business Development | [ ] | [Entity] |
| HUBZone | [ ] | [Entity] |

### Network Partner Certifications (Tracked)
The system must track which network vendors hold which certifications, because:
- Partner certifications enable JV formation for specialized set-asides
- Similarly Situated Entity rule allows certified subs to count toward set-aside requirements

## Set-Aside Bidding Logic

### Your Entity Holds the Certification
→ Bid as Prime directly. Route work to any qualified sub.

### Your Entity Does NOT Hold Certification, but Network Partner Does
→ Trigger JV Workflow:
1. System auto-generates SBA-compliant JV agreement
2. Certified partner = Managing Venturer (51%)
3. Your entity = Administrative Member (49%)
4. JV entity registered on SAM.gov
5. Bid submitted under JV

### Neither Holds Certification
→ Cannot bid on that set-aside. System filters it out.

## Verification & Renewal
- Certifications have expiration dates and renewal requirements
- System must track expiration and alert before lapse
- Some certifications require annual recertification (8a, for example, has a 9-year program with annual reviews)

## Dependencies
- [[entity-structure]]
- [[../03-agreements/joint-venture-agreement]]
- [[../13-integrations/sba-data-integration]]

## Key Rules & Compliance
- Similarly Situated Entity rule: 13 CFR § 125.1
- WOSB certification: 13 CFR § 127
- SDVOSB certification: 13 CFR § 128
- 8(a) program: 13 CFR § 124
- HUBZone: 13 CFR § 126
- False certification = severe penalties under False Claims Act

## Open Questions
- Which certifications do Justice Quest and FunLink currently hold?
- Should the platform track certifications on SAM.gov or independently?
