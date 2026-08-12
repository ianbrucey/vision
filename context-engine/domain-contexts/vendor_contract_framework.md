# Justice Quest LLC — Vendor Contract Framework
> Status: Brainstorm / Internal Working Document | Last Updated: 2026-08-12
> NOT LEGAL ADVICE — have counsel review before any live submission.

---

## The Core Question Claude Raised: One Contract or Many?

Claude was right, and here's the precise legal reason why. **FAR 9.601** defines a Contractor Team Arrangement (CTA) in two distinct flavors:

> *(1) Two or more companies form a partnership or joint venture to act as a potential prime contractor; or*
> *(2) A potential prime contractor agrees with one or more other companies to have them act as its subcontractors **under a specified Government contract or acquisition program**.*

The phrase **"specified Government contract or acquisition program"** is the kill shot on the "sign once, use everywhere" dream. The FAR recognizes that teaming relationships must be disclosed per-bid, with the specific subcontractor identified. **FAR 9.603** reinforces this:

> *"The Government will recognize the integrity and validity of contractor team arrangements; provided, the arrangements are identified and company relationships are fully disclosed in an offer..."*

This means **two tiers of contracts are legally necessary** — not optional, not bureaucratic overhead. The Robert Half analogy is actually more apt than you might realize, because Robert Half has both (a) an employment agreement with each temp worker and (b) a separate placement order for each client engagement. You need the same structure.

---

## The Two-Tier Contract Architecture

### TIER 1 — Master Teaming Agreement (MTA)
**When:** Signed at vendor registration (onboarding). One-time, evergreen.
**Purpose:** Establishes the relationship, the framework, and the vendor's consent to be marketed as a subcontractor. Does NOT bind anyone to a specific bid.

### TIER 2 — Bid-Specific Teaming Addendum (BSTA)
**When:** Signed per opportunity, before JQ submits the proposal.
**Purpose:** Activates the MTA for a specific solicitation number (SAM.gov contract number), identifies the subcontractor's specific scope on that bid, and locks in the workshare commitments needed for LoS compliance.

---

## TIER 1: Master Teaming Agreement — Full Clause Breakdown

This is your registration-time "sign once" document. Here's what it must cover and why.

### Article 1 — Relationship of Parties
**What it says:** JQ is the prime intermediary. Vendor is a prospective subcontractor. Neither party is an employee, partner, or agent of the other. No joint venture is formed by the MTA itself.

**Why:** Without this, SBA could find affiliation under the ostensible subcontractor rule (13 CFR 121.103(h)(3)) if the vendor is actually doing all the work. The "no joint venture" language preserves JQ's status as an independent prime.

**Key clause language:**
> "This Agreement does not create a joint venture, partnership, employment relationship, or agency between the Parties. Justice Quest LLC shall act as the prime contractor on any awarded Government contract. Vendor shall act solely as a subcontractor. Nothing herein obligates either Party to enter into any subcontract."

---

### Article 2 — Scope of Marketing Authorization
**What it says:** Vendor explicitly authorizes JQ to represent Vendor's past performance, capabilities, NAICS codes, certifications, bonding capacity, and personnel in proposals to Government agencies.

**Why:** This is the heart of the "Robert Half of GovCon" model. Without explicit written authorization, using a vendor's experience in a proposal without their knowledge is misrepresentation. This clause is what makes it legal.

**Key clause language:**
> "Vendor hereby grants Justice Quest LLC a non-exclusive, revocable authorization to represent Vendor's capabilities, past performance, certifications, personnel qualifications, equipment, and bonding capacity in responses to Government solicitations, provided that: (a) a Bid-Specific Teaming Addendum (BSTA) has been executed for the relevant solicitation prior to submission; and (b) the representation is accurate as of the date of submission."

**Critical data fields this clause requires in your database:**
- `vendor_profiles.naics_codes[]` — must be current; stale NAICS = false representation
- `vendor_profiles.certifications[]` — expiration dates must be tracked
- `vendor_profiles.bonding_capacity` — must be refreshed at least annually

---

### Article 3 — Similarly Situated Entity Representation (the LoS Engine)
**What it says:** Vendor represents and warrants that it holds the same small-business program status (or qualifies under the relevant NAICS) as JQ for any bid on which it is used. Vendor agrees to notify JQ immediately of any change in its SB program status.

**Why:** This is the mechanism that makes your cost math work. Per **FAR 52.219-14(e)(1)**, on a services set-aside, JQ cannot pay more than 50% to *non-similarly-situated* subs. But work by a similarly situated entity *counts toward* JQ's self-performance. The MTA must lock in the vendor's warranty of that status so JQ can rely on it in its LoS calculation.

