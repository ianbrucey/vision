# Capability Scoring

## Purpose
Score the relevance of a vendor's past performance and capabilities to a specific solicitation's Statement of Work. Goes beyond simple NAICS matching — semantically evaluates how similar the vendor's past work is to the government's current need.

## Inputs
- Vendor past performance snippets (scopes of work, values, recency)
- Solicitation SOW and work elements
- Solicitation evaluation criteria (from [[../04-solicitation-pipeline/section-m-parser]])

## Outputs
- Capability relevance score (0-100)
- Matched past performance snippets (for proposal inclusion)
- Relevance narrative: "Vendor X scored high because their 2024 Fulton County Parks contract is directly relevant to this grounds maintenance requirement"

## Scoring Dimensions

### 1. Scope Similarity (40%)
- Vector embedding comparison: solicitation SOW ↔ each past performance snippet
- Cosine similarity between SOW embedding and past project description embedding
- Highest single-snippet similarity + average of top-3 snippets

### 2. Value Similarity (20%)
- How close are vendor's past contract values to the estimated value of this solicitation?
- A vendor who handled $50K projects may not be credible for a $5M contract
- Score: proximity of past values to estimated solicitation value

### 3. Recency (25%)
- Projects within last 1-2 years: full weight
- Projects 3-5 years old: 70% weight
- Projects 5+ years old: 40% weight
- Very old projects (>7 years): 10% weight or excluded

### 4. Client Type Relevance (10%)
- Federal government client: highest weight
- State/local government client: moderate weight
- Commercial client: lower weight
- Same agency as current solicitation: bonus weight

### 5. Outcome Quality (5%)
- Completed on time / under budget: bonus
- Issues or CPARS below satisfactory: penalty
- No outcome data: neutral

## Score Tiers

| Score | Tier | Meaning |
|-------|------|---------|
| 85-100 | Excellent | Highly relevant past performance |
| 70-84 | Good | Relevant with minor gaps |
| 50-69 | Adequate | Partially relevant |
| 25-49 | Weak | Low relevance — use only if no better options |
| 0-24 | Not Relevant | Do not recommend |

## Dependencies
- [[vendor-matching-algorithm]]
- [[../02-onboarding/past-performance-database]]
- [[../04-solicitation-pipeline/sow-extraction]]

## Key Rules & Compliance
- Past performance must be RELEVANT to be creditable — submitting irrelevant past performance weakens the proposal
- "Relevancy" is defined in FAR 15.305(a)(2): past performance should be recent AND relevant
- CO may reject proposals where past performance is too old or too different in scope

## Open Questions
- Embedding model for semantic similarity?
- Should the system allow Proposal Managers to manually adjust relevance scores?
