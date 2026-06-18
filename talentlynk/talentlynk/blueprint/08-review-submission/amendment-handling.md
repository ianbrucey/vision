# Amendment Handling

## Purpose
Detect, ingest, and process solicitation amendments (SF-30 forms) that modify the original solicitation after it's been posted — and potentially after TalentNyk has already begun or submitted a proposal. Missing or ignoring an amendment = proposal thrown out.

## What Amendments Can Change

- **Due date:** Extended (or rarely, shortened)
- **SOW:** Scope modified, added, or removed
- **Evaluation criteria:** Weights changed, new factors added
- **NAICS code:** Changed (rare but possible)
- **Set-aside status:** Modified
- **Wage determination:** Updated to new revision
- **Forms:** New or updated government forms
- **Q&A:** Agency responses to bidder questions (often incorporated via amendment)

## Detection

### Active Monitoring
- System periodically polls SAM.gov for amendments to any solicitation TalentNyk is actively tracking or has submitted on
- CO email notifications parsed (if TalentNyk is on the bidders list)
- Manual: Proposal Manager can upload an amendment PDF

### Amendment Parsing
- Ingest amendment document
- Classify as SF-30 (or other amendment form)
- Extract: amendment number, solicitation number, what changed, new due date (if changed), acknowledgment requirements

## Impact Analysis

When an amendment is detected, the system performs automated impact analysis:

```json
{
  "amendmentNumber": "0002",
  "changes": [
    {
      "area": "due_date",
      "oldValue": "2026-08-15",
      "newValue": "2026-08-30",
      "impact": "deadline_extended",
      "action": "Update submission timeline"
    },
    {
      "area": "sow",
      "description": "Added requirement for snow removal services",
      "impact": "scope_changed",
      "action": "Re-run SOW extraction, re-evaluate vendor matching, update technical narrative"
    },
    {
      "area": "wage_determination",
      "oldRevision": "16",
      "newRevision": "17",
      "impact": "pricing_may_change",
      "action": "Re-run pricing engine with new WD rates"
    }
  ],
  "proposalImpact": "significant_changes_required",
  "requiresResubmission": true,
  "acknowledgmentRequired": true,
  "acknowledgmentDeadline": "2026-08-30T14:00:00-05:00"
}
```

## System Actions by Impact Level

| Impact | Automated Actions |
|--------|-------------------|
| **Minor** (due date change only) | Update internal deadlines; notify PM |
| **Moderate** (wage determination update, form change) | Re-run affected pipeline stages; flag for PM review |
| **Major** (SOW change, NAICS change, eval criteria change) | Re-run full pipeline from classification onward; re-route for vendor re-sign |
| **Critical** (set-aside changed, scope fundamentally different) | Full re-evaluation; bid/no-bid decision may need revisiting |

## Amendment Acknowledgment

Most solicitations require offerors to acknowledge all amendments in their proposal. The system:
1. Generates amendment acknowledgment page for inclusion in Volume 1
2. Fills SF-30 acknowledgment section (if included)
3. Tracks: which amendments were acknowledged in which proposal version

## Dependencies
- [[submission-tracking]]
- [[../04-solicitation-pipeline/document-ingestion]]
- [[../04-solicitation-pipeline/classification-engine]]
- [[../04-solicitation-pipeline/sow-extraction]]
- [[../06-pricing-engine/cost-estimation-formula]]

## Key Rules & Compliance
- FAR 52.212-1: Amendments must be acknowledged before the submission deadline
- Failure to acknowledge all amendments = proposal may be rejected as non-responsive
- Proposal Manager must confirm receipt of all amendments before submission
- If amendment significantly changes scope, vendor must re-sign the Task-Specific TA for the amended scope

## Open Questions
- Polling frequency for amendment detection: daily, hourly, or real-time (webhook)?
- Should the system auto-acknowledge amendments on behalf of the PM, or require manual review?
