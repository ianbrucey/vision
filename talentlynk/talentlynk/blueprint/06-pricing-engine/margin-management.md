# Margin Management

## Purpose
Manage the two-layer margin structure — the vendor's overhead/profit margin AND TalentNyk's prime management margin — ensuring bids are both competitive and profitable. This is the financial engine of the entire business model.

## The Two Margins

### Layer 1: Subcontractor/Vendor Margin
- Vendor's profit + indirect costs layered on top of direct labor/materials
- Set by the vendor in their pricing matrix
- Varies by trade, project type, and competitive environment
- Typically 10-25% for services, 5-15% for products

### Layer 2: TalentNyk Prime Management Margin
- Revenue for proposal writing, compliance, payment administration, platform infrastructure
- Set by TalentNyk per bid or per contract type
- Typically 8-20% depending on contract complexity, risk, and value
- Can be fixed fee or percentage-based

## Margin Strategy Settings

### Per-Contract-Type Defaults
```json
{
  "marginDefaults": {
    "service_small": { "primeDefaultPercent": 12, "primeMinPercent": 8, "primeMaxPercent": 18 },
    "service_medium": { "primeDefaultPercent": 10, "primeMinPercent": 7, "primeMaxPercent": 15 },
    "service_large": { "primeDefaultPercent": 8, "primeMinPercent": 5, "primeMaxPercent": 12 },
    "product_small": { "primeDefaultPercent": 20, "primeMinPercent": 12, "primeMaxPercent": 30 },
    "product_large": { "primeDefaultPercent": 12, "primeMinPercent": 8, "primeMaxPercent": 20 }
  }
}
```

### Competitive Adjustments
- **LPTA solicitation:** System suggests lower margin to be price-competitive
- **Best Value / Trade-Off:** System allows higher margin if technical score is strong
- **Sole Source:** Margin can be at upper end (no competition)
- **Full & Open (Unrestricted):** Margin on lower end (competing against large businesses)

### Risk-Adjusted Margins
- Higher risk (complex SOW, tight timeline, high bonding): system suggests higher margin
- Lower risk (simple scope, long POP, stable customer): system allows lower margin

## System Behavior

### Default Margin Application
- On bid creation: system applies default prime margin based on contract type and size
- Proposal Manager can override within configured bounds
- If override exceeds max: requires justification (logged for audit)

### Margin Transparency
- Proposal shows: sub cost, sub margin, prime margin, total price
- Internal view shows full breakdown
- Government/client view may show only total price (depending on contract type)

### Profit Forecasting
- Estimated profit per bid: `(Total Bid Price × Prime Margin %)`
- Annual pipeline projection: sum of estimated profits across all bids in play

## Guardrails

### Minimum Profitability
- System warns if estimated prime margin dollars fall below a configurable floor (e.g., $2,500 minimum profit per contract)
- Below-floor bids require explicit approval

### Maximum Reasonableness
- System warns if total price exceeds government Independent Government Estimate (IGE) by more than X%
- System warns if prime margin exceeds 25% (risk of fair-and-reasonable challenge)

## Dependencies
- [[cost-estimation-formula]]
- [[../02-onboarding/pricing-matrix-schema]]
- [[../04-solicitation-pipeline/section-m-parser]] (for LPTA vs. Best Value)

## Key Rules & Compliance
- FAR 15.404-1: Price reasonableness — "fair and reasonable" to the government
- Excessive margins can be challenged by CO or result in post-award audit issues
- Under TINA (Truth in Negotiations Act), certified cost or pricing data may be required for contracts over $2M
- Government can request supporting cost data to justify prices

## Open Questions
- Should prime margin be configurable per Proposal Manager, or set centrally?
- Dynamic margin: should the system auto-adjust margin based on competitive intelligence?
- Is the margin split between entities (Justice Quest vs. FunLink) the same or different?
