# Notification Engine

## Purpose
Manage all outbound communications — email, SMS, and in-app notifications — triggered by system events across the entire platform lifecycle.

## Notification Categories

### Bid & Proposal Notifications
| Trigger | Recipient | Channel | Priority |
|---------|-----------|---------|----------|
| Solicitation matched to vendor | Vendor (after TA signed) | Email + In-App | High |
| Task-Specific TA ready for signature | Vendor | Email + SMS | Urgent |
| Vendor hasn't signed TA (48h reminder) | Vendor | Email + SMS | Urgent |
| TA still unsigned (24h before deadline) | Vendor + PM | Email + SMS | Critical |
| Proposal submitted to government | PM + Compliance Officer | Email | Normal |
| Amendment detected on submitted bid | PM | Email + SMS | Urgent |

### Agreement & Legal Notifications
| Trigger | Recipient | Channel | Priority |
|---------|-----------|---------|----------|
| Agreement ready for signature | Signatory | Email + In-App | High |
| Agreement signed (all parties) | All signatories | Email | Normal |
| Agreement approaching expiration | Owner | Email | Normal |

### Compliance Notifications
| Trigger | Recipient | Channel | Priority |
|---------|-----------|---------|----------|
| License expiring in 60 days | Vendor | Email | Normal |
| License expiring in 30 days | Vendor + Network Coordinator | Email + In-App | High |
| License expiring in 7 days | Vendor + NC + Compliance | Email + SMS | Urgent |
| License EXPIRED | Vendor blocked from matching | Email + SMS | Critical |
| SAM registration expiring | Compliance Officer | Email + SMS | Critical |
| Insurance certificate expiring | Vendor + Compliance | Email | High |

### Financial Notifications
| Trigger | Recipient | Channel | Priority |
|---------|-----------|---------|----------|
| Government payment received | Financial Controller | Email + In-App | High |
| Sub payment initiated | Vendor + Financial Controller | Email | Normal |
| Sub payment DELAYED (past 3 days) | Vendor + FC + Compliance | Email + SMS | Critical |
| Invoice rejected by government | PM + Financial Controller | Email + SMS | Urgent |
| Cash flow gap detected | Financial Controller | Email + In-App | High |

### Contract & Performance Notifications
| Trigger | Recipient | Channel | Priority |
|---------|-----------|---------|----------|
| Contract awarded | All stakeholders | Email | High |
| Contract kickoff | PM + Vendor + Specialists | Email | Normal |
| Deliverable due in 7 days | Subcontractor | Email + In-App | Normal |
| Deliverable OVERDUE | Subcontractor + PM | Email + SMS | Urgent |
| Contract closeout initiated | PM + Financial Controller | Email | Normal |

## Delivery Configuration

### Per-User Preferences
- Users can configure: which channels per notification type
- Default: Email for all, SMS for Urgent/Critical only
- Opt-out: certain compliance notifications cannot be opted out

### Templates
- All notifications use templates with merge fields
- Branded HTML emails with clear action buttons
- SMS: short, actionable messages with link
- In-app: notification bell with badge count

### Rate Limiting
- Maximum X notifications per user per day
- Batch: daily digest option for non-urgent notifications
- No duplicate notifications within Y minutes

## Dependencies
- [[../13-integrations/email-sms-provider]]
- [[../13-integrations/docusign-integration]]
- [[internal-team-management]]
- [[vendor-portal]]

## Key Rules & Compliance
- Opt-out compliance: certain notifications cannot be suppressed (legal/regulatory)
- Data privacy: notification content must not expose other vendors' information
- Delivery tracking: log all notifications sent, delivered, opened (for audit)

## Open Questions
- Email provider: SendGrid, AWS SES, Postmark?
- SMS provider: Twilio, AWS SNS?
- Should vendors receive a weekly digest instead of per-event emails for lower-priority notifications?
