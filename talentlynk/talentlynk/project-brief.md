    dfe

# Project Brief: TalentNyk — GovCon Aggregator Platform

## What It Is

TalentNyk is a **tech-enabled Management Prime Engine** — a software platform that sits between the U.S. Federal Government (the world's largest buyer) and a pre-vetted network of hyper-local small businesses, independent professionals, and domestic manufacturers. The platform automates the entire federal contracting lifecycle: from solicitation ingestion and parsing, through vendor matching and compliant pricing, to proposal generation and post-award payment orchestration.

The core insight: most small businesses and skilled professionals are locked out of federal contracting not because they can't do the work, but because they can't navigate the administrative, legal, and proposal-writing bureaucracy. TalentNyk becomes their administrative wrapper — handling compliance, technical writing, and cash flow — while they focus on execution.

## The Business Model

TalentNyk operates as a **Prime Contractor** to the government, winning contracts on its own legal footing, then routing execution to its network via subcontracts. Revenue comes from the spread between what the government pays and what the sub gets paid (the "management margin"). The platform carries **zero upfront cost** for talent or inventory — all commitments are contingent on contract award.

## The Three Network Buckets

1. **Individual Specialists (Contingent W-2 Workforce):** Skilled professionals (project managers, IT leads, compliance experts) onboarded via Contingent Offer Letters and Letters of Commitment. They appear as proposed Key Personnel in bids at $0 upfront cost. If the contract is won, they activate as W-2 employees on Day 1 of performance.
2. **Small Business Service Partners (The Execution Network):** Local trades — landscapers, roofers, janitorial, logistics — onboarded via Master Teaming Agreements. Under "Similarly Situated Entity" rules, subbing to other certified small businesses counts as prime performance, avoiding pass-through violations.
3. **Small Domestic Manufacturers (The "American Alibaba" Layer):** U.S.-based factories producing physical goods. This is the product-acquisition side — subject to the Non-Manufacturer Rule (NMR), meaning products sold under small business set-asides must be made by small business manufacturers, not large corporate factories.

## The Core Pipeline (What the Software Does)

```
[Solicitation Drop] → [AI Classification: RFI/RFQ/RFP + SOW Extraction]
    → [NAICS/Code Matching → Pull Network Vendors]
    → [Wage Determination Overlay: SCA/Davis-Bacon compliance]
    → [Algorithmic Cost Estimation: mandated wage + fringe + sub margin + prime margin]
    → [Mandatory Review Routing: sub digital sign-off required before submission]
    → [Multi-Volume Proposal Compilation: filled gov forms + custom technical narrative]
    → [Submit to Government]
```

## What's Already Been Mapped

- The legal framework for contingent hiring (no-cost workforce)
- The Master Teaming Agreement → Task-Specific Exclusivity workflow
- The multi-volume proposal standard (government PDF forms vs. custom technical narrative)
- The Document Layout Analysis approach for auto-filling flattened/scanned government PDFs
- The SCA/Davis-Bacon wage determination overlay logic
- The Non-Manufacturer Rule and product-side compliance structure
- The post-award cash flow engine (Prompt Payment Act, AR factoring, Assignment of Claims)
- The two-entity SAM.gov strategy (Justice Quest for IT, FunLink repurposed as the Management Prime)
- The Joint Venture branching logic for specialized socioeconomic set-asides (WOSB, SDVOSB, 8a)

## What Needs to Be Built (High-Level)

- **Onboarding System:** Vendor profile intake, NAICS auto-classification, licensing matrix, pricing matrix
- **Ingestion Pipeline:** S3-triggered document parsing, SOW extraction, classification
- **Matching Engine:** Cross-reference solicitation NAICS/CAGE codes against vendor database
- **Pricing Calculator:** Wage determination ingestion + vendor margin layering
- **Review & Sign-Off Engine:** Mandatory digital signature routing before submission
- **Proposal Compiler:** PDF form-filling (AcroForm + computer vision for flattened forms) + custom narrative generation
- **Post-Award Orchestration:** Payment tracking, accelerated payment routing, AR factoring API hooks
- **Compliance Guardrails:** NMR checks, class waiver lookups, exclusivity enforcement, set-aside branching logic

## Open Questions

- **The name** — the directory is `talentlynk` but referenced entities include "General Consulting LLC," "Justice Quest," and "FunLink." Is "TalentNyk" the platform/product name?
- **The MVP scope** — of everything described, which piece should be built first? Onboarding? Solicitation ingestion? Proposal compilation?
- **The audience** — is this platform for internal team use, or a marketplace that external vendors and clients log into?
