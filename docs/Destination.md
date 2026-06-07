# Destination: The War Room Agent

## The Metaphor

You are Tony Stark. The War Room Agent is Jarvis.

You don't tell Jarvis which file to open or which database table to query. You say:

> *"Jarvis, does the pathology report contradict the surgeon's operative notes?"*

And Jarvis already has every sensor, every document, every record indexed and ready. It answers with a conclusion, and — critically — shows you exactly where that conclusion came from. Every claim is a citation. Every citation is a click away from the source.

This is not a chatbot bolted onto a file system. This is an **intelligence layer** that sits on top of an ingested, indexed, and fully queryable case corpus. The agent does not search through documents. The agent **sees through** them.

---

## What This System Does

The War Room Agent ingests unstructured documents — medical records, credit reports, contracts, discovery productions, RFP documents, correspondence — and makes them **transparent to an AI agent**. Once ingested, the agent can:

1. **Research.** Answer factual questions about the case corpus. "Was the WBC count ever normal after admission?" The agent searches, retrieves, and answers with citations.

2. **Analyze.** Cross-reference documents against each other. "Does the discharge summary mention the pathology findings?" The agent finds contradictions, gaps, and patterns across documents.

3. **Strategize.** Decompose legal claims into their atomic elements, map facts to every element, walk every adversarial path to its terminal state, and compute the disposition of the case before the fight begins. Run the gauntlet — systematic cross-claim screening for vulnerabilities the element-by-element analysis would miss: standing, chain of title, licensing, statute of limitations, preclusion, arbitration exposure. Find the one path that wins.

4. **Draft.** Produce legal documents — demand letters, board complaints, RFP responses, discovery requests — where every factual claim is anchored to a specific source block. Not "the record shows X" but "on page 117 of the medical record, the 8:47 PM tissue exam states X."

5. **Organize.** Structure e-discovery productions, tag documents by relevance and privilege, build chronological timelines from scattered records, index exhibits for trial.

5. **Brief.** Given a case intake narrative, produce a structured case screening report: parties, allegations, clinical timeline, red flags, recommendation — all citation-backed, all auditable.

The through-line: **the agent has complete, queryable access to every document in the case, down to the individual text block.** That is the superpower. Everything else is an application of that superpower.

The second through-line: **legal claims have discoverable anatomy. That anatomy can be modeled. That model can be computed. The computation can find the optimal path.** The Evidence Agent gives you visibility. The Strategy Engine gives you foresight.

---

## How It Works

### Layer 1: Ingestion

Documents enter the system through OCR pipelines. DataLab is the current best path — it produces structured JSON with hierarchical blocks (Page → SectionHeader → Text → Table → ListItem), each with a unique `block_id`, bounding box coordinates, page number, block type, and HTML content. This is richer than plain text extraction because it preserves structure, tables, and spatial relationships.

The ingestion pipeline is:

```
PDF → DataLab API → datalab.json → normalize → Evidence Store
```

Ingestion is document-type-agnostic. A medical record, a credit report, and a contract all become: documents → pages → blocks. The structure is universal.

#### On Document Summaries: We Don't Do Them

In a prior version of the system, every uploaded document was immediately sent to an LLM for summarization. This made sense for short documents (a 5-page complaint, a 20-page motion), where a 3-sentence summary captures the gist. It does not make sense for 300-500 page medical records, discovery productions, or contract portfolios, where any summary short enough to be cheap is too vague to be useful, and any summary detailed enough to be useful is too expensive to generate on ingest.

**What we do instead:**

| Instead of... | We do... |
|---|---|
| A document summary | **Structural indexing.** The section outline IS the summary. Knowing the document has "Operative Report (pp. 12-16)" and "Pathology Report (pp. 28-31)" is more actionable than a paragraph saying "this is a medical record about a salpingectomy." |
| Pre-computed answers | **On-demand deep reads.** The agent reads specific sections when it needs to understand them. When the user asks about the pathology report, the agent retrieves and reads the pathology report section. Not before. |
| Upfront LLM cost per document | **Cheap structural + metadata extraction.** Page count, document type (inferrable from filename and first page), creation date, source. All extractable without an LLM or with a single cheap call. |

The section structure is free, deterministic, and more useful than a summary. The agent discovers what's in the document by searching it — not by reading a summary of it. When it needs to understand something specific, it reads that specific part. This is both cheaper and more accurate.

### Layer 2: Evidence Store

The evidence store is a PostgreSQL database with three universal tables:

| Table         | Purpose                                                                                                               |
| ------------- | --------------------------------------------------------------------------------------------------------------------- |
| `documents` | One row per ingested document. Name, page count, metadata.                                                            |
| `sections`  | The structural hierarchy of each document. Headers, sections, subsections. Parent/child relationships.                |
| `blocks`    | Every individual text block from DataLab. Block type, page number, HTML content, stripped text content, bounding box. |

Every block is indexed three ways:

- **Full-text search** — PostgreSQL `tsvector` for keyword and phrase search. Exact matches, stemming, ranking. Answers "where is 'adhesion' mentioned?"
- **Vector embeddings** — pgvector for semantic similarity search. Concept-level matching. Answers "what sections discuss surgical complications?" even when the word "adhesion" isn't used.
- **Structural navigation** — section hierarchy + page range for scoped retrieval. Answers "what's in the Operative Report section?"

---

### Layer 3: Case Core

Above the evidence store sits the case model. This is structured data that the user provides up front and the agent enriches as it works. It is the **long-term memory** of the agent across sessions.

#### The Case

```yaml
Case:
  name: string              # Human-readable label. "Alhad v. Edmonds" or "Smith Estate Review"
  case_number: string | nil # Optional. May not exist for pre-litigation matters, board complaints, internal reviews.
  case_type: enum           # The kind of matter. Drives which prompts, schemas, and workflows apply.
    - medical_board_complaint
    - civil_litigation
    - pre_litigation_investigation
    - internal_investigation
    - e_discovery
    - rfp_response
    - contract_review
    - insurance_claim
    - regulatory_response
    - other
  status: enum              # Where the case is in the workflow.
    - intake                 # Documents being ingested, parties being identified
    - indexing               # Evidence store being populated
    - analysis               # Agent actively reviewing and extracting
    - drafting               # Output being generated
    - complete               # Delivered
    - archived               # Done, but kept for reference
  jurisdiction: string | nil # Optional. Where filed or where the matter sits.
  filing_date: date | nil    # Optional. When filed, if applicable.
  description: string        # Free-text summary. "327-page medical record review for GA Composite Medical Board complaint alleging surgical error during salpingectomy."
  created_at: timestamp
  updated_at: timestamp
```

The `case_type` field is critical. It determines:
- Which ingestion workflows fire (medical records need section mapping; contracts need clause extraction)
- Which schemas the agent uses for extraction (clinical events vs. contractual obligations vs. discovery tags)
- Which output templates are available (board complaint vs. demand letter vs. RFP response vs. privilege log)
- Which parties are expected (a medical board complaint has a respondent physician; an RFP response has a procurement officer)

#### Parties

Parties are **tagged, not typed.** A person can be a defendant AND a witness AND an expert — or start as one and become another as the case develops. The party model uses role tags rather than rigid types:

