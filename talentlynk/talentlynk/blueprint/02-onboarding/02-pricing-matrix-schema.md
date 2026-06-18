# Pricing Matrix Schema

## Purpose
Define the data model for vendor commercial pricing — the baseline rates that feed into the cost estimation engine. Vendors provide their standard commercial pricing upfront so the system can instantly estimate bid costs when a solicitation drops.

## Data Model

```json
{
  "vendorId": "vnd_99218",
  "pricingMatrix": {
    "primaryUnitType": "sq_ft",
    "baseRate": 0.12,
    "unitTypes": [
      {
        "type": "sq_ft",
        "rate": 0.12,
        "description": "Per square foot, standard service"
      },
      {
        "type": "hourly",
        "rate": 75.00,
        "description": "Emergency/after-hours callout"
      },
      {
        "type": "per_acre",
        "rate": 450.00,
        "description": "Large-area grounds maintenance"
      }
    ],
    "minProjectValue": 1500.00,
    "maxProjectCapacity": 500000.00,
    "geographicMultipliers": [
      { "state": "GA", "multiplier": 1.0 },
      { "state": "AL", "multiplier": 1.15 }
    ],
    "marginPercent": 18.0,
    "lastUpdated": "2026-06-01",
    "validUntil": "2027-06-01"
  }
}
```

## Pricing Models Supported

| Model | Example | Use Case |
|-------|---------|----------|
| Per square foot | $0.12/sq ft | Landscaping, janitorial, roofing |
| Per acre | $450/acre | Large grounds maintenance |
| Hourly | $75/hr | Emergency services, specialist labor |
| Per project | $5,000/project | Defined-scope work |
| Per unit | $30/unit | Product manufacturing |
| Per linear foot | $8/linear ft | Fencing, piping |
| Cost-plus | Cost + 15% | Unpredictable scope |

## System Behaviors

### Pre-Forecasting
- Vendor rates stored as "pre-forecasted" baseline
- When solicitation drops, system instantly pulls rates + applies wage determination overlay
- Eliminates the bottleneck of waiting for sub quotes before a deadline

### Rate Validity
- Pricing has a validity period (vendor sets: "these rates are good until X date")
- System alerts vendor when rates are expiring
- Stale rates flagged in cost estimation

### Geographic Adjustments
- Vendors can set multipliers by state/region
- System applies correct multiplier based on contract performance location

## Dependencies
- [[vendor-profile-schema]]
- [[../06-pricing-engine/cost-estimation-formula]]
- [[../06-pricing-engine/margin-management]]

## Key Rules & Compliance
- Pricing in federal proposals must be "fair and reasonable" (FAR 15.404-1)
- Price quotes for specific bids require vendor sign-off (task-specific TA)
- Pre-forecasted pricing is a baseline, not a binding quote

## Open Questions
- Should the system track historical bid pricing vs. actuals for accuracy analysis?
- How to handle vendors who price differently per client type (federal vs. commercial)?
