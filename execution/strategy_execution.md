    PRIMARY AGENT (Orchestrator)
                        "Build the strategy for Count II"
                                  │
                                  │ Reads: case_facts, doctrine_elements, strategy intent
                                  │ Writes: strategy_propositions, strategy_facts, mappings
                                  │ Delegates: specialized sub-agents for focused work
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
   DOCTRINE AGENT           FACT AGENT              ADVERSARY AGENT
   "Research elements     "Map facts to           "Attack E1 from
    for wrongful repo      element E1"             CPS's perspective"
    under GA law"
                                  │                         │
                                  │                         │
                          DEFENDER AGENT             ADVERSARY AGENT
                          "Respond to T1"           "Counter T2"
                                  │                         │
                          DEFENDER AGENT
                          "Rebuttal T3"
                                  │
                        GATE WALK (deterministic function)
                        "AND/OR propagate terminal states"
                                  │
                        GAUNTLET RUNNER
                        "Check licensing, SOL, standing..."
                                  │
                        PRIMARY AGENT
                        Presents SPOF map, rankings, gaps to user
