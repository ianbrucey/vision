---
name: sources-sought-response
description: >
  Analyze a federal Sources Sought Notice (SSN), Request for Information (RFI), or similar
  market research notice and produce a polished, factually-grounded response for Justice Quest LLC.
  Use when the user provides a solicitation notice and wants to draft a capability statement or
  response letter. Also triggers for: "respond to this SSN", "draft a sources sought response",
  "analyze this RFI", "write up our capabilities for this notice", or "can we respond to this?"
---

# Sources Sought Response Skill

Transform a federal SSN or RFI into a polished, compliance-ready response for Justice Quest LLC — fast, at scale, without inventing experience.

---

## ██ THE IRON RULE (Read This First — It Is Inviolable)

> **You are forbidden from claiming experience that does not appear in the resource files below.**
>
> - Every factual claim about past performance MUST trace directly to `resources/past-performance.md`.
> - Every personnel credential MUST trace to a file in `resources/personnel/`.
> - Every company identifier (UEI, CAGE, NAICS) MUST come from `resources/company-profile.md`.
> - If a capability is within reach but not yet performed for a government client, it MUST be labeled as a **"Proposed Approach"** — not past performance.
> - If a capability is outside current experience, disclose the gap using the Gap Registry in `past-performance.md`. **Never paper over a gap with vague language.**
>
> **Violation of the Iron Rule is a protocol failure. The response must be rebuilt.**

---

## Resource Files (Load Before Drafting)

All resources are in the skill's `resources/` directory:

| File | Purpose |
|---|---|
| `resources/company-profile.md` | All company identifiers, contacts, NAICS, business type, certifications status |
| `resources/capability-map.md` | Every capability with confidence level, evidence sources, and match keywords |
| `resources/past-performance.md` | Authoritative project registry with response-ready summaries and gap disclosures |
| `resources/personnel/ian-bruce.md` | Ian Bruce's full professional background and credential index |
| `resources/personnel/xavier-monroe.md` | Xavier Monroe's IT/cybersecurity background |

**Templates:**
| File | Purpose |
|---|---|
| `templates/ssn-response-letter.md` | Full response letter (multi-section, multi-page) |
| `templates/capability-statement.md` | One-page capability statement |

**Reference Example:**
| File | Purpose |
|---|---|
| `examples/discos-ma-idiq-response.md` | Annotated DISCOS response — the gold standard for tone and disclosure approach |

---

## Phase 1: Intake & Capability Fitness Check

### Step 1.1 — Extract the Solicitation Header Block

Read the SSN the user provided. Extract and present:

```
SOLICITATION INTAKE
═══════════════════════════════════════════
Agency:           [Extract from notice]
Program/Vehicle:  [Extract from notice]
Solicitation #:   [Extract from notice — "N/A" if not given]
Notice Type:      [SSN / RFI / RFQ / RFP]
Due Date:         [Extract or "Not stated"]
Page Limit:       [Extract or "Not stated"]
Primary NAICS:    [Extract from notice]
Set-Aside:        [Extract: Small Business / Unrestricted / HUBZone / etc.]
Submission Method:[Email / Portal — extract or "Not stated"]
Pricing/Quote Req:[Yes / No — FLAG IMMEDIATELY IF YES]
POC:              [Contracting officer name and contact if listed]
```

If any of these fields cannot be extracted, note them as **"NOT FOUND IN NOTICE"** — do not guess.

---

### Step 1.2 — Identify Requirements / Functional Areas

List every distinct requirement, functional area, task, or question the SSN asks about. Number them.

Example output:
```
REQUIREMENTS IDENTIFIED:
1. Custom software development for case management systems
2. Cloud infrastructure (AWS) migration and operations
3. Cybersecurity: network monitoring and incident response
4. AI/ML for document processing
5. Legacy system modernization
6. Question: Do you hold CMMC ML1 or ML2 certification?
7. Question: What is your experience with FISMA moderate systems?
```

---

### Step 1.3 — Run the Capability Fitness Check

For each requirement identified in Step 1.2, score it against `resources/capability-map.md`:

- **✅ DIRECT MATCH** — High-confidence capability with documented evidence in `past-performance.md`
- **⚠️ ADJACENT** — Medium-confidence; analogous commercial experience exists; must be labeled as proposed approach in the response
- **❌ OUT OF SCOPE / GAP** — Not currently held; use Gap Registry language from `past-performance.md`

