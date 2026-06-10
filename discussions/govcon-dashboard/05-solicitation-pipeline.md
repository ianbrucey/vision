# Solicitation Pipeline

**Status:** Needs discussion

## What it is

The core GovCon workflow: after setting up a company profile, the user processes
solicitations (RFIs, RFPs, RFQs, sources sought notices). Each solicitation goes
through an assembly line — extract requirements, analyze scope, cross-reference
with capabilities, generate compliance matrices, and ultimately produce proposal
documents.

## The assembly line (from the brainstorm)

The user described a process they were doing manually in VS Code:

1. Dump all solicitation files into a folder (ZIPs, PDFs, DOCX, XLSX, audio)
2. Ingest everything (OCR, chunk, embed)
3. Extract structured data: contacts, purpose, scope of work, requirements,
   evaluation criteria, deadlines
4. Cross-reference requirements against company capabilities
5. Generate a baseline report (compliance matrix, gap analysis)
6. Synthesize proposal documents (technical response, past performance,
   pricing schedule)

## What already exists

- Ingestion pipeline (documents → blocks → embeddings)
- Synthesis pattern (narrative → structured extraction)
- Strategy engine (`002_strategy.sql` — strategies, propositions, gauntlet)
- The "gauntlet" concept is referenced in existing schema — this is exactly
  the assembly line the user described
- Drafts system (agent generates structured documents)

## Architectural decision: Solicitation as a case type or workspace?

### Option A: Solicitation = Case

Each solicitation is a new case with `case_type = 'rfp_response'` (already
exists in the enum). Company profile is attached to the case. Documents are
ingested into the case. Simple extension of existing architecture.

**Pros:** Zero new entity types, reuses everything
**Cons:** Mixes solicitation management with legal case management in the same
UI, case list gets cluttered

### Option B: Solicitation = Workspace under a "Company" case

The user's company is a case. Each solicitation is a workspace under that case.
Documents are scoped to the workspace. Company profile lives at the case level.

**Pros:** Clean separation, workspaces already exist in schema, natural hierarchy
**Cons:** Workspaces are lightly used currently, would need UI for workspace
management

### Option C: New top-level entity "Solicitation"

A new `solicitations` table, new routes, new tabs. Full greenfield.

**Pros:** Clean domain model, no contamination of legal case concepts
**Cons:** Most work, duplicates patterns that already exist in cases

## Recommendation

**Option A** (solicitation = case with `case_type = 'rfp_response'`). It's the
fastest path and the existing ingestion/synthesis/drafting pipeline already
works for cases. The "GovCon Dashboard" becomes a filter/view on the cases list
showing only RFP-type cases. We can always extract to a separate entity later.

## What needs to be built

### If Option A:

1. **RFP-specific ingestion** — When case_type is `rfp_response`, the ingestion
   pipeline adds RFP-specific tagging (sections like "Scope of Work",
   "Evaluation Criteria", "Instructions to Offerors")

2. **Solicitation synthesis** — A new synthesis job type that extracts:
   - Agency/contact info
   - NAICS/PSC codes
   - Due date
   - Requirements (numbered list)
   - Evaluation criteria (with weights if available)
   - Required submissions (technical, past performance, pricing)
   - Set-aside status
   - Contract type (FFP, T&M, CPFF, etc.)

3. **Compliance matrix** — Auto-generated from requirements × evaluation
   criteria. Each row is a requirement. Columns: requirement text, our
   response capability, evidence document reference, compliance status
   (compliant / partial / non-compliant / TBD)

4. **Gap analysis** — Cross-reference requirements against company profile
   capabilities. Flag gaps (missing certifications, missing past performance
   in a required area, key personnel gaps)

5. **Proposal generation** — Agent drafts:
   - Executive summary
   - Technical approach
   - Past performance references
   - Pricing rationale (if pricing data available)
   - Compliance checklist

### Gauntlet integration

The existing strategy engine has a "gauntlet" concept (propositions, strategies,
evidence linking). This is the right foundation for the solicitation assembly
line. Each step in the pipeline is a strategy proposition. The gauntlet
evaluates each requirement against available evidence.

## Files that would be touched (rough estimate)

- `backend/schemas/002_strategy.sql` — extend for solicitation-specific propositions
- `backend/ingestion/synthesizer.py` — new RFP synthesis job
- `backend/api/main.py` — new synthesis endpoint or extend existing one
- `frontend/src/app/cases/` — RFP-specific dashboard cards/views
- `frontend/src/components/` — compliance matrix component, gap analysis view

## Open questions

1. **Architecture:** Option A (case-type), B (workspace), or C (new entity)?

2. **Pipeline scope:** Do we build the full 6-step assembly line at once, or
   incrementally (ingestion → extraction → matrix → proposal)?

3. **Gauntlet reuse:** Is the existing strategy engine suitable, or does it need
   significant rework for GovCon?

4. **Proposal format:** What output format(s)? Markdown → export to DOCX? Fill
   government forms (SF-33, SF-1449)? The output format determines the draft
   template design.

5. **Pricing:** Does the agent handle pricing schedules, or is that out of scope
   for v1?
