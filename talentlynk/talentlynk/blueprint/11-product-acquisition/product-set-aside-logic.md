# Product Set-Aside Logic

## Purpose
The branching decision engine that determines which path to take when a product solicitation is ingested — manufacturer JV, small manufacturer subcontract, class-waived large supplier, or Full & Open commercial purchase. This is the strategic routing layer for all product-side bids.

## Decision Tree

```
[Product Solicitation Ingested]
          │
          ▼
[Check: Competition Type]
    ├── Full & Open (Unrestricted)
    │       │
    │       ▼
    │   [GREEN LIGHT: Source from ANY supplier]
    │   • NMR does not apply
    │   • BAA/TAA/Berry still apply
    │   • Use large distributors (Uline, Grainger, etc.)
    │   • Purchase Order + standard commercial terms
    │   • Margins typically lower (large business competition)
    │
    └── Small Business Set-Aside
            │
            ▼
        [Check: Do we have a Small Manufacturer?]
            ├── YES → [Path A: Small Manufacturer Subcontract]
            │   • Teaming Agreement or Subcontract with manufacturer
            │   • 100% NMR compliant
            │   • Can bid on any small business set-aside
            │   • JV possible if manufacturer holds socioeconomic cert
            │
            └── NO → [Check: SBA Class Waiver?]
                    ├── YES → [Path B: Waived Item — Source from Large Supplier]
                    │   • Class waiver covers this NAICS
                    │   • Can use large distributors
                    │   • Standard commercial PO terms
                    │   • No manufacturer JV needed
                    │
                    └── NO → [Check: Individual Waiver Feasible?]
                            ├── YES → [Path C: Request Individual Waiver]
                            │   • Market research to prove no small mfr exists
                            │   • Submit waiver request to CO → SBA
                            │   • 15 business days for SBA response
                            │   • Risk: waiver denied, bid deadline missed
                            │
                            └── NO → [CANNOT BID as Set-Aside]
                                    • Only option: hope solicitation is amended to Full & Open
                                    • Or: find and onboard a small manufacturer before deadline
```

## Path Selection Table

| Path | Set-Aside Eligible | NMR Compliant | Supplier Type | Margin Potential | Complexity |
|------|-------------------|---------------|---------------|-----------------|------------|
| A: Small Mfr Sub | Yes | Yes | Small U.S. Manufacturer | Medium-High | Medium |
| B: Class Waiver | Yes | Waived | Any (including large corp) | Medium | Low |
| C: Individual Waiver | Yes (if approved) | Waived (if approved) | Any | Medium | High |
| D: Full & Open | N/A | N/A | Any | Lower | Low |
| Cannot Bid | No | N/A | N/A | None | N/A |

## Edge Cases

### Hybrid Solicitations (Products + Services)
Some solicitations require both product delivery AND installation/training services. In these cases:
- **Product portion:** Product set-aside logic applies
- **Service portion:** Service set-aside logic applies ([[../05-matching-engine/vendor-matching-algorithm]])
- Both must be compliant — a service partner and a product manufacturer may both be needed

### "American Alibaba" Strategy (Path A Preferred)
The strategic vision is to build such a robust small manufacturer directory that Path A becomes the default. Every product solicitation matches to at least one domestic small manufacturer. This:
- Maximizes set-aside eligibility (most contracts are set-asides)
- Builds American manufacturing capacity
- Higher margins (less competition than Full & Open)
- Aligns with government policy priorities (domestic manufacturing)

## Dependencies
- [[non-manufacturer-rule]]
- [[class-waiver-database]]
- [[nmr-waiver-request]]
- [[small-manufacturer-directory]]
- [[buy-american-act]]
- [[../02-onboarding/manufacturer-onboarding]]

## Key Rules & Compliance
- Set-aside eligibility is determined by the CO — system classification may need manual confirmation
- NMR is the law, not a guideline — violations can result in debarment
- The government's definition of "manufacturer" can be contested — be prepared to prove your supplier qualifies

## Open Questions
- Should the system maintain a "win rate by path" metric to optimize bidding strategy?
- How to handle solicitations where the NAICS seems to be a service NAICS but products are the primary deliverable?
