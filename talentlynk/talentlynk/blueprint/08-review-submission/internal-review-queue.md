# Internal Review Queue

## Purpose
Manage the team's internal proposal review and approval workflow — ensuring every proposal gets appropriate human review before submission. The AI drafts, but humans decide.

## Review Stages

### Stage 1: Proposal Manager Review
- Reviews AI-generated proposal draft
- Edits technical narrative for accuracy and persuasiveness
- Confirms vendor selection
- Approves pricing
- Status: "Draft" → "PM Reviewed"

### Stage 2: Compliance Officer Review (if required)
- Reviews compliance checklist
- Verifies all mandatory forms present
- Checks certifications, licenses, SAM registration
- Status: "PM Reviewed" → "Compliance Approved"

### Stage 3: Final Approval
- Final review by authorized approver (CEO, COO, or designated authority)
- Go/no-go decision
- Status: "Compliance Approved" → "Approved for Submission"

### Stage 4: Submission
- Proposal is submitted to government
- Status: "Approved for Submission" → "Submitted"

## Queue Management

### Views & Filters
- **My Queue:** Proposals assigned to me for review
- **All Active:** All proposals in active review
- **By Status:** Draft, In Review, Approved, Submitted
- **By Urgency:** Sorted by proposal due date
- **By Solicitation Type:** RFP, RFQ, etc.

### Assignment
- Proposal Manager auto-assigned or manually assigned per solicitation
- Compliance Officer: round-robin or manual assignment
- Escalation if a stage is stalled beyond configured time

### Collaboration
- Comments and annotations on proposal sections
- @mentions to bring in other team members
- Change tracking: who edited what, when

## Status Flow

```
Draft → PM Assigned → PM In Review → PM Reviewed → Compliance Review → Compliance Approved → Final Approval → Approved → Submitted → Won/Lost
```

## Dependencies
- [[../07-proposal-generation/multi-volume-assembler]]
- [[../07-proposal-generation/compliance-checklist-generator]]
- [[../12-platform-admin/internal-team-management]]

## Key Rules & Compliance
- Internal review process should be documented (for any potential protest or audit)
- Separation of duties: person who drafts pricing should not be the sole approver
- All approvals logged with timestamp and user ID

## Open Questions
- Multi-level approval for high-value proposals (>$X) vs. streamlined for small bids?
- Should the system enforce mandatory "cooling off" period between final approval and submission?
