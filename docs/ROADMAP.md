# Implementation Roadmap

Status: ▢ pending | ▣ in progress | ✓ complete

---

## Phase 0: Foundation

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 0.1 | `Vision/Destination.md` — North Star vision | ✓ | — | Defines what we're building and why. |
| 0.2 | `vision/schema.sql` — Database schema v1.0 | ✓ | — | Tables, indexes, constraints. The data contract. |
| 0.3 | Review and finalize schema | ▢ | 0.2 | Argue about column names, types, missing entities. Lock it. |

---

## Phase 1: Database Layer

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 1.1 | `vision/db.py` — Connection + schema management | ▢ | 0.3 | Port/enhance from `section_mapping_20260505/pipeline/db.py`. `connect()`, `ensure_schema()`, insert helpers. |
| 1.2 | `vision/db_test.py` — Schema smoke test | ▢ | 1.1 | `ensure_schema()` runs idempotent. Every table and index exists. |
| 1.3 | Docker Compose for local Postgres + pgvector | ▢ | — | Single `docker-compose.yml` that boots a dev database. No install instructions needed. |
| 1.4 | `.env.example` — DB credentials + API keys | ▢ | 1.3 | `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`, `DATALAB_API_KEY`, `MISTRAL_API_KEY`, `ANTHROPIC_API_KEY`. |

---

## Phase 2: Ingestion Pipeline

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 2.1 | `vision/ingest.py` — PDF → DataLab → Postgres | ▢ | 1.1, 1.3 | Port from `stage1_datalab.py`. Takes a PDF path + case_id. Submits to DataLab, polls, normalizes JSON into `documents`, `sections`, `blocks`, `block_headings`. |
| 2.2 | `vision/ocr.py` — DataLab client wrapper | ▢ | 2.1 | Port from `datalab_eval/run_convert.py`. `convert_pdf(pdf_path) → result`. Retry logic. Cost estimation. |
| 2.3 | `vision/normalize.py` — DataLab JSON → schema rows | ▢ | 2.1 | Walk the hierarchical JSON. Extract pages, sections, blocks, heading chains. Insert in correct order (documents first, then sections, then blocks, then headings). |
| 2.4 | `vision/index_fts.py` — Full-text search population | ▢ | 2.3 | Trigger tsvector generation (handled by generated columns already). Verify indexes are populated. |
| 2.5 | Ingestion smoke test | ▢ | 2.1-2.4 | Run against the 327-page Wellstar record. Verify: document row exists, ~220 sections, ~8,500 blocks, heading chains correct, FTS returns results. |

---

## Phase 3: Embedding + Semantic Search

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 3.1 | `vision/embed.py` — Section-level embedding | ▢ | 2.4 | Port from `stage3_embed.py`. For each section, concat `search_text`, call Mistral embed API, store in `sections.embedding`. Cache in `embedding_cache`. |
| 3.2 | `vision/search.py` — Hybrid search primitives | ▢ | 3.1 | `search_by_keyword(query, scope)`, `search_by_vector(query_text, scope)`, `search_hybrid(query, scope)` — combine FTS + vector with result fusion. |
| 3.3 | Embedding smoke test | ▢ | 3.2 | "post-operative WBC count" returns the Laboratory Results and Discharge Summary sections. |

---

## Phase 4: Query Tools (Agent SDK Interface)

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 4.1 | `vision/tools.py` — `get_document_structure(doc_id)` | ▢ | 2.3 | Return the section outline with page ranges. The agent's first call almost every time. |
| 4.2 | `vision/tools.py` — `search_blocks(query, scope?)` | ▢ | 3.2 | Hybrid search. Optional scope filters (document_id, page range, section_id, block_type). Returns ranked blocks with context. |
| 4.3 | `vision/tools.py` — `get_block_context(block_id, window=3)` | ▢ | 2.3 | Return ±N surrounding blocks. SQL: blocks ±N by page and position. |
| 4.4 | `vision/tools.py` — `list_documents(case_id)` | ▢ | 2.3 | Return all documents for a case: name, page count, type, status. |
| 4.5 | `vision/tools.py` — `execute_readonly_sql(sql)` | ▢ | 1.1 | Execute agent-written SQL in a read-only transaction. The critical freedom tool. |
| 4.6 | `vision/tools.py` — `get_case(case_id)` | ▢ | 1.1 | Return full case core: case info, parties, allegations, events extracted so far. |
| 4.7 | Tool smoke test | ▢ | 4.1-4.6 | Each tool called against a populated case. Returns expected shape. |

