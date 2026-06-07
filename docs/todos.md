# Vision — Implementation Todos

---

## Agent Synthesis (Post-SDK)

**What:** After a user saves a case narrative, the agent (via Claude SDK) extracts structured data — parties, allegations, case theory, extraction focus. This is the Phase 2 "Case Brief Extraction" from `Destination.md`.

**Why:** Converts unstructured narrative into structured data the system can act on. Parties → search documents by name. Allegations → analyze evidence against each one. Extraction focus → scope document search to relevant sections.

**Trigger:** Narrative saved AND at least one document ingested. Firing it without documents is wasteful — extraction focus like "operative report" is useless with nothing to search.

**Dependencies:**
- Claude/Anthropic SDK wired up
- Structured output schemas defined (CaseBrief Pydantic model)
- Parties and allegations tables exist in schema (they do — `CaseManager.add_party`, `CaseManager.add_allegation`)
- Frontend: Overview tab shows extracted parties/allegations instead of static placeholders

**Not started.** Blocked on SDK integration.

---

## Document Ingestion Wiring

**Status:** Recon complete. See `docs/ingestion-plan.md`.

---

## Chat Implementation

**Status:** Placeholder UI in `ChatTab.tsx`. Not wired.

**Dependencies:** Agent SDK.

---

## Drafting System

**Status:** Placeholder UI in `DraftsTab.tsx`. Not designed yet.

**Dependencies:** Strategy engine, agent SDK, drafting templates.
