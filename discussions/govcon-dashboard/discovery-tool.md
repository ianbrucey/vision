# The Ultimate Discovery Tool — Brainstorm & Scope

Discovery is the backbone of litigation. Millions of documents, dozens of
custodians, tight deadlines, and the constant pressure of not missing the
smoking gun. This document scopes what the ultimate discovery tool looks like
within Vision — building on everything we already have, and imagining what's
missing.

---

## What We Already Have (the foundation)

| Capability | Status | What it means for discovery |
|---|---|---|
| **Ingestion pipeline** | Built | PDF, DOCX, XLSX, CSV, images, audio, ZIP — anything goes in. OCR via DataLab, chunked into blocks, FTS-indexed, vector-embedded. |
| **Section hierarchy** | Built | Every document has a structural Table of Contents — headings, page ranges, block counts. Critical for understanding document organization. |
| **Full-text search** | Built | PostgreSQL tsvector across all blocks. Ranked results with snippets, page numbers, document context. |
| **Semantic search** | Built | Vector embeddings (Mistral 1024-dim) for conceptual queries. "Show me documents about post-operative infection" even if the words differ. |
| **Hybrid search** | Built | Combined keyword + semantic, deduplicated and ranked. |
| **Agent tools** | Built | The agent can search, read, analyze, create drafts, manage tasks, log correspondence. Full programmatic access to the evidence store. |
| **Strategy engine** | Built | Propositions, AND/OR gates, evidence mapping. Legal claims modeled as trees. |
| **Citation layer** | Built | Every factual claim links back to specific blocks. Verifiable. |
| **Parties & allegations** | Built | Structured entities the agent extracts and the user can manage. |
| **Tasks system** | Built | Assign review tasks, track progress, set deadlines. |
| **Correspondence tracker** | Built | Log discovery letters, meet-and-confer communications, production cover letters. |
| **Drafts** | Built | Agent-generated documents — privilege logs, discovery responses, motions to compel. |

This is already a respectable e-discovery platform. But "respectable" isn't the goal.

---

## The Discovery Tool — Complete Feature Map

### Layer 1: Ingestion & Processing (the intake funnel)

#### 1.1 Load File Import
**What:** Import standard discovery load files — Concordance (DAT), Relativity,
CSV with document-level metadata. This is how productions arrive from opposing
counsel and how exports leave.

**How it works:**
- Drag-and-drop a ZIP containing documents + load file
- Parse load file fields: BegBates, EndBates, BegAttach, EndAttach, Custodian,
  DateSent, DateReceived, EmailSubject, Confidential, Redacted, etc.
- Map load file columns to Vision's document metadata
- Link parent-child relationships (email ↔ attachments) via attachment range
- Ingest documents + populate metadata in one operation

**Existing foundation:** ZIP ingestion already works. Document metadata already
has a JSONB `metadata` column. Load file parsing is a new parser module.

#### 1.2 Native File Processing
**What:** Beyond PDF/DOCX — handle email containers (PST, MBOX, EML),
spreadsheets as structured data, CAD files, forensic images, and proprietary
formats.

**How it works:**
- PST/MBOX → extract individual emails as documents, preserve threading,
  participants, date headers, attachment relationships
- XLSX → extract as structured data sheets, not just flat text. Preserve
  formulas, cell references, named ranges
- EML/MSG → individual email documents with full header preservation
- Forensic images (E01, AFF4) → mount and extract filesystem, then ingest files

**Existing foundation:** `ingest_file()` dispatches by extension. Each new
format is a new handler in the dispatcher.

#### 1.3 Email Threading
**What:** Group related emails into threads. Identify inclusive emails (the
final email in a thread that contains all prior messages). Avoid producing
duplicate content.

**How it works:**
- Parse `Message-ID`, `In-Reply-To`, `References` headers
- Build thread trees (in-reply-to chains)
- Detect inclusive emails (emails whose body contains the text of prior emails)
- Mark thread root and inclusive emails in metadata
- Review UI shows threads as expandable groups
- Search can be scoped to "thread-inclusive only" (avoid duplicate review)

**Existing foundation:** Section hierarchy already models tree structures.
Threading adds a new relationship type parallel to sections.

#### 1.4 Near-Duplicate Detection
**What:** Identify documents that are substantially similar — different versions
of a contract, draft/final pairs, email chains with slight variations.

