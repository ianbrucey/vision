# Recommendation Ranking

## Purpose
Synthesize matching scores, capability scores, and availability into a final ranked recommendation presented to the Proposal Manager. This is the decision-support output of the matching engine.

## Inputs
- Vendor match scores (from [[vendor-matching-algorithm]])
- Capability scores (from [[capability-scoring]])
- Availability results (from [[availability-check]])
- Solicitation evaluation criteria (from [[../04-solicitation-pipeline/section-m-parser]])

## Outputs
- Ranked list of recommended vendors
- Composite score per vendor
- Recommendation rationale
- Confidence indicator

## Composite Score Formula

```
Composite = (Match Score × 0.35) + (Capability Score × 0.35) + (Availability × 0.15) + (Certification Fit × 0.15)
```

### Certification Fit Bonus
- Vendor holds socioeconomic certification matching the set-aside requirement: bonus
- Similarly Situated Entity advantage: certified sub strengthens the bid

## Ranking Tiers

| Tier | Criteria | Action |
|------|----------|--------|
| **Recommend** | Composite > 80, no conflicts | Auto-surface as top pick |
| **Consider** | Composite 60-80, minor gaps | Show with caveats |
| **Fallback** | Composite 40-60, significant gaps | Show only if no better options |
| **Do Not Use** | Composite < 40, or conflicts, or missing mandatory certs | Filtered out |

## Presentation to Proposal Manager

For each recommended vendor, display:
1. **Vendor name & company**
2. **Composite score** with breakdown
3. **Top 3 matching past performance snippets**
4. **Relevant licenses/certifications**
5. **Pricing baseline** (pre-forecasted rate)
6. **Availability status** with any warnings
7. **Rationale summary** (1-2 sentences why matched)
8. **Action buttons:** Select for bid, Request more info, Dismiss

## System Behavior

### Auto-Shortlisting
- Top 3 vendors auto-surfaced per solicitation
- Proposal Manager can expand to see all matches above threshold

### Manual Override
- Proposal Manager can manually add a vendor not surfaced by the algorithm
- Manual additions are logged for analysis: "Why wasn't this vendor surfaced?"

### Feedback Loop
- Track which recommendations were selected vs. dismissed
- Use selection patterns to tune matching weights over time

## Dependencies
- [[vendor-matching-algorithm]]
- [[capability-scoring]]
- [[availability-check]]
- [[../12-platform-admin/dashboard-analytics]]

## Key Rules & Compliance
- Vendor selection must be based on merit — not personal relationships or kickbacks (FAR 3.104)
- All selection rationale should be documented for potential protest defense
- The system recommends; the human decides

## Open Questions
- Should the system track "conversion rate" (selected → won) per vendor to inform future rankings?
- Should past vendors who performed well get a loyalty bonus in ranking?
