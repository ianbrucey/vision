---
name: solicitation-pipeline
description: Process a federal solicitation (RFP, RFI, RFQ, Sources Sought) through the full assembly line — triage, deep read, assessment, response drafting, and quality gate. Use when documents are already ingested in a case folder and the user wants to produce a response.
---

# Solicitation Pipeline Skill

Transform a federal solicitation through a fixed 6-phase assembly line: Triage → Deep Read (parallel) → Synthesize Brief → Go/No-Go Assess → Draft Response → Quality Gate. Every phase produces a standard artifact. Nothing leaves the line without passing its gate. The human reviews at every checkpoint.

## When to Run

Invoke this skill when:
- The user says "process this solicitation," "run the solicitation pipeline," "analyze this RFP," "draft a response to this," or similar
- A new solicitation case has been set up with documents in a working directory
- The user uploads solicitation documents and wants to go through the full pipeline

**Do not run** for:
- General questions about a solicitation ("what does this clause mean?") — use a general-purpose subagent
- Editing an existing response — use the response-drafter agent directly
- Research unrelated to a specific solicitation

## Prerequisites Check

Before starting, verify the working directory has:

1. **Solicitation documents** — extracted text files in `extracted-text/` or `documents/` directory, OR the original PDF/DOCX files that can be read
2. **A working directory** — the case folder or solicitation folder

If documents are missing, tell the user: "I need the solicitation documents in this folder before I can run the pipeline. Please add the RFP/RFI/RFQ documents (PDF, DOCX, or extracted text) and I'll proceed."

If documents are present, announce the pipeline start and proceed.

## The Phases

```
SOLICITATION IN
      │
      ▼
┌─────────────────┐
│ PHASE 2: TRIAGE │  solicitation-triage agent → TRIAGE.md
│    (~5 min)     │
└────────┬────────┘
         │
         ├── QUICK-KILL → No-Go Brief → STOP
         │
         ▼
┌──────────────────────────┐
│ PHASE 3: DEEP READ       │  3 agents IN PARALLEL
│    (~20-30 min)          │  ├─ scope-extractor → SCOPE.md
│                          │  ├─ compliance-extractor → COMPLIANCE.md
│                          │  └─ submission-extractor → SUBMISSION.md
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ PHASE 3b: SYNTHESIZE     │  opportunity-brief-writer → BRIEF.md
│    (~5 min)              │
└────────┬─────────────────┘
         │
         ▼  [HUMAN CHECKPOINT: Review BRIEF.md]
         │
         ▼
┌──────────────────────────┐
│ PHASE 4: ASSESS          │  go-no-go-assessor → DECISION.md
│    (~5 min)              │
└────────┬─────────────────┘
         │
         ▼  [HUMAN CHECKPOINT: Make GO/NO-GO decision]
         │
         ├── NO-GO → No-Go Brief → ARCHIVE
         │
         ▼
┌──────────────────────────┐
│ PHASE 5: DRAFT           │  response-drafter → RESPONSE.md
│    (~15-20 min)          │
└────────┬─────────────────┘
         │
         ▼  [HUMAN CHECKPOINT: Review draft]
         │
         ▼
┌──────────────────────────┐
│ PHASE 6: QUALITY GATE    │  quality-gate-checker → QUALITY.md
│    (~5 min)              │
└────────┬─────────────────┘
         │
         ▼  [FINAL: Human approval]
         │
         ▼
    RESPONSE OUT
```

---

## Phase 2: Triage

### Step 2.1: Invoke the Triage Agent

Delegate to the `solicitation-triage` agent:

> "Classify this solicitation and run the quick-kill checklist. The working directory is [path]. Read the first 2-3 pages of the solicitation documents, classify the notice type (RFI/RFP/RFQ/SSN), extract the header block, and run the quick-kill checklist. Write TRIAGE.md."

### Step 2.2: Human Checkpoint — Review Triage

When the triage agent completes, present its findings to the user:

```
## Triage Complete

**Notice Type:** [RFI / RFP / RFQ / SSN]
**Agency:** [Name]
**Solicitation #:** [Number]
**Due Date:** [Date]
**Quick-Kill:** [PASS / KILL — reason]

📄 TRIAGE.md has been written.

**Review the triage results.** If this is a quick-kill, we stop here. If anything looks wrong in the classification or header block, tell me and I'll re-run triage.

Continue to Phase 3 (Deep Read)?
```

**If quick-kill is triggered:** The pipeline stops. File the reason. Do not proceed.

**If the user disagrees with the classification:** Re-run the triage agent with the user's correction.

**If the user approves:** Proceed to Phase 3.

---

## Phase 3: Deep Read (Parallel)

### Step 3.1: Launch Three Agents in Parallel

Run these THREE agents simultaneously. They are independent and designed to not overlap:

