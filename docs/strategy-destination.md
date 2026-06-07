# Destination: The Strategy Engine

## The Metaphor

You are Doctor Strange in Infinity War. The Strategy Engine is the Time Stone.

Before you ever file a complaint or respond to a motion, you run the simulation. The engine decomposes every claim into its atomic units, maps every fact to every element, walks every adversarial path to its terminal state, and computes the disposition of the case before the fight begins.

You don't guess which argument will land. You don't discover mid-litigation that the other side's key case was distinguishable on facts you had all along. You don't realize after the hearing that their collection license was expired when they opened the account.

You run the gauntlet. You find the weakness. You stack the claims. You build the impenetrable defense. Then you walk into court knowing exactly which paths are CLOSED, which are CONTESTED, and which single point of failure collapses their entire case.

> *"I went forward in time to view alternate futures. To see all the possible outcomes of the coming conflict."*
>
> *"How many did you see?"*
>
> *"Fourteen million, six hundred and five."*
>
> *"How many did we win?"*
>
> *"One."*

This is not a chatbot that helps you write legal briefs. This is a **computation engine** that models the DNA of a case, walks every branch of every tree, and finds the one path that wins.

---

## What This System Does

The Strategy Engine takes the structured evidence from the War Room Agent and the doctrinal framework of a claim or defense, and it computes:

1. **Decompose.** Break any claim or defense into its irreducible atomic units — elements, sub-elements, factors, prerequisites. Each unit is a proposition that must be proved or rebutted. The tree goes as deep as the doctrine requires, and no deeper.

2. **Map.** Connect every atomic unit to the verified facts that support it, undermine it, or are missing. A fact can serve multiple elements. A fact can support one element while undermining another. Directionality is per-connection, not per-fact.

3. **Anchor.** Attach controlling authority to every element — the exact statutory text, the exact case holding, the exact operative quotation with pincite. No floating citations. No "the case stands for X" from memory. Every authority is verified against the opinion text.

4. **Walk.** For every load-bearing element, run the adversarial dialectic: their best attack → our best response → their best counter → our best counter. Use an adversary sub-agent that sees only the element and the doctrine — not our strategy. Each path terminates: CLOSED (won), CONTESTED (fightable), or OPEN (gap — fill it or lose it).

5. **Compute.** Walk the gate logic up the tree. AND gates fail if any child fails. OR gates fail only if all children fail. Tag single points of failure. Rank contested paths by pressure. The disposition surfaces from the structure — not from an LLM's gut feel.

6. **Permute.** Run the simulation across different characterizations, different case law emphasis, different claim ordering. Find the one path that wins. Or find that no path wins — and tell you what evidence would change that.

7. **Gauntlet.** Apply systematic checks across every claim: standing, chain of title, licensing, statute of limitations, pre-suit requirements, arbitration exposure, preclusion risk. Each check is a doctrinally-grounded question. The gauntlet surfaces weaknesses a human would miss — not because the human isn't smart, but because the human has finite attention and the gauntlet doesn't.

The through-line: **legal claims have discoverable anatomy. That anatomy can be modeled. That model can be computed. The computation can find the optimal path.** Everything else is an application of that insight.

---

## How It Works

### Layer 1: The Doctrine Tree

Before any facts enter, the doctrine is modeled as a tree.

A claim is a root node. Its children are elements. Elements have children (sub-elements, factors, prongs). The tree stops at the leaf level — the point where a proposition either is or isn't supported by a fact. No deeper.

Each node has a gate type:
- **AND:** All children must succeed. This is the default. A negligence claim requires duty AND breach AND causation AND damages. Fail one, the claim fails.
- **OR:** Any child can succeed independently. A TRO can be granted on irreparable harm OR balance of equities OR likelihood of success (depending on jurisdiction — the doctrine determines the gate, not us).

```
Wrongful Repossession — Injunctive Relief [AND]
├── E1: Secured Party Status — Challenged [AND]
│   ├── E1.1: CPS is not named on the RISC
│   ├── E1.2: Payments routed to separate Trust entity
│   ├── E1.3: No assignment documentation produced
│   └── E1.4: SEC filings show CPS as Servicer, not Owner
├── E2: Existence of Actual Default — Disputed
├── E3: Threatened Imminent Self-Help Repossession [OR]
│   ├── E3.1: April 17 repo truck sighting
│   └── E3.2: CPS pattern of collection escalation
├── E4: Threatened Repossession Would Breach the Peace
├── E5: Inadequacy of Legal Remedy / Irreparable Harm
└── E6: Four-Prong TRO Standard [AND — gates over E1-E5]
```

