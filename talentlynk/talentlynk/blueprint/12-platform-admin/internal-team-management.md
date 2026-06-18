# Internal Team Management

## Purpose
Manage the internal TalentNyk team — roles, permissions, assignments, and workflow. This is the administrative control layer for who can do what within the platform.

## Roles & Permissions Matrix

| Capability | Admin | Proposal Mgr | Compliance Officer | Financial Controller | Network Coordinator |
|------------|-------|-------------|-------------------|---------------------|---------------------|
| User management | ✅ | - | - | - | - |
| System configuration | ✅ | - | - | - | - |
| View all proposals | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create/edit proposals | ✅ | ✅ | - | - | - |
| Submit proposals | ✅ | ✅ | - | - | - |
| Approve pricing | ✅ | ✅ | - | ✅ | - |
| Manage agreement templates | ✅ | - | ✅ | - | - |
| Compliance review & sign-off | ✅ | - | ✅ | - | - |
| Vendor onboarding | ✅ | - | - | - | ✅ |
| License/cert verification | ✅ | - | ✅ | - | ✅ |
| Payment routing approval | ✅ | - | - | ✅ | - |
| Financial reporting | ✅ | ✅ | - | ✅ | - |
| Audit log access | ✅ | - | ✅ | ✅ | - |
| Notification config | ✅ | - | - | - | - |

## Team Workflows

### Proposal Assignment
- New solicitation ingested → auto-assigned to Proposal Manager (round-robin or by NAICS specialty)
- PM can re-assign if needed
- Compliance Officer auto-assigned when proposal enters compliance review

### Approval Chains
- Pricing over threshold → requires Financial Controller approval
- High-value proposals (>$X) → require dual approval (PM + Compliance Officer)
- Submission: any PM can submit, but Compliance checklist must be green

### Coverage & Escalation
- If assigned PM is out of office → auto-escalate to backup or pool
- Stalled proposals (no activity in X days) → alert PM and Admin

## Team Performance Metrics

- Proposals drafted per PM per month
- Win rate per PM
- Average days from ingestion to submission
- Compliance issues caught per Compliance Officer
- Vendor onboarding volume per Network Coordinator

## Dependencies
- [[../00-platform-overview/user-roles]]
- [[../08-review-submission/internal-review-queue]]
- [[vendor-portal]]

## Key Rules & Compliance
- Separation of duties: pricing approval should be separate from proposal drafting
- Audit trail: all user actions on proposals must be logged
- Access control: former employees must be immediately deactivated

## Open Questions
- SSO integration (Okta, Azure AD) vs. built-in auth?
- Should the system support part-time or contract team members with limited access?
