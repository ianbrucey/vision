LIMIT THE FILE CONTENT TO AT MOST 150 LINES. IF MORE CONTENT NEEDS TO BE ADDED USE THE str-replace-editor TOOL TO EDIT THE FILE AFTER IT HAS BEEN CREATED.
# GSA Lease Partnership (RFL) — Analysis & Recommendations

**Prepared for:** Ian Bruce (JusticeQuest LLC) — potential partnership with Kenton Waldroup (real estate broker)
**Reference materials:** `scope.md`, `eval.md`, `deliverables.md`, `tech.md` (RLP No. 6FL0489-3, Port St. Lucie/Fort Pierce, FL); email thread `JusticeQuest Mail - Govt. Contracting opportunity.pdf`

## ⚠️ Threshold Issue: Which Solicitation Is This?

The breakdown files (`scope.md`/`eval.md`/`deliverables.md`/`tech.md`) analyze **RLP No. 6FL0489-3** (Port St. Lucie/Fort Pierce, FL — GSA verified this is a live, active solicitation with offers due 8/10/2026). However, the PDF you sent Kenton was titled **"Sacramento-lease-triage.pdf"** and linked to a **different** SAM.gov notice (`.../a56d6d81c1fa4115a5f5923fc1f261b3/view`, Sacramento, CA). Kenton caught this discrepancy directly: *"A few details in the pdf don't line up... can you send me the original SAM.gov notice."*