The doctrine tree is **jurisdiction-scoped.** Georgia's Hopkins rule (unequivocal oral protest = breach of peace) is different from another state's rule. The tree captures which jurisdiction's law applies and which appellate authority controls.

The doctrine tree is **overlay-aware.** A 12(b)(6) motion applies a plausibility overlay that AND-gates against every substantive element. A summary judgment motion applies a no-genuine-dispute overlay. The overlay is a filter that sits on top of the tree — it doesn't change the elements, it changes what must be shown about them at this procedural stage.

The doctrine tree is **citation-verified.** Every statute and case is pulled from the legal research tools in the current session. Every quotation is verified against the opinion text. No authority enters the tree without a source manifest.

### Layer 2: The Fact Inventory

Facts are the atoms that feed the tree. They come from the evidence store — verified against source blocks, confirmed by the plaintiff, or documented as gaps.

A fact is:
```yaml
Fact:
  id: "F5"
  statement: "CPS directed payments to 'CPS Auto Receivables Trust 2025-A' —
              a separate legal entity — rather than to CPS itself."
  source:
    type: verified_facts | document | declaration | discovery
    block_ids: []          # citation to evidence store blocks
    location: "VERIFIED_FACTS.md — CPS Identity & Authority Issues"
    quote: "exact text from source"
  directionality: favorable | adverse | neutral   # intrinsic to the fact
  confirmation: plaintiff_confirmed | document_only | agent_inferred
  contradictions: []       # other facts that conflict with this one
```

Facts are **intrinsically directional** but their directionality can flip per element. F4 (vehicle at residence, garage open) is **favorable** to E5 (harm is preventable) but **adverse** to E3 (open garage = innocent explanation for truck). The intrinsic directionality is the default; per-element overrides are stored in the mapping layer.

Facts are **verified or flagged.** A fact confirmed by the plaintiff carries more weight than one inferred by the agent from document context. A fact sourced to a specific block in the evidence store is stronger than one from a summary. The confirmation status travels with the fact and affects every element it touches.

Facts have **contradictions.** F13 (repo truck sighting April 17) directly contradicts F21 (R&R found "no indication" of repo attempts as of March 9). The contradiction is recorded, not resolved — the adversarial walk resolves it, or the fact-finder does.

### Layer 3: The Element-Fact Mapping

This is the connective tissue. Every element gets its supporting facts, its undermining facts, its gaps, and its controlling authority.

```yaml
ElementMapping:
  element_id: "E1"
  element_name: "Defendant's Secured Party Status — Challenged"
  strength: strong | moderate | weak | missing
  supporting_facts:
    - fact_id: "F2"
      rationale: "RISC identifies Honda South as sole seller-creditor — CPS is not the original secured party."
    - fact_id: "F5"
      rationale: "Payments routed to separate Trust entity place beneficial ownership in the Trust, not CPS."
  undermining_facts:
    - fact_id: "F22"
      severity: low
      rationale: "CPS's 27+ collection contacts show CPS asserted creditor authority — but this is conduct, not legal status."
  controlling_authority:
    - citation: "Lewis v. Nicholas Financial, Inc., 300 Ga. App. 888 (2009)"
      holding_applied: "Secured party's repossession duty is personal and nondelegable —
                        CPS must establish its own status, and on this record it cannot."
  gaps:
    - missing_fact: "Assignment chain from Honda South to CPS or Trust"
      path_to_fill: discovery_request
```

The mapping captures **why** a fact supports or undermines — the rationale is the connective reasoning. A fact doesn't automatically map to an element; the connection requires a legal argument, even if it's a one-sentence syllogism.

The mapping produces a **strength score** per element: strong, moderate, weak, or missing. This is a preliminary assessment — the adversarial walk stress-tests it.

### Layer 4: The Adversarial Walk

For every load-bearing element, the system runs a structured dialectic:

```
T1 (Their Attack):  "CPS is the servicer. Servicers routinely enforce on behalf of trusts.
                     Plaintiff's 'no name on RISC' theory mistakes standard industry practice
                     for absence of authority. O.C.G.A. § 11-9-203(g) — the security interest
                     follows the obligation."

T2 (Our Response):  "Servicer ≠ secured party under O.C.G.A. § 11-9-102(a)(72)(A).
                     CPS produced zero documentation: no PSA, no assignment, no allonge.
                     The burden is on the party asserting secured status to prove it.
                     Lewis holds this duty is personal and nondelegable — CPS can't
                     bootstrap status from conduct."

T3 (Their Counter): "Plaintiff's own payment history and 27+ collection contacts establish
                     a course of dealing where all parties treated CPS as entitled to collect.
                     The 'burden on CPS' argument is backwards at TRO stage — plaintiff must
                     show likelihood of success, which means plaintiff must disprove CPS's
                     authority, not the reverse."

T4 (Our Counter):   "At TRO stage, 'substantial likelihood' doesn't require certainty.
                     CPS's complete failure to produce the one document that would resolve
                     this — the assignment — supports an adverse inference. And § 11-9-210
                     gives plaintiff an independent right to demand an accounting, which
                     CPS has ignored. The absence of documentation, combined with the
                     Trust structure and SEC filings, meets the TRO threshold."
```

Each turn cites authority. Each turn is grounded in the element's doctrine. T1 and T3 are generated by an **adversary sub-agent** that sees the element statement and the controlling authority — but NOT our T2/T4. This prevents the agent from pulling its punches.

The walk terminates:
- **CLOSED:** The path is resolved in our favor. Their attack fails, or our response is dispositive. No further work needed.
- **CONTESTED:** Both sides have viable arguments. The path is fightable. The walk records what the fight looks like and ranks the pressure.
- **OPEN:** We have no response. The gap is real. Either we fill it (find the missing fact, research the missing authority) or we lose this element.

Each terminal carries a **vulnerability rating** for CONTESTED paths:
- **Lethal:** If they win this argument, the element fails. And if the element is under an AND gate, the claim fails.
- **Wounding:** They have a real argument, but we have a real response. The outcome is uncertain.
- **Minor:** They'll make the argument, but our response is substantially stronger.

### Layer 5: The Gate Walk (Vulnerability Computation)

Once every leaf has a terminal state, the system walks upward through the gate logic:

```
Rule: AND parent fails if ANY child fails.
Rule: OR parent fails only if ALL children fail.

Walk E1 (AND):
  E1.1: CONTESTED (wounding) → could fail
  E1.2: CLOSED (our favor)   → passes
  E1.3: CLOSED (our favor)   → passes
  E1.4: CLOSED (our favor)   → passes
  Result: E1 is CONTESTED — E1.1 is the single point of failure.

Walk E6 (AND over E1-E5):
  E1: CONTESTED → could fail
  E2: CONTESTED → could fail
  E3: CONTESTED → could fail
  E4: CONTESTED → could fail
  E5: CLOSED    → passes
  E6: CONTESTED → any of E1-E4 failing collapses E6.

SPOF Analysis:
  - Claim-level SPOF: E3 (if truck-to-CPS link fails, no imminent threat → no TRO)
  - Element-level SPOF: E1.1 (if court accepts servicer-authority argument, E1 fails)
  - E6 is derivative — it fails if any underlying element fails.
```

The gate walk produces:
- **SPOF map:** Which nodes, if they fail, collapse the entire claim or strategy
- **Pressure ranking:** Which CONTESTED paths are under the most authority pressure
- **Missing evidence impact:** Which gaps, if filled, would move an OPEN or CONTESTED path to CLOSED
- **Claim dependency graph:** Which claims depend on which elements, so you know what happens if a fact is excluded or an authority is distinguished

### Layer 6: The Gauntlet

The gauntlet is a systematic set of checks that run across every claim, every defense, and every party. It is not claim-specific — it is a universal sieve that catches what individual element analysis misses.

The gauntlet is organized by **attack surface:**

**Standing / Capacity:**
- Does the plaintiff have standing to bring this claim? (Constitutional + prudential)
- Does the defendant have capacity to be sued in this jurisdiction?
- Is the plaintiff the real party in interest?
- If an assignee is suing: is the assignment valid? Is the chain of title complete?

