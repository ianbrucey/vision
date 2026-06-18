# Data Flow

## Purpose
Document how data moves through the TalentNyk system end-to-end — from vendor onboarding through contract closeout.

## Data Domains

### 1. Vendor & Network Data
- **Source:** Onboarding wizards (02-onboarding)
- **Flow:** Vendor profiles → JSON database ← Queried by matching engine
- **Persistence:** Vendor master DB with NAICS codes, pricing matrices, past performance snippets, licenses

### 2. Solicitation Data
- **Source:** Federal solicitation uploads (S3 bucket)
- **Flow:** Raw PDF/ZIP → Classification → Extraction → Structured bid data
- **Persistence:** Bid database with parsed SOW, NAICS, wage determinations, evaluation criteria

### 3. Pricing Data
- **Source:** Wage determination ingestion + vendor pricing matrices
- **Flow:** Government wage sheets + vendor commercial rates → Cost estimation formula → Bid price
- **Persistence:** Calculated bid pricing stored with solicitation record

### 4. Agreement Data
- **Source:** Agreement generation engine (03-agreements)
- **Flow:** Template + vendor/solicitation data → Generated document → Digital signature → Stored
- **Persistence:** Signed agreements archive (compliance audit trail)

### 5. Proposal Data
- **Source:** Compilation engine (07-proposal-generation)
- **Flow:** Filled forms + technical narrative → Multi-volume package → Submission
- **Persistence:** Submitted proposal archive

### 6. Post-Award Data
- **Source:** Award notification + government payment events
- **Flow:** Award → Contract activation → Invoicing → Payment receipt → Sub payment routing
- **Persistence:** Contract database, payment ledger, audit log

## Key State Transitions

```
Vendor: Invited → Onboarded (profile complete) → Standby (MOU signed) → Engaged (task-specific TA signed) → Active (subcontract executed) → Paid
Bid: Ingested → Classified → Matched → Priced → Reviewed → Submitted → Won/Lost
Contract: Awarded → Activated → In Progress → Invoiced → Paid → Closed
```

## Dependencies
- [[architecture-diagram]]

## Key Rules & Compliance
- All agreement state changes must be audit-logged (FAR compliance)
- Payment timestamps must track Prompt Payment Act deadlines

## Open Questions
- Database technology choice?
- Real-time vs. batch processing for solicitation ingestion?
