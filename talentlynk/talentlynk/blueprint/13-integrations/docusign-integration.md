# DocuSign Integration

## Purpose
Integrate with DocuSign (or equivalent e-signature provider) for legally binding digital signatures on all agreements, forms, and proposal documents. Electronic signatures must comply with the ESIGN Act and UETA.

## Integration Scope

All documents requiring signature flow through DocuSign:
- Master Teaming Agreements (vendor onboarding)
- Non-Disclosure Agreements (vendor/specialist onboarding)
- Contingent Offer Letters (specialist onboarding)
- Letters of Commitment (per-bid, per-specialist)
- Task-Specific Teaming Agreements (per-bid, per-vendor)
- Joint Venture Agreements
- Subcontract Agreements (post-award)
- Assignment of Claims
- Government forms (SF-1449 signature block)
- Internal approvals (high-value proposals)

## Workflow

### Sending for Signature
```
1. TalentNyk generates document (via agreement generation engine)
2. Document pushed to DocuSign via API with:
   - Document PDF
   - Recipient(s): name, email, signing order
   - Signature/initial fields: coordinates on document
   - Email subject and body template
3. DocuSign sends email to signatory
4. Signatory receives email, clicks link, reviews document, signs
5. DocuSign notifies TalentNyk (webhook) when:
   - Signatory viewed document
   - Signatory signed
   - Signatory declined
   - Envelope completed (all signatures collected)
6. Signed document downloaded and stored in TalentNyk document repository
```

### Signing Order (for multi-party documents)
```
Example: Task-Specific Teaming Agreement
  1. TalentNyk Proposal Manager reviews and signs (internal sign-off)
  2. Vendor receives notification, reviews pricing, signs
  3. Final: fully executed document stored
```

### Envelope Status Tracking
| DocuSign Status | TalentNyk Status |
|----------------|-----------------|
| Created | Draft |
| Sent | Sent for Signature |
| Delivered | Delivered (recipient received email) |
| Viewed | Viewed (recipient opened document) |
| Signed | Partially Signed (one party signed) |
| Completed | Fully Executed |
| Declined | Declined (signatory refused) |
| Voided | Voided (TalentNyk cancelled) |
| Expired | Expired (didn't sign in time) |

## Key Integration Points

### REST API
- Create envelope
- Add recipients
- Add documents
- Specify signing fields (tabs)
- Send
- Check status
- Download completed documents

### Webhooks
- Envelope status changes (sent, delivered, signed, completed, declined)
- Real-time sync with TalentNyk document status

### Template Management
- DocuSign templates for each agreement type
- Merge fields populated before sending
- Templates stored in DocuSign; TalentNyk triggers with data

## Authentication & Security

- DocuSign OAuth 2.0 authentication
- API key + service account
- Documents encrypted in transit (TLS) and at rest
- DocuSign is FedRAMP authorized (important for government-related use)

## Dependencies
- [[../03-agreements/agreement-generation-engine]]
- [[../08-review-submission/digital-signature-routing]]
- [[../12-platform-admin/notification-engine]]

## Key Rules & Compliance
- ESIGN Act (15 U.S.C. § 7001): Electronic signatures are legally valid
- UETA: Uniform Electronic Transactions Act (adopted by 49 states)
- Signature must be attributable to the signatory
- Audit trail: DocuSign provides certificate of completion with IP, timestamp, email
- Government forms (SF-1449, etc.): most COs accept electronic signatures; some require pen-and-ink — check solicitation
- Some government portals (PIEE, WAWF) use CAC/PKI, not DocuSign — this is separate

## Open Questions
- DocuSign pricing tier: Standard, Business Pro, or API plan?
- Alternative providers: PandaDoc, HelloSign, Adobe Sign — should any be supported for vendor choice?
- Should the system support "sign in person" mode for vendors who can't use digital signatures?
