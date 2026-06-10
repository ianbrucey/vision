# Solicitation Assembly Line — System Design

## Core Principle

Professionals focus on logistics. The solicitation assembly line transforms any federal opportunity — RFI, Sources Sought, or RFP — through a fixed pipeline: Ingest → Triage → Extract → Assess → Respond. Every step produces a standard artifact. Nothing leaves the line without passing its gate.

---

## Phase 1: Ingest & Extract

**Goal:** Get every document into searchable, skimmable text. No reading the raw docs yet.

### For PDFs
```
pdftotext file.pdf -          # text-based PDFs
pdf2image → pytesseract       # scanned/image-based PDFs
```

### For Word Documents
```
textutil -convert txt file.docx -stdout    # macOS native
pandoc file.docx -t plain                  # cross-platform
python-docx                                # programmatic extraction
```

### Artifact Produced
Raw text extract saved to working directory. Original zip preserved.

---

## Phase 2: Triage (5 Minutes)

**Goal:** Classify the opportunity type and decide whether to proceed to deep read. Don't read the full PWS yet — read the first 2-3 pages and the submission instructions.

### Step 2.1: Identify the Notice Type

| Type | What it means | Government is... |
|---|---|---|
| **RFI** (Request for Information) | Market research, no money yet | Asking "what's possible?" |
| **Sources Sought / SSN** | Market research, acquisition strategy | Asking "who can do this?" |
| **RFP** (Request for Proposal) | Live procurement with money | Asking "how much and how well?" |
| **RFQ** (Request for Quote) | Commercial buy, usually simpler | Asking "what's the price?" |

### Step 2.2: Extract the Header Block

From the first pages, pull these fields:

```
DUE DATE:
AGENCY:
OFFICE:
NAICS:
SET-ASIDE:
CONTRACT TYPE:
PLACE OF PERFORMANCE:
CLEARANCE:
PAGE LIMIT:
POC NAME:
POC EMAIL:
```

### Step 2.3: Quick-Kill Checklist

If ANY of these are true, skip to Phase 4 (No-Go brief). Don't read further.

- [ ] Product buy (they want a specific COTS product by name)
- [ ] Requires facility clearance we don't have
- [ ] Requires TS/SCI personnel clearance
- [ ] Place of performance is on-site at a military base we can't access
- [ ] NAICS is 541513 (Facilities Management) or other non-IT services
- [ ] "Brand Name Only" with no "or Equal" clause
- [ ] Requires existing contract vehicle we can't access (e.g., Must be JWCC awardee)
- [ ] Done in 5 minutes? Move on.

---

## Phase 3: Deep Read & Extract (20-30 Minutes)

**Goal:** Produce the Opportunity Brief — a standardized one-page extraction of everything that matters.

### Reading Order (This Sequence Only)

1. **Submission instructions** — page limit, format, what they want in the response, email or portal
2. **Scope/Background** — what problem are they trying to solve? What's the current state?
3. **Specific requirements** — what are they actually asking for? Services? Product? Both?
4. **Qualifications** — personnel certs, past performance requirements, clearance, NDA
5. **Evaluation criteria** — what matters to them? (Only present in RFPs)
6. **NAICS and set-aside** — confirms acquisition strategy

### Opportunity Brief Template

```
─────────────────────────────────────────────
OPPORTUNITY: [Short descriptive name]
FOLDER: [Path]
SOLICITATION #: [Number]
NOTICE TYPE: [RFI / SSN / RFP / RFQ]
AGENCY: [Department / Command / Office]
─────────────────────────────────────────────

THE ASK (one sentence):
[What they actually need — not what the title says]

CONTRACT:
  Type: [FFP / IDIQ / T&M / Hybrid]
  Duration: [Base + Options]
  Est. Value: [ROM or stated budget, if any]
  NAICS: [Code — Name]

SECURITY:
  Facility Clearance: [None / Secret / TS]
  Personnel Clearance: [None / Tier 1 / Secret / TS]
  Other: [HIPAA, CUI, FedRAMP, etc.]

PLACE: [Contractor facility / Government site / Hybrid]

RESPONSE:
  Due: [Date, Time, Timezone]
  Page Limit: [Number]
  Submit To: [Name, Email]
  Format: [PDF / Word / ATOMS portal]

SCOPE SUMMARY:
[3-5 bullets covering what they need]

DECISION FACTORS:
  Strengths: [Why this fits us]
  Risks: [What could make this a no]
  Gaps: [What we'd need to partner/subcontract for]

TEAMING: [Solo / Partner / Sub — who?]

DECISION: [GO / NO-GO / NEEDS MORE INFO]
─────────────────────────────────────────────
```

---

## Phase 4: Go / No-Go Assessment

### Decision Matrix

| Factor | Weight | Go | No-Go |
|---|---|---|---|
| Place of performance | Critical | Remote or contractor facility | On-site military base or foreign |
| Clearance required | Critical | None, or Secret w/ sponsorship path | TS facility clearance required at proposal |
| Contract type | High | FFP, commercial services, IDIQ task orders | Cost-reimbursement, massive scale ($50M+) |
| Teaming feasibility | High | Gaps fillable via known partner | Gaps require expertise we can't source |
| Past performance requirements | Medium | 1-3 relevant projects, or explainable | Requires 3+ $10M+ contracts in exact domain |
| Due date | Medium | 2+ weeks out | < 5 days, no existing relationship |
| Incumbent situation | Low | No incumbent, or incumbent likely leaving | Entrenched incumbent, bridge contract they want |
| Small business set-aside | Low | Set-aside in our category | Full and open against defense primes |