```yaml
Party:
  id: uuid
  case_id: uuid
  name: string
  party_kind: enum          # individual | organization
  roles: list[enum]         # Multiple roles allowed. Tags, not categories.
    - plaintiff
    - defendant
    - respondent            # The professional being reviewed (medical board context)
    - claimant
    - witness
    - expert                 # Retained expert witness
    - treating_provider      # Treating physician (not the respondent)
    - attorney                # Counsel for any party
    - insurer
    - employer
    - facility               # Hospital, clinic, nursing home
    - regulatory_body        # GA Composite Medical Board, FDA, etc.
    - procurement_officer    # RFP context
    - interested_party       # Someone with a stake but not a formal party
    - other
  contact_info: json | nil  # Phone, email, address — optional
  notes: string | nil       # Free-text. "Attending OB/GYN who performed the salpingectomy. Did not visit patient post-op."
  associated_documents: list[uuid]  # Which documents mention this party
  created_at: timestamp
  updated_at: timestamp
```

Why tags instead of a single role enum?
- A treating physician can also be a witness
- A facility can be both the employer of the respondent AND the location where the injury occurred
- In e-discovery, a custodian can be both a witness AND an interested party
- Tags let the agent add roles as it discovers them without losing the original designation

#### The user provides upfront:

The user creates a case and fills in what they know. The minimum is a name, a case type, and a description. They can add parties, allegations, and documents as they go. The agent asks clarifying questions when it needs more.

The upfront work the user does:
1. **Name the case.** Something they'll recognize.
2. **Set the case type.** This tells the agent which playbook to load.
3. **Write a description.** One paragraph about what happened and what's being asked.
4. **Identify known parties.** Who is involved? Tag them with whatever roles are known. This can be partial — the agent will discover more parties and suggest role tags as it reads the documents.
5. **List the allegations or key questions.** What are we trying to answer? For a medical board complaint, these are the numbered allegations. For an RFP, these are the requirements. For e-discovery, these are the search terms and relevance criteria.
6. **Upload documents.** PDFs, correspondence, prior reports, anything relevant.

This is deliberately lightweight. The user doesn't fill out a 40-field form. They give the agent enough to orient itself, and the agent comes back with questions and discoveries.

#### What the agent populates:

As the agent works, it enriches the case core:

- **Events.** Timestamped facts extracted from the evidence. Each has an actor (linked to a party), an action, a kind (finding, decision, intervention, result, transition, communication), and citations to source blocks.
- **Citations.** The link layer. Every event, allegation verdict, and claim points back to specific `block_id`s.
- **Allegation verdicts.** For each allegation, the agent records: supported, contradicted, silent, or partial — with the evidence that supports that conclusion.
- **Red flags.** Discrepancies, missing documents, contradictions, timeline gaps. Each with citations.
- **Party discoveries.** New people and organizations found in the documents, with suggested role tags.

---

### Layer 4: Agent Query Interface — The Search Strategy

This is the bridge between the agent and the data. And the search strategy is **not one query type. It is a composition of query types, applied in sequence, each doing what it does best.**

#### The Search Principle

> **Search is multi-step because documents are multi-layered.**
>
> A document has structure (sections, headers, hierarchy), content (words, phrases, values), and meaning (concepts, implications, contradictions). No single search primitive covers all three. The agent composes them.

#### The Search Primitives

| Primitive | What it answers | Engine | Cost |
|---|---|---|---|
| **Structural** | "Where is the Operative Report section?" | SQL against `sections` table | Free |
| **Keyword (FTS)** | "Where is 'WBC' or 'leukocytosis' mentioned?" | PostgreSQL `tsvector` + GIN index | Free |
| **Semantic (Vector)** | "What sections discuss post-operative complications?" | pgvector cosine similarity | Free (pre-computed embeddings) |
| **Contextual** | "What's around block X?" | SQL: blocks ±N by page and position | Free |
| **Analytical** | "What was the WBC trend over time?" | Agent-written SQL: JOIN, aggregate, filter | Free |
| **Extractive** | "From these 15 blocks, extract all WBC measurements with timestamps." | LLM call against retrieved blocks | ~$0.01-0.05 |

#### How They Compose: A Real Example

> **User:** *"Was the patient's WBC count ever normal after surgery?"*

The agent does not run one search. It runs a **search chain:**

**Step 1 — Structural: Scope the search.**
```sql
SELECT id, title, page_start, page_end
FROM sections
WHERE document_id = $doc_id
  AND (title ILIKE '%lab%'
       OR title ILIKE '%wbc%'
       OR title ILIKE '%hematology%'
       OR title ILIKE '%blood%');
```
Result: "Laboratory Results" section, pages 44-52. "Hematology" section, pages 53-58. The agent now knows where to look. It does not search the entire 327-page record blindly.

**Step 2 — Keyword: Find exact mentions within scope.**
```sql
SELECT id, page, text_content, block_type
FROM blocks
WHERE document_id = $doc_id
  AND page BETWEEN 44 AND 58
  AND text_tsv @@ to_tsquery('english', 'WBC | leukocytosis | leukocyte | white blood');
```
Result: 47 blocks across 15 pages. Too many to read raw, but the agent now has every mention.

**Step 3 — Analytical: Aggregate to understand the shape.**
```sql
SELECT page, COUNT(*) as mentions,
       string_agg(LEFT(text_content, 80), ' | ' ORDER BY id) AS snippets
FROM blocks
WHERE document_id = $doc_id
  AND page BETWEEN 44 AND 58
  AND text_tsv @@ to_tsquery('english', 'WBC | leukocytosis | leukocyte | white blood')
GROUP BY page
ORDER BY page;
```
Result: The agent now sees that most mentions cluster on pages 44-45 (admission labs) and pages 56-57 (post-op labs). Pages 46-55 are noise — the word "WBC" appears in boilerplate headers. The agent narrows further.

**Step 4 — Contextual: Pull the signal blocks with surrounding context.**
```sql
-- Get the top-15 most relevant blocks by keyword density + position
-- plus their ±3 neighbors for context
-- (This is a simplified sketch; the real query uses window functions)
SELECT b.*
FROM blocks b
WHERE b.id IN (signal_block_ids)
   OR b.id IN (neighbor_block_ids)
ORDER BY b.page, b.id;
```
Result: ~90 blocks — the 15 signal blocks plus their neighbors. This is ~3,000 tokens. Comfortably fits in a single LLM call.

**Step 5 — Extractive: Feed to LLM with a focused prompt.**
> "Here are the WBC-related lab results from the medical record. The surgery was on May 11. Extract every WBC measurement with its timestamp and value. Then answer: was the WBC count ever within normal range (4.5-11.0 x10³/µL) after surgery?"

The LLM returns structured data and an answer. Each measurement has a citation `block_id`.

**Step 6 — Verify: Audit the citations.**
```sql
-- For each cited block, verify the quoted text actually exists
SELECT id, text_content ILIKE '%' || $quoted_snippet || '%' AS match_found
FROM blocks
WHERE id = ANY($cited_block_ids);
```
Result: 100% match or flag the failures. No hallucinated citations survive.

#### Why This Composition Matters