---

## Phase 5: Case Management

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 5.1 | `vision/case.py` — `create_case(name, case_type, narrative)` | ▢ | 1.1 | Insert case row. Return case_id. |
| 5.2 | `vision/case.py` — `add_party(case_id, name, party_kind, roles)` | ▢ | 5.1 | Insert party row. |
| 5.3 | `vision/case.py` — `add_allegations(case_id, allegations_list)` | ▢ | 5.1 | Insert allegation rows. |
| 5.4 | `vision/case.py` — `upload_document(case_id, pdf_path)` | ▢ | 2.1, 5.1 | Full ingest pipeline triggered from a single call. |

---

## Phase 6: Stage 0 — Intake Processing

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 6.1 | `vision/intake.py` — Narrative → CaseBrief extraction | ▢ | 5.1 | Port from `stage0_intake.py`. LLM call with structured output schema. Extracts patient, respondent, encounter dates, allegations, case theory, extraction focus. |
| 6.2 | `vision/intake.py` — Party discovery pass | ▢ | 6.1 | Cross-reference extracted names against existing parties. Suggest additions. |
| 6.3 | `vision/intake.py` — Document structure review | ▢ | 6.1, 4.1 | Call `get_document_structure()` on all case documents. Identify high-signal sections based on allegations and extraction focus. |
| 6.4 | Intake smoke test | ▢ | 6.1-6.3 | Narrative → structured brief. Parties suggested. Key sections flagged. |

---

## Phase 7: Agent Reasoning Loop

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 7.1 | `vision/reason.py` — Assemble allegation context | ▢ | 6.3, 4.2 | For each allegation: scope to relevant sections, search for evidence blocks, expand context, assemble prompt. |
| 7.2 | `vision/reason.py` — Dispatch to LLM | ▢ | 7.1 | Structured output: verdict (supported/contradicted/silent/partial), claims, cited evidence. Parallel dispatch for all allegations. |
| 7.3 | `vision/audit.py` — Citation verification | ▢ | 7.2, 2.3 | For every quote in every verdict: `SELECT text_content ILIKE '%quote%' FROM blocks WHERE id = $block_id`. Flag failures. |
| 7.4 | `vision/reason.py` — Retry on audit failure | ▢ | 7.3 | If a quote fails verification, re-dispatch with flagged quotes annotated. Max 1 retry. |
| 7.5 | Reasoning smoke test | ▢ | 7.1-7.4 | Full run against Alhad case. 7 allegation verdicts, all citations verified. |

---

## Phase 8: Output Generation

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 8.1 | `vision/synthesize.py` — Merge verdicts into report | ▢ | 7.5 | Single LLM call: structured data → prose report. Sections: header, allegations vs record, timeline, red flags, recommendation. |
| 8.2 | `vision/render.py` — HTML + Markdown output | ▢ | 8.1 | Port from `render_html.py`. Citation hyperlinks. Printable. |
| 8.3 | End-to-end smoke test | ▢ | 8.2 | Full pipeline: create case → ingest PDF → process intake → reason → synthesize → render. Output matches expected structure. |

---

## Phase 9: Agent Integration

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 9.1 | MCP server tools — Expose query tools as MCP tools | ▢ | 4.7 | Agent SDK integration. `search_evidence`, `get_block_context`, etc. available to Claude Code. |
| 9.2 | Agent prompt — System instructions for the War Room Agent | ▢ | 9.1 | How the agent should compose search, when to use SQL, citation discipline, output format expectations. |
| 9.3 | Agent smoke test | ▢ | 9.2 | "Was the patient's WBC count ever normal after surgery?" Agent composes search chain, returns cited answer. |

---

## Phase 10: Strategy Engine — Schema + Doctrine Library

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 10.1 | Review and finalize strategy schema | ▢ | 0.3 | `002_strategy_schema.sql` exists. Review for alignment with core schema. Resolve any FK or type conflicts. |
| 10.2 | Port file-based doctrine trees to `doctrine_elements` | ▢ | 10.1 | `doctrine.json` → `doctrine_elements` rows. Template trees for: negligence, wrongful repossession, FDCPA, GFBPA, TRO four-factor. |
| 10.3 | Port file-based facts to `case_facts` + `strategy_facts` | ▢ | 10.2 | `fact-inventory.json` → case_facts. Element maps → strategy_facts + proposition_fact_mappings. |
| 10.4 | Port adversarial walks to structured rows | ▢ | 10.3 | `adversarial-analysis.json` → adversarial_attacks + adversarial_turns. One row per turn. |
| 10.5 | Doctrine library smoke test | ▢ | 10.4 | CPS TRO case fully ported from files to database. Doctrine tree, facts, mappings, adversarial walk all queryable. |