**Key clause language:**
> "Vendor represents and warrants that, as of the date of each executed Bid-Specific Teaming Addendum, Vendor qualifies as a 'similarly situated entity' as defined in 13 CFR 125.1 and FAR 52.219-14 with respect to the applicable solicitation's set-aside program and primary NAICS code. Vendor shall provide written notice to Justice Quest LLC within five (5) business days of any change in Vendor's size status, certifications, or program eligibility that would affect this representation."

---

### Article 4 — Workshare Commitment Framework
**What it says:** When a BSTA is executed, Vendor commits to perform the workshare percentage stated in that BSTA. Vendor agrees that JQ, as prime, retains full discretion to determine and certify self-performance percentages to the Government.

**Why:** The prime is on the hook to the Government for LoS compliance under FAR 52.219-14. JQ cannot transfer that certification risk to a vendor without a contractual backstop. This clause is what gives JQ the right to sue a vendor who bails mid-contract and blows the LoS ratio.

---

### Article 5 — Confidentiality and Proposal Information
**What it says:** All bid-related information (solicitation number, bid strategy, pricing approach, teammates) is confidential during and after the bid period.

**Why:** Vendors who shop JQ's intel to competitors is a real risk. Standard NDA language here.

---

### Article 6 — Exclusivity (Per-Bid, Not Global)
**What it says:** Vendor is NOT globally exclusive to JQ. However, for any specific solicitation covered by a BSTA, Vendor agrees not to team with any other prime on the same solicitation while the BSTA is active.

**Why:** You cannot realistically demand global exclusivity from small businesses. But per-bid exclusivity is standard and enforceable. This protects JQ from a vendor teaming with a competitor on the same contract.

---

### Article 7 — Termination and Suspension
**What it says:** Either party may terminate the MTA with 30 days written notice. Termination does not affect any in-force BSTA on active bids or contracts.

---

### Article 8 — Flow-Down Clauses
**What it says:** Vendor agrees that any subcontract executed under an awarded Government contract will include mandatory FAR flow-down clauses required by the prime contract.

**Why:** The Government requires primes to flow down certain clauses to subs (e.g., equal opportunity, labor standards, whistleblower protections). FAR Part 44 and the prime contract's clause list will dictate which ones. JQ cannot comply with its prime contract if vendors refuse to accept flow-downs.

---

## TIER 2: Bid-Specific Teaming Addendum (BSTA) — Full Clause Breakdown

This is signed per opportunity, before proposal submission. It activates the MTA for one bid.

### Required fields/sections in every BSTA:

| Field | Why Required |
|---|---|
| Solicitation Number (from SAM.gov) | FAR 9.603 — teaming must be disclosed against a "specified contract" |
| Government Agency | For tracking and disclosure |
| NAICS Code assigned to this solicitation | Determines which LoS threshold applies (services/construction/supplies) |
| Estimated contract value | Determines whether LoS clause even attaches (above/below SAT) |
| Set-aside type | Competitive vs. sole-source (affects LoS applicability trigger) |
| Vendor's scope of work (SOW excerpt) | Defines what "primary and vital requirements" vendor performs (ostensible sub defense) |
| Vendor's workshare % | The LoS math — must be calculated before signing |
| Similarly situated status confirmation | Vendor re-certifies status at bid time |
| Proposal submission deadline | Creates urgency/deadline in the contract |
| Exclusivity period | Vendor cannot team with competitor on this same solicitation |
| Compensation structure | How vendor will be paid if JQ wins (T&M, FFP, percentage of award) |
| Survivability clause | BSTA survives MTA termination for duration of that contract |

---

### BSTA — Key clause: The LoS Certification Backstop
**What it says:** Vendor acknowledges that JQ will certify LoS compliance to the Government based in part on Vendor's committed workshare. If Vendor fails to perform its committed workshare and JQ suffers a False Claims Act exposure or contract termination, Vendor is liable for resulting damages.

**Why:** This is the False Claims Act firewall. JQ's LoS certification to the Government is a legal representation. If the vendor's non-performance makes that certification false, JQ is exposed. This clause gives JQ indemnification rights.

---

## Contract Trigger Timeline (When to Execute What)