I could not resolve the exact Sacramento notice content (SAM.gov's workspace UI is client-side rendered and blocks scraping), but I found evidence in public sources that GSA has run at least two prior iterations of the Port St. Lucie requirement (6FL0489-2, 6FL0489(R2)) with **its own retained tenant-rep brokers already named** (Timothy Mazzucca as CO; brokers Megan Shulin / Patrick Burke listed in the R2 posting). **Before doing anything else, confirm which notice number you're actually working, and whether GSA already has its own broker of record on that requirement** — this changes your commission structure (see Section 3).

## 1. FAR/GSAR Nuances for RFLs

Leasing is **not** procured under the FAR you're used to for services/supplies. Key differences:

| Standard FAR Contract | GSA Lease (RFL) |
|---|---|
| FAR Part 15 (negotiated procurement) governs | **GSAR Part 570** governs. Per GSAR 570.101(d): *"The FAR does not apply to leasehold acquisitions of real property"* except where specifically cross-referenced |
| Uniform Contract Format | Not required (570.116) — lease uses SF-2 or GSA Form 3626 |
| CLINs/pricing schedule | Rent schedule (Shell/TI/BSAC/Operating Costs) on GSA Forms 1364 & 1217 |
| Cost realism / trade-off common | **LPTA only** — pass/fail technical gates, then lowest Present Value price wins (RLP 4.03/4.04) |
| Progress payments per FAR 32 | Rent paid **monthly, in arrears** — first payment 45–60 days after occupancy (per Kenton's "Government Lease Payment Cycle" attachment) |
| Broker/agent fees generally unallowable as direct pass-through | **Commission is baked into the deal by design** — GSA Form 1217 captures commission; the Lease's "Broker Commission and Commission Credit" clause splits commission between the broker(s) and a rent credit to the Government |

**Practical implication:** when far_lookup returns nothing for a "570.xxx" citation, that's expected — GSAR Part 570 is **Title 48, Chapter 5**, not ingested in your local FAR database (which only covers Chapter 1, FAR Parts 1–53). Use `lookup_cfr_section` / `search_cfr` (eCFR) for GSAR citations instead, and reserve `far_lookup` for core FAR clauses incorporated by reference (e.g., 52.204-13, 52.222-35/36/37, 52.219-4 HUBZone, 15.403 pricing).

**Commission mechanics (confirmed via GSA lease templates):**
- The Lease names a **"Broker"** — the real estate broker "representing GSA in connection with this Lease transaction."
- Commission is earned on lease execution, payable per a **separate Commission Agreement between the Lessor and the Broker** (not part of the Lease itself, but referenced by it).
- If the broker agrees to forgo part of the commission, that portion becomes a **"Commission Credit"** — amortized as a rent reduction over the shortest practicable period.
- If **GSA already has its own broker** on a requirement (as appears to be the case on the Port St. Lucie history), that broker is the one named in the Lease/RLP and typically shares commission with a **cooperating/procuring broker** representing the property owner, under industry-standard cooperating-broker agreements — separate from anything GSA controls.

## 2. Systematic Workflow for RFLs

1. **Source opportunities** — `search_sam_opportunities` filtered to NAICS 531120 (Lessors of Nonresidential Buildings) and notice types Presolicitation/Solicitation; supplement with `query_forecast_opportunities` to catch requirements before SAM posting.
2. **Triage (quick kill/no-kill)** — pull ABOA SF range, delineated area, term, and award basis. RFLs are LPTA far more often than negotiated trade-off — if Kenton can't find a compliant building at a competitive rate, don't bid.
3. **Confirm the broker landscape** — check the notice/RLP for a **named "GSA's Broker"** (as in the Port St. Lucie postings). If GSA already retained a broker, your structure must work through/around them (cooperating broker), not in place of them.
4. **Property identification (Kenton's lane)** — match candidate buildings against the *mandatory* gates in `scope.md`/`eval.md`: ABOA SF, single contiguous floor, elevator (if above ground floor), parking ratio, 1,000-ft setback from prohibited uses, ENERGY STAR/EISA, floodplain, asbestos, ABAAS accessibility, FSL II security buildout feasibility.
5. **Compliance verification (Ian's lane)** — for every FAR/GSAR clause cited in the RLP, verify verbatim text with `far_lookup` (core FAR) or `lookup_cfr_section`/`search_cfr` (GSAR Part 570, Title 48). Never paraphrase from memory — GSA LCOs will bounce non-conforming offers (4.03.C/E: no exceptions to Lease provisions).
6. **Price modeling** — build the Present Value Cost per ABOA SF model per RLP 4.04 (5% discount, 2.5% opex escalation, A/E + PM fee uplift, 80 hrs/yr overtime HVAC, commission credit subtracted from year-1 gross rent). This is the *only* number that matters once technically acceptable.
7. **Submission** — package GSA Forms 1364/1217, Form 12000 (FPE evaluation), floor plans, financial capability evidence, and submit via RSAP (leasing.gsa.gov) before the 5:00 PM ET deadline. No paper, no late offers.
8. **Post-award (if won)** — Kenton's role mostly ends at execution; Ian's admin role continues through DIDs, CD review, TI/BSAC negotiation, and NTP milestones (see `deliverables.md` timeline) — this is a 12–18 month tail, not a one-time submission.

## 3. Recommended Partnership Structure

Kenton's open questions (compensation, division of commission, documentation, exclusive representation) need to be locked down **before** approaching any property owner. Recommended structure:

**A. Two separate documents, not one blended agreement:**

1. **Teaming/Services Agreement (Ian ↔ Kenton)** — governs *your* relationship. Defines:
   - Ian's role: opportunity identification, requirements analysis, compliance packaging, proposal drafting/submission, SAM registration/eligibility (already in place).
   - Kenton's role: property sourcing, owner outreach, price/terms negotiation with owners, technical site qualification.
   - Compensation to Ian: **fixed fee or percentage of Kenton's commission, paid out of the Commission Credit/broker fee** at lease execution (not at rent commencement) — this decouples Ian's pay from the 45–60 day rent-in-arrears lag Ian described. Recommend a **success fee** (paid only if a lease is awarded) rather than hourly, since RFL cycles are long and speculative.
   - Exclusivity/non-circumvent: neither party pursues a sourced opportunity without the other once work has begun on it.

2. **Exclusive Right-to-Represent / Listing Agreement (Kenton ↔ Property Owner)** — this is the document Kenton correctly flagged as required. SAM registration does *not* authorize anyone to offer a property; only the **owner** (or someone with the owner's written authority per RLP 3.01.F/G) can be the Offeror. This agreement should:
   - Grant Kenton the exclusive right to represent the owner for this GSA transaction.
   - Specify the commission rate (industry-standard, expressed as % of aggregate lease value for the firm term, per GSA's own commission guidance).
   - Explicitly reference the GSA "Broker Commission and Commission Credit" lease clause so the owner understands part of the negotiated commission may be credited back to GSA as reduced rent, not paid out in full.
   - Authorize Kenton (or Kenton + Ian, as the owner's representative team) to sign/submit the offer on the owner's behalf (GSA Form 1364 requires this authorization if the Offeror isn't the ultimate owner).

**B. Why not a Joint Venture?** A JV creates shared liability for the *lease itself* (a 15-year real property obligation) and complicates SAM/CAGE registration. A services/teaming agreement plus a standard brokerage listing agreement keeps Ian's exposure limited to his admin/proposal role and Kenton's exposure limited to his brokerage duties — consistent with how GSA's own broker relationships are structured (broker ≠ obligor on the lease; the property owner is).

## Next Steps

1. Resolve the Sacramento vs. Port St. Lucie notice confusion with Kenton — send him the correct SAM.gov link for whichever opportunity you intend to pursue.
2. If proceeding on Port St. Lucie (6FL0489-3) or a similar live RLP, check the notice for a **named GSA broker** before committing to a commission structure.
3. Draft the Teaming Agreement (Ian/Kenton) and template Listing Agreement (Kenton/Owner) — happy to draft both once you confirm the deal terms above.
