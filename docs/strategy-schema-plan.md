# Strategy Schema — Implementation Plan & Rationale

## Architecture Overview

The strategy schema extends the existing `vision` schema (case core + evidence store). It adds three new conceptual layers:

```
vision (existing)                    vision (new — strategy)
─────────────────────────           ──────────────────────────────
cases                               strategies
parties                              ├── strategy_propositions (recursive tree)
allegations                          │    ├── proposition_fact_mappings
events                               │    ├── proposition_authorities
documents → sections → blocks        │    ├── adversarial_turns
citations                            │    └── overlay_propositions
workspaces                           ├── strategy_facts
                                     ├── doctrine_elements (reusable law library)
                                     ├── rhetorical_moves (enum table)
                                     ├── gauntlet_check_definitions
                                     └── strategy_gauntlet_results
```

## Design Decisions

### D1: SERIAL integers for PKs (not UUIDs)

**Rationale:** The existing `schema.sql` uses `SERIAL PRIMARY KEY` for all tables. Using the same convention means:
- JOINs are consistent across evidence store and strategy tables
- No migration burden on existing tables
- Simpler foreign key relationships
- If we later need UUIDs for API exposure, we add an `external_id UUID` column (as the `cases` table already does)

### D2: Unified `strategy_propositions` table with type discriminator

**Rationale:** A claim, an element, a sub-element, an affirmative defense, and a procedural attack are structurally identical — each is a boolean proposition that either passes or fails. One recursive table avoids:
- Duplicate schema for claims vs. defenses
- Separate JOIN paths for walking the tree
- Schema migration when a new proposition type emerges

The `proposition_type` column discriminates: `claim`, `element`, `sub_element`, `affirmative_defense`, `procedural_attack`, `factor`, `prong`.

### D3: Gate logic on strategy_propositions, not doctrine_elements

**Rationale:** The same legal element can function as an AND gate in one claim and an OR gate in another. "Causation" might be a single required element (AND child) in a negligence claim, but one of several alternative pathways (OR child) in a strict liability claim. Gate logic is claim-structure, not element-definition. It belongs on the case-specific proposition, not the reusable doctrine element.

### D4: `strategy_facts` separate from `events`, with optional link

**Rationale:** An event is raw history ("Tow truck observed April 17 at 1:00 AM"). A strategy fact is a legally interpretive characterization ("The tow truck's presence constitutes an imminent threat of self-help repossession"). Decoupling them enables the permutation engine to characterize the same event differently and recompute the tree. An optional `core_event_id` FK preserves the provenance chain without collapsing the distinction.

### D5: Structured `adversarial_turns` as individual rows

**Rationale:** Storing T1→T2→T3→T4 in a JSONB blob prevents querying across turns. With structured rows:
```sql
-- Find every contested path where our counter-argument lacks a verified pincite
SELECT sp.id, sp.proposition_text, at2.argument_text
FROM strategy_propositions sp
JOIN adversarial_turns at2 ON sp.id = at2.proposition_id AND at2.turn_number = 2
WHERE at2.citation_id IS NULL AND sp.current_status = 'CONTESTED';
```
This queryability is essential for quality control and vulnerability analysis.

### D6: Rhetorical moves as a reference table with enum values

**Rationale:** Characterization is a finite set of argumentative moves. Storing them as a reference table (rather than a CHECK constraint) allows the taxonomy to grow without schema migration. The current taxonomy, grounded in actual adversarial walk data, includes:

| Move | What It Does | Example |
|------|-------------|---------|
| `ASSERT` | Direct fact-to-element mapping | "RISC names Honda South, not CPS → CPS is not secured party" |
| `REFUTE` | Attack the opposing fact's relevance or accuracy | "Their 27 contacts are conduct, not legal status" |
| `CONCEDE_AND_DISTINGUISH` | Accept the fact, show why it doesn't apply | "Yes, damages exist, but they're inadequate here" |
| `REFRAIM` | Recast the fact with different implications | "The truck's flight is deterrence, not absence of intent" |
| `AMPLIFY` | Add context that strengthens the fact | "And the truck had no plate — independent O.C.G.A. violation" |
| `NARROW` | Limit the scope of their fact or authority | "Deavers applies only to completed repos, not threatened ones" |
| `DISTINGUISH` | Show why their authority doesn't control | "Aetna is real-property foreclosure, not vehicle repossession" |
| `CONCEDE_AND_NEUTRALIZE` | Accept the fact but show it's legally irrelevant | "CPS did send billing statements — but billing doesn't prove ownership" |
| `EXTRAPOLATE` | Extend a fact to its logical conclusion | "If CPS can't produce the PSA, no servicer authority exists" |
| `FLIP` | Turn their fact into our weapon | "Their non-authoritative copy watermark proves our authenticity argument" |

### D7: Vulnerability is computed, not stored

**Rationale:** A proposition's vulnerability changes when new facts are added, new authority is found, or the adversary discovers a new attack. Storing `vulnerability_rating` as a column invites staleness. Instead:
- Each `adversarial_turn` carries a `turn_vulnerability` rating for that specific turn
- The terminal vulnerability for a proposition is computed by a deterministic function that reads the turns
- The function implements: LETHAL (path has no viable counter), WOUNDING (path is contested with real arguments on both sides), MINOR (path is contested but our response is substantially stronger)

### D8: Overlays as a proposition subtype