```
VENDOR REGISTERS ON PORTAL
         │
         ▼
[TRIGGER 1] → Execute MTA immediately at registration
  - Article 2 (marketing auth) cannot be used without this
  - Target: same session as account creation (DocuSign/e-signature embedded)

         │
         ▼ (Opportunity identified on SAM.gov)

JQ IDENTIFIES MATCHING SOLICITATION
         │
         ▼
[TRIGGER 2] → Compliance triage (your bidding pipeline)
  - Is it above/below SAT? ($350K (current per FAR 2.101))
  - Is it sole-source under 19.8/19.13/19.14/19.15?
  - What contract type? (services / construction / supplies)
  - Is vendor's NAICS code similarly situated for this bid?

         │
         ▼ (Bid decision: GO)

[TRIGGER 3] → Execute BSTA — BEFORE submitting proposal
  - Solicitation number locks in
  - Workshare % calculated and signed
  - Exclusivity period begins
  - Vendor re-certifies similar-situated status

         │
         ▼ (JQ wins award)

[TRIGGER 4] → Execute actual Subcontract Agreement
  - This is distinct from both MTA and BSTA
  - Contains FAR flow-down clauses from the prime contract
  - Contains Payment terms (net 30/45, milestone-based, etc.)
  - References the BSTA workshare commitments
  - Contains the False Claims Act indemnification clause

         │
         ▼ (Contract performance)

[TRIGGER 5] → Maintain LoS tracking throughout performance
  - Track actual payments to vendor vs. total contract value
  - Flag if ratio approaches the LoS limit
  - Document similarly-situated status for any SBA audit
```

---

## The Third Contract Claude Was Referring To: The Subcontract Agreement

When JQ actually wins a contract, the BSTA is not sufficient as a subcontract. You need a formal **Subcontract Agreement** that:

1. **Incorporates FAR flow-down clauses** — the prime contract's clause list tells you which ones are mandatory. Minimum examples:
   - FAR 52.222-26 (Equal Opportunity)
   - FAR 52.222-21 (Prohibition of Segregated Facilities)
   - FAR 52.215-2 (Audit/Records — if cost-reimbursement)
   - FAR 52.203-7 (Anti-Kickback Procedures)

2. **States payment terms compliant with the Prompt Payment Act** — primes must pay subs within 7 days of receiving Government payment (FAR 52.232-27 on construction; best practice for all).

3. **Contains the actual SOW** — more detailed than the BSTA scope stub, derived from the prime contract's PWS/SOW/specifications.

4. **References the prime contract number** — the subcontract is legally subordinate to the prime contract. The sub must perform in a way that allows JQ to perform its prime obligations.

---

## Database Schema Implications

The `vendor_profiles` table and the platform need to support this three-tier structure. Here's what needs to be added beyond what's already in the schema:

### New table: `vendor_teaming_agreements` (already flagged in domain context)
```sql
-- MTA record per vendor
CREATE TABLE vendor_teaming_agreements (
  id SERIAL PRIMARY KEY,
  vendor_user_id INTEGER REFERENCES users(id),
  agreement_type TEXT CHECK (agreement_type IN ('mta', 'bsta', 'subcontract')),
  solicitation_id INTEGER REFERENCES solicitations(id),  -- NULL for MTA
  document_id INTEGER REFERENCES documents(id),          -- signed PDF
  naics_code TEXT,                                        -- for BSTA/subcontract
  workshare_pct NUMERIC(5,2),                            -- for BSTA/subcontract
  similarly_situated_certified BOOLEAN,                   -- vendor's rep at signing
  estimated_value NUMERIC(12,2),                         -- for BSTA
  set_aside_type TEXT,                                   -- for BSTA
  los_applicable BOOLEAN,                                -- computed at BSTA time
  status TEXT CHECK (status IN ('draft', 'pending_signature', 'executed', 'terminated')),
  executed_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### New field in `vendor_profiles`: `mta_executed_at TIMESTAMPTZ`
The portal dashboard can show vendors "MTA not yet signed" as a blocking state before they can receive quote requests.

---

## Priority Order for Drafting

| Priority | Contract | When to Draft | Blocking What |
|---|---|---|---|
| **P0** | Master Teaming Agreement (MTA) | Now — needed before any vendor onboarding completes | Marketing authorization, first bid |
| **P1** | Bid-Specific Teaming Addendum (BSTA) template | Before first live bid | Proposal submission |
| **P2** | Subcontract Agreement template | Before first awarded contract | Contract performance |
| **P3** | Supplemental NDAs for sensitive solicitations | As needed | High-sensitivity bids |

---

## Open Questions for Counsel Review

1. **State law**: Which state's law governs the MTA? (Maryland, Virginia, or federal law principles?)
2. **SBA program status tracking**: How frequently must vendor re-certify similarly-situated status? At each BSTA or annually?
3. **False Claims Act indemnification**: Is the vendor FCA backstop in the BSTA enforceable as drafted, or does counsel need to strengthen it?
4. **Construction-specific**: Does the PM-only construction model need a separate contract variant that explicitly defines JQ's scope as "management, supervision, and oversight only" per the SBA final rule?
5. **Exclusivity enforceability**: Per-bid exclusivity clauses — have counsel confirm enforceability in your target states.
6. **DocuSign/e-signature**: Confirm that e-signature satisfies the writing requirement for teaming agreements in Government contracting context.