**How it works:**
- Compute document-level MinHash or SimHash fingerprints
- Cluster by similarity threshold (e.g., 85%+)
- Within clusters, identify exact duplicates (byte-identical)
- Mark "parent" (most complete/authoritative version) and "children"
- Review UI groups duplicates, allows "review one, apply coding to all"

**Existing foundation:** We already have block-level embeddings and FTS.
Doc-level fingerprinting is a new module. PostgreSQL can compute Hamming
distance on integer hashes efficiently.

#### 1.5 Communication Network Analysis
**What:** Map who communicated with whom, when, and about what. Visualize the
social graph of the case.

**How it works:**
- Extract sender/recipient/CC/BCC from emails
- Link participants to known parties (or create new party suggestions)
- Build a weighted graph: nodes = people, edges = communications, weight =
  frequency, time dimension
- Visualize as interactive force-directed graph
- Filter by date range, topic (via semantic clustering), custodians
- Identify key players, communication patterns, gaps, outliers

**Existing foundation:** Parties table already exists. Correspondence items
have sender/receiver. Emails ingested from PST/MBOX would create structured
communication records.

---

### Layer 2: Review & Coding (the decision layer)

#### 2.1 Document Review Workspace
**What:** The core review interface. A split-panel view: document on one side,
coding panel on the other. Keyboard-driven for speed.

**How it works:**
- **Document viewer** — rendered PDF/image with highlighted search hits,
  redaction overlays, and section navigation
- **Coding panel** — keyboard shortcuts for:
  - Responsiveness: Responsive / Non-Responsive / Needs Further Review
  - Privilege: Not Privileged / Attorney-Client / Work Product / Joint Defense / Other
  - Confidentiality: Not Confidential / Confidential / Highly Confidential / Attorneys Eyes Only
  - Issue tags: link to specific allegations from the case
  - Notes: free-text reviewer notes
- **Navigation** — Next/Previous document, Next uncoded, Jump to Bates number
- **Batch management** — assign batches of N documents to reviewers
- **QC review** — second-pass review on coded documents, flag disagreements
- **Review stats** — documents/hour, coding breakdowns, reviewer comparisons

**Existing foundation:** Documents are already in the DB with blocks and
sections. The document preview modal already exists. Coding metadata goes
into the `documents.metadata` JSONB column or new `document_tags` tables.

#### 2.2 Automated First-Pass Coding
**What:** The agent reviews documents before humans do. It proposes
responsiveness and privilege calls. Humans review the agent's proposals
rather than reading every document cold.

**How it works:**
- For each uncoded document, the agent:
  1. Reads the document content (via existing block-reading tools)
  2. Compares against the case narrative, allegations, and discovery requests
  3. Proposes: Responsive/Non-Responsive + reasoning
  4. Flags potential privilege (attorney names in headers, "legal advice"
     language, privilege markings)
  5. Links to specific allegations where relevant
- Human reviewer sees: "Agent suggests: RESPONSIVE to A03 (Negligent
  Credentialing). [Show reasoning]"
- Human confirms or overrides with a single keystroke
- Agent learns from corrections (feedback loop for prompt refinement)

**Existing foundation:** Agent already has search, read, analyze capabilities.
The synthesis pattern (agent reads → produces structured output) is proven.
This is a prompt engineering + tool-calling workflow, not new infrastructure.

#### 2.3 Technology-Assisted Review (TAR / Predictive Coding)
**What:** Train a model on human coding decisions, then predict coding for
remaining documents. Prioritize review queue by predicted relevance.

**How it works:**
- **Seed set:** Human codes ~1,000 documents (statistically representative sample)
- **Training:** Train a classifier on seed set decisions. Features include:
  document text embeddings (already exist), metadata, sender/recipient,
  document type, section headings
- **Prediction:** Model scores all remaining documents for responsiveness
- **Review queue:** Sorted by predicted responsiveness — most likely responsive
  first. Reviewer sees prediction as a suggestion.
- **Active learning:** Model retrains as more documents are coded. Identifies
  documents where it's least confident → prioritizes those for human review
- **Validation:** Statistical sampling to validate recall/precision against
  agreed thresholds

**Existing foundation:** Embeddings already exist (Mistral 1024-dim). The
classifier is a lightweight model (logistic regression or small neural net).
We're not building Relativity — we're building a focused TAR workflow that
works with our existing embedding infrastructure.

#### 2.4 Redaction Tool
**What:** Redact privileged, confidential, or PII content from documents
before production. The agent proposes redactions; human confirms.

