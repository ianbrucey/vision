# Credit Report Gauntlet — Technical Outline v1

## Design Principles

- **No novel legal theories.** Every step is grounded in established statutory/regulatory requirements or provable factual contradictions.
- **Facial errors first.** Find what's already broken before setting traps.
- **Objective and verifiable.** Every finding must be provable with documentation — not legal argument.
- **Each step produces a decision.** Green (no violation found) → advance. Red (violation found) → artifact generated. Yellow (insufficient data) → flag for human review.
- **Eventually implementable as a Vision AI workflow.** Structured inputs, structured outputs, decision trees.

---

## Phase 0: Intake — Gather the Raw Materials

### Step 0.1: Pull All Three Bureau Reports

- **Input:** User identity (name, SSN, DOB, current address)
- **Action:** Pull reports from Experian, Equifax, TransUnion (hard copy or via annualcreditreport.com)
- **Output:** Three standardized report objects, normalized to common data model
- **Normalization needed:** Each bureau uses different field names, different date formats, different status codes. Convert to canonical representation before analysis.

### Step 0.2: Gather Account Documentation

- **Input:** User-provided documents
- **Action:** Ingest and classify any supporting documents the user has:

  - Account statements
  - Payment records
  - Settlement letters
  - Bankruptcy discharge orders
  - Court judgments
  - Prior dispute correspondence
  - Prior CRA responses
- **Output:** Indexed document set, classified by type and account association

### Step 0.3: Account Extraction & Matching

- **Input:** Normalized bureau reports
- **Action:** Extract every tradeline and inquiry from each report. Match accounts across bureaus using fuzzy matching on: account number (last 4), furnisher name, account type, date opened, balance range. Assign each account a canonical ID.
- **Output:** Canonical account list with cross-bureau mapping table. Flag unmatched accounts (appear on only 1 or 2 bureaus).

---

## Phase 1: Facial Errors — Find What's Already Broken

No mail sent yet. This phase scans for violations visible on the face of the reports.

### Step 1.1: Cross-Bureau Contradiction Detection (Vector #13)

**Scan:** For each canonical account, compare every data field across all bureaus reporting it.

| Field                       | Tolerance     | Check                                               |

| --------------------------- | ------------- | --------------------------------------------------- |

| Date of First Delinquency   | Exact match   | If Bureau A ≠ Bureau B, at least one is wrong      |

| Date Opened                 | ±30 days     | Wider variance = potential error                    |

| Balance                     | ±2% or ±$50 | Wider variance = potential inaccuracy               |

| Account Status              | Exact match   | "Open" vs. "Closed" vs. "Charged Off" — must agree |

| Payment Status              | Exact match   | "Current" vs. "30 days late" vs. "Collection"       |

| High Balance / Credit Limit | ±5%          | Significant variance = error                        |

| Account Type                | Exact match   | "Individual" vs. "Joint" vs. "Authorized User"      |

| Monthly Payment Amount      | ±$10         | Material variance = reportable                      |

**Red Flag Logic:**

- If any field contradicts across bureaus: generate a **Cross-Bureau Contradiction Alert**
- The alert identifies: account, field, Bureau A value, Bureau B value, date of reports
- Both values cannot be correct. At least one bureau is reporting inaccurate information.

**Artifact Output:** Dispute letter template for the contradiction, addressed to the CRA whose value appears to be the outlier (or to both CRAs if unclear).

---

### Step 1.2: Metro 2 Logical Paradox Detection (Vector #5)

**Scan:** For each tradeline on each bureau, check Metro 2 field combinations for logical impossibility.

| Paradox                | Field A                                            | Field B                                                                             | Why Impossible                             |

| ---------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------ |

| Closed but moving      | Account Status = "Closed"                          | Balance or Amount Past Due changes month-to-month                                   | Closed accounts can't accrue new debt      |

| Charged off AND open   | Status = "Charged Off" (97)                        | Account Type = "Open" (01)                                                          | Mutually exclusive states                  |

| Paid but owing         | Payment Status = "Paid in Full"                    | Balance > $0 | Paid means $0 balance                                                |                                            |

| Settled but owing      | Remarks = "Settled"                                | Balance > $0                                                                        | Settlement means agreed zero               |

| Current but delinquent | Payment Status = "Current"                         | Payment History shows 30/60/90-day lates                                            | Contradiction in payment string            |

| DOFD inconsistency     | Date of First Delinquency provided                 | Payment History profile shows delinquency starting earlier                          | The DOFD doesn't match the payment pattern |

