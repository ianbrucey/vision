# Fringe Benefit Calculator

## Purpose
Calculate the mandatory fringe benefit costs that must be layered on top of base wage rates for federal service and construction contracts. Under SCA and DBA, the government mandates specific per-hour fringe amounts (or equivalent benefits) that the contractor must provide.

## Inputs
- Wage determination entry (base wage + fringe rate)
- SCA Health & Welfare rate (e.g., $4.80/hour)
- DBA fringe rate (varies by trade classification)
- Vendor's actual benefit costs (if benefits are provided in lieu of cash fringe)

## Outputs
- Fully burdened hourly labor rate (base + fringe)
- Fringe cost per labor category
- Fringe as percentage of base wage
- Compliance flag: does the vendor's benefit package satisfy the fringe requirement?

## Fringe Components

### SCA Health & Welfare (H&W)
- Flat per-hour rate set by DOL for all SCA-covered workers
- Updated annually (typically $4.80-$5.00+/hour, trending upward)
- Covers: health insurance, life insurance, sick leave, vacation, holidays, retirement
- **Option A:** Pay the cash H&W rate directly to the employee
- **Option B:** Provide bona fide benefits that cost at least the H&W rate per hour

### DBA Fringe
- Specified per trade classification in the WD (e.g., Roofer: $28.50 base + $6.25 fringe)
- Fringe can be paid as cash or as bona fide benefits
- If benefits are provided, the cost must be documented and allocated per hour

## Calculation Logic

### SCA Calculation
```
Fully Burdened Rate = Base Wage Rate + H&W Rate
Fringe Percentage = H&W Rate / Base Wage Rate × 100
```

### DBA Calculation
```
Fully Burdened Rate = Base Wage Rate + Fringe Rate
Fringe Percentage = Fringe Rate / Base Wage Rate × 100
```

### Benefit Offset (for vendors who provide benefits)
```
IF vendor.providesBenefits AND benefitCostPerHour >= fringeRate:
  Cash Fringe Owed = 0
  Compliance = "satisfied_by_benefits"
ELSE:
  Cash Fringe Owed = fringeRate - benefitCostPerHour
  Compliance = "partial_cash_fringe_required"
```

## System Behavior

### Auto-Calculation
- On solicitation pricing: pull applicable WD, auto-calculate fully burdened rates
- Layer on vendor benefits data if available
- Default assumption: pay full cash fringe unless vendor benefit data is on file

### Fringe Tracking
- Different fringe rates may apply to different labor categories on the same contract
- System tracks which fringe rate applies to which labor category
- Fringe rates for SCA change annually in July — system must flag active contracts with outdated fringe rates

## Dependencies
- [[wage-determination-database]]
- [[cost-estimation-formula]]
- [[../04-solicitation-pipeline/wage-determination-extraction]]

## Key Rules & Compliance
- SCA H&W rate is non-negotiable — must be paid or equivalent benefits provided
- DBA fringe: if paying cash fringe, it's taxable; if providing benefits, they're generally pre-tax
- If benefits are provided, the employer must document and allocate the cost
- Vacation and holiday are separate requirements under SCA (in addition to H&W)
- Independent contractors (1099) are not subject to SCA/DBA — but government contracts strongly prefer W-2 labor

## Open Questions
- Should the system model the vendor's actual benefit costs for more accurate pricing?
- Track annual SCA H&W rate changes and auto-update active subcontract pricing?
