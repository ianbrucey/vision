# Dashboard & Analytics

## Purpose
Provide real-time visibility into the entire TalentNyk operation — pipeline health, financial performance, vendor network status, and compliance posture. Dashboards serve both internal decision-making and strategic planning.

## Internal Dashboards

### 1. Pipeline Dashboard
- Total active bids by status (Draft, In Review, Submitted, In Evaluation)
- Pipeline value ($): submitted, expected win value (probability-weighted)
- Win rate: by NAICS, by agency, by PM, by vendor
- Days to close: average time from ingestion to award
- Upcoming deadlines (sorted by urgency)

### 2. Financial Dashboard
- Revenue: won contracts, total value, prime margin retained
- Cash position: current + forecasted (30/60/90 day)
- Accounts Receivable: outstanding government invoices, aging
- Accounts Payable: upcoming sub payments, supplier payments
- Factoring utilization: active advances, fees paid
- Profit margin: per contract, average across all contracts

### 3. Vendor Network Dashboard
- Total vendors in network (by status: Standby, Engaged, Active)
- Vendor pipeline: how many vendors matched to how many bids
- Vendor performance: scorecard averages, top/bottom performers
- Onboarding funnel: invited → started → completed → standby
- License/certification health: % with all licenses current
- Network diversity: by NAICS, by socioeconomic status, by geography

### 4. Compliance Dashboard
- Active contracts with expiring subs licenses/certs
- Prompt Payment Act compliance: % sub payments within 3 days
- Agreement status: pending signatures, expired agreements
- Audit log summary: recent actions by type
- SAM registration status across all entities

### 5. Product Dashboard (if product acquisition active)
- Manufacturer directory size and growth
- Class waivers: tracked items, expiring waivers
- NMR waiver requests: pending, approved, denied

## Key Metrics (KPIs)

| Metric | Definition | Target |
|--------|-----------|--------|
| Win Rate | Awards / Submissions | TBD |
| Pipeline Value | Total value of all submitted proposals | TBD |
| Prime Margin % | Average prime management margin | 8-20% |
| Sub Payment Speed | % subs paid within 3 days | 100% |
| Vendor Retention | Active vendors after 12 months | TBD |
| Onboarding Time | Days from invite to standby status | <7 days |
| Proposal Cycle Time | Days from ingestion to submission | TBD |
| Compliance Score | % proposals with green checklist at submission | 100% |

## External Dashboard (Vendor View)

Vendors see a limited dashboard:
- Active bids (with TalentNyk)
- Active contracts and payment status
- Performance scorecard
- License/certification status and upcoming expirations

## Dependencies
- [[../08-review-submission/submission-tracking]]
- [[../09-post-award/payment-tracking]]
- [[../09-post-award/subcontractor-management]]
- [[../10-financial-infrastructure/cash-flow-forecasting]]

## Key Rules & Compliance
- Financial data must be accurate for tax and audit purposes
- Vendor performance data is confidential — only shared with the vendor themselves
- Dashboard access is role-restricted

## Open Questions
- Real-time dashboards or daily-refreshed reports?
- Should the system generate a weekly "state of the network" summary email?
- Data warehouse / BI tool: built-in analytics or integrate with external BI?
