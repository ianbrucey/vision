# Vendor Contract Logic Guide
### Implementation Reference for the Vision Platform
> Last Updated: 2026-08-12 | NOT LEGAL ADVICE — have counsel review before live use.

This document translates the legal framework from our FAR research sessions into concrete conditional logic for the Vision platform. Every decision tree below maps directly to a FAR citation or SBA regulation.

---

## The Three-Contract Stack

| # | File | Trigger | One-Time or Per-Event |
|---|---|---|---|
| 1 | `01-master-teaming-agreement.md` | Vendor registration | One-time, evergreen |
| 2 | `02-bid-specific-teaming-addendum.md` | Before each formal offer submission | Per solicitation |
| 3 | `03-subcontract-agreement.md` | After each prime contract award | Per award |

**Why you cannot collapse these into one document:** FAR 9.601 defines contractor team arrangements as being tied to "a specified Government contract or acquisition program." The Government (per FAR 9.603) only recognizes teaming relationships that are disclosed against a specific bid. A single sign-once agreement cannot substitute for per-bid disclosure.

---

## Contract 1: Master Teaming Agreement (MTA)

### When to Trigger
```
Vendor completes registration form → MTA is presented for e-signature → 
Vendor cannot receive quote requests until MTA is executed.
```

### Database Field
`vendor_profiles.mta_executed_at TIMESTAMPTZ` — NULL = not yet signed; populated timestamp = active MTA.

### Portal Blocking Logic
```
IF vendor_profiles.mta_executed_at IS NULL:
    → Block vendor from receiving quote requests
    → Show banner: "Please sign your Master Teaming Agreement to activate your account."
    → Present MTA for e-signature in portal
ELSE:
    → Vendor is eligible to receive quote requests
```

### Data the MTA Locks In (Captured at Registration)
From `vendor_profiles`:
- `business_name` — used in MTA party block
- `uei`, `cage_code`, `tax_id` — federal identifiers
- `naics_codes[]` — the NAICS codes Vendor authorizes JQ to market
- `certifications[]` — small business program status at time of signing
- `bonding_capacity` — for construction vendors

### Key Legal Point
The MTA's Article 2 (marketing authorization) is the written permission that makes it **legal** for JQ to put a vendor's past performance and capabilities into a proposal. Without it, using a vendor's experience in a proposal is misrepresentation. With it, JQ is a legitimate prime intermediary.

---

## Contract 2: Bid-Specific Teaming Addendum (BSTA)

### When to Trigger: The Decision Tree

```
JQ identifies an opportunity on SAM.gov
                │
                ▼
    What is the solicitation type?
                │
    ┌───────────┼───────────────────┬──────────────────┐
    │           │                   │                  │
  Sources    RFI               RFQ                 RFP / IFB
  Sought      │                   │                  │
    │          │                   │                  │
    ▼          ▼                   ▼                  ▼
NO BSTA    NO BSTA           Is value > SAT?      BSTA REQUIRED
(not a     (not a           ($350K threshold)    before submission
 solicitation) solicitation)      │
                          ┌───────┴───────┐
                          │               │
                        YES              NO
                          │               │
                          ▼               ▼
                    BSTA strongly    No BSTA required,
                    recommended      but note vendor used
                    before           in opportunity_vendors
                    submission       tracking table
```

**FAR citations:**
- Sources Sought / RFI: FAR 15.201(e) — "responses are not offers and cannot be accepted by the Government to form a binding contract"
- RFQ quotations: FAR 2.101 — "responses to requests for quotations are 'quotations,' not offers"
- RFP/IFB: FAR 9.603 — teaming must be "fully disclosed in an offer"
- SAT threshold: FAR 2.101 (verify current figure — was $350,000 as of mid-2026 (confirmed by user))

### BSTA Fields to Capture in Database (`vendor_teaming_agreements`)

