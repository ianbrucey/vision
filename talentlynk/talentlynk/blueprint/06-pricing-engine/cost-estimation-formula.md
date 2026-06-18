# Cost Estimation Formula

## Purpose
The master pricing algorithm that calculates the total bid price for any solicitation, layering government-mandated wage floors, vendor commercial rates, and TalentNyk's management margin into a single compliant, profitable number.

## The Master Formula

### For Service Contracts (SCA/DBA)

```
Total Bid Price = Σ (Fully Burdened Labor Rate × Estimated Hours) × (1 + Subcontractor Overhead/Margin) × (1 + Prime Management Margin)
```

Where:
- **Fully Burdened Labor Rate** = Government Mandated Wage + Fringe Benefits
- **Estimated Hours** = SOW-parsed effort estimate × vendor productivity factor
- **Subcontractor Overhead/Margin** = Vendor's profit + indirect costs (from pricing matrix)
- **Prime Management Margin** = TalentNyk's margin for admin, compliance, proposal writing

### For Product Supply Contracts

```
Total Bid Price = Σ (Unit Cost × Quantity + Shipping) × (1 + Prime Management Margin)
```

## Breakdown

### Step 1: Base Labor Cost (Government Floor)
```
BaseLaborCost = Σ (WD_Wage_Rate + WD_Fringe_Rate) × Estimated_Hours
```
This is the non-negotiable minimum. All calculations build upward from here.

### Step 2: Vendor's Total Cost
```
VendorCost = BaseLaborCost + (BaseLaborCost × VendorOverheadPercent) + MaterialsCost + EquipmentCost + TravelCost
```
Vendor overhead covers: supervision, tools, consumables, admin, compliance, profit.

### Step 3: Prime Management Fee
```
PrimeCost = VendorCost × (1 + PrimeManagementMarginPercent)
```
The management margin covers: proposal writing, compliance, payment administration, audit support, platform costs.

### Step 4: Final Bid Price
```
BidPrice = PrimeCost + Contingency (if applicable) + Bond Costs (if required)
BidPrice = Round to nearest dollar (or as specified by solicitation)
```

## Worked Example: Landscaping Contract

**Inputs:**
- SCA WD: Groundskeeper at $15.40/hr + $4.80 H&W = $20.20/hr fully burdened
- Estimated hours: 2,000 per year
- Vendor overhead/margin: 18%
- Prime management margin: 12%
- Materials (mulch, plants): $5,000

**Calculation:**
```
Base Labor: $20.20 × 2,000 = $40,400
Vendor Overhead: $40,400 × 0.18 = $7,272
Materials: $5,000
VendorCost: $40,400 + $7,272 + $5,000 = $52,672
PrimeCost: $52,672 × 1.12 = $58,992.64
BidPrice: $58,993 (rounded)
```

**TalentNyk Spread:** $58,993 - $52,672 = **$6,321**
**Vendor Revenue:** $52,672 - $40,400 = **$12,272** (labor markup + materials)

## Worked Example: Product Supply

**Inputs:**
- 1,000 units at $30/unit from manufacturer
- Shipping: $2,500
- Prime management margin: 20%

**Calculation:**
```
Unit Cost: 1,000 × $30 = $30,000
Shipping: $2,500
PrimeCost: ($30,000 + $2,500) × 1.20 = $39,000
BidPrice: $39,000
Per Unit: $39.00
```

**TalentNyk Spread:** $39,000 - $32,500 = **$6,500**

## System Behavior

### Price Generation
- Auto-calculate bid price from solicitation data + vendor data
- Generate price breakdown (CLIN pricing if required)
- Show: government minimum floor, vendor cost, prime margin, final price

### Scenario Analysis
- Proposal Manager can adjust vendor selection, margin percentages, and hours estimates
- System recalculates in real-time
- "What if we use Vendor B instead of Vendor A?"

### Pricing Compliance
- Flag if calculated price exceeds government budget/IGE (if disclosed)
- Flag if margin exceeds typical ranges (risk of price reasonableness challenge)

## Dependencies
- [[wage-determination-database]]
- [[fringe-benefit-calculator]]
- [[margin-management]]
- [[../04-solicitation-pipeline/sow-extraction]]
- [[../04-solicitation-pipeline/wage-determination-extraction]]
- [[../02-onboarding/pricing-matrix-schema]]

## Key Rules & Compliance
- FAR 15.404-1: Price must be "fair and reasonable"
- TINA (Truth in Negotiations Act): for contracts over $2M, certified cost or pricing data may be required
- Price reasonableness can be challenged by CO or protested by competitors
- Underbidding to win then billing change orders = fraud (False Claims Act)

## Open Questions
- Should the system maintain a "margin floor" (minimum profitable margin below which it warns)?
- How to estimate hours from SOW when the government doesn't specify quantities?
- Competitive analysis: should the system suggest pricing based on "what competitors likely bid"?