1. **scope-extractor** — "Extract the scope of work, background, specific requirements, and technical objectives. Read TRIAGE.md first. Write SCOPE.md."
2. **compliance-extractor** — "Extract NAICS, set-aside, clearance, evaluation criteria, contract type, and all compliance-relevant information. Read TRIAGE.md first. Write COMPLIANCE.md."
3. **submission-extractor** — "Extract submission instructions, due dates, POC details, page limits, format requirements, and logistics. Read TRIAGE.md first. Write SUBMISSION.md."

All three receive the working directory path. Each writes its own artifact. They can run in parallel because they extract different things from the same documents.

### Step 3.2: Verify All Three Completed

After all three agents finish, verify that `SCOPE.md`, `COMPLIANCE.md`, and `SUBMISSION.md` all exist. If any agent failed, re-run it.

### Step 3.3: Synthesize the Brief

Delegate to the `opportunity-brief-writer` agent:

> "Synthesize TRIAGE.md, SCOPE.md, COMPLIANCE.md, and SUBMISSION.md into a standardized Opportunity Brief. Write BRIEF.md."

### Step 3.4: Human Checkpoint — Review the Brief

Present the brief summary:

```
## Opportunity Brief Complete

**Opportunity:** [Name]
**Notice Type:** [Type]
**The Ask:** [One sentence from brief]

📄 BRIEF.md has been written.
📄 SCOPE.md — [N] requirements extracted
📄 COMPLIANCE.md — [Evaluation type, security, contract]
📄 SUBMISSION.md — Due [Date] via [Method]

**Review the brief carefully.** This is the foundation for the Go/No-Go decision and the response. If anything is inaccurate, tell me what to fix.
```

If the user wants changes to any artifact, make them (or re-run the relevant agent) before proceeding.

---

## Phase 4: Go/No-Go Assessment

### Step 4.1: Invoke the Assessor

Delegate to the `go-no-go-assessor` agent:

> "Run the formal Go/No-Go decision matrix against BRIEF.md. Score each factor, apply hard gates, and produce a recommendation. Write DECISION.md."

### Step 4.2: Human Checkpoint — The Decision

Present the scored assessment:

```
## Go/No-Go Assessment Complete

**Score:** [X]/70 ([X]%)
**Recommendation:** [GO / GO (Caution) / NEEDS MORE INFO / NO-GO]
**Hard Gates:** [None / Triggered — list]

📄 DECISION.md has been written.

**Key Strengths:**
- [Strength 1]
- [Strength 2]

**Key Risks:**
- [Risk 1]
- [Risk 2]

**The decision is yours.** The agent's recommendation is advisory. What's your call?

[GO — proceed to response drafting]
[NO-GO — file and archive]
[NEEDS MORE INFO — what questions need answers?]
```

**If NO-GO:** Write a one-paragraph `NO-GO.md` explaining the reason. Archive. Pipeline ends.

**If NEEDS MORE INFO:** List the specific questions. Pause the pipeline until answers are available.

**If GO:** Proceed to Phase 5.

---

## Phase 5: Response Assembly

### Step 5.1: Check for Company Profile

Look for `profile/COMPANY_PROFILE.md` in the project root or the case folder. If it doesn't exist, warn the user:

> ⚠️ **No COMPANY_PROFILE.md found.** The response will use placeholder brackets for company-specific information (UEI, CAGE, NAICS, past performance). Do you want to create a company profile first, or proceed with placeholders?

### Step 5.2: Invoke the Drafter

Delegate to the `response-drafter` agent:

> "Draft the complete response using the appropriate template based on the notice type in TRIAGE.md. Read all artifacts in the working directory. Use COMPANY_PROFILE.md if available. Write RESPONSE.md."

### Step 5.3: Human Checkpoint — Review the Draft

```
## Response Draft Complete

**Template:** [RFI Response / Capability Statement / RFP Proposal]
**Estimated Pages:** [N]
**Artifacts Used:** TRIAGE.md, SCOPE.md, COMPLIANCE.md, SUBMISSION.md, BRIEF.md, DECISION.md
[**Company Profile:** Used / Not found — placeholders used]

📄 RESPONSE.md has been written.

**Review the draft.** Check for:
- Accuracy of all claims
- Appropriate tone for the notice type
- Completeness (every question answered?)
- Company information (if profile was available)

Tell me what to change, or approve to proceed to the quality gate.
```

Allow the user to iterate on the draft. They may want to re-run the drafter with specific instructions, or manually edit sections.

---

## Phase 6: Quality Gate

### Step 6.1: When Ready

Only proceed to quality gate when the user says the draft is ready. The user may iterate on the draft multiple times before this step.

### Step 6.2: Invoke the Checker

Delegate to the `quality-gate-checker` agent:

> "Run the complete quality checklist against RESPONSE.md. Verify every question is answered, page limits are respected, no marketing language, all logistics correct, no placeholder text. Cross-check against SUBMISSION.md and the original solicitation. Write QUALITY.md."