**How it works:**
- **Agent-proposed redactions:** Agent reads document, identifies:
  - Attorney-client communications (based on participants + content)
  - Work product (analysis, strategy, mental impressions)
  - PII (SSN, DOB, financial account numbers, medical record numbers)
  - Court-ordered redactions (specific terms, names)
- **Redaction editor:** PDF-like view with draw-to-redact. All redactions
  are stored as bounding boxes in a `redactions` table (linked to blocks +
  coordinates).
- **Redaction log:** Auto-generated from stored redaction data. Includes:
  redaction ID, document Bates, page, reason code, redacting attorney, date.
- **Burned production:** When producing, redactions are burned into the PDF.
  Original + redacted versions are both preserved.

**Existing foundation:** Blocks have bounding boxes (bbox_x1, bbox_y1, etc.)
and page numbers. Redactions are just bounding box annotations with reason
codes. The agent already reads block content and can identify PII patterns.

#### 2.5 Privilege Log Generation
**What:** Auto-generate a privilege log from coded documents. Every document
marked "Privileged" gets a log entry with all required fields.

**How it works:**
- When a document is coded "Privileged" with a privilege type:
  1. Agent reads the document
  2. Agent populates log fields: Date, Author, Recipients, Privilege Type,
     Description (without revealing privileged content), Basis for Privilege
  3. Human reviews and confirms each entry
- Export as CSV/Excel/load file compatible with common e-discovery platforms
- Integrate with the Drafts system — the privilege log IS a draft document
  that can be edited and finalized

**Existing foundation:** Drafts system generates structured documents. Agent
can read and analyze. This is a template-driven agent workflow.

---

### Layer 3: Production (the output layer)

#### 3.1 Bates Numbering
**What:** Assign Bates numbers to every produced document. Multi-level
numbering (prefix-counter-suffix). Support for multiple production waves.

**How it works:**
- Define Bates schema: `PREFIX-000001` through `PREFIX-999999`
- Assign numbers sequentially to documents in the production set
- Handle:
  - Multi-page documents: Bates per page, not per document
  - Attachments: families get contiguous or attachment-range numbering
  - Cross-referencing: "See Bates XYZ-000042"
- Bates numbers stored as document metadata. Displayed in review UI.
- Production export stamps Bates numbers on each page.

**Existing foundation:** Documents already have `id` and `metadata JSONB`.
Bates is just a structured identifier stamped at production time.

#### 3.2 Production Set Builder
**What:** Select documents for production, apply redactions, generate load
files, export.

**How it works:**
- **Filter:** Responsive + Not Privileged + Not Highly Confidential → production set
- **Preview:** See document count, page count, file size before exporting
- **Redaction check:** Warn if any documents in the set have unresolved
  redactions
- **Export formats:**
  - PDF with burned redactions + Bates stamps
  - Native files (original format, if no redactions)
  - Load file (DAT/CSV with metadata)
  - OPT file (image cross-reference)
- **Production log:** Track every production — what was produced, when,
  to whom, under what agreement.
- **Clawback support:** Mark documents produced in error. Track clawback
  notices as correspondence items.

**Existing foundation:** Document storage (MinIO) already holds originals.
The export is a transformation pipeline: DB query → file processing →
packaging → download.

#### 3.3 Production Comparison
**What:** Compare incoming productions from opposing counsel against your
own evidence. Identify gaps, overlaps, and inconsistencies.

**How it works:**
- Import opposing party's production (documents + load file)
- De-duplicate against your existing document collection
- Flag: documents they have that you don't, documents you both have,
  documents you have that they haven't produced
- For overlapping documents: compare metadata (dates, custodians, redactions).
  Opposing party's redactions are noted but not lifted.

**Existing foundation:** Load file import (from 1.1) + deduplication (from
1.4). This is a comparison workflow on top of both.

---

### Layer 4: Analytics & Strategy (the insight layer)

#### 4.1 Discovery Dashboard
**What:** A real-time overview of the discovery process. What's been reviewed,
what's left, what's hot.

**How it works:**
- **Pipeline health:** Documents ingested, processed, enriched, ready for review
- **Review progress:** % coded, by reviewer, by batch, by issue tag
- **Hot documents:** Documents the agent flags as potentially case-dispositive
- **Gaps:** Search terms that returned 0 results, custodians with no documents,
  date ranges with no evidence
- **Deadlines:** Upcoming discovery deadlines (close of fact discovery,
  expert disclosures, production deadlines) — pulled from the events timeline