| Transferred and active | Status = "Transferred/Sold"                        | Balance > $0 AND Status Date is recent | Transferred account should show $0 balance |                                            |

| Discharged but owing   | Remarks = "Included in Bankruptcy" or "Discharged" | Balance > $0                                                                        | Discharge extinguishes the obligation      |

**Red Flag Logic:**

- If any paradox detected: generate a **Metro 2 Paradox Alert**
- These are structural errors in the data format itself

**Artifact Output:** One-sentence dispute letter citing the specific Metro 2 contradiction.

---

### Step 1.3: Reporting Period Violation Detection

**Scan:** For each negative tradeline, check the FCRA's 7-year reporting window.

| Check               | Calculation                                          | Rule                                 |

| ------------------- | ---------------------------------------------------- | ------------------------------------ |

| Collection accounts | Date of First Delinquency + 7 years + 180 days       | Must fall off by this date           |

| Charge-offs         | DOFD + 7 years                                       | Must fall off by this date           |

| Late payments       | Date of Late + 7 years                               | Individual lates fall off at 7 years |

| Bankruptcy (Ch. 7)  | Filing Date + 10 years                               | Chapter 7 reports for 10 years       |

| Bankruptcy (Ch. 13) | Filing Date + 7 years                                | Chapter 13 reports for 7 years       |

| Civil judgments     | Filing Date + 7 years (or SOL)                       | Most judgments: 7 years              |

| Tax liens           | Release Date + 7 years (paid); indefinitely (unpaid) | Complex rules                        |

**Red Flag Logic:**

- If the reporting period has expired: generate an **Expired Reporting Period Alert**
- This is a strict violation — no dispute about accuracy needed. The account must be deleted.

**Artifact Output:** Demand letter citing the expired reporting period with the calculation shown.

---

### Step 1.4: "Closed Account Still Active" Detection (Vector #14)

**Scan:** For each negative account marked "Closed," "Charged Off," or "Transferred":

- Compare sequential reports (if user has pulled reports at different times)
- Check if: Balance changed between reports, Amount Past Due changed, Payment Status changed from prior month, Account Status date updated

**Red Flag Logic:**

- If a closed/charged-off account shows any movement: generate a **Closed Account Active Alert**

---

### Step 1.5: FDCPA / Statutory Violation Flags (If Collection Account)

**Scan:** For accounts where the furnisher is a third-party collection agency:

| Check                                                                | Rule                                         |

| -------------------------------------------------------------------- | -------------------------------------------- |

| Is the account marked "Disputed by Consumer" if previously disputed? | Collection agencies must report disputes     |

| Is the debt time-barred under state SOL?                             | Reporting time-barred debt may be actionable |

| Does the furnisher have a valid state collection license?            | Some states require licensing                |

| Has the collection agency sent proper validation notice?             | FDCPA § 1692g                               |

**Red Flag Logic:**

- Generate appropriate alert based on violation type

---

### Phase 1 Decision Point

```

┌─────────────────────────────────────┐

│   Any facial errors found?          │

├─────────────────────────────────────┤

│                                     │

│  YES (≥1 Red Flag)                  │

│    ├── Multiple errors on same      │

│    │   account → Compound Dispute   │

│    │                                │

│    ├── Single error →               │

│    │   Direct Dispute               │

│    │                                │

│    └── Proceed to Phase 2           │

│        (Permissible Purpose Audit)  │

│                                     │

│  NO (Clean on face)                 │

│    └── Proceed to Phase 3           │

│        (Documentation Gap Analysis) │

│                                     │

└─────────────────────────────────────┘

```

---

## Phase 2: Permissible Purpose Audit (Vector #32)

No dispute needed. This scans for unauthorized access to your credit file.

### Step 2.1: Inquiry Audit

**Scan:** Extract every inquiry (hard and soft) from all three bureau reports.

### Step 2.2: Permissible Purpose Classification

For each inquiry, classify the puller and the likely permissible purpose:

| Puller Type        | Permissible Purpose      | Valid If                          |

| ------------------ | ------------------------ | --------------------------------- |

| Credit card issuer | Application review       | You applied                       |

| Mortgage lender    | Application review       | You applied                       |

| Auto lender        | Application review       | You applied                       |

| Employer           | Employment screening     | You authorized background check   |

| Landlord           | Rental application       | You applied for housing           |

| Current creditor   | Account review           | Account is open/active            |

| Collection agency  | Collection of an account | They own or are assigned the debt |