### Step 6.3: Final Checkpoint — The Gate Report

```
## Quality Gate Complete

**Verdict:** [PASS / CONDITIONAL PASS / FAIL]
**BLOCKERS:** [N]
**HIGH:** [N]
**MEDIUM:** [N]
**LOW:** [N]

📄 QUALITY.md has been written.

[If PASS:]
✅ **The response is ready.** Here's what to do before submission:
- Triple-check the POC email
- Verify the subject line matches SUBMISSION.md exactly
- Attach all required forms
- Submit BEFORE the deadline

[If CONDITIONAL PASS:]
⚠️ **N blocker(s) must be fixed.** After fixes, I'll re-run the quality gate on just the affected items.

[If FAIL:]
❌ **The response is not ready.** Address all BLOCKER and HIGH items and I'll re-run the quality gate.
```

---

## Pipeline States and Recovery

### If an Agent Fails

If any agent returns an error or incomplete output:
1. Report the failure to the user with the agent's error message
2. Ask if they want to retry or skip
3. Retry with more specific instructions if needed

### Resume After Interruption

The pipeline is resumable. If the conversation is interrupted:
- Check which artifacts exist in the working directory
- Resume from the next incomplete phase
- Announce: "Pipeline resuming from Phase [N]. Artifacts found: [list]. Proceeding with Phase [N+1]."

### Skip Phases

The user may request to skip a phase. Honor this but warn about the consequences:
- Skipping triage → risk of wrong document type or missed quick-kill
- Skipping deep read → brief will be incomplete
- Skipping assessment → no scored Go/No-Go recommendation
- Skipping quality gate → no automated checklist verification

### Re-run a Phase

The user may request to re-run any phase. Re-invoke the relevant agent with any additional instructions.

## File Manifest

At pipeline completion, the working directory should contain:

```
[Working Directory]/
├── TRIAGE.md          ← Phase 2
├── SCOPE.md           ← Phase 3 (parallel)
├── COMPLIANCE.md      ← Phase 3 (parallel)
├── SUBMISSION.md      ← Phase 3 (parallel)
├── BRIEF.md           ← Phase 3b (synthesis)
├── DECISION.md        ← Phase 4
├── RESPONSE.md        ← Phase 5
├── QUALITY.md         ← Phase 6
└── NO-GO.md           ← Phase 4 (if no-go)
```

## Announce Template

At the start of the pipeline:

```
> ═══════════════════════════════════════════
> SOLICITATION PIPELINE — STARTING
> ═══════════════════════════════════════════
> Working Directory: [path]
> Documents Found: [N] files
>
> Phases:
>   2. Triage (~5 min)
>   3. Deep Read — 3 agents in parallel (~20-30 min)
>   3b. Synthesize Brief (~5 min)
>   4. Go/No-Go Assess (~5 min)
>   5. Draft Response (~15-20 min)
>   6. Quality Gate (~5 min)
>
> Human checkpoints: After triage, after brief, after assessment, after draft.
> ═══════════════════════════════════════════
>
> Starting Phase 2: Triage...
```

At the end of the pipeline (if GO and PASS):

```
> ═══════════════════════════════════════════
> PIPELINE COMPLETE — RESPONSE READY
> ═══════════════════════════════════════════
> Artifacts: TRIAGE.md, SCOPE.md, COMPLIANCE.md, SUBMISSION.md, BRIEF.md, DECISION.md, RESPONSE.md, QUALITY.md
> Quality Gate: PASS ✅
>
> Pre-Submission Checklist:
> ☐ POC email triple-checked
> ☐ Subject line verified
> ☐ All forms attached
> ☐ Submit BEFORE [due date]
> ═══════════════════════════════════════════
```

## Hard Constraints

> **NEVER skip a human checkpoint.** The pipeline pauses at each checkpoint and waits for user input. Do not proceed automatically. The human is the decision-maker at every gate.

> **NEVER modify agent artifacts directly.** If the user wants changes to TRIAGE.md, SCOPE.md, etc., re-invoke the agent with corrected instructions. The skill orchestrates; it does not rewrite agent output.

> **ALWAYS run Phase 3 agents in parallel.** Scope, compliance, and submission are independent. Running them sequentially wastes ~20 minutes. Use the Agent tool to invoke all three simultaneously.

> **The company profile is critical for Phase 5.** If `COMPANY_PROFILE.md` doesn't exist, warn the user explicitly. A response with `[COMPANY NAME]` placeholders cannot be submitted.

> **The quality gate is the last line of defense.** Do not let the user skip it unless they explicitly insist. Warn them: skipping quality gate means no automated verification of page limits, question completeness, or marketing language.

> **NEVER submit anything.** The pipeline produces a draft. The human submits it. We do not send emails, upload to portals, or transmit responses.
