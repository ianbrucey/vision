# Email & SMS Provider Integration

## Purpose
Integrate with email and SMS delivery providers for all outbound communications — notifications, alerts, agreement routing, and marketing. This is the delivery layer for the notification engine.

## Email Provider

### Options
- **AWS SES (Simple Email Service):** Low cost, high deliverability, scales well; good AWS ecosystem fit
- **SendGrid (Twilio):** Feature-rich, strong template engine, analytics
- **Postmark:** Focused on transactional deliverability, simple API
- **Resend:** Modern, developer-friendly, good for transactional + marketing

### Capabilities Needed
- Transactional email (agreements, notifications, alerts)
- Template management with merge fields
- HTML + plain text multipart
- Open and click tracking
- Bounce and complaint handling
- Webhook callbacks for delivery events
- Dedicated IP (optional, for reputation management as volume scales)

### Email Types
- **Transactional:** Agreement signing requests, payment confirmations, bid status updates
- **Notification:** Deadline reminders, compliance alerts, system events
- **Digest:** Weekly summary (vendor activity, team pipeline)
- **Marketing:** Network growth outreach (separate from transactional pipeline)

## SMS Provider

### Options
- **Twilio:** Industry standard, global coverage, rich API
- **AWS SNS:** Tighter AWS integration, lower cost for high volume
- **Vonage (Nexmo):** Competitive pricing, solid API

### SMS Use Cases
- **Urgent:** "TA signature required — proposal due in 4 hours"
- **Critical compliance:** "License expired — you cannot be matched to new bids"
- **Payment confirmations:** "Payment of $62,000 sent to your account"
- **Operational alerts:** "Government payment received — sub payments pending"

### SMS Constraints
- Character limit (160 chars standard)
- Opt-in required (TCPA compliance)
- Rate limiting: maximum X messages per vendor per day
- Fallback: if SMS fails, fall back to email + in-app notification

## Integration Model

```json
{
  "notification": {
    "recipient": {
      "email": "john@atlantacommercial.com",
      "sms": "+14045550100"
    },
    "channels": ["email", "sms"],
    "template": "ta_signature_reminder_48h",
    "data": {
      "vendorName": "Atlanta Commercial Landscaping LLC",
      "solicitationNumber": "W912HN-24-R-0001",
      "dueDate": "2026-08-15",
      "signingLink": "https://app.talentlynk.com/sign/xyz"
    }
  }
}
```

## Dependencies
- [[../12-platform-admin/notification-engine]]

## Key Rules & Compliance
- CAN-SPAM Act: commercial emails must have unsubscribe link, physical address
- TCPA: SMS requires prior express written consent; automated messages must identify sender
- GDPR (if any EU vendors): data privacy and consent requirements
- CCPA (California): privacy notice and opt-out rights
- Email deliverability: SPF, DKIM, DMARC records must be configured for sending domain

## Open Questions
- Email provider choice driven by AWS ecosystem (SES) or best-of-breed (Postmark/SendGrid)?
- SMS: is SMS necessary at MVP, or can email + in-app notifications suffice initially?
- Should the system maintain a list of "do not contact" preferences across channels?
