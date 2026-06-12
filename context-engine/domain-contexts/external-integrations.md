# External Integrations

> **Purpose:** Document every external tool available to the Vision agent, their dependencies, and usage patterns
> **Last Updated:** 2026-06-11

---

## 1. Business Overview

### What This Domain Does

The Vision agent can reach beyond the case database to research law, verify citations, search the web, and read protected legal websites. These capabilities are provided by 13 external tools ported from the war-room-1 MCP server as in-process SDK custom tools.

### Architecture

```
Agent prompt
    ↓
ClaudeAgentOptions.mcp_servers
    ├── "vision"      → create_vision_server(case_id)     [26 case-scoped DB tools]
    └── "legal_hub"   → create_external_tools_server()    [13 global external tools]
                              ↓
                    chat/external_tools.py
                    ├── Research (4): deep_research, quick_search, extract_page, write_report
                    ├── Court Listener (5): search_cases, get_opinion, query_opinion, query_document, lookup_citation
                    ├── Statutes (3): lookup_cfr_section, search_cfr, lookup_usc_section
                    └── Scraper (1): fetch_protected_url
```

All tools are accessed as `mcp__legal_hub__{tool_name}` in the agent's context. They're all pre-approved via `allowed_tools: ["mcp__legal_hub__*"]`.

---

## 2. Tool Catalog

### Research Tools

| Tool | What It Does | API Dependency | Env Vars |
|---|---|---|---|
| `quick_search` | Fast web search via Tavily | Tavily Search API | `TAVILY_API_KEY` |
| `extract_page` | Full text extraction of a URL | Tavily Extract API | `TAVILY_API_KEY` |
| `deep_research` | Multi-source deep research report | GPT Researcher + Tavily | `TAVILY_API_KEY`, `OPENAI_API_KEY` |
| `write_report` | Format research data into a report | GPT Researcher | `OPENAI_API_KEY` |

**Status:** `quick_search` and `extract_page` are fully operational. `deep_research` and `write_report` require `gpt-researcher` package (builds fail on Apple Silicon — gracefully error).

**Usage pattern:**
```
quick_search("what is the statute of limitations for fraud in Georgia")
    → extract_page(result_url)                          # get full text
    → deep_research("Georgia fraud limitations...")      # comprehensive report (when available)
```

### Court Listener Tools

| Tool | What It Does | API Dependency | Env Vars |
|---|---|---|---|
| `search_cases` | Search case law by keyword, party, citation | Court Listener REST API | `COURT_LISTENER_API_KEY` |
| `get_opinion` | Retrieve full opinion text by ID | Court Listener REST API | `COURT_LISTENER_API_KEY` |
| `query_opinion` | Ask a specific question about an opinion | Court Listener + Mistral | Both keys + `MISTRAL_API_KEY` |
| `query_document` | Ask a question about a document (PDF/DOCX) | Mistral Document Q&A | `MISTRAL_API_KEY` |
| `lookup_citation` | Resolve a legal citation to a case | Court Listener Citation API | `COURT_LISTENER_API_KEY` |

**All fully operational.** Uses `httpx` for async HTTP. The `CourtListenerClient` class is defined inline in `external_tools.py` (lightweight — no external client library needed).

**Usage pattern:**
```
search_cases("summary judgment standard fraud georgia")
    → get_opinion(opinion_id)                           # read full opinion
    → query_opinion(opinion_id, "What standard did the court apply?")
    → lookup_citation("384 U.S. 436")                   # verify a citation
```

### Statutes & Regulations Tools

| Tool | What It Does | API Dependency | Env Vars |
|---|---|---|---|
| `lookup_cfr_section` | Fetch full text of a CFR section | eCFR public API | None |
| `search_cfr` | Full-text search of CFR | eCFR public API | None |
| `lookup_usc_section` | Fetch full text of a USC section | uscode.house.gov | None |

**All fully operational. No API keys needed.** These hit public government endpoints directly.

**Usage pattern:**
```
lookup_cfr_section("29 CFR 1630.2")                     # get specific regulation
search_cfr("reasonable accommodation disability", title=29)  # find relevant sections
lookup_usc_section("42 U.S.C. 12112")                   # get specific statute
```

### Stealth Scraper Tool

| Tool | What It Does | API Dependency | Env Vars |
|---|---|---|---|
| `fetch_protected_url` | Fetch a URL through a stealth browser | CloakBrowser via SSH tunnel | `SCRAPER_*` (from war-room config) |

**Conditionally operational.** Requires the CloakBrowser infrastructure to be running. Uses `ScraperClient` from war-room-1's `clients/` module. Gracefully errors if the scraper is unreachable.

**Use when:** A legal site blocks normal HTTP clients (Cloudflare, Akamai Bot Manager). For public endpoints, prefer dedicated tools (CourtListener, eCFR, uscode).

---

## 3. Dependencies

### Python Packages