A naive RAG approach would embed the user's question, vector-search for "WBC normal after surgery," and return the top-10 chunks. That might work. Or it might return:
- A chunk about WBC from a completely different patient's record (wrong section)
- A chunk that mentions "normal" but in a different context ("normal saline was administered")
- Ten chunks from the same page, missing the post-op labs entirely

The composed search chain avoids all of this because the agent **understands what it's looking at before it asks the LLM to reason about it.**

#### What About Semantic Search?

Vector search is one primitive in the chain, not the whole chain. It excels at:

- **Finding conceptually related content** when the user doesn't know the exact terminology. "Find sections about the surgeon's communication with the patient" — the word "communication" may never appear, but notes about "discussed," "explained," "consented," and "phone call" will cluster nearby in embedding space.
- **Discovery across document boundaries.** "Are there any other documents in this case that discuss surgical adhesions?" Vector search across the entire evidence store can surface a passing mention in a nursing note that keyword search would miss.

But vector search alone is insufficient. It doesn't understand structure (can't scope to a section), it doesn't guarantee recall (can miss exact keyword matches), and it's opaque (you can't explain why a result ranked where it did without additional analysis).

#### The Agent's Tools

| Tool | What it does |
|---|---|
| `get_document_structure(doc_id)` | Return the section outline — the table of contents with page ranges. The agent's first call almost every time. |
| `search_blocks(query, scope?)` | Hybrid search (FTS + vector). Optional scope: document ID, page range, section ID. Returns ranked blocks. |
| `get_block_context(block_id, window=3)` | Return ±N surrounding blocks for reading in context. |
| `list_documents(case_id)` | What documents are in this case? |
| `execute_readonly_sql(sql)` | **The critical one.** Agent-written SQL. JOIN, aggregate, filter, explore. |
| `get_case(case_id)` | Return the full case core: parties, allegations, events extracted so far. |

---

### Layer 5: Agent Workspace

The agent can create temporary tables, materialized views, and working state within its own session-scoped schema. This is where it structures intermediate work product — a timeline under construction, a set of flagged blocks, a comparison table.

The workspace is:
- **Session-scoped** — cleaned up when the agent session ends
- **Agent-owned** — the schema is writable, not read-only
- **Inspectable** — the user can see what the agent is building

This is the "freedom" layer. The agent isn't confined to the pre-defined case core schema. If it needs a pivot table, it creates one. If it needs to track which blocks it has already reviewed, it creates a tracking table. If it's building a timeline and discovers a new event that doesn't fit the existing schema, it adds a column.

---

### Layer 6: Output Generation

Everything above serves this layer. The agent produces:

- **Case screening reports** — structured, citation-anchored analysis of allegations against the record
- **Legal documents** — demand letters, complaints, board filings, RFP responses
- **Timelines** — chronological, actor-tagged, citation-backed event sequences
- **E-discovery indices** — privilege logs, relevance tags, exhibit lists
- **Research memos** — answers to specific factual or legal questions with full provenance

Every output is **verifiable**. Every factual claim carries a citation. Every citation can be resolved to a specific block in a specific document on a specific page. Click the citation, see the source.

---

### Layer 7: The Strategy Engine

The Strategy Engine sits on top of the evidence store and case core. It is a **computational argumentation engine** — it doesn't advise on strategy, it computes it.

Where the Evidence Agent answers "what happened?", the Strategy Engine answers "does this claim survive a 12(b)(6)? Where is the single point of failure? What happens if the court distinguishes Lewis? Is there a licensing violation we missed?"

The Strategy Engine is described in full in [strategy-destination.md](strategy-destination.md) and implemented in [002_strategy_schema.sql](002_strategy_schema.sql). Here is its architecture:

**The Doctrine Tree.** Before any facts enter, the legal claim is modeled as a recursive tree of propositions. A claim (root) → elements (children) → sub-elements → factors. Each node has a gate type: AND (all children must succeed) or OR (any child can succeed). The tree is built from doctrine alone — the law defines what must be proved. Facts determine whether it can be.

**The Fact Inventory.** Facts are interpretive legal characterizations of raw events. An event is "Tow truck observed April 17 at 1:00 AM." A strategy fact is "The tow truck's presence constitutes an imminent threat of self-help repossession." The separation between events (case core) and strategy facts (strategy layer) is essential — it allows the permutation engine to characterize the same event differently and recompute the tree.

**Element-Fact Mapping.** Every connection between a fact and a proposition is a row with a rhetorical move (ASSERT, REFUTE, DISTINGUISH, etc.), a directionality (SUPPORTS or UNDERMINES), and a rationale — the legal reasoning chain. This is the connective tissue.

**Adversarial Walk.** For every load-bearing element, the system runs a structured dialectic: T1 (their best attack) → T2 (our response) → T3 (their counter) → T4 (our rebuttal). T1 and T3 are generated by an adversary sub-agent that sees only the element and the doctrine — not our responses. Each turn is an independent database row, making the walk queryable: "Find every contested path where our counter-argument lacks a verified pincite."

**Gate Walk.** Once every leaf has a terminal state (CLOSED, CONTESTED, OPEN), a deterministic function walks upward through the AND/OR gate logic. AND parents fail if any child fails. OR parents fail only if all children fail. The output: a SPOF map, pressure rankings, and missing evidence impact analysis.

**The Gauntlet.** Systematic cross-claim screening independent of element analysis. Seven attack surfaces: Standing/Capacity, Licensing/Regulatory, Preclusion/Abstention, Timing/Limitations, Pleading/Procedure, Evidence/Proof, Remedies/Damages, Party-Specific Vulnerabilities. Each check produces PASS, FAIL, or INQUIRY. The gauntlet catches what element analysis misses — the OFR license example: no element of wrongful repossession requires a collection license, but the gauntlet's Licensing check catches it, and it becomes an independent basis for a claim or defense.

**The Permutation Engine (Research Target).** Once every claim is modeled, every fact is mapped, and every adversarial walk is complete, the system can permute: different characterizations, different authority emphasis, different claim ordering, different procedural postures. Find the one path that wins. Or find that no path wins — and tell you what evidence would change that. This layer is deferred but the data model supports it from day one.

**Integration with the Evidence Agent.** The Strategy Engine reads from the evidence store (blocks cited as source for facts) and the case core (parties, events, allegations). It writes to strategy-specific tables in the same PostgreSQL database. A single SQL query can trace a strategy claim → element → fact → event → block — from legal conclusion to source document.

---

### Layer 8: Workspaces (Deferred — Design Implications Recorded)

A case is not a single monolithic session. A litigation case moves through phases — motion to dismiss, discovery, summary judgment, trial prep. Each phase has its own documents, its own questions, its own outputs. A medical board complaint might have an initial screening phase, an expert review phase, and a hearing preparation phase.

A **workspace** is a scoped view into the case. It filters the evidence store, focuses the agent on a specific set of questions, and uses a specific output template. Multiple workspaces can exist within one case, each with its own:

| Workspace property | What it is |
|---|---|
| **Name** | "Motion to Dismiss" or "Discovery — First Requests" or "Expert Review" |
| **Phase** | Where this workspace fits in the case lifecycle |
| **Document scope** | Which documents are relevant to this workspace? (Not all documents are relevant to every phase.) |
| **Key questions** | What is the workspace trying to answer? "Does the complaint state a claim?" vs. "Which documents are responsive to RFP 12?" |
| **Output template** | What does success look like? A motion brief? A privilege log? A board complaint draft? |
| **Agent state** | The workspace's own working tables, extracted events, flagged blocks, and intermediate work product. |
| **Parent workspace** | Optional. A summary judgment workspace might derive from a discovery workspace. |

#### Why Workspaces Matter for Design Now

The evidence store and case core must be **workspace-aware** from the start, even if workspaces aren't built yet. Specifically:

- **Documents belong to the case, but are scoped to workspaces.** A document might be relevant to discovery but not to the motion to dismiss. The `documents` table needs a way to associate with workspaces (a join table, not a single `workspace_id` — a document can be relevant to multiple workspaces).
- **Events and extractions are workspace-scoped.** The agent extracts different facts in a discovery workspace (responsive documents, privilege calls) than in a trial prep workspace (key testimony, exhibit chains). The extraction schema changes per workspace phase.
- **Outputs are workspace-scoped.** A case can have multiple reports, briefs, and indices — one set per workspace.
- **Workspaces are cumulative.** The discovery workspace inherits the parties and documents from the motion to dismiss workspace. The trial prep workspace inherits from discovery. Each workspace builds on the ones before it.

#### Design Implication

When we build the case core, we add one concept: **scope.** Every entity (document, event, extraction, output) can optionally be scoped to a workspace. If unscoped, it belongs to the case globally. This is a single nullable `workspace_id` column on the relevant tables — cheap to add now, expensive to retrofit.

#### Deferred

Workspaces as a user-facing concept, workspace creation UI, workspace lifecycle management, and workspace-specific agent behavior are all deferred. We build the ingestion layer first, then the case core, then the query layer. Workspaces are Layer 7 — they sit on top of everything else. But the schema makes room for them from day one.

---

## A Full Walkthrough: Medical Board Complaint

This is what the system looks like end-to-end for a real case. Not the simplified 7-step version — the actual flow with all the branching, edge cases, and decision points.

### Phase 0: Case Setup (User)

The user — an attorney or intake paralegal — opens the War Room and creates a new case.

#### The Input Philosophy: Narrative First, Structure Second

Attorneys think in narratives, not form fields. They are used to writing case summaries, complaint narratives, and intake memos. The Stage 0 intake pipeline already extracts structured data (parties, allegations, case theory, extraction focus) from narrative text. So the primary input mechanism is a **single large text area — a "brain dump"** — not a 40-field form.

The user writes a narrative. The agent extracts the structure.

Structured fields exist as optional shortcuts for things the user might prefer to enter directly (party names, dates, case number), but they are not required. The narrative is the authoritative source. The structured fields are conveniences.

#### Adaptive Placeholder Text

The placeholder text in the narrative text area changes based on the `case_type` the user selects. It gives examples of the kind of information that will help the agent, tailored to the domain:

**`medical_board_complaint`:**
> Tell us everything you know about this case. For example:
> - Who is the patient? What procedure or treatment did they receive?
> - Who is the respondent physician or provider? What is their specialty?
> - What facility did this occur at? When?
> - What went wrong? What are the specific allegations?
> - What records do you have? (medical records, imaging, correspondence)
> - What is your case theory? (e.g., "the surgeon removed the ovary but told the patient it was preserved")
>
> The more detail you provide, the better the agent can organize the evidence and target the relevant parts of the record.

**`civil_litigation`:**
> Tell us everything you know about this case. For example:
> - Who are the parties? Who is suing whom?
> - What court is it filed in? What is the case number?
> - What are the claims or causes of action?
> - What are the key facts? What happened, when, and who was involved?
> - What discovery have you received? What documents do you have?
> - What is your theory of the case?
>
> The more detail you provide, the better the agent can organize the evidence and identify what matters.

**`rfp_response`:**
> Tell us about this RFP. For example:
> - Who issued the RFP? What are they procuring?
> - What is the submission deadline? Are there page limits or format requirements?
> - What are the key requirements or evaluation criteria?
> - What past responses, capability statements, or boilerplate do you have?
> - What are the must-address items? What differentiates your response?
>
> The more detail you provide, the better the agent can match requirements to your existing content.

**`contract_review`:**
> Tell us about the contract(s) you need reviewed. For example:
> - Who are the parties to the contract?
> - What type of contract is it? (services agreement, lease, settlement, etc.)
> - What are your concerns? (indemnification, termination rights, payment terms, liability caps)
> - Are you comparing multiple contracts or reviewing a single one?
> - What is your negotiating position? Are you the buyer, seller, landlord, tenant?
>
> The more detail you provide, the better the agent can identify the clauses and obligations that matter to you.

**`e_discovery`:**
> Tell us about the discovery project. For example:
> - What is the matter? Who are the parties?
> - What is the discovery scope? (date range, custodians, search terms)
> - What types of documents are you collecting? (email, Slack, Sharepoint, etc.)
> - What are the relevance criteria? What are you looking for?
> - What are the privilege considerations?
> - What production format is required?
>
> The more detail you provide, the better the agent can organize, tag, and index the documents.

#### A Help Tooltip

Next to the narrative text area, an icon (?) opens a tooltip or slide-out panel. It shows:
1. **"What makes a good case narrative?"** — examples of well-written intakes for the selected case type
2. **"What the agent will do with this"** — a brief explanation of how the intake drives downstream work (extracts parties, identifies what to search for, etc.)
3. **"You can always add more later"** — reassurance that this isn't a one-shot; the agent asks questions as it works

#### What the User Actually Provides (Example)

The user writes this narrative for the Alhad case:

```
I am representing Roohi Ameenudeen Alhad in a complaint before the Georgia
Composite Medical Board. The respondent is Dr. Kevin J. Edmonds, an OB/GYN
at Wellstar North Fulton Hospital.

The patient was admitted on May 11, 2025 for emergency surgery. An ultrasound
and CT suggested possible ovarian torsion. Dr. Edmonds performed a laparoscopic
procedure, telling the patient afterward that her ovary was fine and had blood
supply — the problem was the fallopian tube, which was badly twisted and had to
be removed. He specifically told her husband that the ovary was in "perfect shape."

The patient was discharged on May 13. Post-operatively, she had elevated WBC
(leukocytosis) that did not resolve with IV antibiotics. Dr. Edmonds did not
visit her once after surgery. Dr. Karen Hamilton covered but could not answer
questions about the pathology results or the plan of care. Dr. Janet Boone
encouraged discharge despite abnormal WBC.

After discharge, the patient accessed her MyChart and found the tissue exam
report dated May 11 at 8:47 PM, which states the specimen included ovarian
tissue adherent to the fallopian tube. This directly contradicts the surgeon's
claim that the ovary was preserved. The patient also requested the removed
tissue for religious rites and was denied.

I have the 327-page medical record from MRO and the ICR from the board.

Allegations:
1. Surgical error — ovary removed due to failure to identify/lyse adhesions
2. Surgeon failed to visit or communicate with patient post-operatively
3. Surgeon made false statements about the condition of the ovary
4. Patient discharged with unresolved leukocytosis
5. Dr. Hamilton failed to answer patient questions
6. Pathology report contradicts surgeon's account — ovarian tissue removed
7. Patient denied opportunity to retain tissue for religious rites

Uploading: medical record PDF (327 pp) and ICR PDF (3 pp).
```

The user also fills in a few structured fields for convenience:

```
Case name: Alhad v. Edmonds
Case type: medical_board_complaint
Case number: (blank — board complaints don't always have one yet)
```

That's it. The agent extracts the structured data from the narrative. The user spent 5-10 minutes writing what they already know. They did not fill out a form.

#### Why This Works

- **Low friction.** The user writes what they already know in the way they already think about it. No field-by-field data entry.
- **Rich signal.** A narrative contains subtext — the user's theory of the case, their priorities, their tone — that a form strips out.
- **Adaptive.** The placeholder text guides without constraining. Different case types get different prompts. The user can ignore the prompts and write whatever they want.
- **Iterable.** The user can come back and add to the narrative as the case develops. New allegations, new parties, new theories. The agent re-extracts.
- **Agent-driven follow-up.** The agent reads the narrative and asks clarifying questions: "You mentioned Dr. Janet Boone — should I add her as a party? What is her role?" The user answers in conversation, not in form fields.

### Phase 1: Ingestion

**1a. OCR.** The 327-page PDF hits the DataLab API. The system requests JSON output with pagination — every page, every block, every table. DataLab returns a hierarchical JSON structure: 327 Page blocks containing ~8,500 child blocks (Text, SectionHeader, Table, ListItem, PageHeader, PageFooter).

**Time:** ~60 seconds for 327 pages in "accurate" mode. **Cost:** ~$4.00.

**1b. Normalize.** The DataLab JSON is parsed and inserted into the evidence store:

```
mr_documents:  1 row   (name: "02._Medical_Records_decrypted.pdf", page_count: 327)
mr_sections:   ~220 rows  (the structural hierarchy — section headers and their parent/child relationships)
mr_blocks:     ~8,500 rows  (every text block, with page, position, type, and content)
```

**1c. Index.** For each block, the system:
- Generates a `tsvector` for full-text search
- Computes a `pgvector` embedding (Mistral embed, 1024 dimensions)
- Links the block to its parent section for structural navigation
- Records heading ancestry (H1 → H2 → H3 chain) so the agent knows a block on page 117 is inside "Visits > Operative Report > Findings"

**Time:** ~10 seconds for 8,500 blocks. **Cost:** ~$0.05 for embeddings.

**1d. Ingest the ICR.** Same process for the Investigative Complaint Record — a 3-page PDF that provides the board's perspective on the complaint. Normalized and indexed alongside the medical record.

The evidence store now contains two documents, ~8,600 blocks, ~225 sections, all fully searchable. **Total ingestion time: ~2 minutes. Total cost: ~$4.05.**

### Phase 2: Intake Processing (Agent + LLM)

The agent reads the user's intake and processes it. This is one or two LLM calls, not a pipeline of hundreds.

**2a. Case Brief Extraction.** The agent sends the user's intake text to the LLM with a structured output schema (`CaseBrief`). The LLM returns:

```json
{
  "patient": { "name": "Roohi Ameenudeen Alhad", "dob": null, "mrn": null },
  "respondent": { "name": "Dr. Kevin J. Edmonds", "role": "respondent", "specialty": "OB/GYN", "facility": "Wellstar North Fulton Hospital" },
  "encounter_dates": { "admit": "2025-05-11", "discharge": "2025-05-13" },
  "allegations": [
    { "id": "A01", "category": "surgical_error", "text": "Surgeon failed to identify or lyse adhesions...", "targets": ["Dr. Kevin J. Edmonds"] },
    ...
  ],
  "case_theory": "The respondent performed a salpingectomy and represented that the ovary was preserved, but the pathology report indicates ovarian tissue was removed. The respondent then avoided the patient post-operatively. This suggests the respondent recognized the error and attempted to conceal it.",
  "extraction_focus": ["operative report", "pathology report", "tissue exam", "discharge summary", "nursing notes post-op day 1-2", "lab results WBC", "consent form"]
}
```

**2b. Party Discovery.** The agent cross-references the case brief parties against the evidence store. It searches for every named person in the medical record and flags any it finds that aren't in the user's party list yet. "I found 14 additional providers mentioned in the record — Dr. Janet Boone, Dr. Karen Hamilton, several nurses, an anesthesiologist. Should I add any of them as parties?"

**2c. Document Structure Review.** The agent calls `get_document_structure()` on the medical record and reads the section outline. It identifies the high-signal sections:

```
Section "Visits > Operative Report"          pp. 12-16   ← KEY for A01, A03
Section "Visits > Pathology Report"          pp. 28-31   ← KEY for A06
Section "Visits > Discharge Summary"         pp. 33-37   ← KEY for A04
Section "Laboratory Results"                  pp. 44-58   ← KEY for A04
Section "Non-Physician Notes > Nursing"      pp. 72-94   ← KEY for A02, A05
Section "Visits > History & Physical"        pp. 6-11    ← relevant for timeline
Section "Visits > ED Report"                 pp. 1-5     ← relevant for timeline
```

It flags sections that are likely low-signal: "Vitals Flowsheets" (pp. 95-310 — 215 pages of repetitive vitals readings), "Medication Administration Records" (pp. 311-320), "Insurance Information" (pp. 321-322).

**This step costs almost nothing** — one structural query, one LLM call for party discovery, and one LLM call for case brief extraction. **Total Phase 2 cost: ~$0.03.**

### Phase 3: Targeted Evidence Retrieval (Agent + SQL + Vector)

Now the agent retrieves the evidence relevant to each allegation. This is where the composed search strategy shines.

**For A01 (surgical error / adhesions):**

The agent's extraction focus says "operative report." It:
1. Scopes to the Operative Report section (pages 12-16) — structural
2. Within that scope, searches for blocks semantically related to "adhesions, ovary, fallopian tube, lysis, dissection" — vector
3. Also does keyword search for "adhesion," "ovary," "ovarian," "salpingectomy," "specimen" — FTS
4. Expands to the Pathology Report section (pages 28-31) because the allegation is about what was removed — cross-section structural
5. Searches the pathology section for "ovary," "ovarian," "adherent," "specimen" — keyword
6. Pulls context windows around the top 25 blocks — contextual
7. Assembles ~6,000 tokens of evidence

**For A04 (WBC / discharge):**

The agent's extraction focus says "lab results WBC, discharge summary." It:
1. Scopes to Laboratory Results (pages 44-58) — structural
2. Keyword search for "WBC," "leukocytosis," "white blood," "leukocyte" — FTS
3. Analytical SQL to extract trends: "GROUP BY date, calculate min/max/trend" — analytical
4. Scopes to Discharge Summary (pages 33-37) — structural
5. Searches for "discharge," "stable," "normal," "follow up," "outcome" — keyword
6. Pulls context windows — contextual
7. Assembles ~4,000 tokens of evidence

**For A07 (religious rites):**

This is the hardest one. There's no standard medical section for "religious accommodation." The agent:
1. Does a broad vector search across the entire record for anything semantically related to "religious rites, tissue retention, cultural accommodation, patient request for specimen" — unconstrained vector
2. Keyword searches for "religious," "rite," "ritual," "tissue," "specimen," "disposition," "request," "ask," "faith" — broad FTS
3. Reviews the nursing notes section specifically, since patient requests are typically documented by nurses — structural + keyword
4. Searches the consent form section for any mention of tissue disposition — structural + keyword
5. If the evidence is thin, the agent tells the user: "I found no documentation in the record addressing the patient's request for tissue retention. This absence is itself evidence — it supports the allegation that the request was not honored." — the agent recognizes that *absence of evidence is evidence of absence* in certain contexts

**This phase costs nothing in LLM calls.** It's all SQL, vector math, and structural navigation. The agent is building its understanding of where the evidence lives before it spends a single token on reasoning.

### Phase 4: Reasoning (LLM Fan-Out)

For each allegation, the agent assembles a reasoning prompt:

```
You are reviewing a medical board complaint.

CASE HEADER:
  Patient: Roohi Ameenudeen Alhad
  Respondent: Dr. Kevin J. Edmonds, OB/GYN
  Facility: Wellstar North Fulton Hospital
  Admitted: 2025-05-11 | Discharged: 2025-05-13
  Procedure: Left salpingectomy

ALLEGATION A01:
  Surgeon removed the fallopian tube without identifying or lysing adhesions
  between the ovary and the fallopian tube, resulting in unnecessary removal
  of ovarian tissue that could have been preserved.

EVIDENCE FROM THE MEDICAL RECORD:
  [6,000 tokens of retrieved blocks, each with its block_id, page number,
   and section context. Operative report, pathology report, tissue exam.]

INSTRUCTIONS:
  1. Does the evidence SUPPORT, CONTRADICT, or is it SILENT on this allegation?
  2. Cite specific block_ids for every factual claim.
  3. If the evidence is contradictory, explain both sides.
  4. Flag any missing documents that would be needed to fully resolve this allegation.
```

This prompt goes to a reasoning model — Claude Sonnet or Opus, dispatched to the local nanobot fleet or directly to the Anthropic API.

The agent dispatches all 7 allegations in parallel. Each returns a structured verdict:

```json
{
  "allegation_id": "A01",
  "status": "supported",
  "record_evidence": "The tissue exam report (page 117, block /page/116/Text/6) states: 'Received in formalin labeled with the patient's name and 'left fallopian tube and ovary' is a 5.5 cm length of fallopian tube with attached fibrofatty tissue and a 2.8 x 1.5 x 0.8 cm portion of tan-pink soft tissue consistent with ovary.' The operative report (page 14, block /page/13/SectionHeader/2) describes the procedure as 'left salpingectomy' but does not mention adhesions, lysis of adhesions, or any attempt to separate the ovary from the fallopian tube prior to removal. The pathology report confirms ovarian tissue was present in the specimen, directly contradicting the surgeon's statement to the patient that 'the ovary was in perfect shape.'",
  "claims": [
    {
      "claim": "Ovarian tissue was present in the removed specimen",
      "status": "supported",
      "evidence": [
        {
          "quote": "a 2.8 x 1.5 x 0.8 cm portion of tan-pink soft tissue consistent with ovary",
          "block_id": "/page/116/Text/6",
          "page": 117
        }
      ]
    },
    {
      "claim": "The operative report does not document adhesiolysis",
      "status": "supported",
      "evidence": [
        {
          "quote": "The left fallopian tube was identified and found to be torsed. The tube was dissected free and removed using bipolar cautery.",
          "block_id": "/page/13/Text/4",
          "page": 14
        }
      ]
    }
  ],
  "missing_documents": ["Laparoscopic video recording (if available)", "Pre-operative ultrasound images", "Informed consent form with specific risks discussed"]
}
```

**Time:** ~45 seconds for all 7 allegations in parallel. **Cost:** ~$1.50 (Claude Sonnet) to ~$5.00 (Opus).

### Phase 5: Citation Audit (Deterministic)

For every claim in every verdict, the system verifies the quoted text actually appears in the cited block:

```sql
SELECT id, text_content ILIKE '%' || $quoted_snippet || '%' AS match_found
FROM blocks WHERE id = $cited_block_id;
```

If a quote doesn't match (fuzzy match threshold < 80%), the claim is flagged. The system can either:
- Auto-retry that allegation with the failed quotes annotated ("These quotes could not be verified — use only exact text from the provided blocks")
- Flag for human review: "The agent claims X but the cited block does not contain the quoted text"

**Time:** < 1 second per claim. **Cost:** $0.

### Phase 6: Synthesis and Output

The agent now has:
- A case brief with parties, allegations, and case theory
- 7 allegation verdicts, each with cited evidence
- A structured timeline of events extracted from the record
- A list of red flags (discrepancies, missing documents, contradictions)

It calls the LLM one final time to synthesize everything into the 5-part case screening report. This is a single LLM call, ~$0.10. The prompt includes the full structured data; the LLM's job is prose organization, not factual discovery.

**Output:** `07_case_report.md` + `07_case_report.json` + `07_case_report.html` (rendered for human reading, with hyperlinked citations).

### Phase 7: Human Review

The user opens the report. They read Section 2 (Allegations vs. Record) and see that A01 is marked **SUPPORTED.** They click the citation and see the exact block from the pathology report on page 117. They can navigate to surrounding blocks for full context. They can compare the operative report against the pathology report side-by-side.

If they disagree with a conclusion, they can see exactly what evidence the agent relied on and form their own judgment. The agent's job was not to replace the reviewer — it was to do the legwork of finding, organizing, and citing the evidence so the reviewer can make an informed decision in minutes instead of days.

---

## How This Adapts to Different Case Types

The same architecture handles different domains by switching the **extraction schemas, search strategies, and output templates.** The ingestion and evidence store don't change.

### E-Discovery

**The user provides:** A set of search terms, custodians, a date range, and relevance criteria. Uploads 50,000 emails and attachments.

**The agent:**
1. Structural: Indexes email metadata (from, to, date, subject) as sections; email bodies and attachments as blocks
2. Keyword: FTS across all documents for the search terms
3. Semantic: Vector search for conceptually relevant documents that don't hit on keywords
4. Analytical: SQL to find communication patterns — "who talked to whom about what and when?"
5. Output: Privilege log, relevance-tagged document index, chronological email timeline, exhibit list

**Key difference from medical review:** Volume is much higher, individual document importance is lower. The search strategy emphasizes recall (find everything) over precision (find the right 15 blocks). The agent uses SQL aggregation heavily — "show me the top 10 most emailed domains" — before diving into individual documents.

### Contract Review

**The user provides:** A stack of contracts. Asks: "What are the indemnification obligations? Who has the most favorable termination clause?"

**The agent:**
1. Structural: Indexes each contract by article and section
2. Keyword: FTS for "indemnify," "hold harmless," "terminate," "cure period"
3. Semantic: Vector search for clauses that are functionally equivalent but differently worded — "indemnify and hold harmless" vs. "shall defend, indemnify, and hold harmless" vs. "agrees to assume liability for"
4. Analytical: SQL to build a comparison matrix — each contract is a column, each clause type is a row
5. Output: Clause comparison table, risk summary, recommended negotiation positions

**Key difference from medical review:** The unit of analysis is the clause, not the block. The agent needs to understand that a single obligation may span multiple blocks or sections. Cross-document comparison is primary.

### RFP Response

**The user provides:** An RFP document and a library of past responses, capability statements, and boilerplate.

**The agent:**
1. Structural: Extracts RFP requirements by section — each requirement becomes a row
2. Semantic: For each requirement, searches the response library for relevant past content
3. Analytical: Tracks which requirements have been addressed, which need new content, and which are ambiguous
4. Output: First-draft RFP response with requirement-to-response mapping, flagging gaps for human input

**Key difference:** The agent is matching requirements to existing content, not discovering new facts. The output is a draft, not a final product. The human is expected to review and customize.

---

## Design Principles (Non-Negotiable)

### 1. Citation-Anchored Everything

No floating facts. No "the record suggests." Every factual claim is linked to a specific source block. If the agent says something happened, it can show you exactly where it came from. This is what makes the output **legally defensible.**

### 2. The Agent Has Eyes

The agent does not guess. It does not rely on summary. It reads the source blocks directly — via SQL, via search, via context windows. When it makes a claim, it has seen the evidence.

### 3. Deterministic Where It Matters

Ingestion and indexing are deterministic — same document produces the same blocks, same sections, same embeddings. Extraction is LLM-driven but the schema constrains it. The audit layer verifies it.

### 4. Domain-Agnostic Evidence Layer

The ingestion pipeline and evidence store do not know what a "medical record" or a "credit report" is. They know about documents, pages, sections, and blocks. Domain understanding lives in the prompts, the extraction schemas, and the output templates — not in the storage layer.

### 5. The Agent Owns Its Workspace

The agent can write SQL. It can create tables. It can structure its own intermediate state. This is not a chatbot with a search bar — it is an intelligence that can **organize information.**

### 6. Progressive Structure

Documents enter unstructured (PDF) → become semi-structured (DataLab JSON) → become queryable (blocks in Postgres) → become structured (extracted into case core tables). Each layer adds value without destroying the layers below it.

### 7. The User Provides the Lens

The agent is powerful but it is not clairvoyant. The user sets the direction: the allegations, the key questions, the case theory. The agent does the legwork of finding, organizing, and citing the evidence. The user makes the final judgment. This is an augmentation tool, not an automation tool.

---

## Resolved Design Decisions

These are decisions we've already made. They are recorded here so we don't re-litigate them, and so we understand the trade-offs we accepted.

### 1. Narrative-first user input, not form-first

**Decision:** The primary input mechanism is a single narrative text area with adaptive placeholder text that changes based on `case_type`. Structured fields (party names, dates, case number) are optional shortcuts. The agent extracts structure from the narrative via Stage 0 intake.

**Why:** Attorneys think in narratives, not form fields. A narrative contains subtext — case theory, priorities, tone — that a form strips out. Adaptive placeholder text guides the user toward providing the kind of information that helps the agent without constraining them to a rigid structure.

**Trade-off accepted:** The agent must be good at extracting structure from narrative text. We already have a working Stage 0 intake pipeline that does this. It costs ~$0.02 per extraction. Worth it.

### 2. No document summaries on ingest

**Decision:** We do not generate LLM summaries of documents at upload time. Instead, we do structural indexing (section outline), extract cheap metadata (page count, document type, dates), and rely on on-demand deep reads when the agent needs to understand something specific.

**Why:** Summarizing a 327-page medical record is expensive (~$2-5) and produces output too vague to be actionable. The section outline is free, deterministic, and more useful — knowing the document has "Operative Report (pp. 12-16)" and "Pathology Report (pp. 28-31)" is more valuable than a paragraph saying "this is a medical record about a salpingectomy." The agent discovers content by searching, not by reading summaries.

**Trade-off accepted:** The agent has no high-level "this document is about X" summary to orient itself. It compensates by reading the section structure first and by using the user's intake narrative as the lens. For very large document sets (e-discovery with thousands of documents), we may revisit this — but the summary would be a one-line document type classification, not a prose paragraph.

### 3. Multi-step composable search, not single-pass retrieval

**Decision:** The agent composes search primitives (structural → keyword → analytical → contextual → extractive → verify) rather than relying on a single retrieval call. No search type is sufficient alone. The agent chooses the composition based on what it's trying to answer.

**Why:** A single vector search for "WBC normal after surgery" can miss exact keyword matches, return results from the wrong section, or fail to capture temporal trends. Structural scoping narrows the search to the right section. Keyword search guarantees recall. Analytical SQL surfaces patterns. Contextual expansion provides readability. The LLM extracts and reasons. The citation audit verifies. Each step does what it does best.

**Trade-off accepted:** Multiple round-trips to the database. Each round-trip is cheap (< 50ms for SQL, < 10ms for vector), so the total latency is dominated by the final LLM call, not the search chain.

### 4. PostgreSQL as the single data store

**Decision:** Evidence blocks, sections, embeddings, case core entities, and agent workspace all live in PostgreSQL. pgvector for embeddings, tsvector for full-text search, standard relational tables for structured data. No separate vector database. No document store.

**Why:** One database means the agent can JOIN across evidence and case core in a single query. "Find all blocks where the respondent's name appears within 5 pages of a mention of 'adhesion'" is a single SQL query, not a federated search across three systems. pgvector performance is adequate for our scale (tens of thousands of blocks per case, not millions). We can always migrate to a dedicated vector store later if needed.

**Trade-off accepted:** pgvector is not as fast as Pinecone or Weaviate at very large scale (>10M vectors). We accept this because our unit of scale is the case (thousands to tens of thousands of blocks), not the corpus (millions of cases). Each case's evidence store is independent.

### 5. The user provides the lens; the agent does the legwork

**Decision:** The agent is an augmentation tool, not an automation tool. The user sets the direction (allegations, case theory, key questions). The agent finds, organizes, and cites the evidence. The user makes the final judgment.

**Why:** Legal and medical decisions require professional judgment, context, and accountability. The agent can find that the pathology report contradicts the operative note — but the attorney decides whether that rises to the level of a standard-of-care violation. The agent can flag a documentation gap — but the reviewer decides whether the gap matters.

**Trade-off accepted:** The system cannot operate fully autonomously. It requires a human in the loop. This is intentional.

### 6. Domain-agnostic evidence layer, domain-specific everything else

**Decision:** The ingestion pipeline and evidence store (`documents`, `sections`, `blocks`) are identical regardless of whether the case is a medical board complaint, an RFP response, or a contract review. Domain understanding lives in the extraction schemas, search strategies, prompts, and output templates.

**Why:** Building a separate ingestion pipeline and storage schema for each document type would be a maintenance nightmare. A medical record and a credit report are structurally similar — both have pages, sections, headers, tables, and text blocks. The difference is in what you look for and how you interpret it, not in how you store it.

**Trade-off accepted:** The universal block model loses some domain-specific structure. A lab result table and a contract payment schedule are both stored as "Table" blocks — the agent must understand the difference from context, not from the schema. This is acceptable because the LLM is good at interpreting context, and the alternative (per-domain schemas) would fragment the query layer.

### 7. Workspaces are deferred; schema support is not

**Decision:** Workspaces as a user-facing concept (scoped views into a case, each with its own documents, questions, and outputs) are deferred. But the schema is designed to support them from day one: `workspace_id` as a nullable foreign key on documents, events, extractions, and outputs. If null, the entity is case-global.

**Why:** A litigation case moves through phases — motion to dismiss, discovery, summary judgment, trial prep. Each phase uses different subsets of the evidence and produces different outputs. Retrofitting workspace scoping into a flat case model would require schema migration across every table. Adding a nullable column now costs nothing and prevents that pain.

**Trade-off accepted:** We are designing for a feature we haven't built yet. The risk is that when we actually build workspaces, we realize the model is wrong and the nullable column wasn't sufficient. This risk is low — the concept of "scoped view into a case" is well-understood — and the cost of the column is zero.

### 8. Strategy facts ≠ case events

**Decision:** Raw events (what happened) and strategy facts (what this means for our legal argument) are separate tables in separate layers. Events live in the case core. Strategy facts live in the strategy layer with an optional `core_event_id` FK back to events. The same event can be characterized differently in different strategies.

**Why:** This separation enables the permutation engine — re-characterize the same event (offensively vs. defensively) and recompute the tree. It also preserves the integrity of the case core: events are the historical record, strategy facts are argumentative interpretations. Conflating them would make it impossible to test alternative characterizations.

**Trade-off accepted:** Two tables where one might seem sufficient. This adds JOIN complexity but preserves the ability to permute characterizations later.

### 9. Doctrine trees are reusable across cases

**Decision:** The `doctrine_elements` table stores element definitions by jurisdiction independently of any case. "Negligence — Duty/Breach/Causation/Damages (Georgia)" is defined once and instantiated into `strategy_propositions` for each case that needs it. Gate logic (AND/OR) lives on `strategy_propositions`, not `doctrine_elements`, because the same element can be AND in one claim and OR in another.

**Why:** The doctrine tree models the law, not the case. The same negligence elements apply whether the case is a car accident or a surgical error. Only the fact mappings and adversarial walks are case-specific. Reusable doctrine trees save agent work and ensure consistency.

**Trade-off accepted:** Maintaining the doctrine library requires curation. An element defined incorrectly will propagate to every case that uses it. We accept this because the alternative — re-deriving elements per case — is more error-prone and wasteful.

### 10. Adversarial turns are structured rows, not JSONB

**Decision:** Each turn (T1→T2→T3→T4) in the adversarial walk is an independent row in `adversarial_turns` with metadata: turn number, author type (ADVERSARY/DEFENDER/ATTORNEY), turn result (STRONG/ADEQUATE/WEAK/NO_RESPONSE), and primary authority. Not a JSONB blob.

**Why:** Queryability. "Find every contested path where our counter-argument lacks a verified pincite" is a SQL query against structured rows. It's not possible against JSONB. The adversarial walk is the most valuable output of the strategy engine — if it can't be queried, it can't be quality-controlled.

**Trade-off accepted:** 4 rows per attack instead of 1 JSONB field. More storage, but the queryability pays for it.

### 11. The gauntlet is systematic and reusable

**Decision:** Gauntlet checks are defined in a reference table (`gauntlet_check_definitions`) and applied to strategies via `strategy_gauntlet_results`. Checks are organized by attack surface (Standing, Licensing, Preclusion, Timing, Pleading, Evidence, Remedies, Party-Specific). Each check produces PASS, FAIL, or INQUIRY.

**Why:** The gauntlet catches what element-by-element analysis misses. The OFR license example: no element of a wrongful repossession claim requires the collector to be licensed, so element analysis never checks it. But the gauntlet's Licensing check catches it, and it becomes an independent basis for a claim or defense. Systematic screening prevents blind spots.

**Trade-off accepted:** The gauntlet is only as good as its check catalog. Missing checks mean missing vulnerabilities. The catalog must grow over time as new attack surfaces are discovered.

---

## What We've Already Built

### Evidence + Case Core

| Component | Status | Location |
|---|---|---|
| DataLab OCR integration | Working | `scripts/datalab_eval/` |
| Evidence store schema (Postgres + pgvector) | Working | `scripts/section_mapping_20260505/pipeline/db.py` |
| Stage 0 intake (CaseBrief extraction) | Working | `scripts/section_mapping_20260505/pipeline/stage0_intake.py` |
| Stage 1 OCR indexing | Working | `scripts/section_mapping_20260505/pipeline/stage1_datalab.py` |
| Stage 2 structural indexing | Working | `scripts/section_mapping_20260505/pipeline/stage2_index.py` |
| Stage 3 embedding (pgvector) | Working | `scripts/section_mapping_20260505/pipeline/stage3_embed.py` |
| Stage 4 retrieval (per-allegation) | Working | `scripts/section_mapping_20260505/pipeline/stage4_retrieve.py` |
| Stage 5 reasoning (nanobot dispatch) | Spec exists | `scripts/section_mapping_20260505/pipeline/stage5_reason.py` |
| Citation auditor (SQL-based quote verification) | Designed | `06-nanobot-architecture.md` |
| Medical review schemas (Pydantic) | Working | `scripts/medical_review/pipeline/schemas.py` |
| Nanobot fleet (Dockerized LLM dispatch) | Working | `scripts/rene/nanobot_review/` |
| Chunking + extraction pipeline (Mistral) | Working | `scripts/medical_review/pipeline/` |
| Report rendering (HTML/PDF) | Working | `scripts/section_mapping_20260505/pipeline/render_html.py` |

### Strategy Engine

| Component | Status | Location |
|---|---|---|
| Strategy vision + architecture | Written | `vision/strategy-destination.md` |
| Strategy schema (14 tables, seed data) | Written | `vision/002_strategy_schema.sql` |
| Schema implementation plan (12 design decisions) | Written | `vision/strategy-schema-plan.md` |
| Open questions + cosmic exploration | Written | `vision/discussions/strategy-open-questions.md` |
| Execution flow (agent delegation model) | Written | `vision/execution/strategy_execution.md` |
| Rhetorical moves taxonomy (11 moves) | Seed data in schema | `002_strategy_schema.sql` |
| Gauntlet check catalog (8 categories, 20+ checks) | Seed data in schema | `002_strategy_schema.sql` |
| Doctrine tree structure | Working in files | `doctrine.json`, `element-map.json` (CPS case) |
| Fact inventory with sources | Working in files | `fact-inventory.json` (CPS case) |
| Adversarial walk with T1→T4 dialectic | Working in files | `adversarial-analysis.json` (CPS case) |
| Gate logic walk (AND/OR propagation) | Spec | Step 4 contract |

---

## The Name

**Vision.** Because that's what we're giving the agent — the ability to see the entire case, not just the document someone handed it. Complete visibility. No blind spots.

---

*This document is the North Star. Every architectural decision, every pipeline stage, every schema change should move us closer to this destination. If a decision doesn't serve this vision, it's the wrong decision.*