---

## Phase 11: Strategy Engine — Gate Logic + Gauntlet

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 11.1 | `vision/gate_walk.py` — Deterministic AND/OR propagation | ▢ | 10.5 | Pure function. Reads `strategy_propositions` tree. Walks upward from leaves. Outputs SPOF map, pressure ranking, disposition. No LLM. |
| 11.2 | `vision/gauntlet.py` — Gauntlet runner | ▢ | 10.5 | Runs `gauntlet_check_definitions` against a strategy. Produces `strategy_gauntlet_results`. Systematic cross-claim screening. |
| 11.3 | Gate logic smoke test | ▢ | 11.1 | CPS TRO tree: E1 (AND) with E1.1 CONTESTED produces E1: CONTESTED. E6 (AND over E1-E5) with any child CONTESTED produces E6: CONTESTED. |
| 11.4 | Gauntlet smoke test | ▢ | 11.2 | OFR license check catches license-gap issue. Standing check catches chain-of-title gap. |

---

## Phase 12: Strategy Engine — Agent Integration

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 12.1 | Doctrine agent — "Research elements for [claim] under [jurisdiction]" | ▢ | 10.5 | Agent tool that researches and populates `doctrine_elements` + `strategy_propositions`. |
| 12.2 | Adversary agent — "Attack this proposition from opposing party's perspective" | ▢ | 12.1 | Blind sub-agent. Sees element + doctrine, not our responses. Populates T1, T3. |
| 12.3 | Defender agent — "Respond to this attack" | ▢ | 12.2 | Sees the attack + the full strategy. Populates T2, T4. |
| 12.4 | Strategy agent smoke test | ▢ | 12.3 | Full run: user provides claim → agent builds tree → maps facts → walks adversary → runs gauntlet → presents SPOF map. |

---

## Phase 13: Workspaces (Deferred — Schema Support Exists)

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 13.1 | Workspace creation and scoping UI | ▢ | 5.1 | Create workspace within a case. Scope documents. Set key questions. |
| 13.2 | Workspace-aware agent behavior | ▢ | 13.1 | Agent filters evidence by workspace scope. Output is workspace-scoped. |
| 13.3 | Workspace inheritance | ▢ | 13.2 | Discovery workspace inherits parties and documents from motion to dismiss workspace. |

---

## Phase 14: Additional Document Types + Case Types

| # | Step | Status | Dependencies | Notes |
|---|---|---|---|---|
| 14.1 | Contract review schemas + prompts | ▢ | 8.3 | Clause extraction, obligation tracking, comparison matrix output. |
| 14.2 | E-discovery schemas + prompts | ▢ | 8.3 | Custodian indexing, search term hit reports, privilege log output. |
| 14.3 | RFP response schemas + prompts | ▢ | 8.3 | Requirement extraction, past response matching, gap analysis output. |

---

## Dependency Graph (Simplified)

```
Phase 0: Foundation         ─── schema, vision docs
    ↓
Phase 1: Database Layer     ─── db.py, Docker
    ↓
Phase 2: Ingestion          ─── PDF → DataLab → Postgres
    ↓
Phase 3: Embedding          ─── pgvector, FTS
    ↓
Phase 4: Query Tools        ─── search_blocks, get_context, execute_sql
    ↓
Phase 5: Case Management    ─── create_case, add_party, upload_document
    ↓
Phase 6: Intake             ─── narrative → CaseBrief
    ↓
Phase 7: Reasoning          ─── allegation → evidence → verdict
    ↓
Phase 8: Output             ─── synthesize → render
    ↓
Phase 9: Agent Integration  ─── MCP tools, system prompt
    ↓
Phase 10: Strategy Schema   ─── port file-based data to DB
    ↓
Phase 11: Gate Logic        ─── deterministic walk, gauntlet runner
    ↓
Phase 12: Strategy Agents   ─── doctrine, adversary, defender agents
    ↓
Phase 13: Workspaces        ─── (deferred)
    ↓
Phase 14: More Case Types   ─── contracts, e-discovery, RFPs
```