**Rationale:** A 12(b)(6) plausibility overlay, a summary judgment no-genuine-dispute overlay, and a TRO four-factor overlay are all propositions that AND-gate against other propositions. Rather than a separate `overlays` table, overlays are `strategy_propositions` with `proposition_type = 'overlay'`. They link to the propositions they gate against via a join table. This allows:
- The gate walk function to treat overlays identically to other propositions
- Multiple overlays on the same claim (12(b)(6) + review standard)
- Overlays to themselves have adversarial walks

### D9: Gauntlet is a separate layer

**Rationale:** The gauntlet is not claim-specific. It's a systematic sieve applied across every claim, party, and procedural posture. It needs its own tables:
- `gauntlet_check_definitions` — the reusable catalog of checks (standing, licensing, SOL, etc.)
- `strategy_gauntlet_results` — the results of running each check on a specific strategy

### D10: Authority links use the existing `citations` table pattern

**Rationale:** The existing `citations` table links `source_type` + `source_id` to `block_id` with `quote` and `page`. Proposition authorities follow the same pattern but cite case law rather than evidence blocks. Rather than using a free-text `anchored_citation` column, we use a `proposition_authorities` table that stores the citation metadata and optionally links to a `citations` row for the exact quoted text.

### D11: Verified facts live at the case level, not the strategy level

**Rationale:** The V2 pipeline references `VERIFIED_FACTS.md` as the single source of truth that both offensive and defensive strategies draw from. A fact like "Plaintiff executed the RISC with wet-ink signature" exists independently of any strategy. Multiple strategies (offensive complaint, defensive MTD response) reference the same verified fact. It belongs in the case core, not the strategy schema.

The `case_facts` table fills the gap between `events` (raw timestamped happenings) and `strategy_facts` (interpretive legal characterizations):
- **Event:** "Tow truck observed April 17 at 1:00 AM" (what happened)
- **Case fact:** "A black hook-style tow truck with dimmed headlights drove slowly down plaintiff's cul-de-sac on April 17, 2026 at approximately 1:00 AM" (what we know to be true)
- **Strategy fact:** "The tow truck's presence constitutes an imminent threat of self-help repossession" (what this means for our legal argument)

`strategy_facts` has a `case_fact_id` FK — each strategy fact can trace back to the verified fact it interprets.

### D12: Intent is structured on the strategy, not a separate table

**Rationale:** The V2 pipeline's Step 0 produces an `INTENT.md` with objective, constraints, success criteria, strategic philosophy, and overlay standards. This is a single structured document per strategy — not a set of rows. A JSONB column on `strategies` captures the intent without adding a table that would always be 1:1 with strategies.

The intent JSONB schema:
```json
{
  "objective": "File Verified Petition and Emergency TRO to halt repossession",
  "strategic_philosophy": "Forward-looking — targets what CPS is about to do, not what it did",
  "court_jurisdiction": "Superior Court of Gwinnett County, Georgia",
  "claims_summary": ["Wrongful Repossession", "GFBPA", "Declaratory Judgment"],
  "relief_sought": ["Emergency TRO", "Preliminary injunction", "Treble damages", "Attorney's fees"],
  "constraints": ["Pro se plaintiff", "Arbitration clause in contract", "Federal preclusion risk"],
  "success_criteria": ["TRO granted ex parte", "Vehicle protected during litigation"],
  "overlay_standards": ["O.C.G.A. § 9-11-65 TRO four-factor test"]
}
```

## Table Inventory

| # | Table | Purpose | New/Extends |
|---|-------|---------|-------------|
| 0 | `case_facts` | Verified facts corpus at case level (ground truth for all strategies) | New (case core) |
| 1 | `strategies` | Container for a filing strategy | New |
| 2 | `doctrine_elements` | Reusable element definitions (law, not case) | New |
| 3 | `strategy_propositions` | Recursive tree of claims/elements/defenses | New |
| 4 | `strategy_facts` | Interpretive facts for a strategy | New |
| 5 | `proposition_fact_mappings` | Connect facts to propositions with rhetorical moves | New |
| 6 | `rhetorical_moves` | Reference table of valid rhetorical moves | New |
| 7 | `adversarial_turns` | T1→T2→T3→T4 per proposition | New |
| 8 | `adversarial_attacks` | One structured attack per proposition | New |
| 9 | `proposition_authorities` | Case law and statutes linked to propositions | New |
| 10 | `proposition_overlay_gates` | Which overlays gate against which propositions | New |
| 11 | `gauntlet_check_definitions` | Reusable catalog of gauntlet checks | New |
| 12 | `gauntlet_check_categories` | Categories for organizing gauntlet checks | New |
| 13 | `strategy_gauntlet_results` | Results of gauntlet checks on a strategy | New |

## Integration Points with Existing Schema

| Strategy Table | Links To | Relationship |
|---------------|----------|-------------|
| `strategies.case_id` | `cases.id` | A strategy belongs to a case |
| `strategies.workspace_id` | `workspaces.id` | Optional workspace scoping |
| `strategy_propositions.party_id` | `parties.id` | Which party asserts this proposition |
| `strategy_facts.core_event_id` | `events.id` | Optional link to raw historical event |
| `strategy_facts.source_block_ids` | `blocks.id` | Citation anchor to evidence store |
| `proposition_authorities.citation_id` | `citations.id` | Optional link to citation verification |
| `strategy_gauntlet_results.party_id` | `parties.id` | Which party the check targets |

## Column Convention

All strategy tables include:
- `id SERIAL PRIMARY KEY`
- `created_at TIMESTAMPTZ DEFAULT now()`
- `updated_at TIMESTAMPTZ DEFAULT now()`
- `metadata JSONB DEFAULT '{}'`

This matches the existing schema convention.