| Insurance company  | Underwriting             | You applied for insurance         |

| Debt buyer         | Account review           | They own the debt                 |

### Step 2.3: Invalid Pull Detection

**Red Flag triggers:**

- Soft pull from a collection agency on an account you don't recognize
- Soft pull from a creditor on a charged-off, settled, or closed account (no existing relationship)
- Hard pull you didn't authorize
- Pull by a debt buyer who can't demonstrate they own the debt
- Pull on a bankruptcy-discharged account

**Red Flag Logic:**

- If any pull lacks a permissible purpose: generate **Permissible Purpose Violation Alert**
- Strict liability. No accuracy dispute needed. No malice standard. No preemption fight.

**Artifact Output:** Demand letter citing § 1681b and demanding deletion of the inquiry and statutory damages.

---

## Phase 3: Documentation Gap Analysis

This identifies what you can demand from the furnisher to attack the underlying obligation.

### Step 3.1: Gap Identification

For each negative account, map what documentation the user has vs. what the furnisher would need to produce to substantiate the account:

| Document                             | User Has | Furnisher Has? | Gap Severity             |

| ------------------------------------ | -------- | -------------- | ------------------------ |

| Original signed contract             | Y/N      | Unknown        | Critical                 |

| Chain of title (each transfer)       | Y/N      | Unknown        | Critical for debt buyers |

| Complete accounting ($0 to current)  | Y/N      | Unknown        | High                     |

| Identity verification (is this you?) | Y/N      | Unknown        | High                     |

| Payment history                      | Y/N      | Unknown        | Medium                   |

| Account terms / agreement            | Y/N      | Unknown        | Medium                   |

| Collection authority / assignment    | Y/N      | Unknown        | Critical for collectors  |

| State licensing                      | Y/N      | Unknown        | Medium                   |

### Step 3.2: Gap-Based Strategy Selection

```

If "Original signed contract" = NO and "Chain of title" includes transfers:

  → Provenance Attack is viable (Vector #33)

  → Generate "Prove-It" letter demanding complete evidentiary chain


If "Complete accounting" = NO:

  → Balance substantiation attack

  → Demand itemized accounting from $0


If statute of limitations has run (debt is 4+ years old on open account):

  → SOL kill shot

  → Demand deletion based on time-barred obligation


If account is with a debt buyer (not original creditor):

  → Debt buyer substantiation attack (Vector #10)

  → They likely can't produce original documents

```

**Artifact Output:** Customized "Prove-It" letter based on identified gaps.

---

## Phase 4: The Dispute Sequence — Set the Trap

### Step 4.1: Select the Error

If Phase 1 found facial errors: select the strongest, most "objectively and readily verifiable" error. Priority:

1. Expired reporting period (strict — no debate possible)
2. Cross-bureau contradiction (documented by reports themselves)
3. Metro 2 logical paradox (structural impossibility)
4. Closed account still active (factual impossibility)
5. Specific field inaccuracy with documentary proof

If no facial errors found: select the documentation gap that has the best chance of producing a failure-to-substantiate.

### Step 4.2: Generate Evidence Packet

Compile the evidence that proves the error:

- Cross-bureau contradiction: both reports side by side
- Metro 2 paradox: the report itself showing the contradiction
- Balance error: account statement showing correct balance
- Expired reporting period: calculation showing DOFD + 7 years
- Documentation gap: the prove-it demand letter

### Step 4.3: Generate Direct Notice Letter (to Furnisher)

Template parameters:

- Furnisher name and address (from report or registered agent lookup)
- Account number
- Specific field in error
- Reported value
- Correct value
- Evidence attached
- Citation of § 1681h(e) malice exception
- 30-day demand
- Statement that continued publication after notice = malice

**Output:** Populated notice letter, ready to print/send

### Step 4.4: Generate CRA Dispute (Simultaneous)

Same evidence packet, addressed to Equifax, Experian, TransUnion dispute addresses.

Template parameters:

- CRA name and dispute address
- Account identification
- Specific error
- Evidence attached
- Demand for reinvestigation under § 1681i

**Output:** Three populated dispute letters, ready to print/send

### Step 4.5: Dispatch Tracking

**Input:** Send date (certified mail, return receipt)

**Tracking:**

- Date mailed
- Date received (return receipt)
- 30-day clock starts: date of receipt

---

## Phase 5: Response Analysis

### Step 5.1: Response Classification

