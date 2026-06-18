---
name: credit-report-gauntlet
description: Systematic 7-phase credit report analysis and dispute workflow. Use when the user uploads credit reports and wants to identify violations, generate dispute letters, or prepare for litigation. Trigger phrases: "analyze my credit report," "run the credit gauntlet," "find errors in my credit report," "dispute credit report errors," "prepare credit litigation."
---

# Credit Report Gauntlet — Systematic Dispute Workflow

You are running a systematic, phase-gated analysis of the user's credit reports. Every finding must be provable with documentation — not legal argument. Each phase produces a decision (GREEN = advance, RED = artifact generated, YELLOW = flag for human).

---

## 1. Phase 0: Intake

### Step 0.1 — Document Survey

First, understand what the user has provided:

```
get_case → see documents list
list_documents → identify credit report files (look for names containing "credit," "Experian," "Equifax," "TransUnion," "bureau")
```

If no credit reports found: "I don't see credit reports uploaded yet. Please upload your reports from Experian, Equifax, and TransUnion. You can get free copies at annualcreditreport.com."

### Step 0.2 — Create the Gauntlet State Tracker

Create a markdown workspace item to track progress across sessions:

```
create_workspace_item(
  name="Credit Gauntlet — State Tracker",
  file_type="markdown",
  folder="research",
  content=[{"markdown": "# Credit Report Gauntlet\n\n## Status: Intake\n\nStarted: [today's date]\n\n### Reports\n[list each uploaded report]\n\n### Accounts Identified\nNone yet — pending extraction\n\n### Phase Progress\n- [ ] Phase 0: Intake\n- [ ] Phase 1: Facial Errors\n- [ ] Phase 2: Permissible Purpose Audit\n- [ ] Phase 3: Documentation Gap Analysis\n- [ ] Phase 4: Dispute Sequence\n- [ ] Phase 5: Response Analysis\n- [ ] Phase 6: Escalation\n- [ ] Phase 7: Litigation Preparation"}]
)
```

Save the item ID for updates as you progress.

---

## 2. Phase 1: Facial Errors — Find What's Already Broken

**No mail sent yet.** Scan for violations visible on the face of the reports.

### Step 1.1 — Extract Accounts

For each uploaded credit report document:
```
get_document_structure(document_id) → see sections
get_blocks_in_section(section_id) → read account listings
```

Extract every tradeline with: account name, account number (last 4), furnisher, date opened, balance, status, DOFD, payment history. Create a canonical account list.

Create a json_view table in the workspace:
```
create_workspace_item(
  name="Credit Gauntlet — Accounts",
  file_type="json_view",
  folder="artifacts",
  content={...table with all extracted accounts...}
)
```

### Step 1.2 — Run the Five Scans

For each account, check these scan vectors. EVERY violation gets a RED FLAG entry in the state tracker.

#### Scan A: Cross-Bureau Contradictions

Compare each field across bureaus. If any field contradicts:
- Date of First Delinquency: must match exactly
- Balance: ±2% or ±$50 tolerance
- Account Status: must match exactly
- Payment Status: must match exactly

**Action for each contradiction:** Generate a `json_view` card showing Bureau A value vs. Bureau B value. "Both cannot be correct. At least one bureau is reporting inaccurate information."

#### Scan B: Metro 2 Logical Paradoxes

Check for impossible field combinations:
- "Closed" status + changing balance month-to-month
- "Charged Off" + "Open" account type
- "Paid in Full" + Balance > $0
- "Settled" remarks + Balance > $0
- "Current" payment status + 30/60/90-day lates in history
- "Transferred/Sold" + Balance > $0
- "Included in Bankruptcy" + Balance > $0

**Use `statute_lookup("1681e")`** to verify the furnisher's duty to maintain reasonable procedures. Cite the statute in findings.

#### Scan C: Reporting Period Violations

For each negative tradeline, calculate the fall-off date:
- Collection accounts: DOFD + 7 years + 180 days
- Charge-offs: DOFD + 7 years
- Late payments: Date of late + 7 years
- Chapter 7 bankruptcy: Filing date + 10 years
- Chapter 13 bankruptcy: Filing date + 7 years

**Use `statute_lookup("1681c")`** for the FCRA's reporting period rules. If the reporting period has expired, this is a **strict violation** — the account must be deleted. No accuracy dispute needed.

#### Scan D: Closed Account Still Active

For accounts marked "Closed," "Charged Off," or "Transferred":
- Check if balance changes between sequential reports
- Check if payment status updates
- Check if account status date changes