**Licensing / Regulatory:**
- Is the defendant licensed to do business in this jurisdiction?
- Was the license valid at the time of the conduct at issue? (NOT just at the time of suit)
- Does the conduct require a license the defendant doesn't hold?
- Are there regulatory consent orders, prior enforcement actions, or pattern-of-conduct findings?

**Preclusion / Abstention:**
- Is there a prior action pending between these parties? (Claim preclusion / res judicata)
- Were any of these claims actually litigated in a prior action? (Issue preclusion / collateral estoppel)
- Is there a federal action that overlaps? (Abstention, stay, or consolidation risk)
- Is there an arbitration clause that covers some or all claims?

**Timing / Limitations:**
- Has the statute of limitations run on any claim?
- Has the statute of repose run?
- Are there notice requirements? Pre-suit demand requirements? Administrative exhaustion requirements?
- Is there a laches defense? (Equity — delay + prejudice)

**Pleading / Procedure:**
- Does the complaint state a claim under the applicable pleading standard? (Twombly/Iqbal vs. notice pleading)
- Are all elements pled? Are any elements pled on information and belief without a factual basis?
- Are the right parties named? Are there necessary parties missing? (FRCP 19 / state equivalents)
- Is venue proper? Is jurisdiction proper? (Subject matter + personal)

**Evidence / Proof:**
- For each element, what is the burden of proof? Who bears it?
- What evidence exists for each element? What is the quality of that evidence?
- What evidence is missing? Is it obtainable through discovery?
- Are there spoliation issues? Adverse inference opportunities?

**Remedies / Damages:**
- What remedies are available for each claim? Are they legal, equitable, or both?
- Are there statutory damage multipliers? Fee-shifting provisions?
- Are there damage caps? Limitations on equitable relief?
- Is there a right to jury trial? Can it be waived?

**Party-Specific Vulnerabilities:**
- Is any party pro se? (Affects pleading standard, procedural latitude)
- Is any party a repeat player? (Pattern evidence, prior inconsistent positions)
- Is any party judgment-proof? (Collectability of any judgment)
- Are there insurance coverage issues? (Who is paying for the defense?)

Each gauntlet check produces: **PASS, FAIL, or INQUIRY.** FAIL means there's an independently dispositive problem. INQUIRY means the check raised a question that needs further investigation. The gauntlet output is a prioritized list of vulnerabilities the element-by-element analysis would miss.

The OFR license example: the element analysis would never check "was the collector licensed when the account was opened?" because no element requires it. But the gauntlet's Licensing check catches it, and it becomes an independent basis for a claim or a defense.

### Layer 7: The Permutation Engine (Future — Research Target)

This is the Doctor Strange layer. It is not built yet. It may require approaches we haven't discovered. But the architecture makes room for it from day one.

The idea: once every claim is modeled as a tree, every fact is mapped, every adversarial walk is complete, and every gauntlet check has fired — the system can permute.

**What gets permuted:**

- **Characterization.** The same fact can be framed differently. "CPS cashed the payment-in-full check" can be characterized as "CPS accepted accord and satisfaction" (offensive) or "CPS processed a routine payment without noticing the notation" (their response). Different characterizations produce different leaf states.
- **Authority emphasis.** A claim might succeed under Case A but fail under Case B. The system can test which authority to lead with, which to distinguish, and which to concede as non-controlling.
- **Claim ordering.** Filing Claim X before Claim Y might affect preclusion, arbitration, or settlement dynamics. The system can model different claim stacks and sequences.
- **Procedural posture.** The same facts and doctrine produce different outcomes at 12(b)(6) (plausibility overlay) vs. summary judgment (no genuine dispute overlay) vs. trial (preponderance overlay). The system can model the same tree under different overlays.
- **Missing evidence scenarios.** "If we get the dispatch records showing the tow truck was dispatched by CPS, E3 goes from CONTESTED to CLOSED." The system can identify the minimum additional evidence needed to change the outcome.

The permutation engine doesn't need to be built now. What matters is that the data model supports it: every element state, every fact connection, every characterization choice, and every authority link is stored as a discrete, queryable record. When the permutation engine arrives, it has a complete dataset to work with.

---

## The Data Model (What Lives in the Database)