- **Cost estimates:** Projected review hours × hourly rate

**Existing foundation:** The Overview tab pattern already exists. This is a
specialized Overview for discovery cases, pulling from the same data sources.

#### 4.2 Timeline Builder
**What:** Construct a visual, interactive case timeline from document metadata
and extracted events.

**How it works:**
- **Auto-populate:** Extract dates from documents (date sent, date filed,
  date of service, date signed) and populate events timeline
- **Manual entries:** User adds events (key meetings, phone calls, milestones)
- **Document links:** Each timeline entry links to source documents
- **Visualization:** Horizontal scrolling timeline. Color-coded by event type.
  Zoom from decades → years → months → days.
- **Agent analysis:** "What happened between March 15 and April 3?" Agent
  reads all documents in that date range and summarizes.
- **Gap detection:** "We have no documents from the week of the incident."

**Existing foundation:** Events table already exists with date, kind, summary,
actor. Block-level dates can be extracted from document metadata.

#### 4.3 Deposition Preparation
**What:** For a given witness, the agent assembles everything they need to
know and everything they might be asked about.

**How it works:**
- **Select witness:** Choose from case parties or add a new deponent
- **Agent builds a prep packet:**
  1. All documents authored by or mentioning the witness
  2. All communications with/from the witness
  3. Timeline of the witness's involvement
  4. Key topics the witness can testify about
  5. Documents that contradict the witness's expected testimony
  6. Suggested deposition questions (direct + cross)
  7. Exhibit list
- **Output:** A structured draft document (using the Drafts system) that
  the attorney can refine

**Existing foundation:** Agent search, drafts system, parties table, events
timeline. This is an orchestration of existing tools.

#### 4.4 Gap Analysis & Discovery Planning
**What:** Before discovery closes, the agent analyzes whether you have what
you need for each claim, defense, and element.

**How it works:**
- **Map claims to evidence:** For each proposition in the strategy tree,
  what evidence supports it? What evidence contradicts it? What's missing?
- **Flag gaps:** "Element 3 of Negligence (Causation) has only 2 supporting
  documents but opposing expert will require strong rebuttal."
- **Suggest discovery:** "Plaintiff's production is light on documents from
  the emergency department. Consider a follow-up RFP or deposition subpoena
  for the ED director."
- **Discovery plan:** A structured document the agent generates laying out:
  what you have, what you need, who has it, and how to get it.

**Existing foundation:** Strategy engine (propositions, evidence mapping,
AND/OR gates). This is an agent-driven analysis walk of the strategy tree.

#### 4.5 Hot Document & Issue Tracking
**What:** The agent continuously monitors the document population and flags
documents that warrant attorney attention.

**How it works:**
- **Rules engine:** Configurable triggers. Examples:
  - Any document with "settlement" within 50 words of a dollar amount
  - Communications between [Key Custodian A] and [Key Custodian B] in the
    48 hours before [Critical Date]
  - Documents that mention any party name in a negative context
- **Agent-driven:** The agent periodically scans new documents and flags
  notable findings based on its understanding of the case narrative
- **Alert feed:** A real-time feed on the discovery dashboard: "3 new hot
  documents flagged"
- **Escalation:** Hot documents can auto-create tasks assigned to specific
  reviewers

**Existing foundation:** Agent tools for search and analysis. The task system
for escalation. This is a scheduled agent workflow.

---

### Layer 5: Chain of Custody & Compliance (the trust layer)

#### 5.1 Chain of Custody Tracking
**What:** Immutable audit trail from collection through production. Every
action on a document is logged.

**How it works:**
- **Collection log:** Date, source, method, collector identity
- **Processing log:** File format conversions, OCR timestamps, exception
  handling
- **Review log:** Every coding decision: who, when, from what to what
- **Production log:** What was produced, when, in what format, to whom
- **Integrity verification:** SHA-256 hashes at each stage. Verification
  that produced documents match originals
- **Export:** Chain of custody reports for court admissibility challenges

**Existing foundation:** Jobs table already tracks processing actions.
A `custody_events` table would extend this with a unified event model.

#### 5.2 Legal Hold Management
**What:** Issue, track, and release legal hold notices to custodians.
Integrate with the correspondence tracker.

**How it works:**
- **Create hold:** Define scope (custodians, date ranges, subject matter),
  generate hold notice letter
- **Issue:** Send via correspondence system (email integration or manual
  tracking)
