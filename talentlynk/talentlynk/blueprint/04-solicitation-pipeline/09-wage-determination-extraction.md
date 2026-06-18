# Wage Determination Extraction

## Purpose
Parse the government-mandated wage and fringe benefit rates attached to a solicitation. These wage determinations override any commercial pricing — the government sets mandatory minimum hourly rates for specific labor categories. This is the data that feeds the pricing engine's compliance layer.

## Why This Matters

If a solicitation requires a Roofer to be paid $28.50/hour + $4.80/hour fringe, and a vendor's commercial rate is $22/hour, the vendor CANNOT use their commercial rate. The system must calculate pricing from the government-mandated floor upward, layering the vendor's overhead/profit margin on top.

## Inputs
- Wage determination document (WD) attached to solicitation (PDF or text)
- WD number (e.g., WD 2015-4567, Revision 17)
- Applicable law: Service Contract Act (SCA) or Davis-Bacon Act (DBA)

## Outputs
- Structured wage rates by labor category
- Fringe benefit rates (Health & Welfare, pension, vacation)
- Applicable county/region
- Effective date and revision number
- Calculated fully-burdened hourly rate per labor category

## SCA vs. DBA Wage Determinations

### Service Contract Act (SCA)
- Applies to service contracts (janitorial, landscaping, security, IT support, etc.)
- Wage rates specified by labor category (e.g., "Janitor," "Groundskeeper")
- Health & Welfare (H&W) fringe rate: typically a flat per-hour amount (e.g., $4.80/hr)
- WD issued by Department of Labor, Wage and Hour Division
- Location-based: different rates for different counties

### Davis-Bacon Act (DBA)
- Applies to construction contracts (roofing, HVAC, electrical, general construction)
- Wage rates specified by trade classification (e.g., "Roofer," "Electrician")
- Fringe benefits: specified as hourly cash equivalent, OR employer-provided benefits
- WD issued by DOL for specific construction types (Building, Highway, Heavy, Residential)
- Location-based by county

## Extraction Logic

### 1. Document Type Detection
- SCA WD: Title contains "Service Contract Act," includes "Health & Welfare"
- DBA WD: Title contains "Davis-Bacon," includes "General Decision Number"
- System determines which parsing logic to apply

### 2. Structured Parsing

#### SCA Wage Determination
```json
{
  "wageDeterminationNumber": "2015-4567",
  "revision": 17,
  "dateOfLastRevision": "2026-01-15",
  "state": "Georgia",
  "county": "Fulton",
  "act": "SCA",
  "healthAndWelfareRate": 4.80,
  "occupations": [
    {
      "code": "11150",
      "title": "Groundskeeper",
      "wageRate": 15.40,
      "totalBurdenedRate": 20.20
    },
    {
      "code": "11210",
      "title": "Janitor",
      "wageRate": 13.85,
      "totalBurdenedRate": 18.65
    }
  ]
}
```

#### DBA Wage Determination
```json
{
  "generalDecisionNumber": "GA20260001",
  "constructionType": "Building",
  "county": "Fulton",
  "act": "DBA",
  "classifications": [
    {
      "code": "ROOF001",
      "title": "Roofer",
      "baseRate": 28.50,
      "fringeRate": 6.25,
      "totalRate": 34.75
    }
  ]
}
```

### 3. Locality Matching
- Extract county/city from solicitation Place of Performance
- Match to correct WD
- Flag if Place of Performance spans multiple counties with different rates → use highest

## Dependencies
- [[classification-engine]]
- [[naics-extraction]]
- [[../06-pricing-engine/wage-determination-database]]
- [[../06-pricing-engine/cost-estimation-formula]]

## Key Rules & Compliance
- Wage determinations are minimums — paying less = violation of SCA/DBA
- Health & Welfare fringe: if employer provides benefits that cost at least the H&W rate, the cash H&W rate doesn't need to be paid separately
- DBA: workers can be classified at different rates based on actual work performed (apprentice rates available)
- WD revision matters: the WD in effect at award governs, not the one in the solicitation
- FAR 52.222-41 (SCA) and FAR 52.222-4 (DBA): mandatory flow-down clauses

## Open Questions
- Should the system automatically pull the latest WD from SAM.gov/WDOL at proposal time?
- How to handle WDs with 50+ labor categories (auto-matching vs. manual selection)?