The strategy engine is not a file system. It's a relational model inside PostgreSQL — the same database that holds the evidence store and case core. This means the agent can JOIN from a fact in the strategy layer to the exact block in the evidence store that sourced it.

### Core Entities

```
Strategy
  ├── Claim/Count (or Defense/Attack)
  │     ├── Element (recursive: elements can have sub-elements)
  │     │     ├── ElementFact (mapping: fact → element, with directionality + rationale)
  │     │     ├── ElementAuthority (mapping: case/statute → element)
  │     │     └── AdversarialWalk (T1→T2→T3→T4 per element)
  │     └── ClaimAuthority (authority specific to the claim as a whole)
  ├── GauntletCheck (per-strategy gauntlet results)
  └── StrategyFact (strategy-scoped fact inventory)
```

### What's Already in Schema.sql That We Build On

The strategy tables connect to existing tables:
- `cases` — the strategy belongs to a case
- `workspaces` — the strategy is scoped to a workspace (deferred but column exists)
- `parties` — claims target parties, facts involve parties
- `blocks` — facts cite source blocks in the evidence store
- `citations` — authority citations use the same citation verification pattern
- `allegations` — user-provided allegations map to strategy claims (different table — allegations are what the user says happened; claims are the legal vehicle for addressing them)

### Key Design Decisions to Resolve

These are the things I need to work through with you before writing the schema:

1. **Are claims and defenses the same thing in the database?** An "attack" on their motion to dismiss is structurally identical to an "element" of an affirmative claim — both are propositions that must be proved or rebutted with facts and authority. Do we unify them into a single `propositions` table, or keep `claims` and `defenses` separate?

2. **How deep does the tree go?** The doctrine tree is recursive — elements can have sub-elements. But at some point a node becomes a "leaf" that maps directly to facts. Is the leaf-ness a property of the node (a boolean), or is it inferred from the absence of children?

3. **Are facts in the strategy layer the same as facts in the case core?** The case core has `events` (timestamped happenings). The strategy layer has `facts` (propositions that support or undermine elements). An event ("repo truck sighted April 17 at 1:00 AM") can be multiple facts ("truck was a wheel-lift tow truck," "truck had dimmed headlights," "truck fled when plaintiff approached"). Is there a `facts` table in the strategy schema, or are facts just events + characterization?

4. **Does the adversarial walk live as structured data or as a document?** The current `adversarial-analysis.json` is a rich document with narrative turns, case law citations, and vulnerability ratings. Should the T1→T2→T3→T4 turns be individual rows in an `adversarial_turns` table, or stored as JSONB on the element?

5. **How do we handle characterization?** Two attorneys can look at the same fact and characterize it differently. "CPS sent a contract with electronic signatures" can be "CPS fabricated evidence" or "CPS sent a standard business record." Is characterization a separate entity, or is it embedded in the fact-to-element mapping?

6. **What is the relationship between user-provided allegations and strategy claims?** The user says "Allegation A01: Surgeon removed ovary without identifying adhesions." The strategy layer creates "Claim: Medical Negligence — Failure to Identify and Lyse Adhesions." The allegation is the user's framing; the claim is the legal vehicle. Do they map 1:1? Many-to-many? Is an allegation a parent of the claims that address it?

---

## Design Principles (Non-Negotiable)

### 1. Doctrine First, Facts Second

The tree is built from doctrine alone. No facts enter until Step 2. This is not a preference — it is a structural requirement. If facts shape the tree, the tree conforms to the available evidence rather than the actual law. The law defines what must be proved. The facts determine whether it can be.

### 2. Citation-Anchored Everything

Every legal proposition links to a specific statute or case. Every case links to an exact quotation from the opinion. Every quotation is verified against the opinion text in the current session. The citation chain is auditable from claim → element → authority → quotation → opinion text. No link in the chain can be invented.

### 3. Facts Are Sourced, Not Asserted

Every fact in the strategy layer traces to a source: a block in the evidence store, a verified fact confirmed by the plaintiff, a document in discovery, or a recorded gap. The source carries a confirmation status. The confirmation status affects the weight the fact carries in the adversarial walk.

### 4. The Adversary Must Be Adversarial

The sub-agent that generates T1 and T3 attacks does not see our T2 and T4 responses. It sees the element statement, the controlling authority, and the facts — and it is instructed to win. If the adversary agent can't find a viable attack, the element is genuinely strong. If it finds one we didn't think of, we just avoided an ambush at oral argument.

