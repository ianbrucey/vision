# SAM.gov API Integration

## Purpose
Integrate with SAM.gov (System for Award Management) for entity validation, solicitation search, exclusion checks, and wage determination retrieval. SAM.gov is the single source of truth for all federal contracting data.

## Integration Points

### 1. Entity Validation
- **Validate UEI:** Confirm a UEI is registered and active
- **Validate CAGE Code:** Confirm CAGE code matches UEI
- **Check SAM Registration Status:** Active, Expired, Inactive
- **Check NAICS Codes:** Registered primary and secondary NAICS
- **Check Socioeconomic Status:** Verified SBA certifications on file

### 2. Exclusion Check (Debarment)
- Before naming any vendor in a proposal: check SAM.gov exclusions
- Search by: company name, UEI, CAGE code, individual name
- Flag: Active exclusions → vendor CANNOT participate in federal contracts
- Flag: Potential matches that need manual review (similar names)

### 3. Solicitation Search
- Search active solicitations by: NAICS code, set-aside type, agency, keyword, place of performance
- Retrieve full solicitation details
- Monitor for amendments to tracked solicitations
- **Potential feature:** Proactive solicitation discovery — system searches daily and surfaces new opportunities matching network capabilities

### 4. Wage Determination Retrieval
- Pull current SCA and DBA wage determinations by: WD number, state, county, construction type
- Check for new revisions (for amendment handling)
- Download WD for solicitation attachment verification

### 5. Contract Data (FPDS)
- Query Federal Procurement Data System (FPDS) for: historical contract data, competitor award analysis, agency buying patterns
- Research: what has this agency paid for similar services?

## API Technical Details

### Authentication
- SAM.gov API requires API key (register at https://sam.gov)
- Rate limits apply (varies by endpoint)
- System must cache responses to minimize API calls

### Key Endpoints
```
GET /entity-information/v1/entities?uei={UEI}
GET /exclusions/v1/exclusions?uei={UEI}
GET /opportunities/v2/opportunities?naics={NAICS}&setAside={TYPE}
GET /wage-determinations/v1/wd/{WD_NUMBER}
```

### Caching Strategy
- Entity data: cache for 24 hours (changes infrequently)
- Exclusion checks: cache for 1 hour (critical — must be current at proposal submission)
- Solicitation search: cache for 1 hour (new solicitations posted throughout the day)
- Wage determinations: cache until new revision detected

## System Behaviors

### Pre-Bid Validation
Before submitting any proposal, auto-run:
1. Validate TalentNyk entity SAM registration is active
2. Validate proposed subcontractor SAM registration is active (if sub is SAM-registered)
3. Check exclusions for all proposed participants
4. If anything fails → block submission, alert Compliance Officer

### Proactive Solicitation Discovery
- Scheduled job: query SAM.gov daily for new solicitations matching network NAICS codes
- Filter: set-aside types the network can bid on
- Surface new matches to Proposal Manager for review
- Auto-classify and pre-populate solicitation record

## Dependencies
- [[../01-corporate-foundation/sam-registration]]
- [[../01-corporate-foundation/sba-certifications]]
- [[../04-solicitation-pipeline/document-ingestion]]
- [[../06-pricing-engine/wage-determination-database]]
- [[../08-review-submission/amendment-handling]]

## Key Rules & Compliance
- SAM registration must be verified at time of proposal submission (FAR 52.204-7)
- Exclusion checks are mandatory for all proposed participants
- API terms of use: data must not be resold; attribution may be required
- FPDS data: publicly available; no authentication needed for basic queries

## Open Questions
- Should the system auto-fetch new solicitations daily, or only on manual trigger?
- SAM.gov API rate limits: how many requests per day are allowed?
