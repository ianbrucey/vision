# SOP-04: Vendor Email Outreach, Response Logging & System Tracking

> **Role:** Sourcing Specialist (Outreach Agent)  
> **Input:** Logged Vendor Contacts & Sourcing Packet  
> **Output:** Dispatched Outreach Emails, Updated Contact Status, Thread History  
> **Channels:** In-App Email Dispatch System (Mailgun integration)

---

## 1. Golden Rules of Vendor Outreach

1. **Be Short and Direct:** Subcontractors are busy. Emails longer than 3 paragraphs will be deleted.
2. **Lead with Value:** State clearly that we are a Prime Contractor bidding an active project and want to include their pricing.
3. **Clarify Roles:** We handle 100% of the federal compliance, billing, paperwork, and proposal submission. They perform their trade and get paid.
4. **Give a Clear Deadline:** Always provide an explicit date and time for when numbers are needed.

---

## 2. In-App Dispatch Workflow

1. Open the Solicitation Record in the internal portal.
2. Click on the matched/logged vendor contact.
3. Click **Dispatch Outreach Email**.
4. Choose the appropriate email template (see Section 3).
5. Verify auto-populated fields:
   - Recipient Name & Company
   - Project Location & Brief Scope
   - Quote Due Date
6. Click **Send Email**.
   - The system automatically assigns a tracking message ID and logs the activity in the vendor's correspondence thread.
7. Change the vendor status from `Identified` to `Outreach Sent`.

---

## 3. Approved Email Templates

### Template A: Initial Request for Quote (RFQ / SOW Sourcing)

```email
Subject: Subcontractor Pricing Request: [Project Name / Brief Scope] — [City, State]

Hi [Contact Name],

My name is [Agent Name] with Gov Services Connect (a division of Justice Quest LLC). 

We are currently preparing a prime bid for an upcoming government facility project in [City, State], and we are looking for a qualified local subcontractor to perform the [Trade/Scope] portion of the work.

Here is a quick snapshot of the project:
• Scope: [1-2 sentence plain-English SOW summary]
• Location: [Facility Name / City, State]
• Performance Period: [Estimated timeline / duration]
• Role: You deliver the trade work; we hold the prime contract and manage all federal compliance, paperwork, and invoicing.

Are you available and interested in submitting a quote for this scope? 

If so, please let me know and I can send over the detailed drawings/specifications. We are collecting quotes by [Quote Due Date].

Best regards,

[Agent Name]
Sourcing Specialist | Gov Services Connect
Justice Quest LLC — CAGE: 21GM9 | UEI: MU8FAL4JBL91
Office: (470) 785-3007 | admin@govservicesconnect.com
```

---

### Template B: Follow-Up (Sent 48 Hours Later If No Reply)

```email
Subject: Following up: Subcontractor Pricing for [Project Name / City, State]

Hi [Contact Name],

I wanted to quickly follow up regarding my note earlier this week about the [Trade/Scope] project in [City, State]. 

We are finalizing our subcontractor teaming list over the next 48 hours and would value the opportunity to review your pricing for this scope. 

Does your team have capacity for this project? If so, reply here and I will immediately forward the 1-page scope packet.

Thank you,

[Agent Name]
Sourcing Specialist | Gov Services Connect
Office: (470) 785-3007 | admin@govservicesconnect.com
```

---

### Template C: Scope Packet & Pricing Request (Once Vendor Says "Yes")

```email
Subject: Scope Packet & Pricing Sheet: [Project Name] (Due: [Quote Due Date])

Hi [Contact Name],

Thank you for your response. We’re glad to connect.

Attached is the 1-page Scope Breakdown and technical specifications for the [Project Name] at [Location].

Key details needed for your quote:
1. Total Firm-Fixed Price for materials & labor as specified.
2. Confirmation that technicians can pass background checks for base access.
3. Proof of active General Liability insurance and state license.

Please email your quote or estimate to us by [Quote Due Date, 5:00 PM EST]. 

If you have any technical questions or would like to speak with our US operations team regarding site conditions, you can call our office directly at (470) 785-3007.

Best regards,

[Agent Name]
Gov Services Connect | Justice Quest LLC
```

---

## 4. Response Handling & Status Updates

When an email reply arrives:
* **Vendor Responds Interested / Requests Drawings:**
  - Status → `Engaged - Scope Sent`.
  - Reply promptly with Template C.
* **Vendor Expresses Doubts / Requests Technical Call:**
  - Status → `Escalation: Phone Follow-Up Needed (US Team)`.
  - Add internal note in system: *"Vendor wants to discuss site access / wage determination. Phone: (xxx) xxx-xxxx."*
* **Vendor Declines:**
  - Status → `Declined`. Note reason (Capacity, Out of Area, Scope Mismatch).
* **Vendor Submits Quote:**
  - Status → `Quote Received`. Proceed immediately to **SOP-05**.