### Output
- GO → Phase 5 (Response Assembly)
- NO-GO → No-Go Brief (one paragraph, file it, move on)
- NEEDS MORE INFO → Specific question list for the POC

---

## Phase 5: Response Assembly

**Goal:** Produce the deliverable. Template depends on notice type.

**Before starting:** Open `profile/COMPANY_PROFILE.md`. All firm information, UEI, CAGE, NAICS, capabilities, and past performance language lives there. Pull from the profile rather than rewriting from memory. The profile is the single source of truth for company details across all responses.

### Decision: Which Template?

| Notice Type | Template | Structure |
|---|---|---|
| RFI | RFI Response | White paper. Shaping document. Help them understand what's possible. |
| Sources Sought | Capability Statement | Direct answers. Past performance. Team structure. Prove you can do it. |
| RFP | Proposal | Technical volume + Price volume + Past performance. Full compliance matrix. |

### RFI Response Template

```
1. Executive Summary (who we are, what we're responding to)
2. Understanding of the Problem (show you read it)
3. Our Approach (how we'd solve it)
4. Response to Specific Questions (answer every numbered question)
5. Differentiators (what makes us different from other respondents)
6. ROM / Pricing (if asked — always non-binding)
7. Corporate Experience (past performance summary)
8. Closing / Call to Action
```

### Sources Sought Capability Statement Template

```
1. Firm Information (name, UEI, CAGE, NAICS, status, POC)
2. Interest Statement (prime or sub, teaming arrangements)
3. Technical Capabilities (bullet list mapped to PWS requirements)
4. Past Performance (3 projects, contract number, value, scope, relevance)
5. Response to Specific Questions (answer every question directly)
6. ROM / Pricing Approach (if asked)
7. Recommendations (PWS improvements, competition structure — optional but high-impact)
```

### RFP Proposal Template

```
TBD — requires an actual RFP to design against.
Minimum structure:
  Volume I — Technical Approach
  Volume II — Management & Staffing
  Volume III — Past Performance
  Volume IV — Price
  Compliance matrix (requirement-by-requirement cross-reference)
```

---

## Phase 6: Quality Gate

Before any response leaves, pass through:

- [ ] Every question in the notice has been answered
- [ ] Page limit observed
- [ ] No marketing language ("world-class," "best-in-class," "synergistic")
- [ ] Claims backed by evidence (contract numbers, certifications, metrics)
- [ ] PWS terminology echoed back (shows you read it)
- [ ] POC email correct, subject line matches requirement
- [ ] Proprietary information marked if applicable
- [ ] Submitted on time (not 5 minutes before deadline)

---

## The Assembly Line Visualized

```
SOLICITATION IN
      │
      ▼
┌─────────────┐
│  INGEST      │  pdftotext, textutil → raw text
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  TRIAGE      │  Notice type, header block, quick-kill checklist
└──────┬──────┘
       │
       ├── QUICK-KILL → No-Go Brief → ARCHIVE
       │
       ▼
┌─────────────┐
│  DEEP READ   │  Structured reading order → Opportunity Brief
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  ASSESS      │  Decision matrix → GO / NO-GO / NEEDS INFO
└──────┬──────┘
       │
       ├── NO-GO → No-Go Brief → ARCHIVE
       │
       ▼
┌─────────────┐
│  TEMPLATE    │  Select: RFI / SSN / RFP template
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  ASSEMBLE    │  Draft response against template
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  QUALITY     │  Gate checklist → FINAL
└──────┬──────┘
       │
       ▼
RESPONSE OUT
```

---

## File Naming Conventions

```
[Folder]/source.md              ← sam.gov URL
[Folder]/[docname].md           ← extracted raw text
[Folder]/BRIEF.md               ← Opportunity Brief (standardized)
[Folder]/RESPONSE.md            ← Final response document
[Folder]/NO-GO.md               ← Why we passed (archive)
[Folder]/[original files]       ← Keep the original zip/pdf/docx
```

---

## Templates Master Set

Three response templates active. One per notice type. They share the same DNA but differ in structure and tone.

### Template DNA (Shared Across All Types)

- No marketing words. Evidence over adjectives.
- Echo the government's own terminology back to them.
- Answer every question. Directly. In order.
- Page limit is law. Don't write 11 pages for a 10-page limit.
- ROM is always non-binding and range-based.
- Proprietary marking only where genuinely sensitive.
- POC email and subject line triple-checked before send.

### What Each Solicitation Type Demands

| | RFI | Sources Sought | RFP |
|---|---|---|---|
| Tone | Educational. "Here's what's possible." | Confident. "Here's why we can do this." | Compliant. "Here's exactly what you asked for." |
| Goal | Shape the eventual RFP | Get on the shortlist | Win the contract |
| Length | Up to 25 pages | 5-10 pages | As specified (volumes) |
| Price | ROM, optional | ROM if asked | Binding or budget |
| Key section | Technical approach + vision | Past performance + capability | Compliance matrix + price |
| Risk of over-investing | Medium (no money yet) | Low (acquisition strategy being set) | High (but this is where the money is) |
