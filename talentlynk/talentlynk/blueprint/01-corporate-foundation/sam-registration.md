# SAM.gov Registration

## Purpose
Manage the System for Award Management (SAM.gov) footprint — UEI numbers, CAGE codes, NAICS classifications, and entity validation for all bidding entities.

## What SAM.gov Requires

- **UEI (Unique Entity ID):** Replaces DUNS; assigned at registration
- **CAGE Code:** Assigned during SAM registration; used in proposals
- **Primary NAICS Code:** Main business classification
- **Secondary NAICS Codes:** Additional capabilities
- **SBA Socioeconomic Certifications:** WOSB, SDVOSB, 8a, HUBZone (verified in SAM)
- **Financial Information:** EFT/ACH details for government payments
- **Points of Contact:** Past performance POC, electronic business POC, government business POC

## System Responsibilities

### Entity Registration Tracking
- Store and monitor SAM.gov registration status for each entity
- Track annual renewal deadlines (SAM registration must be renewed yearly)
- Flag expiring registrations 60, 30, and 7 days before lapse

### NAICS Management
- Maintain primary and secondary NAICS codes per entity
- Validate that a solicitation's NAICS matches at least one entity before bidding
- Alert if entity lacks required NAICS for a target solicitation

### Proposal Auto-Population
- Auto-fill entity data (UEI, CAGE, address, NAICS) into government forms
- Pull correct entity based on solicitation type (IT → Justice Quest, Services → FunLink)

## Dependencies
- [[entity-structure]]
- [[../13-integrations/sam-gov-api]]

## Key Rules & Compliance
- SAM registration must be active at time of proposal submission and award
- False or expired registrations = ineligible for award
- FAR 52.204-7: System for Award Management registration required
- Annual renewal with no grace period for lapsed registrations

## Open Questions
- Will SAM.gov data be synced automatically or manually maintained?
- Need to track entity reps & certs (FAR 52.212-3) updates?