- **Track:** Acknowledge receipt, send reminders, document compliance
- **Release:** When hold is lifted, generate release notice, update status
- **Dashboard:** Active holds, expiring holds, non-responsive custodians

**Existing foundation:** Correspondence tracker, tasks, parties. Legal holds
are a specialized correspondence thread type.

---

## Architecture Decisions to Make

### 1. Review Coding Data Model

**Option A:** Extend `documents.metadata` JSONB column with coding fields.
Simple, no migration needed. But hard to query, hard to index, hard to enforce.

**Option B:** New `document_tags` table with columns: document_id, tag_type
(responsiveness, privilege, confidentiality, issue), tag_value, coded_by,
coded_at, notes, is_agent_proposed, is_confirmed. Indexed, queryable, joinable.

**Recommendation: Option B.** Review coding is first-class data, not metadata.

### 2. Review UI Architecture

**Option A:** New "Review" tab in the case dashboard. Full-page split-panel
review interface. Keyboard shortcuts. Coding panel.

**Option B:** Modal/overlay review panel that can be opened from any tab
(documents, search results, timeline).

**Recommendation: Option A for primary review.** Option B as a quick-preview
supplement.

### 3. TAR Implementation

**Option A:** Lightweight in-process classifier (scikit-learn) running in
the worker. Simple, no new infrastructure.

**Option B:** External ML service. More powerful models but more complexity.

**Recommendation: Option A for v1.** Logistic regression on 1024-dim embeddings
is surprisingly effective and requires zero new infrastructure.

### 4. Email Ingestion: Native vs. Converted

**Option A:** Convert all emails to PDF via a rendering service, then process
through the standard DataLab pipeline. Simpler, uniform processing.

**Option B:** Parse emails natively — extract structured metadata (headers,
participants, thread info), store body as text, render attachments separately.

**Recommendation: Option B.** Email metadata is too valuable to lose. Threading,
participant analysis, and header forensics all require native parsing. A hybrid
approach: parse natively, render the body to PDF for OCR if needed.

---

## What Changes Today vs. What's Future

### Immediate (build on existing foundation)

- Load file import (1.1) — a new parser module, ~300 lines
- Email threading (1.3) — new relationship model, ~200 lines agent logic
- Automated first-pass coding (2.2) — prompt engineering + agent workflow
- Privilege log generation (2.5) — draft template + agent workflow
- Discovery dashboard (4.1) — new Overview card + specialized view
- Review coding data model — new table + migration
- Agent tools for coding — add `code_document` and `list_document_tags` to tools.py

### Next (significant new components)

- Full review workspace (2.1) — new tab, keyboard-driven UI
- Redaction tool (2.4) — redaction annotation model + editor UI
- Bates numbering (3.1) — numbering engine + export pipeline
- Production set builder (3.2) — export pipeline
- Deposition preparation (4.3) — agent orchestration workflow
- Gap analysis (4.4) — agent strategy walk

### Vision (bigger infrastructure)

- PST/MBOX native processing (1.2) — new ingest handlers
- TAR predictive coding (2.3) — ML pipeline
- Communication network analysis (1.5) — graph visualization
- Timeline builder (4.2) — interactive visualization
- Legal hold management (5.2) — new entity type
- Production comparison (3.3) — cross-collection analysis
- Chain of custody (5.1) — immutable audit trail

---

## How It All Fits Together

```
                      DOCUMENTS IN
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          Uploads     Load Files    Email (PST/MBOX)
              │            │            │
              └────────────┼────────────┘
                           ▼
                   Ingestion Pipeline
                   (OCR → Chunk → Embed → Enrich)
                           │
                           ▼
                   Evidence Store
           (documents → sections → blocks → embeddings)
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          Search       Review        Analytics
       (FTS/Semantic  (Coding/     (Timeline/Network/
        /Hybrid)       Redaction)    Gap Analysis)
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          Production   Privilege    Depositions
          (Bates/       Log          (Prep Packets)
           Load File)
                           │
                      DOCUMENTS OUT
```

---

## The "Agent-First" Philosophy

Every feature in this document follows one rule: **the agent goes first.**

- Agent proposes coding → human confirms
- Agent drafts privilege log → human edits
- Agent flags hot documents → human investigates
- Agent builds depo prep → human refines
- Agent identifies gaps → human decides strategy

The human is always in control. The agent is always doing the first pass.
This isn't about replacing attorneys. It's about giving them superpowers.
