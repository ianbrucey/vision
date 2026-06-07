-- ============================================================================
-- Vision — Strategy Engine Schema v2.0
-- ============================================================================
-- The strategy layer extends the evidence store and case core with the tables
-- needed to model legal claims as computable trees: doctrine decomposition,
-- fact-to-element mapping, adversarial dialectic, gate-logic vulnerability
-- computation, and systematic gauntlet screening.
--
-- Design principles:
--   1. Doctrine first, facts second — the tree is built from law, not evidence
--   2. Unified propositions — claims, elements, defenses are all boolean nodes
--   3. Citation-anchored everything — every authority links to verified opinion text
--   4. Facts ≠ events — strategy facts are interpretive characterizations of raw events
--   5. Adversarial turns as structured rows — queryable, not JSON-blobbed
--   6. Gate logic is deterministic — AND/OR propagation is math, not LLM
--   7. Vulnerability is computed — not a stale column
--   8. The gauntlet is systematic — cross-claim screening independent of element analysis
--   9. Reusable doctrine library — element definitions shared across cases
--  10. SERIAL integers — consistent with existing schema convention
--
-- Depends on:
--   - vision schema v1.0 (cases, parties, events, blocks, citations, workspaces)
-- ============================================================================

SET search_path TO vision, agent_work, public;