| Package | Version | Used By | Status |
|---|---|---|---|
| `claude-agent-sdk` | 0.2.93 | `@tool`, `create_sdk_mcp_server`, `ToolAnnotations` | ✓ |
| `httpx` | 0.28.1 | Court Listener, statutes, scraper HTTP | ✓ |
| `tavily` | 1.1.0 | `quick_search`, `extract_page` | ✓ |
| `gpt-researcher` | — | `deep_research`, `write_report` | ✗ (build failure) |

### Environment Variables

| Variable | Required By | Set in .env? |
|---|---|---|
| `TAVILY_API_KEY` | `quick_search`, `extract_page`, `deep_research` | ✓ |
| `COURT_LISTENER_API_KEY` | All 5 Court Listener tools | ✓ |
| `MISTRAL_API_KEY` | `query_opinion`, `query_document` | ✓ |
| `OPENAI_API_KEY` | `gpt-researcher` backend (when available) | ✓ |

### War-Room Imports

The `fetch_protected_url` tool and the disabled `kg_*` tools import from war-room-1:

```python
_WAR_ROOM_MCP = Path("/Users/ianbruce/code/war-room-1/mcp-server")
sys.path.insert(0, str(_WAR_ROOM_MCP))

from clients import ScraperClient, ScraperError   # scraper
from clients.legal_brain import Neo4jClient        # kg_* tools (disabled)
from config import config as war_room_config       # scraper + kg config
```

These imports happen inside the tool handlers (lazy), so a missing war-room-1 path only breaks those specific tools.

---

## 4. Code Navigation

### Key Files

| File | Purpose |
|---|---|
| `chat/external_tools.py` | All 13 external tool definitions + server factory |
| `chat/manager.py` | Registers `legal_hub` server in `ClaudeAgentOptions` |
| `.env` | API keys for external services |
| `/Users/ianbruce/code/war-room-1/mcp-server/server.py` | Original MCP tools (source of truth) |
| `/Users/ianbruce/code/war-room-1/mcp-server/clients/` | Client libraries for scraper, Neo4j, etc. |

### Adding a New External Tool

1. Add `@tool(...)` in `chat/external_tools.py` following the existing pattern
2. Handle all exceptions — return `is_error: True`, never let the handler throw
3. Add to the `tools` list in `create_external_tools_server()`
4. Add any new env vars to `.env`
5. If importing from war-room-1, use lazy import inside the handler
6. Restart the backend to pick up changes

### Disabling a Tool

Comment it out of the `tools` list in `create_external_tools_server()`. The code stays. The agent stops seeing it.

---

## 5. Common Tasks

### "I need to add a new statute lookup source"

1. Add helper functions (citation parser, HTML stripper) near the statutes section
2. Add `@tool(...)` following the `lookup_usc_section` pattern
3. Register in server factory
4. If public API, no env vars needed. If authenticated, add to `.env`

### "I need to debug a tool that's erroring"

1. Check the agent's tool call output in the chat UI
2. Check env vars are set: `python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); print(os.getenv('KEY'))"`
3. Check the tool's import path: `python -c "from chat.external_tools import tool_name; print('OK')"`
4. Check the war-room-1 path is accessible (for scraper/kg tools)

### "I need to port another tool from the war-room-1 MCP server"

1. Find the tool in `war-room-1/mcp-server/server.py`
2. Convert `@mcp.tool()` → `@tool(...)` with JSON Schema params
3. Convert return `dict` → `{"content": [{"type": "text", "text": json.dumps(result)}]}`
4. Convert individual params → `args: dict[str, Any]` with `args.get()`
5. Add `readOnlyHint=True` if read-only
6. Copy any inline client classes (like `CourtListenerClient`)
7. Register in server factory

---

## 6. Disabled Tools (Future)

All `kg_*` Legal Brain (Neo4j) tools are defined but disabled:

- **Write (4):** `kg_ingest_case`, `kg_ingest_strategy`, `kg_ingest_counter_requirements`, `kg_ingest_evidence_bundle`
- **Read (8):** `kg_get_case_documents`, `kg_get_case_parties`, `kg_get_claim_support`, `kg_get_attack_context`, `kg_find_contradictions`, `kg_get_exhibit_impact`, `kg_get_unsupported_claims`, `kg_get_case_readiness`

To enable: uncomment in `create_external_tools_server()` tools list. Requires Neo4j credentials in `.env` (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`).

---

## 7. Known Issues

- [ ] **gpt-researcher unavailable:** `deep_research` + `write_report` error gracefully
- [ ] **Scraper depends on war-room-1 path:** Hardcoded to `/Users/ianbruce/code/war-room-1/mcp-server`
- [ ] **No integration tests:** Can't call `@tool`-wrapped functions directly
- [ ] **Court Listener rate limits:** Free tier has request caps — agent may hit them during heavy research

---

## 8. Related Domains

| Domain | Relationship | Context File |
|---|---|---|
| Agent Tool Building | How to build and register tools | `domain-contexts/agent-tool-building.md` |
| Chat Manager | Agent session lifecycle | `chat/manager.py` |
| Database | Vision DB tools (the other half of the agent's toolkit) | `core/db.py` |