### 5. Gate Logic Is Deterministic

The vulnerability computation is not an LLM call. It's a deterministic walk up the tree applying two rules: AND parent fails if any child fails; OR parent fails only if all children fail. The LLM's job is to classify the terminal state of each leaf (CLOSED/CONTESTED/OPEN). The gate walk is math.

### 6. The Tree Models the Law, Not the Case

The doctrine tree for "Negligence — Duty/Breach/Causation/Damages" is the same tree regardless of whether the case is a car accident or a surgical error. The facts change. The tree doesn't. This means doctrine trees are **reusable across cases** — the same jurisdiction's negligence tree applies to every negligence claim in that jurisdiction. Only the fact mappings and adversarial walks are case-specific.

### 7. The Database Is the Source of Truth

No more JSON files in strategy folders. The database holds the tree, the facts, the mappings, the walks, and the gauntlet results. Files become export artifacts — generated from the database for human review, sharing, or filing. The database is the system of record.

---

## What We've Already Built (And What's Still in Files)

| Component | Status | Current Form |
|---|---|---|
| Doctrine tree structure (elements + sub-elements + gates) | Working | `doctrine.json` (file) |
| Fact inventory with sources and confirmation | Working | `fact-inventory.json` (file) |
| Element-to-fact mapping with directionality + rationale | Working | `element-map.json` (file) |
| Adversarial walk with T1→T2→T3→T4 dialectic | Working | `adversarial-analysis.json` (file) |
| Vulnerability scoring (lethal/wounding/minor) | Working | In adversarial JSON |
| Gate logic walk (AND/OR propagation) | Spec exists | Step 4 contract |
| Gauntlet checks (systematic cross-claim screening) | Concept | Not yet built |
| Permutation engine (characterization × authority × ordering) | Research target | Not yet built |
| Citation verification pipeline | Working | Via legal-research skill + MCP tools |
| Evidence store (documents → sections → blocks) | Working | `schema.sql` tables |
| Case core (parties, allegations, events) | Working | `schema.sql` tables |

---

## Open Questions (What We're Reaching Into the Cosmos For)

1. **Is disposition deterministic or probabilistic?** If the tree is fully built, facts are fully mapped, and adversarial walks are complete — does the answer fall out, or do we need to permute through characterizations and compute probabilities? The OFR license example suggests some weaknesses are deterministic (license invalid at time of conduct = per se violation) while others are probabilistic (how will this judge weigh this authority against that one?).

2. **Can characterization be systematized?** Two attorneys characterize the same fact differently. Is there a finite set of characterization moves (framing, emphasis, context-widening, context-narrowing, analogy, distinction) that can be enumerated and applied algorithmically? Or is characterization the irreducibly human art that the system can't automate — only present options for?

3. **How does judge modeling work?** Every judge has a history of rulings. Those rulings reveal patterns: this judge grants 12(b)(6) motions at a 70% rate; this judge is deferential to agency interpretations; this judge has never granted a TRO to a pro se plaintiff. Can the strategy engine incorporate judge-specific data to refine its probability estimates?

4. **How do we handle the other side's unknown arguments?** The adversarial walk generates the best attacks we can think of. But the other side has lawyers we haven't met, with strategies we haven't anticipated. Is the adversarial walk's completeness a function of the adversary agent's quality? Can we measure how thorough the walk was?

5. **What is the relationship between the strategy engine and the drafting engine?** In the V2 pipeline, strategy output feeds directly into drafting. But if the strategy engine is computing permutations — testing 14 million futures — at what point does it stop and hand off to drafting? When it finds one winning path? When it has ranked the top N paths? When the attorney says "that one"?

---

## The Name

**The Strategy Engine.** Because it doesn't advise on strategy — it computes it. The engine takes doctrine, facts, and authority as inputs and produces the disposition of every viable path as output. The attorney chooses which path to walk. But the attorney chooses with full knowledge of where every path leads.

---

*This document is a research target. We don't know exactly how to build all of it. But we know what we're reaching for: a system that models the DNA of a case, walks every branch of every tree, and finds the path that wins. Every schema change, every new table, every new agent capability should move us closer to that destination. If a decision doesn't serve this vision, it's the wrong decision.*