```sql
agreement_type = 'bsta'
solicitation_id         → FK to solicitations table
vendor_user_id          → FK to users table (vendor role)
naics_code              → NAICS assigned by agency to this solicitation
set_aside_type          → 'sb' | 'wosb' | 'sdvosb' | 'hubzone' | '8a' | 'other'
estimated_value         → dollar amount
contract_type           → 'services' | 'supplies' | 'gen_construction' | 'specialty_construction'
los_applicable          → BOOLEAN (computed — see LoS logic below)
workshare_pct           → NUMERIC — vendor's % of total estimated contract value
similarly_situated      → BOOLEAN (computed — see similarly situated logic below)
similarly_situated_cert → BOOLEAN — vendor's re-certification at BSTA time
status                  → 'draft' | 'pending_signature' | 'executed' | 'terminated'
executed_at             → TIMESTAMPTZ
```

### LoS Applicability Logic (Whether to Run the Math)
```
IF (estimated_value > CURRENT_SAT):         -- currently $350,000
    los_applicable = TRUE
ELSE IF set_aside_type IN ('8a', 'wosb', 'sdvosb', 'hubzone')
     AND award_mechanism = 'sole_source':   -- sole-source under FAR 19.8/19.13/19.14/19.15
    los_applicable = TRUE
ELSE:
    los_applicable = FALSE                  -- competitive set-aside below SAT: LoS does not attach
```

**FAR citation:** FAR 19.507(e) — "if any portion of the requirement is to be set aside for small business and the contract amount is expected to exceed the simplified acquisition threshold... [LoS clause is inserted]"

### LoS Threshold Logic (The Math, Run Only When `los_applicable = TRUE`)
```
SWITCH contract_type:
    CASE 'services':
        required_self_performance_pct = 50.0   -- prime must retain ≥50% of amount paid
    CASE 'supplies':
        required_self_performance_pct = 50.0   -- excl. cost of materials
    CASE 'gen_construction':
        required_self_performance_pct = 15.0   -- excl. cost of materials
    CASE 'specialty_construction':
        required_self_performance_pct = 25.0   -- excl. cost of materials

jq_direct_cost = [JQ self-performed labor cost]
similarly_situated_sub_costs = SUM(workshare_pct * estimated_value
                                   FOR EACH vendor WHERE similarly_situated = TRUE
                                   ON this solicitation)
total_qualifying_cost = jq_direct_cost + similarly_situated_sub_costs
qualifying_pct = total_qualifying_cost / estimated_value * 100

IF qualifying_pct >= required_self_performance_pct:
    los_check = PASS
ELSE:
    los_check = FAIL → block bid submission, flag for restructuring
```

**Note on construction:** JQ's PM-only model on general construction means `jq_direct_cost` is JQ's management/supervision/oversight fee only. This will rarely clear 15% alone — the similarly situated sub cost aggregation carries the load. Per a 2023 SBA final rule, PM/supervision IS the "primary and vital requirement" for general construction, which satisfies the ostensible subcontractor prong — but the 15% LoS percentage is a separate cost-math test.

### Similarly Situated Logic (Per Bid, Per Vendor)
```
FUNCTION is_similarly_situated(vendor, solicitation):

    -- Step 1: Does vendor's status match the set-aside?
    SWITCH solicitation.set_aside_type:
        CASE 'sb':          -- plain small business set-aside
            program_match = vendor.is_small_business  
            -- ANY small business qualifies, regardless of socioeconomic status
            -- (FAR 52.219-14(b)(1): "any small business concern, without regard 
            --  to its socioeconomic status")
            -- WOSB, SDVOSB, HUBZone, 8(a) all qualify here ✓
        CASE 'wosb':
            program_match = vendor.is_wosb_certified
        CASE 'sdvosb':
            program_match = vendor.is_sdvosb_certified
        CASE 'hubzone':
            program_match = vendor.is_hubzone_certified
        CASE '8a':
            program_match = vendor.is_8a_certified

    -- Step 2: Is vendor small under the subcontract NAICS?
    naics_size_match = vendor_is_small_under_naics(vendor, solicitation.naics_code)

    RETURN program_match AND naics_size_match
```

