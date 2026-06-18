# Section M Parser

## Purpose
Extract and parse Section M — "Evaluation Factors for Award" — which tells bidders how their proposal will be judged. This is arguably the most strategic section: it reveals what the government actually cares about and how they weigh trade-offs between technical quality and price.

## Inputs
- Classified solicitation text (RFP, Combined)
- Document section labeled "Section M" or containing FAR 52.212-2

## Outputs
- Structured evaluation criteria with weights
- Trade-off vs. LPTA determination
- Adjectival rating scheme (if disclosed)
- Price vs. non-price weight ratio
- Evaluation subfactors and their relative importance

## Evaluation Method Detection

### Best Value Trade-Off
Government weighs technical merit against price. Higher technical quality can justify higher price. The system must identify:
- Technical factors and their weights
- Price factor weight
- Whether technical is "significantly more important," "approximately equal," etc.

### LPTA (Lowest Price Technically Acceptable)
Price is the differentiator. Technical is pass/fail. The system must identify:
- Minimum technical acceptability thresholds
- Pass/fail criteria
- Price then becomes the sole differentiator

## Structured Output

```json
{
  "evaluationMethod": "best_value_tradeoff",
  "factors": [
    {
      "name": "Technical Approach",
      "weight": "most_important",
      "subfactors": [
        {
          "name": "Understanding of Requirements",
          "description": "Demonstrated understanding of the SOW and proposed approach"
        },
        {
          "name": "Staffing and Management Plan",
          "description": "Qualifications of key personnel and management structure"
        }
      ]
    },
    {
      "name": "Past Performance",
      "weight": "important",
      "subfactors": [
        {
          "name": "Relevancy",
          "description": "How similar past projects are to this requirement"
        },
        {
          "name": "Quality",
          "description": "How well past projects were performed"
        }
      ]
    },
    {
      "name": "Price",
      "weight": "less_important_than_technical",
      "description": "Evaluated for fairness and reasonableness"
    }
  ],
  "adjectivalRatings": ["Outstanding", "Good", "Acceptable", "Marginal", "Unacceptable"],
  "lptaThresholds": null
}
```

## Strategic Value

Section M data drives:
- **Proposal emphasis:** Where to allocate page count and effort
- **Pricing strategy:** If price is LPTA, be the lowest; if trade-off, justify value
- **Past performance selection:** Which references to feature based on evaluation weight
- **Staffing recommendations:** How prominently to feature Key Personnel

## Dependencies
- [[classification-engine]]
- [[../07-proposal-generation/technical-narrative-templates]]
- [[../06-pricing-engine/cost-estimation-formula]]

## Key Rules & Compliance
- FAR 15.101: Best value continuum (trade-off vs. LPTA)
- FAR 15.304: Evaluation factors and significant subfactors
- Evaluation factors must be consistent with the SOW (protest risk if they're not)
- Adjectival ratings are NOT standardized across agencies — each agency defines its own

## Open Questions
- Should the system suggest proposal strategy based on Section M analysis?
- How to handle solicitations where evaluation criteria are vague ("the government will evaluate proposals holistically")?
