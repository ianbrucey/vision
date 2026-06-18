# Buy American Act (BAA)

## Purpose
Enforce Buy American Act compliance in the product sourcing pipeline. The BAA requires that products purchased with federal funds be manufactured in the United States from U.S. components — with specific exceptions and waivers. Non-compliance can result in contract termination and False Claims Act liability.

## BAA Basics

### What BAA Requires
- **Manufactured in the U.S.:** Final product must be manufactured in the United States
- **Domestic Component Test:** More than 60% (or 65% for some contracts) of the component cost must be U.S. origin
- **Iron & Steel:** Must be 100% U.S. origin (no foreign iron or steel, with limited exceptions)

### When BAA Applies
- All federal contracts for supplies or construction materials (FAR Part 25)
- Unless a trade agreement waiver applies (see below)
- Applies regardless of set-aside status (unlike NMR, which is set-aside-specific)

## Trade Agreement Act (TAA) Exception

Under the Trade Agreements Act (FAR 25.4), the BAA is waived for products from "designated countries":
- **WTO GPA countries:** UK, EU, Japan, South Korea, Canada, etc.
- **FTA countries:** Countries with U.S. Free Trade Agreements (Australia, Singapore, Mexico/Canada via USMCA, etc.)
- **Caribbean Basin countries:** Limited exceptions
- **Least Developed Countries:** Some exceptions

**China, India, Russia, Brazil:** NOT designated countries. Products from these countries are generally NOT TAA-compliant for federal contracts.

## Berry Amendment (DoD Only)

For DoD contracts, the Berry Amendment (DFARS 225.7002) goes FURTHER than BAA:
- **100% U.S. origin required** for: textiles, clothing, footwear, food, specialty metals
- TAA exceptions do NOT apply to Berry-covered items
- System must detect: is this a DoD contract? → Does the product fall under Berry categories? → If yes, 100% U.S. origin required

## System Compliance Logic

```
For each product solicitation:

1. CHECK: Is BAA applicable?
   YES for all federal contracts → Continue
   
2. CHECK: Does TAA waiver apply?
   Trade agreement country product → BAA waived (TAA applies instead)
   Non-designated country product → BAA applies fully

3. CHECK: Is Berry Amendment applicable?
   DoD contract + covered product → 100% U.S. origin required
   Not DoD or not covered product → Standard BAA domestic content test

4. MATCH: Filter manufacturer directory by compliance level:
   - Berry: U.S. manufacturers only, 100% U.S. components
   - BAA: U.S. manufacturers, 60%+ U.S. components
   - TAA: U.S. or designated country manufacturers
   - None (commercial item exception or Full & Open): Any country
```

## Manufacturer Profile Fields

```json
{
  "bAACompliance": {
    "manufacturingCountry": "USA",
    "domesticComponentPercentage": 85,
    "berryCompliant": true,
    "taaDesignatedCountry": false,
    "countryOfOriginCertification": "s3://..."
  }
}
```

## System Behavior

### Solicitation-Time Check
- System reads solicitation for BAA/TAA/Berry clauses
- Determines applicable trade regime
- Filters manufacturer matches to compliant manufacturers only
- Flags: "This solicitation requires Berry-compliant products. 2 of 5 matching manufacturers do NOT qualify."

### Price Adjustment for BAA
- BAA allows a price preference for domestic products (typically 20% for small business, added to foreign bid for evaluation)
- System can calculate evaluation price vs. actual price for BAA preference

## Dependencies
- [[non-manufacturer-rule]]
- [[small-manufacturer-directory]]
- [[product-set-aside-logic]]
- [[../02-onboarding/manufacturer-onboarding]]

## Key Rules & Compliance
- Buy American Act: FAR Part 25.1 (41 U.S.C. chapter 83)
- Trade Agreements Act: FAR 25.4
- Berry Amendment: DFARS 225.7002 (10 U.S.C. 4862)
- False Claims Act: penalties for falsely certifying BAA compliance
- Component test: 60% domestic for most civilian contracts; 65% for some DoD acquisitions
- Iron and steel: 100% U.S. origin, with very limited exceptions

## Open Questions
- Should the system maintain a database of "designated countries" for TAA lookup?
- How to verify a manufacturer's domestic component percentage (beyond self-certification)?
