# NMR Waiver Request

## Purpose
Manage the workflow for requesting an individual Non-Manufacturer Rule waiver from the SBA when no class waiver exists and no small manufacturer is in the network. This is a case-by-case exemption process — time-consuming but sometimes the only path to bidding on an attractive product set-aside.

## When to Request

An individual NMR waiver is worth pursuing when:
1. Solicitation is a small business set-aside for supplies
2. No small manufacturer in the network produces the product
3. No SBA Class Waiver covers the product
4. The contract value justifies the effort
5. There's reason to believe no domestic small manufacturer exists (market research supports this)

## The Waiver Request Process

### Step 1: Market Research
- TalentNyk conducts research to prove "no domestic small business manufacturer exists for this product"
- Sources: SBA Dynamic Small Business Search (DSBS), ThomasNet, industry databases, internet search
- System can assist: query small manufacturer directory, search DSBS
- Document: who was contacted, what was found (or not found)

### Step 2: Draft Waiver Request
The request must include:
- Solicitation number and agency
- Product description and NAICS code
- Evidence of market research (lack of small manufacturers)
- Statement that TalentNyk will supply the product of a domestic (or designated country) manufacturer
- TalentNyk's size representation (under 500 employees)

### Step 3: Submit to Contracting Officer
- Waiver request is submitted to the CO
- The CO forwards to the SBA for review
- SBA has 15 business days to respond (by regulation)
- During this time, the proposal deadline may be approaching — timing risk

### Step 4: SBA Decision
- **Approved:** Waiver granted. TalentNyk can bid, sourcing from any compliant manufacturer.
- **Denied:** SBA identifies a small manufacturer TalentNyk missed. Waiver denied.
- **Conditional:** Approved with restrictions (must use specific manufacturer, price limitations, etc.)

## System Workflow

```
Waiver Request Status Flow:
[Draft] → [Market Research Phase] → [Waiver Document Generated] → [Submitted to CO]
    → [Under SBA Review] → [Approved / Denied / Conditional]
    → If Approved → GREEN LIGHT for bid
    → If Denied → BLOCKED from set-aside bid (can bid Full & Open only)
```

### Timeline Tracking
- SBA has 15 business days to respond
- System tracks days since submission
- Alert if SBA response is overdue
- Alert if proposal due date is approaching without SBA response

### Success Rate Tracking
- Track waiver request outcomes over time
- Identify which NAICS codes consistently get waivers (might become class waivers)
- Inform bid/no-bid decisions

## Dependencies
- [[non-manufacturer-rule]]
- [[class-waiver-database]]
- [[small-manufacturer-directory]]

## Key Rules & Compliance
- 13 CFR § 121.406(b): Individual waivers
- CO submits the waiver request to SBA on behalf of the offeror
- SBA must respond within 15 business days
- Waiver is contract-specific — it doesn't carry over to other solicitations
- Burden of proof is on the offeror to demonstrate no small manufacturer exists

## Open Questions
- Should the system proactively pre-request waivers for common NAICS codes without class waivers?
- Template automation: should the system auto-draft the waiver request from market research data?