**FAR citation (exact text from FAR 52.219-14(b)):**
> "Similarly situated entity means a first-tier subcontractor that: (1) Has the same small business program status as that which qualified the prime contractor for the award (e.g., for a small business set-aside contract, **any small business concern, without regard to its socioeconomic status**); and (2) Is considered small for the size standard under the NAICS code the prime contractor assigned to the subcontract."

---

## Contract 3: Subcontract Agreement

### When to Trigger
```
Government issues award to JQ (prime contract number assigned)
                │
                ▼
    System creates subcontract record for each vendor 
    identified in the executed BSTA for this solicitation
                │
                ▼
    Prefill from BSTA: vendor info, scope, workshare %, 
    NAICS, set-aside type, LoS applicability
                │
                ▼
    Admin reviews, adds:
    - Actual prime contract number
    - Period of performance dates
    - Final SOW (from prime contract's PWS)
    - Final rate schedule
    - Flow-down clause list from prime contract
                │
                ▼
    Presented to vendor for e-signature via portal
```

### Database Field
`agreement_type = 'subcontract'` in `vendor_teaming_agreements`, with `solicitation_id` linking to the awarded contract.

### Conditional Article 5 (LoS) in the Subcontract
```
IF bsta.los_applicable = TRUE:
    → Include Article 5 (LoS Compliance) in subcontract
    → Include FCA backstop clause (Article 5.4)
    → Include LoS reporting obligation (Article 5.3)
ELSE:
    → Replace Article 5 with: "Article 5 — Reserved (LoS clause not applicable to this contract)"
```

### Flow-Down Clause Logic
The subcontract's flow-down clause table (Article 6) should be dynamic:

```
ALWAYS include:
    FAR 52.222-26 (Equal Opportunity)
    FAR 52.222-21 (Prohibition of Segregated Facilities)
    FAR 52.203-7 (Anti-Kickback Procedures)

CONDITIONALLY include:
    FAR 52.219-14   IF los_applicable = TRUE
    FAR 52.215-2    IF prime contract is cost-reimbursement
    FAR 52.222-41   IF contract is subject to Service Contract Labor Standards
    FAR 52.204-21   IF vendor will handle federal information systems or data

ALWAYS:
    Attach prime contract clause list and require vendor acknowledgment
```

---

## Solicitation Type Reference (What Contract Logic to Apply)

| Solicitation Type | Definition | Award Possible? | BSTA Required? | LoS Math? |
|---|---|---|---|---|
| **Sources Sought Notice** | Market research only; no solicitation | No | ❌ No | ❌ No |
| **RFI (Request for Information)** | Information/planning only; FAR 15.201(e): "responses not offers" | No | ❌ No | ❌ No |
| **RFQ below SAT** | Simplified acquisition; response is a "quotation, not offer" (FAR 2.101) | Yes (via PO) | ⚠️ Not legally required, track vendor used | ❌ No |
| **RFQ above SAT** | Simplified acquisition, higher value | Yes | ✅ Best practice before submission | ✅ If LoS attaches |
| **RFP (Request for Proposals)** | Negotiated acquisition; response IS an offer | Yes | ✅ Required before submission | ✅ If LoS attaches |
| **IFB (Invitation for Bids)** | Sealed bidding; response IS a bid/offer | Yes | ✅ Required before submission | ✅ If LoS attaches |

---

## Vendor Profile Fields Required by This Framework

The following fields must be present in `vendor_profiles` for the contract logic to function. Fields marked with * are required for similarly situated computation.

| Field | Purpose |
|---|---|
| `business_name` | Used in all contract party blocks |
| `uei` | Required in all federal contracting documents |
| `cage_code` | Required in all federal contracting documents |
| `tax_id` | Required for subcontract payment |
| `naics_codes[]` * | NAICS codes vendor is small under — compared against solicitation NAICS |
| `vendor_type` | Determines which profile fields are relevant |
| `is_small_business` * | Self-certification; used in similarly situated check |
| `sb_program_status[]` * | Array: ['wosb', 'sdvosb', 'hubzone', '8a', 'sb'] — for per-set-aside matching |
| `certifications_expiry{}` | Track expiration of socioeconomic certs — stale cert = broken warranty |
| `bonding_capacity` | Needed for construction subcontracts |
| `mta_executed_at` | Blocks quote requests until MTA is signed |
| `sam_registration_active` | Boolean + expiry — SAM must be active at bid time |
| `sam_expiry_date` | Alert 60 days before expiry |

