# Non-Manufacturer Rule (NMR)

## Purpose
Enforce the SBA's Non-Manufacturer Rule (13 CFR § 121.406) compliance within the product acquisition pipeline. This is the critical gate that determines whether TalentNyk can legally supply a product under a small business set-aside contract — and which suppliers it can source from.

## The Rule

When a small business prime contractor supplies products under a small business set-aside, the products must be manufactured by a **domestic small business manufacturer** — unless a waiver applies.

The government wants to prevent small "pass-through" companies from winning set-aside contracts and simply shipping products from large corporations (Kimberly-Clark, Georgia-Pacific, etc.).

## Compliance Requirements

To legally supply products under a small business set-aside, TalentNyk must meet ALL of:

1. **Size:** TalentNyk cannot have more than 500 employees (for most manufacturing NAICS)
2. **Ownership:** TalentNyk must take ownership or legal possession of the items
3. **Origin:** The product must be manufactured by a **domestic small business manufacturer**

Requirement #3 is the hard one — it restricts WHO TalentNyk can source from.

## The Three Paths to Compliance

### Path A: Source from a Small Business Manufacturer (Always OK)
- Find a U.S.-based small business that actually MAKES the product
- Sign Teaming Agreement or Subcontract
- Bid on any small business set-aside
- **100% compliant**

### Path B: NMR Class Waiver (OK for Waived Items)
- SBA publishes a list of items by NAICS where there are NO small business manufacturers
- If the product's NAICS is on the class waiver list, TalentNyk can source from ANY supplier (including large corporations)
- System must check: is this product's NAICS on the SBA Class Waiver list?

### Path C: NMR Individual Waiver (Case-by-Case)
- For a specific contract, TalentNyk (or the CO) requests an individual NMR waiver from the SBA
- Must prove: no domestic small business manufacturer exists for this product
- Takes time — typically 15-30 days
- SBA may or may not grant the waiver

### Path D: Full & Open Competition (No NMR)
- If the solicitation is UNRESTRICTED (Full & Open), NMR does NOT apply
- TalentNyk can source from any supplier anywhere
- Margins are typically thinner due to large business competition

## System Enforcement Logic

```
When a product solicitation is ingested:

1. CHECK: Is the solicitation a small business set-aside?
   NO → Path D: Full & Open. No NMR restriction. Any supplier OK.
   YES → Continue...

2. CHECK: Do we have a Small Manufacturer in the network for this product?
   YES → Path A: Route to small manufacturer. Compliant.
   NO → Continue...

3. CHECK: Is this product's NAICS on the SBA Class Waiver list?
   YES → Path B: Can source from any supplier. Compliant.
   NO → Continue...

4. OPTION: Request Individual NMR Waiver?
   YES → Path C: Initiate waiver request. Wait for SBA approval.
   NO → CANNOT BID on this solicitation as a small business set-aside.
```

## Dealer Trap Prevention

During manufacturer onboarding ([[../02-onboarding/manufacturer-onboarding]]), the system must verify:
- Does this company actually MANUFACTURE products in their own facility?
- Or are they a dealer/distributor/reseller?

A certified small business that is only a dealer does NOT satisfy the NMR. Even if you form a JV with them, the PRODUCT still comes from a large business. **The SBA looks at who MADE the product, not who SOLD it.**

## Dependencies
- [[class-waiver-database]]
- [[nmr-waiver-request]]
- [[small-manufacturer-directory]]
- [[product-set-aside-logic]]
- [[../02-onboarding/manufacturer-onboarding]]

## Key Rules & Compliance
- 13 CFR § 121.406: Non-Manufacturer Rule
- FAR 19.102(f): Small business set-aside procedures
- NMR applies to supply contracts under small business set-asides
- Does NOT apply to service contracts or construction contracts
- SBA Size Standards: 500 employees for most manufacturing NAICS (some are 750, 1,000, or 1,500)
- Waivers: SBA maintains the class waiver list; check current before every bid

## Open Questions
- How frequently does the SBA update the Class Waiver list (auto-sync needed)?
- Should the system proactively identify products with NO small manufacturers for individual waiver pre-approval?
