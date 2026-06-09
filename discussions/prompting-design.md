## Analysis: The Prompt Assembly Problem

This is two problems that look like one:

### Problem A: Security (Tool Scoping)

Solved. The answer is in the transcript — **implicit scoping at the tool execution layer.** The LLM never sees a `user_id`. The backend injects it from the session token before any query hits the database. This is standard multi-tenant SaaS architecture, just applied to tool calls.

```
LLM calls: search_documents(query="motion to dismiss")
Backend executes: search_documents(query="motion to dismiss", case_id=session.case_id)
```

One sentence of implementation: every tool handler receives a session context and all DB-facing parameters are hardcoded from that context, not extracted from LLM output.

---

### Problem B: Protocol Bloat (The Real Challenge)

You described this perfectly with the law book metaphor. The question is: **how does the agent find the right chapter?**

Three architectures, ordered by complexity:

|                          | Pattern A: Fat System Prompt                 | Pattern B: JIT Assembly                                           | Pattern C: Supervisor Router                        |
| ------------------------ | -------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------- |
| **How it works**   | All protocols in the system prompt           | Search protocol registry → inject matching protocols into prompt | Supervisor agent delegates to specialist sub-agents |
| **Protocol limit** | ~5 before degradation                        | ~50-100 (only 2-3 loaded at a time)                               | Unlimited (each agent only knows its protocol)      |
| **Complexity**     | None                                         | Medium (registry + search + assembly)                             | High (sub-agent lifecycle, streaming, state)        |
| **Latency**        | Zero                                         | One search call before agent starts                               | Sub-agent spawn overhead per delegation             |
| **Cost**           | Every turn pays for all protocols in context | Only pay for relevant protocols                                   | Supervisor is cheap; workers pay only when invoked  |

**Pattern A is what you have now** with CLAUDE.md files. It breaks at scale.

**Pattern B is the natural next step.** It preserves the single-agent model but makes the system prompt dynamic. This is the right architecture for the Evidence Agent (Layers 1-6) where one agent does many things — search, read, cite, summarize.

**Pattern C is the end state for the Strategy Engine (Layers 7-X).** Those protocols are deep, sequential, and adversarial. An Adversarial Walk sub-agent needs its own context window with its own adversarial instruction — it can't share context with the main agent without contamination.

---

### What a Protocol Registry Looks Like

```
protocols/
├── registry.json          # Index — what exists and when to use it
├── core/
│   ├── personality.md     # Always loaded — "You are the Vision Evidence Agent..."
│   └── tools.md           # Always loaded — tool descriptions
├── evidence/
│   ├── search.md          # Composed search chain protocol
│   ├── summarize.md       # Citation-anchored summarization
│   └── timeline.md        # Chronological event extraction
├── strategy/
│   ├── doctrine-tree.md   # Build legal claim model
│   ├── fact-map.md        # Map facts to claim elements
│   ├── adversarial-walk.md
│   ├── gate-walk.md
│   └── gauntlet.md
└── outputs/
    ├── company-profile.md
    └── legal-memo.md
```

`registry.json`:

```json
{
  "adversarial-walk": {
    "name": "Adversarial Walk",
    "triggers": ["analyze claim", "test argument", "adversarial", "opposing counsel"],
    "protocol_file": "strategy/adversarial-walk.md",
    "tools": ["read_blocks", "cite_authority"],
    "sub_agent": true,
    "reason": "Requires isolated adversarial context"
  }
}
```

The assembly flow:

```
User: "Run an adversarial analysis on the negligence claim"
       │
       ▼
Backend: semantic search registry for "adversarial analysis"
       │
       ▼
Backend: loads core/personality.md + strategy/adversarial-walk.md
       │
       ▼
Backend: constructs system prompt = core instructions + protocol + scoped tools
       │
       ▼
Agent runs with exactly the context it needs — nothing more, nothing less
```

---

### Where to Store the Protocols

**Files, indexed by the database.** Not one or the other — both.

| What                                              | Where                                       | Why                                                        |
| ------------------------------------------------- | ------------------------------------------- | ---------------------------------------------------------- |
| Protocol markdown (the actual instructions)       | Files in `protocols/`                     | Version-controlled, human-editable, diffable               |
| Registry index (name, triggers, tools, file path) | Database table `protocols`                | Queryable at runtime, searchable by the assembly step      |
| Runtime assembly                                  | Backend reads file → injects into API call | The DB points to the file; the file is the source of truth |

This gives you: `git diff` on protocol changes, database-speed discovery, and no markdown in SQL rows.

---

### What to Document

Same approach as tagging — capture the design decisions in a file, then put it away until tooling is ready. The document would cover:

1. Implicit tool scoping (security)
2. JIT prompt assembly architecture
3. Protocol registry schema (DB + files)
4. Supervisor vs. specialist agent boundary
5. Implementation sequence
