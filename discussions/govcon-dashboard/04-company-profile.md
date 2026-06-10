# Company Profile

**Status:** Needs discussion

## What it is

A company profile feature for GovCon use cases. Before a user can process
solicitations, the system needs to know about their company — capabilities,
certifications, past performance, key personnel, etc. This data feeds into
proposal generation and compliance analysis.

## The core tension

From the brainstorm:

> "We can either go with individual fields where the user types in their
> information... or we can just say, hey, give us all the documents that you
> have, and then the agent will put together a profile for you... And then
> maybe we can have the agent synthesize a JSON profile that we display on
> the screen and that is editable."

Three approaches:

### Option A: Structured form

Traditional approach. Pre-defined fields for:
- Company name, legal name, DBA
- CAGE code, UEI (formerly DUNS), TIN
- NAICS codes, PSC codes
- Certifications (8(a), WOSB, SDVOSB, HUBZone, etc.)
- Capabilities statement
- Past performance references
- Key personnel (with resumes)
- SF-330 / SF-254 / SF-255 data

**Pros:** Predictable, queryable, agent can rely on structured data
**Cons:** Rigid, user has to type everything, hard to know all required fields upfront

### Option B: Document-driven + agent synthesis

User uploads whatever documents they have (articles of incorporation, tax docs,
capabilities statements, resumes, certifications, etc.). The agent reads
everything and synthesizes a structured profile (JSON). The profile is displayed
as editable cards. User can fill gaps manually.

**Pros:** Minimal user effort, agent does the work, flexible
**Cons:** Agent may miss things, hallucinate, or make errors that need manual correction

### Option C: Hybrid (recommended)

Start with Option B (document-driven), but display the profile as Option A
(editable structured fields). The agent populates what it can from documents.
Empty fields are clearly marked as "needs input." User can:
- Upload more docs → agent re-processes and fills more fields
- Manually edit any field
- Mark fields as "verified" (lock from agent overwrites)

**Pros:** Best of both worlds, iterative, user always in control
**Cons:** More complex UI, need merge logic for agent updates vs manual edits

## Data model considerations

### As a case/matter entity

The company profile could live as an extension of the `cases` table — add a
`company_profile JSONB` column. Simple, but only works if the profile is
scoped to one case.

### As a standalone entity

A `company_profiles` table with its own relationships. A profile can be linked
to multiple solicitations. More flexible, but more upfront work.

### As a workspace-level entity

Profiles live in a workspace. Each solicitation workspace inherits or overrides
the base profile. Most aligned with the existing workspace architecture.

## Existing infrastructure to leverage

- Document ingestion pipeline (upload → OCR → chunk → embed)
- Synthesis pattern (like case narrative → parties/allegations extraction)
- The agent can already read documents and extract structured data
- Parties, events, documents tables already exist

## Open questions

1. **Entity scope:** Is the company profile global (one per account), per-case,
   or per-workspace? GovCon use suggests one per account with per-solicitation
   overrides.

2. **Which Option:** A (form), B (agent-driven), or C (hybrid)?

3. **Schema:** Extend `cases` with JSONB, new `company_profiles` table, or
   workspace-based?

4. **Field completeness:** What are the must-have fields for GovCon? Need a
   definitive list before building the form or the agent prompt.

5. **Resume handling:** Key personnel resumes — are these individual documents
   attached to personnel entities, or just part of the document dump?

## Recommendation

Start with **Option C (hybrid)** scoped as a **per-case JSONB column** initially
(for speed), with a clear migration path to standalone profiles if multi-case
reuse becomes a requirement. Build the agent synthesis prompt first (it's the
hardest part to get right), then wrap the UI around it.
