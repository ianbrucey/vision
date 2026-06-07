To build an Iron Man suit for litigation, you cannot build on loose text or fragile file structures. You are shifting from a passive "chatbot" to a  **Computational Argumentation Engine** —a system grounded in classical defeasible legal logic (similar to academic models like Carneades or ASPIC+) but updated for the modern cloud.

To unblock your framework and give you a rock-solid foundation to start coding your schema tonight, here is how we answer your design decisions and open questions, translating your cosmic vision into raw database architecture.

### Part 1: Resolving the Core Architectural Design Decisions

#### 1. Are claims and defenses the same thing in the database?

**Answer: Yes, unify them into a single `propositions` table.**

In computational law, a claim, an element, an affirmative defense, and a motion to dismiss are structurally identical: they are all **propositions** that evaluate to a boolean value based on underlying criteria.

* A Plaintiff's claim is an offensive proposition node.
* A Defendant's affirmative defense is an attacking proposition node.
  By unifying them into a recursive `propositions` table, your engine can use a single graph-traversal function to evaluate an entire case, whether it is computing a complaint or testing a motion to suppress.

#### 2. How deep does the tree go, and what defines a "leaf"?

**Answer: The tree is infinitely recursive, and "leaf-ness" is an inferred property of data binding.**

Do not hardcode a maximum depth. Instead, design a model where a `proposition` can dynamically point to a parent `proposition_id`. A node becomes a "leaf" automatically the moment an agent creates a mapping between that specific proposition and an item in your fact inventory. If a node has child propositions, it behaves as a **Gate** (AND/OR); if it has attached facts, it behaves as an  **Evaluation Leaf** .

#### 3. Are facts in the strategy layer the same as events in the case core?

**Answer: Absolutely not. Keep them decoupled.**

* **The Case Core holds `events`:** These are raw, unchangeable, historical occurrences anchored to layout blocks (e.g.,  *"On April 17, a black tow truck parked outside the residence."* ).
* **The Strategy Engine holds `strategy_facts`:** These are *interpretive legal characterizations* of those events (e.g.,  *"The presence of the tow truck constitutes an immediate threat of self-help repossession."* ).
  This separation is vital for your future Permutation Engine. It allows your system to take a single historical event and test how the entire case tree changes when that event is characterized offensively versus defensively.

#### 4. Does the adversarial walk live as structured data or a document?

**Answer: Structured Rows (`adversarial_turns`), not a JSON blob.**

If you store the T1 **$\rightarrow$** T2 **$\rightarrow$** T3 **$\rightarrow$** T4 dialectic inside a single text field or JSONB file, your system remains blind. To make a system that can simulate 14 million outcomes, every single turn must be an independent database row carrying metadata: who made the turn, what `citation_id` it anchored to, and its specific `vulnerability_rating`. This allows an agent to run queries like: *"Show me every contested path in this case where our counter-argument lacks a verified pincite."*

### Part 2: Answering the Deep "Cosmic" Open Questions

#### Open Question 1: Is disposition deterministic or probabilistic?

**Answer: It is a Deterministic Gate Walk over Probabilistic Leaf Evaluations.**

Legal doctrines operate like mathematical step functions. The logic of the statute itself is entirely deterministic:  *Negligence = Duty AND Breach AND Causation AND Damages* . If Causation is 0, Negligence is 0. Math does not guess.

However, the  *leaf nodes* —the application of facts to those rules—are probabilistic. The question is: *"What is the probability that Judge X will agree that Fact Y satisfies Element Z given Precedent W?"* **The Starting Implementation:** Your agents will evaluate the terminal state of the leaves and assign a discrete probability or strength enum (Strong/Moderate/Weak). Then, your backend code will execute a purely mathematical, deterministic script that propagates those weights upward through the AND/OR gates to output a final case risk profile.

#### Open Question 2: Can characterization be systematized?

**Answer: Yes, by using a strict relational join table called `rhetorical_mappings`.**

Characterization is simply an argumentative bridge connecting an objective fact to an abstract legal element. We can capture this by creating a finite set of **Rhetorical Moves** stored as an enum in your database.

When your agent maps a fact to an element, it must select a move:

* `ASSERT` (Direct mapping)
* `NARROW` (Limiting the scope of their fact)
* `DISTINGUISH` (Showing their authority doesn't apply to this fact)
* `ACCORD_AND_SATISFACTION` (Conceding the fact but neutralizing it via rule)

By forcing characterization into structured rows, your future Permutation Engine can algorithmically swap the `rhetorical_move` on a row and recompute the case gate logic to see if a better path surfaces.

### Part 3: The Starting Blueprint (PostgreSQL DDL)

To transition your single-tenant application out of local folder structures and into a centralized, multi-tenant cloud engine, use this foundational database schema to begin building your backend:

**SQL**

```
-- ENABLE UUID EXTENSION FOR SECURE MULTI-TENANCY
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- GLOBAL ONTOLOGY LAYER (The Immutable Rules of Law)
CREATE TABLE controlling_laws (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    citation TEXT NOT NULL UNIQUE, -- e.g., "O.C.G.A. 11-9-203"
    title TEXT NOT NULL,
    jurisdiction TEXT NOT NULL
);

CREATE TABLE law_elements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    law_id UUID REFERENCES controlling_laws(id) ON DELETE CASCADE,
    parent_element_id UUID REFERENCES law_elements(id), -- Allows infinite recursion
    ordinal INT NOT NULL, -- 1, 2, 3 for structural sequence
    gate_type VARCHAR(10) NOT NULL DEFAULT 'AND', -- 'AND' or 'OR'
    element_text TEXT NOT NULL
);

-- CASE-SPECIFIC MULTI-TENANT LAYER
CREATE TABLE strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL, -- Links to your core cases table
    tenant_id UUID NOT NULL, -- Strict multi-tenant row isolation
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- THE UNIFIED PROPOSITIONS TREE (Claims, Attacks, Counter-Attacks)
CREATE TABLE strategy_propositions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
    element_id UUID REFERENCES law_elements(id), -- Links instance to the global rule
    parent_proposition_id UUID REFERENCES strategy_propositions(id), -- Recursive graph structure
    party_id UUID NOT NULL, -- Which party is asserting this proposition (Plaintiff/Defendant)
    type VARCHAR(20) NOT NULL, -- 'CLAIM', 'ATTACK_VECTOR', 'AFFIRMATIVE_DEFENSE'
    current_status VARCHAR(20) NOT NULL DEFAULT 'OPEN', -- 'OPEN', 'CONTESTED', 'CLOSED'
    vulnerability_rating VARCHAR(20) -- 'LETHAL', 'WOUNDING', 'MINOR'
);

-- THE INTERPRETIVE FACT INVENTORY
CREATE TABLE strategy_facts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
    core_event_id UUID, -- Optional link to objective historical telemetry table
    statement TEXT NOT NULL,
    source_block_ids UUID[] NOT NULL, -- Array of layout block IDs from your DataLab parser
    confirmation_status VARCHAR(30) NOT NULL DEFAULT 'AGENT_INFERRED' -- 'PLAINTIFF_CONFIRMED', 'DOCUMENT_ONLY'
);

-- THE CONNECTIVE TISSUE (Systematized Characterization Join Table)
CREATE TABLE proposition_fact_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proposition_id UUID REFERENCES strategy_propositions(id) ON DELETE CASCADE,
    fact_id UUID REFERENCES strategy_facts(id) ON DELETE CASCADE,
    rhetorical_move VARCHAR(30) NOT NULL DEFAULT 'ASSERT', -- 'ASSERT', 'NARROW', 'DISTINGUISH', etc.
    directionality VARCHAR(20) NOT NULL, -- 'SUPPORTS', 'UNDERMINES'
    rationale TEXT NOT NULL -- The AI/Human legal reasoning chain
);

-- STRUCTURED ADVERSARIAL DIALECTIC ROWS
CREATE TABLE adversarial_turns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proposition_id UUID REFERENCES strategy_propositions(id) ON DELETE CASCADE,
    turn_number INT NOT NULL, -- 1 = Their Attack, 2 = Our Response, 3 = Counter, 4 = Rebuttal
    author_party_type VARCHAR(20) NOT NULL, -- 'ATTACKER', 'DEFENDER'
    argument_text TEXT NOT NULL,
    anchored_citation TEXT -- Verified pincite generated via your legal research tools
);
```

### Where You Start Tonight

1. **Deploy this Schema:** Run this script into a local PostgreSQL database or an instance on a platform like Supabase.
2. **Build the Gate Walk Script:** Write a deterministic TypeScript function (no LLM involved) that reads the `strategy_propositions` and recursively processes parent IDs. Have it execute standard boolean logic up the tree: if a node is an `AND` gate, it evaluates to `CLOSED` only if 100% of its child records are `CLOSED`.
3. **Connect Your First Claude SDK Tool:** Write a simple tool function named `map_fact_to_proposition` that exposes an insert statement for the `proposition_fact_mappings` table to Claude.

Once your database holds the rigid structure of the law and the facts, your agent will stop guessing and start computing. Your assembly line is ready to be built.