Present the Fitness Check as a table:

```
CAPABILITY FITNESS CHECK
═══════════════════════════════════════════
Requirement                        | Score          | Evidence / Notes
----------------------------------|----------------|----------------------------------------
1. Custom software development    | ✅ DIRECT MATCH | CAP-01; PP-006, PP-001, 10 years
2. Cloud / AWS                    | ✅ DIRECT MATCH | CAP-02; PP-006, 99.9% uptime 3yr
3. Cybersecurity: network ops     | ⚠️ ADJACENT     | CAP-09; Xavier Monroe creds; no prime federal
4. AI/ML document processing      | ✅ DIRECT MATCH | CAP-03; PP-001, PP-002, PP-003
5. Legacy modernization           | ✅ DIRECT MATCH | CAP-06; PP-006, PP-007
6. CMMC ML1/ML2 certification     | ❌ GAP          | Not held — use Gap Registry disclosure
7. FISMA moderate systems         | ❌ GAP          | No federal A&A experience as prime
─────────────────────────────────────────────────────────────────────────────
OVERALL: [X] Direct Match | [Y] Adjacent | [Z] Gaps
RECOMMENDATION: [GO — strong match across core areas / GO WITH DISCLOSURES / NO-GO — gaps too material]
```

---

### Step 1.4 — Human Checkpoint (Mandatory)

**STOP. Present the Intake Summary and Fitness Check to the user before drafting anything.**

```
════════════════════════════════════════════════════════════
INTAKE COMPLETE — AWAITING YOUR APPROVAL BEFORE DRAFTING
════════════════════════════════════════════════════════════

[Paste the header block and Fitness Check table]

SUMMARY:
- Strong matches: [list ✅ items]
- Adjacent (will be labeled as proposed approach): [list ⚠️ items]
- Gaps (will be disclosed): [list ❌ items]
- Recommendation: [GO / GO WITH DISCLOSURES / NO-GO]

QUESTIONS FOR YOU BEFORE I DRAFT:
1. [List any ambiguities — e.g., "The SSN mentions NAICS 541512 but your primary is 541511 — should I note both?"]
2. [e.g., "Do you want to pursue this as prime or sub? The teaming posture affects the Executive Summary."]
3. [e.g., "Page limit is 4 pages — do you want me to prioritize [specific areas]?"]

Approve to proceed, or tell me what to change.
════════════════════════════════════════════════════════════
```

**Do not proceed to Phase 2 until the user explicitly approves or gives direction.**

If the recommendation is NO-GO and the user still wants to proceed, honor their decision — note the gaps and proceed with maximum transparency.

---

## Phase 2: Response Strategy

Once the user approves, map the response structure:

1. **Identify the correct template:**
   - Multi-page SSN with specific questions → `templates/ssn-response-letter.md`
   - Standalone capability statement requested → `templates/capability-statement.md`
   - If both are needed, draft the letter first; derive the cap statement from it

2. **Select past performance projects** — Choose 2-4 from `past-performance.md` with the highest keyword overlap to this SSN's requirements. Note which Response-Ready Summary to use for each.

3. **Map personnel to requirements** — For each functional area:
   - Technical/software/AI/cloud/data → Ian Bruce (primary cite)
   - Cybersecurity/IT infrastructure/helpdesk → Xavier Monroe (primary cite)

4. **Identify all gap disclosures needed** — Pull exact language from the Gap Registry in `past-performance.md`.