---

## Alert / Notification Logic

| Condition | Action |
|---|---|
| `mta_executed_at IS NULL` | Block vendor from receiving quote requests; show signing prompt |
| `sam_expiry_date < NOW() + 60 days` | Alert admin: vendor's SAM registration expiring soon |
| `certification expires within 90 days` | Alert admin and vendor: cert expiry approaching |
| `los_check = FAIL` on BSTA | Block bid submission; flag for scope restructuring |
| `similarly_situated = FALSE` for all vendors on a solicitation | Alert admin: JQ may not meet LoS threshold even with full vendor workshare |
| `bsta.executed_at IS NULL` AND solicitation type = 'rfp' | Block proposal submission from system |

---

## Future Schema: `vendor_teaming_agreements` Table

```sql
CREATE TABLE vendor_teaming_agreements (
    id                          SERIAL PRIMARY KEY,
    agreement_type              TEXT NOT NULL CHECK (agreement_type IN ('mta', 'bsta', 'subcontract')),
    vendor_user_id              INTEGER NOT NULL REFERENCES users(id),
    solicitation_id             INTEGER REFERENCES solicitations(id),  -- NULL for MTA
    document_id                 INTEGER REFERENCES documents(id),       -- signed PDF storage
    
    -- BSTA / Subcontract fields
    naics_code                  TEXT,
    set_aside_type              TEXT CHECK (set_aside_type IN ('sb', 'wosb', 'sdvosb', 'hubzone', '8a', 'other')),
    contract_type               TEXT CHECK (contract_type IN ('services', 'supplies', 'gen_construction', 'specialty_construction')),
    estimated_value             NUMERIC(14,2),
    workshare_pct               NUMERIC(5,2),
    
    -- Computed compliance fields
    los_applicable              BOOLEAN,
    los_check_passed            BOOLEAN,
    similarly_situated          BOOLEAN,
    similarly_situated_cert     BOOLEAN,  -- vendor's re-certification at signing
    
    -- Status tracking
    status                      TEXT NOT NULL DEFAULT 'draft'
                                CHECK (status IN ('draft', 'pending_signature', 'executed', 'terminated')),
    executed_at                 TIMESTAMPTZ,
    expires_at                  TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_vta_vendor ON vendor_teaming_agreements(vendor_user_id);
CREATE INDEX idx_vta_solicitation ON vendor_teaming_agreements(solicitation_id);
CREATE INDEX idx_vta_type_status ON vendor_teaming_agreements(agreement_type, status);
```

---

## Open Items for Counsel Review

Before implementing the e-signature flow and going live, the following must be reviewed by an attorney:

1. **False Claims Act indemnification clause (MTA Art. 4.3 / Subcontract Art. 5.4)** — confirm enforceability and language adequacy. FCA exposure is the highest-stakes risk in this model.
2. **State law governing the MTA** — Georgia was chosen as the governing law. Confirm this is appropriate and that Georgia courts will enforce the arbitration clause.
3. **E-signature validity** — confirm that DocuSign/electronic signatures satisfy the "writing" requirement for teaming agreements in the government contracting context.
4. **Per-bid exclusivity enforceability** — have counsel confirm Section 6.2 of the MTA (per-solicitation exclusivity) is enforceable in Georgia.
5. **WOSB/socioeconomic status tracking** — confirm the platform's reliance on vendor self-certification of program status is legally adequate, or whether third-party certification verification is required.
6. **SBA size recertification timing** — confirm how often vendor must re-certify size status, particularly for long-duration contracts with option periods.
7. **Construction PM-only model** — if JQ pursues general construction set-asides with a PM-only role, have counsel confirm the 2023 SBA final rule language adequately supports this structure for your specific target agencies.