-- ============================================================================
-- RHETORICAL MOVES — The finite taxonomy of argumentative characterization.
-- ============================================================================
-- When an agent maps a fact to a proposition, it selects a rhetorical move.
-- This table defines the valid moves. The taxonomy can grow without schema
-- migration (INSERT a new row, don't ALTER a CHECK constraint).
--
-- Grounded in actual adversarial walk data from the CPS TRO workspace.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rhetorical_moves (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,                -- 'ASSERT', 'REFUTE', 'DISTINGUISH', etc.
    description     TEXT NOT NULL,                       -- What this move does and when to use it
    example         TEXT,                                -- Concrete example from actual case data
    requires_authority BOOLEAN DEFAULT false,            -- Does this move typically need a citation?
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Seed the standard moves grounded in actual adversarial analysis data.
-- ON CONFLICT DO NOTHING makes this idempotent across schema re-applications.
INSERT INTO rhetorical_moves (name, description, example, requires_authority, sort_order) VALUES
('ASSERT', 'Direct fact-to-element mapping — the fact, if accepted, satisfies the element',
 'RISC names Honda South as sole seller-creditor → CPS is not the original secured party', false, 1),
('REFUTE', 'Attack the opposing fact''s relevance, accuracy, or legal significance',
 'CPS''s 27 collection contacts are conduct, not legal status — they don''t prove secured party standing', false, 2),
('CONCEDE_AND_DISTINGUISH', 'Accept the fact or authority but show why it does not apply to this element',
 'Yes, damages remedies exist for wrongful repossession — but they are inadequate here because plaintiff is unemployed and CPS is an out-of-state corporation', true, 3),
('REFRAIM', 'Recast the same fact with different legal implications',
 'The truck''s flight upon approach is not absence of intent to repossess — it is deterrence by plaintiff''s visible presence, confirming imminence', false, 4),
('AMPLIFY', 'Add context that strengthens the fact''s legal significance',
 'The truck not only approached at 1:00 AM with dimmed lights — it also bore no visible license plate, an independent O.C.G.A. § 40-2-41 violation', false, 5),
('NARROW', 'Limit the scope of the opposing fact or authority to reduce its impact',
 'Deavers v. Standridge addresses a completed repossession with offensive language — it does not control a threatened-tort theory under § 9-5-1', true, 6),
('DISTINGUISH', 'Show why the opposing authority does not control this case',
 'Aetna Finance Co. v. Culpepper is a real-property foreclosure case — its knowing-intent pleading requirement does not transfer to vehicle repossession under Article 9', true, 7),
('CONCEDE_AND_NEUTRALIZE', 'Accept the fact but show it has no legal weight on this element',
 'CPS did send billing statements identifying itself as a debt collector — but billing conduct does not establish secured party status under § 11-9-102(a)(72)', false, 8),
('EXTRAPOLATE', 'Extend a fact to its logical conclusion to establish an element',
 'If CPS cannot produce the Pooling and Servicing Agreement after a § 11-9-210 demand, no servicer authority to repossess exists as a matter of law', false, 9),
('FLIP', 'Turn the opposing party''s fact or authority into a weapon for our side',
 'CPS''s own document watermark says ''non-authoritative copy'' — CPS admits the produced RISC is not the authoritative version, proving our authenticity challenge', false, 10),
('CONCEDE', 'Accept the fact or authority as true and damaging — used when no viable counter exists',
 'The R&R found no indication of repossession attempts as of March 9, 2026 — this is true and must be addressed by supervening facts', false, 11)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- CASE FACTS — Verified facts corpus at the case level.
-- ============================================================================
-- Case facts are the "ground truth" that all strategies draw from. They exist
-- independently of any strategy and are the single source of truth for what
-- is known about the case. They are confirmed by the plaintiff or sourced
-- from documents. Strategy facts (below) are interpretive characterizations
-- of these case facts — the same case fact can be characterized differently
-- in different strategies.
--
-- This table fills the gap between raw events (timestamped happenings) and
-- strategy facts (interpretive legal characterizations). Events answer "what
-- happened?" Case facts answer "what do we know to be true?" Strategy facts
-- answer "what does this mean for our legal argument?"
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_facts (
    id                  SERIAL PRIMARY KEY,
    case_id             INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,

    -- The statement of fact
    statement           TEXT NOT NULL,

    -- How was this fact established?
    fact_type           TEXT NOT NULL DEFAULT 'verified' CHECK (fact_type IN (
                            'verified',      -- confirmed by plaintiff as true
                            'document',      -- sourced from a document in the evidence store
                            'inferred',      -- inferred by agent from context
                            'disputed',      -- plaintiff says X, opposing party says Y
                            'administrative', -- case number, court, dates — not evidentiary
                            'retired'        -- withdrawn as incorrect or irrelevant
                        )),

    -- Who or what confirmed this fact?
    confirmation_by     TEXT,                                -- "Plaintiff", "Dr. Edmonds deposition p.47", etc.

    -- Provenance: where does this fact come from?
    source_description  TEXT,                                -- human-readable: "VERIFIED_FACTS.md — RISC Execution section"
    source_block_ids    INTEGER[] DEFAULT '{}',              -- FK references to blocks table

    -- What evidence would strengthen or corroborate this fact?
    missing_evidence    TEXT,

    -- Tags for categorization and search
    tags                TEXT[] DEFAULT '{}',

    notes               TEXT,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    -- A fact statement should be unique within a case
    UNIQUE (case_id, statement)
);

CREATE INDEX IF NOT EXISTS idx_case_facts_case ON case_facts (case_id);
CREATE INDEX IF NOT EXISTS idx_case_facts_type ON case_facts (case_id, fact_type);
CREATE INDEX IF NOT EXISTS idx_case_facts_blocks ON case_facts USING GIN (source_block_ids);
CREATE INDEX IF NOT EXISTS idx_case_facts_tags ON case_facts USING GIN (tags);

-- ============================================================================
-- STRATEGIES — The container for a filing strategy.
-- ============================================================================
-- A strategy is the top-level container. It represents one filing (complaint,
-- TRO motion, MTD response) or one defensive posture. A case can have many
-- strategies over its lifecycle. Each strategy produces one or more outputs.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS strategies (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER REFERENCES cases(id) ON DELETE CASCADE NOT NULL,
    workspace_id    INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,  -- deferred: workspace scoping
    name            TEXT NOT NULL,                                   -- human-readable: "State Petition + TRO"
    strategy_type   TEXT NOT NULL CHECK (strategy_type IN (
                        'offensive',    -- building claims, seeking new relief
                        'defensive'     -- responding to opposing filing or ruling
                    )),
    posture         TEXT CHECK (posture IN (
                        'initial_filing',       -- complaint, petition
                        'pretrial_motion',      -- TRO, preliminary injunction, MTD
                        'responsive_filing',    -- opposition to MTD, answer
                        'discovery_motion',     -- compel, protective order
                        'dispositive_motion',   -- summary judgment
                        'post_judgment',        -- appeal, reconsideration
                        'other'
                    )),
    jurisdiction    TEXT,                                            -- court and state
    filing_deadline DATE,                                            -- when this must be filed
    status          TEXT DEFAULT 'drafting' CHECK (status IN (
                        'drafting',         -- strategy being built
                        'review',           -- attorney review
                        'approved',         -- ready for drafting
                        'filed',            -- submitted to court
                        'superseded',       -- replaced by newer strategy
                        'archived'          -- historical reference
                    )),
    objective       TEXT,                                            -- what this strategy aims to accomplish
    intent          JSONB,                                           -- structured intent from V2 Step 0 conversation.
                                                                    -- Schema: { objective, strategic_philosophy,
                                                                    --   court_jurisdiction, claims_summary, relief_sought,
                                                                    --   constraints (array), success_criteria (array),
                                                                    --   overlay_standards (array) }
    notes           TEXT,                                            -- free-text strategic context
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),

    UNIQUE (case_id, name)
);

CREATE INDEX IF NOT EXISTS idx_strategies_case ON strategies (case_id);
CREATE INDEX IF NOT EXISTS idx_strategies_workspace ON strategies (workspace_id);
CREATE INDEX IF NOT EXISTS idx_strategies_type ON strategies (strategy_type);
CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies (case_id, status);

-- ============================================================================
-- DOCTRINE ELEMENTS — Reusable legal element definitions.
-- ============================================================================
-- The law library. Elements are defined once per jurisdiction and reused across
-- cases. Gate logic (AND/OR) is NOT stored here — it lives on strategy_propositions
-- because the same element can be AND in one claim and OR in another.
--
-- Template trees can be built via parent_element_id (e.g., "Negligence" parent
-- of "Duty," "Breach," "Causation," "Damages"). These templates are instantiated
-- into strategy_propositions when an agent builds a claim tree.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doctrine_elements (
    id                  SERIAL PRIMARY KEY,
    parent_element_id   INTEGER REFERENCES doctrine_elements(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,                               -- "Defendant's Secured Party Status"
    element_text        TEXT NOT NULL,                               -- what must be proved
    statutory_phrase    TEXT,                                        -- the operative statutory language
    jurisdiction        TEXT NOT NULL,                               -- "Georgia", "11th Circuit", "Federal"
    standard_of_proof   TEXT,                                        -- "preponderance", "clear and convincing", "substantial likelihood"
    sort_order          INTEGER DEFAULT 0,                           -- ordering within parent
    notes               TEXT,                                        -- commentary on this element
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    UNIQUE (jurisdiction, name, parent_element_id)
);

CREATE INDEX IF NOT EXISTS idx_doctrine_elements_parent ON doctrine_elements (parent_element_id);
CREATE INDEX IF NOT EXISTS idx_doctrine_elements_jurisdiction ON doctrine_elements (jurisdiction);

-- ============================================================================
-- STRATEGY PROPOSITIONS — The recursive tree of claims, elements, and defenses.
-- ============================================================================
-- This is the core table. Every node in the strategy tree is a proposition:
-- a boolean statement that must evaluate to true for the asserting party to
-- succeed. Propositions are recursive — a claim contains elements, elements
-- contain sub-elements, sub-elements contain factors.
--
-- proposition_type discriminates the role:
--   'claim'              — cause of action or count (root of a claim tree)
--   'element'            — a required showing under the claim
--   'sub_element'        — a component of an element
--   'factor'             — a factor in a multi-factor test
--   'prong'              — a prong of a multi-prong standard
--   'affirmative_defense' — a defense the opposing party must prove
--   'procedural_attack'  — an attack on the opposing filing (defensive posture)
--   'overlay'            — a procedural standard that gates against substantive elements
--                          (12(b)(6) plausibility, summary judgment no-genuine-dispute, TRO four-factor)
--   'remedy'             — a remedy or form of relief sought
--
-- gate_type determines how children combine:
--   'AND'  — all children must succeed (default)
--   'OR'   — any child can succeed independently
--   'NONE' — leaf node (no children; determined by fact mapping)
--
-- current_status is the terminal classification after adversarial walk:
--   'OPEN'       — not yet evaluated
--   'CLOSED'     — resolved in asserting party's favor
--   'CONTESTED'  — both sides have viable arguments
--   'ABANDONED'  — conceding this proposition
--   'AMEND'      — needs repleading, not briefing
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS strategy_propositions (
    id                      SERIAL PRIMARY KEY,
    strategy_id             INTEGER REFERENCES strategies(id) ON DELETE CASCADE NOT NULL,
    parent_proposition_id   INTEGER REFERENCES strategy_propositions(id) ON DELETE CASCADE,
    doctrine_element_id     INTEGER REFERENCES doctrine_elements(id) ON DELETE SET NULL,

    -- What kind of proposition this is
    proposition_type        TEXT NOT NULL CHECK (proposition_type IN (
                                'claim', 'element', 'sub_element', 'factor', 'prong',
                                'affirmative_defense', 'procedural_attack',
                                'overlay', 'remedy'
                            )),

    -- How children combine (NULL for leaf nodes)
    gate_type               TEXT CHECK (gate_type IN ('AND', 'OR')),

    -- Which party asserts this proposition (must prove or rebut it)
    party_id                INTEGER REFERENCES parties(id) ON DELETE SET NULL,

    -- Human-readable label and the proposition text
    label                   TEXT NOT NULL,                           -- "E1", "Count II", "Prong 3"
    proposition_text        TEXT NOT NULL,                           -- what must be shown
    statutory_phrase        TEXT,                                    -- operative statutory language anchoring this proposition

    -- Status after adversarial walk
    current_status          TEXT DEFAULT 'OPEN' CHECK (current_status IN (
                                'OPEN', 'CLOSED', 'CONTESTED', 'ABANDONED', 'AMEND'
                            )),

    -- Ordering within parent
    sort_order              INTEGER DEFAULT 0,

    -- Agent-readable notes about this proposition's role in the strategy
    notes                   TEXT,
    metadata                JSONB DEFAULT '{}',
    created_at              TIMESTAMPTZ DEFAULT now(),
    updated_at              TIMESTAMPTZ DEFAULT now(),

    -- A proposition must be unique within its parent and strategy
    UNIQUE (strategy_id, parent_proposition_id, label)
);

-- Lookup indexes
CREATE INDEX IF NOT EXISTS idx_propositions_strategy ON strategy_propositions (strategy_id);
CREATE INDEX IF NOT EXISTS idx_propositions_parent ON strategy_propositions (parent_proposition_id);
CREATE INDEX IF NOT EXISTS idx_propositions_doctrine ON strategy_propositions (doctrine_element_id);
CREATE INDEX IF NOT EXISTS idx_propositions_type ON strategy_propositions (strategy_id, proposition_type);
CREATE INDEX IF NOT EXISTS idx_propositions_party ON strategy_propositions (party_id);
CREATE INDEX IF NOT EXISTS idx_propositions_status ON strategy_propositions (strategy_id, current_status);

-- ============================================================================
-- STRATEGY FACTS — Interpretive legal characterizations of raw events.
-- ============================================================================
-- Strategy facts are NOT the same as case-core events. An event is raw history:
-- "Tow truck observed April 17 at 1:00 AM." A strategy fact is a legally
-- interpretive characterization: "The tow truck's presence constitutes an
-- imminent threat of self-help repossession."
--
-- This separation enables the permutation engine: the same event can be
-- characterized differently (offensively vs. defensively) and the tree
-- recomputed with each characterization.
--
-- Facts optionally link to core events and evidence blocks for provenance.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS strategy_facts (
    id                  SERIAL PRIMARY KEY,
    strategy_id         INTEGER REFERENCES strategies(id) ON DELETE CASCADE NOT NULL,

    -- The legally interpretive statement
    statement           TEXT NOT NULL,

    -- Provenance: what raw data supports this interpretation?
    case_fact_id        INTEGER REFERENCES case_facts(id) ON DELETE SET NULL,   -- links to verified fact in case core
    core_event_id       INTEGER REFERENCES events(id) ON DELETE SET NULL,       -- optional link to raw event
    source_block_ids    INTEGER[] DEFAULT '{}',                                  -- FK to blocks table
    source_description  TEXT,                                                     -- human-readable: "VERIFIED_FACTS.md — CPS Identity section"

    -- Who confirmed this fact? Affects weight in adversarial walk.
    confirmation_status TEXT NOT NULL DEFAULT 'agent_inferred' CHECK (confirmation_status IN (
                            'plaintiff_confirmed',  -- confirmed by the client
                            'document_only',        -- sourced from a document, not separately confirmed
                            'agent_inferred',       -- inferred by agent from context
                            'disputed',             -- contested by opposing party
                            'retired'               -- withdrawn (e.g., OCR artifact)
                        )),

    -- Intrinsic directionality. Per-element overrides live in proposition_fact_mappings.
    directionality      TEXT DEFAULT 'neutral' CHECK (directionality IN (
                            'favorable', 'adverse', 'neutral'
                        )),

    -- Other facts that contradict this one (array of strategy_facts.id)
    contradicting_fact_ids INTEGER[] DEFAULT '{}',

    -- What evidence would strengthen or confirm this fact?
    missing_evidence    TEXT,

    notes               TEXT,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_strategy_facts_strategy ON strategy_facts (strategy_id);
CREATE INDEX IF NOT EXISTS idx_strategy_facts_case_fact ON strategy_facts (case_fact_id);
CREATE INDEX IF NOT EXISTS idx_strategy_facts_event ON strategy_facts (core_event_id);
CREATE INDEX IF NOT EXISTS idx_strategy_facts_blocks ON strategy_facts USING GIN (source_block_ids);
CREATE INDEX IF NOT EXISTS idx_strategy_facts_confirmation ON strategy_facts (confirmation_status);

-- ============================================================================
-- PROPOSITION-FACT MAPPINGS — The connective tissue.
-- ============================================================================
-- Every connection between a fact and a proposition is a row in this table.
-- The rhetorical_move classifies HOW the fact connects (ASSERT, REFUTE, etc.).
-- Directionality is per-mapping (the same fact can SUPPORT one proposition
-- while UNDERMINING another). Severity applies to UNDERMINING mappings.
-- The rationale is the agent's legal reasoning chain for this connection.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS proposition_fact_mappings (
    id                  SERIAL PRIMARY KEY,
    proposition_id      INTEGER REFERENCES strategy_propositions(id) ON DELETE CASCADE NOT NULL,
    fact_id             INTEGER REFERENCES strategy_facts(id) ON DELETE CASCADE NOT NULL,
    rhetorical_move_id  INTEGER REFERENCES rhetorical_moves(id) ON DELETE SET NULL,

    -- Does this fact support or undermine the proposition?
    directionality      TEXT NOT NULL CHECK (directionality IN (
                            'SUPPORTS', 'UNDERMINES'
                        )),

    -- For UNDERMINES: how damaging is this fact to the proposition?
    severity            TEXT CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH')),

    -- The legal reasoning connecting this fact to this proposition
    rationale           TEXT NOT NULL,

    -- Order within the proposition's fact list
    sort_order          INTEGER DEFAULT 0,

    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    -- A fact can only map to a given proposition once
    UNIQUE (proposition_id, fact_id)
);

CREATE INDEX IF NOT EXISTS idx_prop_fact_mapping_proposition ON proposition_fact_mappings (proposition_id);
CREATE INDEX IF NOT EXISTS idx_prop_fact_mapping_fact ON proposition_fact_mappings (fact_id);
CREATE INDEX IF NOT EXISTS idx_prop_fact_mapping_move ON proposition_fact_mappings (rhetorical_move_id);
CREATE INDEX IF NOT EXISTS idx_prop_fact_mapping_direction ON proposition_fact_mappings (proposition_id, directionality);

-- ============================================================================
-- PROPOSITION AUTHORITIES — Case law and statutes linked to propositions.
-- ============================================================================
-- Every legal proposition should be anchored to controlling authority. This
-- table stores the citation, the operative quotation, the holding applied,
-- and verification status. It optionally links to the existing citations
-- table for cross-referenced evidence blocks.
--
-- The verification pattern mirrors the legal-research skill's source logging:
-- every authority must be verified against the opinion text in the current
-- session. Unverified authorities are flagged.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS proposition_authorities (
    id                  SERIAL PRIMARY KEY,
    proposition_id      INTEGER REFERENCES strategy_propositions(id) ON DELETE CASCADE NOT NULL,

    -- The authority
    citation            TEXT NOT NULL,                               -- full Bluebook citation
    authority_type      TEXT NOT NULL CHECK (authority_type IN (
                            'statute', 'case', 'regulation', 'treatise', 'restatement', 'other'
                        )),
    jurisdiction        TEXT,                                        -- court or jurisdiction
    court               TEXT,                                        -- specific court if a case

    -- What the authority says
    holding_summary     TEXT,                                        -- one-sentence statement of what this authority holds
    operative_quotation TEXT,                                        -- exact quoted text from the opinion or statute
    pincite             TEXT,                                        -- exact page or section reference

    -- How it applies to the proposition
    holding_applied     TEXT,                                        -- how this authority applies to this specific element

    -- Verification (follows legal-research provenance pattern)
    verified            BOOLEAN DEFAULT false,                       -- confirmed against opinion text in current session?
    verification_method TEXT,                                        -- 'get_opinion_legal-hub', 'lookup_citation_legal-hub', 'fetch_protected_url'
    verification_note   TEXT,                                        -- any caveats about verification
    opinion_cluster_id  TEXT,                                        -- CourtListener cluster ID if applicable

    -- Optional link to existing citations table for evidence cross-reference
    citation_id         INTEGER REFERENCES citations(id) ON DELETE SET NULL,

    -- Which adversarial turn introduced this authority? (NULL if part of initial doctrine)
    -- FK added via ALTER TABLE after adversarial_turns is created (circular dependency)
    introduced_in_turn_id INTEGER,

    -- Source manifest reference
    source_ids          TEXT[] DEFAULT '{}',                         -- references to sidecar source entries

    sort_order          INTEGER DEFAULT 0,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prop_authorities_proposition ON proposition_authorities (proposition_id);
CREATE INDEX IF NOT EXISTS idx_prop_authorities_citation ON proposition_authorities (citation_id);
CREATE INDEX IF NOT EXISTS idx_prop_authorities_verified ON proposition_authorities (verified);
CREATE INDEX IF NOT EXISTS idx_prop_authorities_type ON proposition_authorities (authority_type);

-- ============================================================================
-- ADVERSARIAL ATTACKS — One row per attack on a proposition.
-- ============================================================================
-- An adversarial attack is a structured challenge to a specific proposition.
-- Each attack has a type (MTD, MSJ, factual_dispute, etc.), an overall
-- vulnerability rating, and a statement of what the adversary needs to win.
-- The attack contains 4 turns (T1→T2→T3→T4) stored in adversarial_turns.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS adversarial_attacks (
    id                  SERIAL PRIMARY KEY,
    proposition_id      INTEGER REFERENCES strategy_propositions(id) ON DELETE CASCADE NOT NULL,
    attack_type         TEXT NOT NULL CHECK (attack_type IN (
                            'MTD',              -- motion to dismiss (failure to state a claim)
                            'MSJ',              -- motion for summary judgment
                            'factual_dispute',  -- genuine dispute of material fact
                            'evidentiary',      -- attack on admissibility or weight of evidence
                            'procedural',       -- attack on procedural grounds
                            'jurisdictional',   -- attack on jurisdiction or venue
                            'constitutional',   -- constitutional challenge
                            'equitable',        -- attack on equitable relief prerequisites
                            'other'
                        )),
    rank                INTEGER DEFAULT 0,                           -- priority within the proposition (1 = most dangerous)

    -- What is the attack?
    motion_or_argument  TEXT NOT NULL,                               -- description of the attack
    target_element_label TEXT,                                       -- which element label this attacks (denormalized for readability)

    -- What authority does the adversary rely on?
    -- (Detailed authority records go in proposition_authorities linked to turns)

    -- What facts does the adversary leverage?
    leveraged_fact_ids  INTEGER[] DEFAULT '{}',                      -- strategy_facts the adversary uses

    -- Vulnerability assessment
    vulnerability       TEXT CHECK (vulnerability IN (
                            'LETHAL',       -- no viable counter; path fails if accepted
                            'WOUNDING',     -- real argument on both sides
                            'MINOR'         -- attack exists but our response is substantially stronger
                        )),

    -- What does the adversary need to win this attack?
    what_they_need_to_win TEXT,

    -- Terminal classification for this attack's path
    terminal_status     TEXT CHECK (terminal_status IN (
                            'CLOSED',       -- resolved in our favor
                            'CONTESTED',    -- both sides viable
                            'OPEN'          -- no response found — gap
                        )),

    notes               TEXT,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_attacks_proposition ON adversarial_attacks (proposition_id);
CREATE INDEX IF NOT EXISTS idx_attacks_vulnerability ON adversarial_attacks (proposition_id, vulnerability);
CREATE INDEX IF NOT EXISTS idx_attacks_type ON adversarial_attacks (attack_type);

-- ============================================================================
-- ADVERSARIAL TURNS — The T1→T2→T3→T4 dialectic per attack.
-- ============================================================================
-- Each turn is an independent row. This structure makes the adversarial walk
-- queryable: "Find every contested path where our counter-argument lacks a
-- verified pincite." Queryability is the point — JSONB can't do this.
--
-- T1 = Their attack (adversary)
-- T2 = Our response (defender)
-- T3 = Their counter (adversary)
-- T4 = Our rebuttal (defender)
--
-- T1 and T3 are generated by an adversary sub-agent that sees only the element
-- statement and controlling authority — not our T2/T4. This prevents
-- pulling punches.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS adversarial_turns (
    id                  SERIAL PRIMARY KEY,
    attack_id           INTEGER REFERENCES adversarial_attacks(id) ON DELETE CASCADE NOT NULL,
    turn_number         INTEGER NOT NULL CHECK (turn_number BETWEEN 1 AND 4),
    author_type         TEXT NOT NULL CHECK (author_type IN (
                            'ADVERSARY',     -- generated by adversary sub-agent (T1, T3)
                            'DEFENDER',      -- our response (T2, T4)
                            'ATTORNEY'       -- human attorney input
                        )),

    -- The argument
    argument_text       TEXT NOT NULL,

    -- Classification of this specific turn's strength
    turn_result         TEXT CHECK (turn_result IN (
                            'STRONG',        -- argument is well-supported and persuasive
                            'ADEQUATE',      -- argument is viable but not overwhelming
                            'WEAK',          -- argument exists but is thin
                            'NO_RESPONSE'    -- no viable argument found (gap)
                        )),

    -- The authority this turn primarily relies on (denormalized for quick access;
    -- detailed authority records go in proposition_authorities)
    primary_authority   TEXT,                                        -- citation string for quick reference

    -- Does this turn introduce new facts not previously mapped?
    introduced_fact_ids INTEGER[] DEFAULT '{}',

    notes               TEXT,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),

    UNIQUE (attack_id, turn_number)
);

CREATE INDEX IF NOT EXISTS idx_turns_attack ON adversarial_turns (attack_id);
CREATE INDEX IF NOT EXISTS idx_turns_author ON adversarial_turns (author_type);
CREATE INDEX IF NOT EXISTS idx_turns_result ON adversarial_turns (attack_id, turn_result);

-- Circular FK: proposition_authorities.introduced_in_turn_id → adversarial_turns.id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_authorities_introduced_in_turn'
          AND conrelid = 'proposition_authorities'::regclass
    ) THEN
        ALTER TABLE proposition_authorities
            ADD CONSTRAINT fk_authorities_introduced_in_turn
            FOREIGN KEY (introduced_in_turn_id) REFERENCES adversarial_turns(id) ON DELETE SET NULL;
    END IF;
END $$;

-- ============================================================================
-- PROPOSITION OVERLAY GATES — Procedural standards that filter substantive elements.
-- ============================================================================
-- An overlay is a proposition (proposition_type = 'overlay') that gates against
-- substantive propositions. The 12(b)(6) plausibility standard applies to every
-- element of every claim. The summary judgment no-genuine-dispute standard
-- applies to every fact. Overlays are AND-gated: the overlay must succeed AND
-- the substantive proposition must succeed.
--
-- Rather than auto-applying overlays to all propositions (which would be
-- implicit and opaque), this table makes gating explicit and queryable.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS proposition_overlay_gates (
    id                  SERIAL PRIMARY KEY,
    overlay_proposition_id INTEGER REFERENCES strategy_propositions(id) ON DELETE CASCADE NOT NULL,
    gated_proposition_id   INTEGER REFERENCES strategy_propositions(id) ON DELETE CASCADE NOT NULL,

    -- Why does this overlay gate against this proposition?
    rationale           TEXT,

    created_at          TIMESTAMPTZ DEFAULT now(),

    UNIQUE (overlay_proposition_id, gated_proposition_id)
);

CREATE INDEX IF NOT EXISTS idx_overlay_gates_overlay ON proposition_overlay_gates (overlay_proposition_id);
CREATE INDEX IF NOT EXISTS idx_overlay_gates_gated ON proposition_overlay_gates (gated_proposition_id);

-- ============================================================================
-- GAUNTLET CHECK CATEGORIES — Attack surfaces for systematic screening.
-- ============================================================================
-- The gauntlet is organized by attack surface. Each category groups related
-- checks that screen for vulnerabilities the element-by-element analysis
-- would miss (licensing, standing, SOL, preclusion, etc.).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gauntlet_check_categories (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,                            -- "Licensing / Regulatory"
    description     TEXT,                                            -- what this category screens for
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now()
);

INSERT INTO gauntlet_check_categories (name, description, sort_order) VALUES
('Standing / Capacity', 'Does the party have standing? Is the party the real party in interest? Is the chain of title complete?', 1),
('Licensing / Regulatory', 'Is the party licensed? Was the license valid at the relevant time? Are there regulatory enforcement actions?', 2),
('Preclusion / Abstention', 'Is there a prior action? Have these issues been litigated? Is there an arbitration clause? Federal overlap?', 3),
('Timing / Limitations', 'Has the statute of limitations run? Statute of repose? Notice requirements? Pre-suit demand requirements?', 4),
('Pleading / Procedure', 'Does the pleading state a claim? Are all elements pled? Proper parties? Venue? Jurisdiction?', 5),
('Evidence / Proof', 'What is the burden of proof? Who bears it? What evidence exists? What is missing? Spoliation issues?', 6),
('Remedies / Damages', 'What remedies are available? Statutory multipliers? Fee-shifting? Damage caps? Right to jury trial?', 7),
('Party-Specific Vulnerabilities', 'Pro se party? Repeat player? Judgment-proof? Insurance coverage?', 8)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- GAUNTLET CHECK DEFINITIONS — Reusable catalog of gauntlet checks.
-- ============================================================================
-- Each check is a doctrinally-grounded question that can be applied across
-- cases. Checks are reusable — defined once, run against every strategy.
-- The check_text is the question the agent asks. The check_logic describes
-- what PASS/FAIL/INQUIRY mean for this check.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gauntlet_check_definitions (
    id              SERIAL PRIMARY KEY,
    category_id     INTEGER REFERENCES gauntlet_check_categories(id) ON DELETE CASCADE NOT NULL,
    name            TEXT NOT NULL,                                   -- short label: "Debt Collector License Validity"
    check_text      TEXT NOT NULL,                                   -- the question: "Was the collector licensed at the time the account was opened?"
    check_logic     TEXT,                                            -- what PASS/FAIL/INQUIRY mean for this check
    applies_to      TEXT NOT NULL CHECK (applies_to IN (
                        'plaintiff', 'defendant', 'either', 'both'
                    )),
    authority_hint  TEXT,                                            -- typical statutory or case law basis
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now(),

    UNIQUE (category_id, name)
);

-- Seed core gauntlet checks
INSERT INTO gauntlet_check_definitions (category_id, name, check_text, check_logic, applies_to, authority_hint, sort_order) VALUES
-- Standing / Capacity
(1, 'Constitutional Standing', 'Does the plaintiff have Article III standing (injury in fact, causation, redressability)?', 'PASS: all three elements satisfied. FAIL: any element missing → dismissal for lack of jurisdiction. INQUIRY: facts unclear on one element.', 'plaintiff', 'U.S. Const. Art. III; Lujan v. Defenders of Wildlife, 504 U.S. 555 (1992)', 1),
(1, 'Real Party in Interest', 'Is the named party the real party in interest under the applicable rules?', 'PASS: named party is the real party. FAIL: wrong party named → FRCP 17 / state equivalent issue. INQUIRY: multiple possible parties.', 'either', 'FRCP 17; state equivalents', 2),
(1, 'Assignment Chain / Chain of Title', 'Can the party asserting the right produce a complete, unbroken chain of assignment from the original creditor?', 'PASS: complete chain documented. FAIL: gap in chain → no standing to enforce. INQUIRY: partial documentation produced.', 'plaintiff', 'UCC Article 9; O.C.G.A. § 11-9-203', 3),

-- Licensing / Regulatory
(2, 'Business License Validity', 'Is the party licensed to do business in this jurisdiction? Was the license valid at the time of the conduct at issue?', 'PASS: license valid at all relevant times. FAIL: no license or lapsed license → potential independent claim or defense. INQUIRY: license status unclear.', 'either', 'State business licensing statutes; state financial regulations', 1),
(2, 'Debt Collector License Validity', 'If a debt collector, is the party licensed under state collection agency laws? Was the license valid AT THE TIME THE ACCOUNT WAS OPENED (not just at time of suit)?', 'PASS: license valid at account opening and all relevant times. FAIL: no license or lapsed at account opening → FDCPA/state law violation. INQUIRY: license status needs verification with state regulator.', 'defendant', 'State collection agency licensing acts; FDCPA; state OFR/DFI websites', 2),
(2, 'Regulatory Enforcement History', 'Has the party been subject to regulatory enforcement actions, consent orders, or pattern-of-conduct findings?', 'PASS: no adverse regulatory history. FAIL: active enforcement action or consent order → potential claim support, pattern evidence. INQUIRY: historical actions of unclear relevance.', 'either', 'FTC, CFPB, state AG enforcement databases; PACER', 3),

-- Preclusion / Abstention
(3, 'Prior Action Pending', 'Is there a prior action pending between these parties that could trigger claim preclusion, issue preclusion, or abstention?', 'PASS: no prior action. FAIL: prior action → dismissal or stay risk. INQUIRY: related action with different parties or claims.', 'either', 'Res judicata; collateral estoppel; Colorado River abstention; Anti-Injunction Act', 1),
(3, 'Arbitration Clause Applicability', 'Is there an arbitration clause that covers any of the claims? Is it enforceable? Has it been waived?', 'PASS: no arbitration clause or it does not cover these claims. FAIL: enforceable clause covers claims → motion to compel risk. INQUIRY: clause exists but scope or enforceability disputed.', 'either', 'FAA 9 U.S.C. § 1 et seq.; state arbitration acts', 2),
(3, 'Federal Overlap / Preclusion Risk', 'Is there a parallel federal action? Do the claims overlap such that a federal ruling could have preclusive effect on state claims?', 'PASS: no federal overlap. FAIL: federal ruling would preclude → file in federal court or narrow state claims. INQUIRY: overlapping facts but different legal theories.', 'either', 'Issue preclusion; claim preclusion; Rooker-Feldman doctrine', 3),

-- Timing / Limitations
(4, 'Statute of Limitations', 'Has the statute of limitations run on each claim? When did the claim accrue? Are there tolling doctrines?', 'PASS: all claims within SOL. FAIL: SOL expired on one or more claims → dismissal. INQUIRY: accrual date or tolling unclear.', 'plaintiff', 'State SOL statutes; continuing violation doctrine; discovery rule; equitable tolling', 1),
(4, 'Statute of Repose', 'Does a statute of repose apply that bars the claim regardless of accrual date?', 'PASS: no repose statute or claim within period. FAIL: repose period expired → absolute bar. INQUIRY: unclear whether repose applies to this claim type.', 'plaintiff', 'State statutes of repose', 2),
(4, 'Pre-Suit Requirements', 'Are there pre-suit notice requirements, demand letters, administrative exhaustion, or other conditions precedent?', 'PASS: all pre-suit requirements satisfied. FAIL: requirement not met → dismissal or abatement. INQUIRY: unclear whether requirement applies.', 'plaintiff', 'State tort claims acts; administrative procedure acts; specific statutory prerequisites', 3),

-- Pleading / Procedure
(5, 'Pleading Standard Compliance', 'Does the complaint or motion satisfy the applicable pleading standard (Twombly/Iqbal plausibility vs. notice pleading)?', 'PASS: well-pled with factual support. FAIL: conclusory allegations without factual basis. INQUIRY: borderline.', 'plaintiff', 'FRCP 8, 9(b), 12(b)(6); Bell Atlantic v. Twombly, 550 U.S. 544 (2007); Ashcroft v. Iqbal, 556 U.S. 662 (2009)', 1),
(5, 'Necessary Parties Joinder', 'Are all necessary parties joined? Is there a risk of dismissal under FRCP 19 or state equivalent for failure to join?', 'PASS: all necessary parties joined. FAIL: missing necessary party. INQUIRY: party''s necessity unclear.', 'plaintiff', 'FRCP 19; state joinder rules', 2),
(5, 'Personal Jurisdiction', 'Does the court have personal jurisdiction over the defendant? Minimum contacts? General or specific jurisdiction?', 'PASS: jurisdiction clear. FAIL: no basis for jurisdiction → dismissal or transfer. INQUIRY: fact-dependent.', 'plaintiff', 'Int''l Shoe v. Washington, 326 U.S. 310 (1945); state long-arm statutes', 3),
(5, 'Subject Matter Jurisdiction', 'Does the court have subject matter jurisdiction? Federal question? Diversity? Amount in controversy?', 'PASS: jurisdiction clear. FAIL: no SMJ → dismissal. INQUIRY: amount in controversy borderline.', 'plaintiff', '28 U.S.C. §§ 1331, 1332; state court jurisdictional statutes', 4),

-- Evidence / Proof
(6, 'Evidence Quality Assessment', 'For each element, what is the quality of the available evidence? Direct vs. circumstantial? Documentary vs. testimonial?', 'INQUIRY: qualitative assessment — outputs evidence quality rating per element.', 'either', 'Rules of evidence; best evidence rule; authentication requirements', 1),
(6, 'Burden of Proof Allocation', 'Who bears the burden of proof on each element? Burden of production? Burden of persuasion? Has the burden shifted?', 'INQUIRY: maps burden to each element for gate walk computation.', 'either', 'State and federal evidence codes; summary judgment standards', 2),
(6, 'Spoliation / Adverse Inference', 'Has any party destroyed, lost, or failed to preserve relevant evidence? Is an adverse inference available?', 'PASS: no spoliation. FAIL: spoliation found → adverse inference or sanctions. INQUIRY: preservation obligations unclear.', 'either', 'FRCP 37; state spoliation doctrines; inherent court authority', 3),

-- Remedies / Damages
(7, 'Statutory Damage Multipliers', 'Are treble damages, statutory damages, or other multipliers available? Under what conditions?', 'INQUIRY: catalogs available multipliers and their prerequisites.', 'plaintiff', 'State consumer protection acts (e.g., O.C.G.A. § 10-1-399); FDCPA § 1692k', 1),
(7, 'Fee-Shifting Availability', 'Is attorney fee-shifting available? Is it mandatory or discretionary? One-way or two-way?', 'INQUIRY: catalogs fee-shifting provisions applicable to each claim.', 'either', 'Fee-shifting statutes; contractual fee provisions; FRCP 54(d)', 2),
(7, 'Equitable Relief Prerequisites', 'For equitable relief, are the prerequisites satisfied? Irreparable harm? Inadequate remedy at law? Balancing of equities?', 'PASS: prerequisites satisfied. FAIL: missing prerequisite → equitable relief unavailable. INQUIRY: borderline on one factor.', 'plaintiff', 'State equity statutes (e.g., O.C.G.A. § 9-5-1); federal equity standards', 3),

-- Party-Specific Vulnerabilities
(8, 'Pro Se Litigant Considerations', 'Is a party proceeding pro se? Affects pleading latitude, procedural compliance, and judicial patience.', 'INQUIRY: notes pro se status and implications for strategy.', 'either', 'Haines v. Kerner, 404 U.S. 519 (1972); Erickson v. Pardus, 551 U.S. 89 (2007)', 1),
(8, 'Repeat Player / Pattern Evidence', 'Has the opposing party been involved in similar litigation? Are there prior inconsistent positions or pattern findings?', 'INQUIRY: searches for prior litigation by this party on similar issues.', 'either', 'PACER; state court dockets; FTC/CFPB enforcement databases', 2),
(8, 'Collectability / Judgment-Proof Risk', 'If we win, can we collect? Is the opposing party judgment-proof? Are there insurance coverage issues?', 'INQUIRY: assesses practical value of a favorable judgment.', 'defendant', 'State collection law; insurance coverage research', 3)
ON CONFLICT (category_id, name) DO NOTHING;

-- ============================================================================
-- STRATEGY GAUNTLET RESULTS — Per-strategy, per-check results.
-- ============================================================================
-- When the gauntlet runs against a strategy, each check produces a result.
-- FAIL means the check found an independently dispositive problem.
-- INQUIRY means the check raised a question needing further investigation.
-- PASS means the check found no issue.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS strategy_gauntlet_results (
    id                  SERIAL PRIMARY KEY,
    strategy_id         INTEGER REFERENCES strategies(id) ON DELETE CASCADE NOT NULL,
    check_definition_id INTEGER REFERENCES gauntlet_check_definitions(id) ON DELETE CASCADE NOT NULL,
    party_id            INTEGER REFERENCES parties(id) ON DELETE SET NULL,  -- which party was checked

    result              TEXT NOT NULL CHECK (result IN (
                            'PASS',         -- no issue found
                            'FAIL',         -- independently dispositive problem
                            'INQUIRY',      -- question raised, needs investigation
                            'NOT_APPLICABLE' -- check does not apply to this strategy
                        )),

    finding             TEXT,                                            -- what the check found (detailed explanation)
    recommendation      TEXT,                                            -- what to do about it
    severity            TEXT CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')),

    -- Citation to evidence or authority supporting the finding
    source_description  TEXT,

    -- Track whether this finding has been addressed
    addressed           BOOLEAN DEFAULT false,
    addressed_notes     TEXT,

    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    UNIQUE (strategy_id, check_definition_id, party_id)
);

CREATE INDEX IF NOT EXISTS idx_gauntlet_results_strategy ON strategy_gauntlet_results (strategy_id);
CREATE INDEX IF NOT EXISTS idx_gauntlet_results_check ON strategy_gauntlet_results (check_definition_id);
CREATE INDEX IF NOT EXISTS idx_gauntlet_results_result ON strategy_gauntlet_results (strategy_id, result);
CREATE INDEX IF NOT EXISTS idx_gauntlet_results_severity ON strategy_gauntlet_results (strategy_id, severity);

-- ============================================================================
-- MIGRATION RECORD
-- ============================================================================
INSERT INTO schema_migrations (version, name) VALUES (2, 'strategy_engine_schema')
ON CONFLICT (version) DO NOTHING;