5. **Confirm page/length strategy** — If a page limit exists, prioritize:
   - Executive Summary (always)
   - ✅ DIRECT MATCH sections (always)
   - ⚠️ ADJACENT sections (include, with proposed approach label)
   - ❌ GAP sections (brief disclosure only — don't waste pages on gaps)
   - Acquisition recommendations (only if the SSN specifically asks)

---

## Phase 3: Draft the Response

### Core Drafting Rules

1. **Source tags required during drafting** — As you write each claim, note its source in a comment `[SOURCE: past-performance.md > PP-006]`. These tags are removed before delivery but serve as your audit trail.

2. **Template first, customize second** — Start from the appropriate template in `templates/`. Fill placeholders; remove unused `<!-- CONDITIONAL -->` sections.

3. **Response-Ready Summaries** — For past performance, paste the summary from `past-performance.md` verbatim, then adapt lightly for context. Do not rewrite from memory.

4. **Adjacent capabilities** — For ⚠️ ADJACENT items, use this exact framing:

   > **Proposed Approach** *(Analogous commercial experience — no prior government performance in this specific area):*
   > [Methodology description]

5. **Gap disclosures** — Use exact language from the Gap Registry. No softening, no hedging. Example:
   > "No current CMMC, FedRAMP, or federal A&A delivery as prime contractor. We would operate under a prime's A&A framework, sourcing certified compliance personnel as required."

6. **Tone standards:**
   - Government contractor register — not startup marketing
   - Concrete metrics over adjectives ("99.9% uptime" not "exceptional reliability")
   - No superlatives: never "world-class," "cutting-edge," "best-in-class"
   - First person plural ("Justice Quest LLC" or "we") — consistent
   - Gaps disclosed honestly — the DISCOS response is the model

7. **Footer on every page:**
   ```
   Justice Quest LLC (dba Vision Systems) · CAGE: 21GM9 · UEI: MU8FAL4JBL91
   [Response Type] Response — [Agency] [Solicitation Number] · Page X of Y
   ```

8. **All bracketed placeholders must be filled** — No `[LIKE THIS]` text in the final output.

---

### Handling Specific Questions in the SSN

If the SSN asks specific questions (common in RFIs), answer each question directly and sequentially. Do not bury answers in narrative. Use the format:

```
Q1: [Copy the question verbatim]
A: [Answer drawn from resource files]

Q2: [Copy the question verbatim]
A: [Answer drawn from resource files]
```

If a question asks about something in the Gap Registry, the answer begins with the gap disclosure, then proposes the mitigation.

---

### Human Checkpoint — Draft Review

After producing the complete draft, present it to the user with:

```
════════════════════════════════════════════════════════════
DRAFT COMPLETE — PLEASE REVIEW BEFORE QUALITY GATE
════════════════════════════════════════════════════════════

Template Used:    [ssn-response-letter / capability-statement]
Estimated Pages:  [N]
Past Performance Used:  [PP-001, PP-002, etc.]
Personnel Cited:  [Ian Bruce / Xavier Monroe / Both]
Gaps Disclosed:   [List]
Adjacent Items:   [List — labeled as proposed approach]

REVIEW CHECKLIST (check these yourself):
☐ All factual claims are accurate — no inflation
☐ Gap disclosures are present where needed
☐ All company identifiers match your records (UEI, CAGE, NAICS)
☐ Contact info is current
☐ Tone matches your target agency (federal vs. DoD vs. civilian)
☐ Page limit respected (if any)
☐ Every SSN question has been answered

Tell me what to revise, or approve to proceed to quality gate.
════════════════════════════════════════════════════════════
```

---

## Phase 4: Quality Gate

Run the quality gate when the user approves the draft. Check every item below. Report each as PASS / FAIL.

### Identity & Registration Checks
- [ ] UEI matches `company-profile.md` (MU8FAL4JBL91)
- [ ] CAGE Code matches `company-profile.md` (21GM9)
- [ ] DUNS matches `company-profile.md` (146671819)
- [ ] Address matches `company-profile.md`
- [ ] POC contact info matches `company-profile.md`
- [ ] NAICS codes are appropriate for this solicitation
- [ ] Business type is "Small Business" (no unsupported set-aside claims)

### Iron Rule Verification
- [ ] No client name appears that is not in `past-performance.md`
- [ ] No certification appears that is not in a personnel file (Security+, AWS CCP, etc.)
- [ ] No metric appears (uptime %, revenue secured, record counts) that is not in `past-performance.md`
- [ ] All ADJACENT sections are explicitly labeled as "Proposed Approach"
- [ ] All GAP items use Gap Registry language — no soft-pedaling

### Solicitation Compliance
- [ ] Every specific question in the SSN has a direct answer
- [ ] Page limit is respected (if stated)
- [ ] Submission format follows SSN instructions (email, portal, file format)
- [ ] Response is addressed to the correct agency/office
- [ ] Notice number appears in the header

### Tone & Professionalism
- [ ] No marketing superlatives ("world-class," "cutting-edge," "best-in-class")
- [ ] All metrics are concrete and specific
- [ ] No placeholder text `[LIKE THIS]` remains
- [ ] Footer appears on every page (if multi-page)
- [ ] Document is professional and submission-ready

### Quality Gate Output

```
════════════════════════════════════════════════════════════
QUALITY GATE REPORT
════════════════════════════════════════════════════════════
Verdict: [PASS / CONDITIONAL PASS / FAIL]

BLOCKERS (must fix before submission):
- [Item] — [Issue]

WARNINGS (should fix):
- [Item] — [Issue]

NOTES:
- [Any other observations]

[If PASS:]
✅ Response is ready for submission. Pre-submission checklist:
   ☐ Triple-check the submission email/portal address
   ☐ Verify subject line matches SSN instructions exactly
   ☐ Attach capability statement or other required files
   ☐ Submit BEFORE [due date]

[If CONDITIONAL PASS:]
⚠️ Fix the blocker(s) above, then resubmit to quality gate for the affected items.

[If FAIL:]
❌ Multiple blockers. Address all BLOCKER items and re-run the full quality gate.
════════════════════════════════════════════════════════════
```

---

## Announce Template

At the start of every run:

```
═══════════════════════════════════════════
SOURCES SOUGHT RESPONSE SKILL — ACTIVATED
═══════════════════════════════════════════
Company: Justice Quest LLC (dba Vision Systems)
Resource Files: Loaded from resources/
Templates: ssn-response-letter.md, capability-statement.md
Reference: examples/discos-ma-idiq-response.md

Phases:
  1. Intake & Fitness Check     → human checkpoint
  2. Response Strategy          → internal only
  3. Draft Response             → human checkpoint
  4. Quality Gate               → final checkpoint

The Iron Rule is active. No experience will be invented.
Starting Phase 1: Intake...
═══════════════════════════════════════════
```

---

## Hard Constraints

> **NEVER skip a human checkpoint.** The pipeline pauses after Phase 1 (intake) and after Phase 3 (draft). The user reviews both. Do not auto-proceed.

> **NEVER invent experience.** If it is not in the resource files, it does not go in the response. Label adjacent capabilities honestly. Disclose gaps using Gap Registry language.

> **NEVER submit anything.** This skill produces drafts. The human submits. Do not send emails, upload to portals, or transmit responses on behalf of the user.

> **ALWAYS load resource files first.** Before producing the Fitness Check or draft, read all resource files. Do not draft from memory.

> **The DISCOS response is your tone benchmark.** When in doubt about how formal, how direct, or how to handle a gap disclosure, consult `examples/discos-ma-idiq-response.md`.

> **Update resource files when facts change.** If Ian updates a certification, adds a new client, or finalizes an SBA designation, update the resource files — not just the response. The resource files are the source of truth.

> **FLAG PRICING/QUOTE REQUIREMENTS.** Sources Sought Notices and RFIs typically do not require pricing. If the notice asks for a "quote", "pricing", or "cost estimate", FLAG THIS IMMEDIATELY to the user during Phase 1 (Intake). Do not attempt to generate pricing.

---

## Quick Reference — Capability-to-NAICS Map

| SSN Mentions... | Primary NAICS to Cite | Capability File |
|---|---|---|
| Custom software, app dev, programming | 541511 | CAP-01 |
| Cloud, AWS, infrastructure, hosting | 518210, 541512 | CAP-02 |
| AI, ML, automation, NLP, document processing | 541511 | CAP-03 |
| Data engineering, ETL, databases, migration | 541511, 518210 | CAP-04 |
| API, systems integration, interoperability | 541511, 541512 | CAP-05 |
| Legacy modernization, tech refresh | 541511, 541512 | CAP-06 |
| Document management, OCR, PDF | 541511, 541519 | CAP-07 |
| Workflow automation, process automation | 541511, 541519 | CAP-08 |
| Cybersecurity, network security, IAM | 541519 | CAP-09 |
| IT helpdesk, endpoint management, IT ops | 541519, 518210 | CAP-10 |
| Software licensing, COTS procurement | 541519 | CAP-11 |
| Legal services, paralegal, legal tech | 541611 | CAP-12 |