**Action:** Generate RED FLAG alert. "This account is reporting as closed but showing active behavior. The furnisher is reporting inaccurate information."

#### Scan E: Collection Account FDCPA Flags

For accounts with a third-party collection agency as furnisher, check:
- Is the account marked "Disputed by Consumer" if previously disputed? (FDCPA § 1692e(8))
- Is the debt time-barred under state SOL?
- Has the collection agency sent proper validation notice? (§ 1692g)

**Use `statute_lookup("1692e")` and `statute_lookup("1692g")`** to verify requirements. Cite specific subsections in findings.

### Step 1.3 — Phase 1 Decision

Update the state tracker.

If violations found → **RED.** Generate a summary json_view (cards + table) showing every violation found, organized by account. Each violation card includes: account name, violation type, specific field in error, evidence. Name it "Credit Gauntlet — Phase 1 Findings."

Then either:
- User chooses to proceed to Phase 2 (permissible purpose audit), OR
- User wants to jump to Phase 4 (generate disputes for what we found)

If no violations → **GREEN.** Proceed to Phase 2.

---

## 3. Phase 2: Permissible Purpose Audit

**No dispute needed.** Scan for unauthorized access to the credit file.

### Step 2.1 — Extract Inquiries

From each credit report, extract every inquiry (hard and soft) including: puller name, date, inquiry type, and (if available) permissible purpose code.

### Step 2.2 — Classify Each Inquiry

For each inquiry, classify whether it had a valid permissible purpose:

| Puller Type | Valid If |
|-------------|----------|
| Credit card issuer | User applied for credit |
| Mortgage/auto lender | User applied for loan |
| Employer | User authorized background check |
| Landlord | User applied for housing |
| Current creditor | Account is open/active |
| Collection agency | They own or are assigned the debt |
| Insurance company | User applied for insurance |

**Use `statute_lookup("1681b")`** for the full list of permissible purposes under the FCRA. Cite the specific subsection for each classification.

### Step 2.3 — Detect Invalid Pulls

**RED FLAG triggers:**
- Hard pull user didn't authorize
- Soft pull from collection agency on unrecognized account
- Pull by debt buyer who can't demonstrate chain of title
- Pull on bankruptcy-discharged account
- Pull after account was closed/settled (no existing relationship)

**Each invalid pull is strict liability.** No accuracy dispute needed. No malice standard.

### Step 2.4 — Phase 2 Decision

Generate findings as cards. "X inquiries found. Y appear to lack permissible purpose." Each invalid pull gets a demand letter template citing § 1681b and demanding deletion + statutory damages.

---

## 4. Phase 3: Documentation Gap Analysis

For accounts where NO facial error exists, identify what you can demand.

### Step 3.1 — Map the Gaps

For each negative account, determine what documentation the user has vs. what the furnisher would need:

| Document | Gap Severity |
|----------|-------------|
| Original signed contract | Critical |
| Chain of title (each transfer) | Critical for debt buyers |
| Complete accounting from $0 | High |
| Identity verification | High |
| Payment history | Medium |
| Collection authority/assignment | Critical for collectors |

### Step 3.2 — Select Attack Strategy

Based on gaps identified:
- **No original contract + chain of title gaps** → Provenance Attack. Generate Prove-It letter demanding complete evidentiary chain.
- **No complete accounting** → Balance substantiation attack. Demand itemized accounting from $0.
- **Statute of limitations expired** → SOL kill shot. Demand deletion.
- **Debt buyer (not original creditor)** → They likely can't produce original documents. Debt buyer substantiation attack.

### Step 3.3 — Generate Prove-It Letters

For each account, if gaps exist, generate an HTML letter:

```
create_workspace_item(
  name="Prove-It Letter — [Account Name]",
  file_type="html",
  folder="freestyle",
  content=[{"html": "[formatted letter]"}]
)
```

Use the freestyle-html skill for formatting. The letter must cite § 1681s-2(b) (furnisher duties) and demand the specific documents the furnisher must produce.

---

## 5. Phase 4: The Dispute Sequence

### Step 4.1 — Select Priority Errors

Rank errors by strength:

1. **Expired reporting period** — strict. No debate possible.
2. **Cross-bureau contradiction** — documented by the reports themselves.
3. **Metro 2 logical paradox** — structural impossibility.
4. **Closed account still active** — factual impossibility.
5. **Specific field inaccuracy with documentary proof.**
6. **Documentation gap** — prove-it demand.

### Step 4.2 — Generate Direct Notice Letter (to Furnisher)

For each selected error, generate an HTML letter to the furnisher:

```
create_workspace_item(
  name="Direct Notice — [Furnisher] — [Account]",
  file_type="html",
  folder="freestyle",
  content=[{"html": "[letter]"}]
)
```

Letter must include:
- Furnisher name/address (from credit report)
- Account number
- Specific field in error
- Reported value vs. correct value
- Evidence attached
- Citation of § 1681h(e) malice exception
- 30-day demand
- Statement: "Continued publication after direct notice of inaccuracy constitutes willful violation with actual malice."

### Step 4.3 — Generate CRA Dispute Letters

Simultaneously, generate disputes to all three CRAs:

```
create_workspace_item(
  name="CRA Disputes — [Account]",
  file_type="html",
  folder="freestyle",
  content=[{"html": "[three letters]"}]
)
```

Each must cite § 1681i (reinvestigation requirement) and include the same evidence packet.

### Step 4.4 — Update State Tracker

Record: letter sent date, certified mail tracking, 30-day deadline date.

---

## 6. Phase 5: Response Analysis

When responses arrive (or don't), classify:

| Response | Classification | Next |
|----------|---------------|------|
| No response within 30 days | Violation — failure to investigate | Phase 6 |
| "Verified" — form letter | Violation — rubber-stamp investigation | Phase 6 |
| "Updated" but error remains | Violation — failed to correct | Phase 6 |
| Updated — error corrected | Partial success | Verify on all 3 bureaus |
| Deleted | Success | Move to next account |
| Requests more information | Stall tactic | Send follow-up: "You have sufficient information. Decide within 15 days." |

**Use `statute_lookup("1681s-2")`** to verify the furnisher's duty to investigate. **Use `statute_lookup("1681i")`** for the CRA's reinvestigation duty.

---

## 7. Phase 6: Escalation

Based on response analysis, select the appropriate track:

### Track A: Federal FCRA — Furnisher
- § 1681s-2(b) — failure to investigate
- Willful violation (actual knowledge via direct notice)

### Track B: Federal FCRA — CRAs
- § 1681e(b) — failure to maintain reasonable procedures
- § 1681i — failure to conduct reinvestigation

### Track C: State Defamation with Malice
- Direct notice establishes actual knowledge
- § 1681h(e) malice exception defeats preemption

### Track D: Permissible Purpose
- § 1681b violation — strict liability
- Separate from accuracy dispute

### Track E: Pre-Litigation Settlement
- Notice of Intent to Litigate to registered agent
- Evidence summary + demand + 15-day deadline

### Track F: CFPB/AG Complaint
- File CFPB complaint online
- File state AG complaint
- Reference complaint numbers in correspondence

For each active track, generate the appropriate HTML letter.

---

## 8. Phase 7: Litigation Preparation

### Step 7.1 — Identify Defendants

For each defendant: legal name, registered agent, state of incorporation.

### Step 7.2 — Assemble Complaint

Create a `structured_draft` pleading:
```
create_workspace_item(
  name="Complaint — [Plaintiff] v. [Defendants]",
  file_type="structured_draft",
  document_type="pleading",
  content=[{...blocks...}],
  metadata={...caption...}
)
```

Use the legal-drafting skill. The complaint must include:
- Jurisdictional allegations
- Factual background (pulled from Phase 1/2/5 findings)
- Counts (one per violation, with statutory citations)
- Prayer for relief

### Step 7.3 — Calculate Damages

- FCRA statutory (willful): $100-$1,000 per violation
- FCRA statutory (negligent): actual damages or statutory
- FCRA punitive: multiplier on statutory for willful violations
- State defamation: actual + presumed + punitive
- Attorney's fees: FCRA fee-shifting provision

---

## 9. Key Rules

1. **Cite every statute from the source.** Use `statute_lookup` — never paraphrase FCRA/FDCPA from memory.
2. **Every violation must be provable.** If you can't point to the exact report field or document line, don't flag it.
3. **Update the state tracker after every phase.** The next session must know exactly where things stand.
4. **Generate workspace artifacts for every output.** Letters as HTML (freestyle), findings as json_view (artifacts), complaints as structured_draft (artifacts).
5. **Explain every decision.** When you flag RED, show the user: what field is wrong, what it should be, what evidence proves it, what statute it violates.
6. **Ask before sending.** All letters are drafts. The user reviews, prints, and mails them. Never tell the user "I've sent the letter" — say "I've drafted the letter. Print it and send it certified mail."
7. **No legal conclusions about what "will happen."** Say: "This violates § 1681e(b)" — not "You will win this case." You are an analyst, not a fortune teller.