When the response arrives (or doesn't), classify:

| Response Type                            | Classification                                           | Next Action                                                                  |

| ---------------------------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------- |

| No response within 30 days               | **Violation** — failure to investigate            | Phase 6: Litigation Track                                                    |

| Form letter: "Verified"                  | **Violation** — rubber-stamp investigation        | Phase 6: Litigation Track                                                    |

| Form letter: "Updated" but error remains | **Violation** — failed to correct                 | Phase 6: Litigation Track                                                    |

| Updated — error corrected               | **Partial Success** — but confirm                 | Re-check reports; if fixed, move to next account                             |

| Deleted                                  | **Success** — tradeline removed                   | Verify on all three bureaus; move to next account                            |

| Request for more information             | **Stall Tactic** — they have the evidence already | Send follow-up: "You have sufficient information. Decide." + 15-day deadline |

### Step 5.2: Verify Across Bureaus

If they claim to have corrected or deleted, pull fresh reports and verify.

### Step 5.3: Document the Failure

If they verified or failed to respond, build the case file:

| Element              | Evidence                                                 |

| -------------------- | -------------------------------------------------------- |

| The original error   | Phase 1 findings + evidence                              |

| The dispute sent     | Copy of letter + certified mail receipt + return receipt |

| The dispute received | Return receipt showing date of delivery                  |

| The response         | Their response letter (or lack thereof)                  |

| The error persists   | Fresh bureau report showing the same error               |

This packet IS your complaint exhibits.

---

## Phase 6: Escalation Decision Tree

### Track A: Federal FCRA Litigation (Furnisher)

**Conditions:** CRA dispute was filed, furnisher verified or failed to respond

**Counts:**

- § 1681s-2(b) — failure to conduct reasonable investigation
- Willful violation (actual knowledge via direct notice)

### Track B: Federal FCRA Litigation (CRAs)

**Conditions:** CRA dispute was filed, CRA failed to conduct independent reinvestigation

**Counts:**

- § 1681e(b) — failure to maintain reasonable procedures
- § 1681i — failure to conduct reasonable reinvestigation

### Track C: State Defamation with Malice

**Conditions:** Direct notice letter was sent, furnisher continued reporting

**Counts:**

- Defamation with malice (actual knowledge established by notice letter)
- Preemption defeated by malice exception under § 1681h(e)

### Track D: Permissible Purpose

**Conditions:** Unauthorized credit report pull detected

**Counts:**

- § 1681b violation — strict liability
- Separate from accuracy dispute

### Track E: Pre-Litigation Settlement Lever

**Conditions:** Violations exist but you want to try settlement before filing

**Actions:**

1. Send Notice of Intent to Litigate to Registered Agent
2. Include: statement of violations, evidence summary, demand (deletion + statutory damages), 15-day deadline
3. If no response → file

### Track F: CFPB/AG Complaint

**Conditions:** Filing simultaneously with litigation (or as standalone if violations are regulatory in nature)

**Actions:**

- File CFPB complaint online
- File Georgia AG complaint
- Reference complaint numbers in litigation correspondence

---

## Phase 7: Litigation Preparation

### Step 7.1: Defendant Identification

| Defendant   | Identity                                             | Role                   |

| ----------- | ---------------------------------------------------- | ---------------------- |

| Furnisher 1 | Legal name, registered agent, state of incorporation | Primary: § 1681s-2(b) |

| Equifax     | Registered agent in Georgia                          | CRA defendant          |

| Experian    | Registered agent in Georgia                          | CRA defendant          |

| TransUnion  | Registered agent in Georgia                          | CRA defendant          |

### Step 7.2: Complaint Assembly

Auto-populate complaint template with:

- Case-specific facts (pulled from Phase 1 findings)
- Counts (selected from Phase 6 tracks)
- Exhibits (Phase 5 documentation packet)

### Step 7.3: Damages Calculation

| Source                     | Basis                        | Amount                      |

| -------------------------- | ---------------------------- | --------------------------- |

| FCRA statutory (willful)   | Per violation                | $100-$1,000                 |

| FCRA statutory (negligent) | Per violation                | Actual damages or statutory |

| FCRA punitive              | Willful                      | Multiplier on statutory     |

| State defamation           | Actual + presumed + punitive | Fact-dependent              |

| Attorney's fees            | FCRA fee-shifting            | Lodestar                    |

---

## Gauntlet Flow Summary

```

PHASE 0: INTAKE

  └── Pull reports → Normalize → Extract accounts


PHASE 1: FACIAL ERRORS (no mail yet)

  ├── 1.1 Cross-bureau contradictions

  ├── 1.2 Metro 2 paradoxes

  ├── 1.3 Expired reporting periods

  ├── 1.4 Closed account still active

  └── 1.5 FDCPA/statutory flags


PHASE 2: PERMISSIBLE PURPOSE AUDIT (strict liability)

  └── 2.1-2.3 Inquiry scan → unauthorized pull detection


PHASE 3: DOCUMENTATION GAP ANALYSIS

  └── 3.1-3.2 Gap identification → Prove-It letter generation


PHASE 4: DISPUTE SEQUENCE (send mail)

  ├── 4.1 Select strongest error

  ├── 4.2 Compile evidence packet

  ├── 4.3 Generate Direct Notice (furnisher)

  ├── 4.4 Generate CRA Dispute (all 3 bureaus)

  └── 4.5 Track dispatch and receipt


PHASE 5: RESPONSE ANALYSIS

  ├── 5.1 Classify response

  ├── 5.2 Verify across bureaus

  └── 5.3 Document the failure


PHASE 6: ESCALATION

  ├── Track A: Federal FCRA (furnisher)

  ├── Track B: Federal FCRA (CRAs)

  ├── Track C: State defamation

  ├── Track D: Permissible purpose

  ├── Track E: Pre-litigation settlement

  └── Track F: CFPB/AG complaint


PHASE 7: LITIGATION PREP

  ├── 7.1 Identify defendants

  ├── 7.2 Assemble complaint

  └── 7.3 Calculate damages

```

---

## Implementation Notes for Vision AI

### What's Deterministic vs. AI-Required

**Deterministic (rules-based):**

- Cross-bureau field comparison (exact match or numeric tolerance)
- Metro 2 paradox detection (boolean logic on field combinations)
- Reporting period calculation (date math)
- SOL calculation (date math + state rules lookup)
- Inquiry classification by puller type
- Response classification by keywords ("verified", "updated", "deleted")

**AI-Assisted (LLM required):**

- Account matching across bureaus (fuzzy matching, conflicting data resolution)
- Document classification and evidence extraction
- Letter generation (template population with case-specific language)
- Gap severity assessment
- Error prioritization
- Complaint paragraph drafting

### Data Model Sketch

```

Account {

  canonical_id: UUID

  furnisher_name: string

  furnisher_type: enum[original_creditor, debt_buyer, collection_agency]

  account_type: enum[credit_card, auto_loan, mortgage, medical, utility, etc.]

  

  // Fields normalized across bureaus

  fields: {

    date_opened: { experian: date, equifax: date, transunion: date }

    date_of_first_delinquency: { ... }

    balance: { ... }

    account_status: { ... }

    payment_status: { ... }

    // ... all reportable fields

  }

  

  // Scan results

  phase1_results: {

    cross_bureau_contradictions: [Contradiction]

    metro2_paradoxes: [Paradox]

    reporting_period_expired: bool

    closed_account_active: bool

    // ...

  }

  

  phase2_results: {

    unauthorized_pulls: [Inquiry]

  }

  

  phase3_results: {

    documentation_gaps: [Gap]

    prove_it_letter_generated: bool

    prove_it_letter_sent: date | null

    prove_it_response: enum[pending, partial, none, full] | null

  }

  

  phase4_results: {

    selected_error: Error

    evidence_packet: [Document]

    direct_notice_sent: date | null

    direct_notice_received: date | null

    cra_dispute_sent: { experian: date, equifax: date, transunion: date }

    response_deadline: date | null

  }

  

  phase5_results: {

    response_received: bool

    response_type: enum[verified, updated, deleted, no_response, stall]

    verification_date: date | null

    fresh_report_pulled: bool

    error_persists: bool | null

  }

  

  phase6_escalation: {

    tracks_active: [enum[A, B, C, D, E, F]]

    lawsuit_filed: bool

    // ...

  }

}


Violation {

  violation_id: UUID

  account_id: UUID (FK)

  violation_type: enum[cross_bureau, metro2_paradox, reporting_period, etc.]

  severity: enum[tier1_irrefutable, tier2_strong, tier3_good]

  evidence: [Document]

  artifact_generated: bool

  artifact_type: enum[dispute_letter, demand_letter, prove_it_letter, litigation_notice]

}


Timeline {

  account_id: UUID (FK)

  events: [

    { date, event_type, description }

  ]

  next_deadline: date | null

  days_until_filing: int | null

}

```
