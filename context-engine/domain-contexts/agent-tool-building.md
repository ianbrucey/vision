# Agent Tool Building

> **Purpose:** Onboard developers to building and registering SDK custom tools for the Vision agent
> **Last Updated:** 2026-06-11

---

## 1. Business Overview

### What This Domain Does

Vision agents (Evidence Agent + Strategy Engine) are powered by tools — functions the agent can call during a conversation to read from the database, write to it, search the web, look up legal citations, and query external APIs. Tools are the agent's hands.

There are two kinds of tools in Vision:

| Kind | Location | Server Name | Scoped To |
|---|---|---|---|
| **Vision tools** (DB, case ops) | `chat/tools.py` | `mcp__vision__*` | Case (closure over `case_id`) |
| **External tools** (research, court listener, statutes) | `chat/external_tools.py` | `mcp__legal_hub__*` | Global (no case scope) |

### Key Rules

- Vision tools MUST be closure-scoped to `case_id` — the agent never provides or sees it
- External tools are global — they don't know about cases
- All tools use the `@tool` decorator from `claude_agent_sdk`
- Tool servers are created via `create_sdk_mcp_server(name, version, tools=[])`
- Servers are registered in `chat/manager.py` via `ClaudeAgentOptions.mcp_servers`
- Tool names become `mcp__{server_name}__{tool_name}` in the agent's context

---

## 2. Code Navigation Guide

### Entry Points

| If you want to... | Start at... | Then follow... |
|---|---|---|
| Add a Vision DB tool | `chat/tools.py` → `create_vision_server()` | Add `@tool(...)` inside the factory, register in the `tools` list |
| Add an external tool | `chat/external_tools.py` | Add `@tool(...)` at module level, register in `create_external_tools_server()` |
| Change tool registration | `chat/manager.py` → `ClaudeAgentOptions` | `mcp_servers` dict + `allowed_tools` list |
| See what tools the agent has | `chat/manager.py:62-74` | `mcp_servers={"vision": ..., "legal_hub": ...}` |

### Key Files

| File | Purpose | Key Functions/Patterns |
|---|---|---|
| `chat/tools.py` | Vision DB tools (26 tools) | `create_vision_server(case_id)` — factory that closes over case |
| `chat/external_tools.py` | External integration tools (13 active) | `create_external_tools_server()` — returns global MCP server |
| `chat/manager.py` | Agent session lifecycle | `AgentSession._connect()` — wires servers into `ClaudeAgentOptions` |
| `core/db.py` | Database helpers | All take `conn` as first param — callers manage connections |

### Tool Declaration Pattern

```python
from claude_agent_sdk import tool, ToolAnnotations, create_sdk_mcp_server

@tool(
    "tool_name",                    # unique name — becomes mcp__server__tool_name
    "Description Claude reads to decide when to call this tool.",  # be specific
    {                               # JSON Schema for parameters
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "What this param is."},
            "param2": {"type": "integer", "description": "..."},
        },
        "required": ["param1"],
    },
    annotations=ToolAnnotations(
        readOnlyHint=True,          # True = no side effects, can run in parallel
    ),
)
async def tool_name(args: dict[str, Any]) -> dict[str, Any]:
    """Handler — receives validated args, returns SDK result."""
    try:
        # ... do the work ...
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    except Exception as exc:
        return {
            "content": [{"type": "text", "text": f"tool_name failed: {exc}"}],
            "is_error": True,
        }
```

### Return Format

```python
# Success
{"content": [{"type": "text", "text": "..."}]}

# Error (agent sees this and can retry)
{"content": [{"type": "text", "text": "..."}], "is_error": True}

# Uncaught exception (agent loop STOPS — avoid this)
raise SomeException("...")
```

### Helpers (in external_tools.py)

```python
def _result(data: dict | str) -> dict:
    """Wrap data as a standard success result."""
    text = json.dumps(data, default=str) if isinstance(data, dict) else data
    return {"content": [{"type": "text", "text": text}]}

def _error(message: str) -> dict:
    """Return an error the agent can react to."""
    return {"content": [{"type": "text", "text": message}], "is_error": True}
```

---

## 3. Server Registration

Tools are grouped into named servers. Each server is a key in `mcp_servers`:

```python
# chat/manager.py

vision_server = create_vision_server(self.case_id)      # case-scoped DB tools
legal_hub = create_external_tools_server()               # global external tools

options = ClaudeAgentOptions(
    mcp_servers={
        "vision": vision_server,
        "legal_hub": legal_hub,
    },
    allowed_tools=[
        "mcp__vision__*",       # all case tools, no prompts
        "mcp__legal_hub__*",    # all external tools, no prompts
        "Read", "Grep", "Write", "Edit",   # built-in filesystem tools
        "WebSearch", "WebFetch",           # built-in web tools
    ],
)
```

### Adding a New Tool — Checklist

1. **Define the tool:** Add `@tool(...)` + async handler in the right file
2. **Register it:** Add the function name to the `tools` list in the server factory
3. **Allowed tools:** If it's in a new server, add `mcp__{server}__*` to `allowed_tools`
4. **Env vars:** If it needs API keys, add them to `.env`
5. **Dependencies:** If it needs new packages, add to `requirements.txt`
6. **Restart:** The server is created at session start — restart the agent session

---

## 4. Case-Scoped Tools (Vision Server)

Tools in `create_vision_server(case_id)` follow a closure pattern:

```python
def create_vision_server(case_id: int):
    # case_id is captured here — every tool closes over it

    def _conn():
        """Return a DB connection with schema ensured."""
        conn = connect()
        ensure_chat_schema()
        return conn

    @tool("get_case", "Get case overview...", {}, annotations=ToolAnnotations(readOnlyHint=True))
    async def get_case(args):
        conn = _conn()
        try:
            # Uses closed-over case_id, NOT args["case_id"]
            row = query_one(conn, "SELECT * FROM cases WHERE id = %s", (case_id,))
            return _result({"case": row})
        finally:
            conn.close()

    # ... more tools ...

    return create_sdk_mcp_server(name="vision", version="1.0.0", tools=[...])
```

The agent NEVER provides `case_id`. It's baked into every tool handler when the server is created.

---

## 5. Content Envelope Convention

When tools return structured data, use the `_result()` helper which JSON-serializes dicts. The agent receives the JSON string in the `text` content block. For very large payloads, truncate or summarize in the description so the agent knows to use `get_workspace_item` or similar for full content.

---

## 6. Common Tasks

### "I need to add a new DB-backed tool for the agent"

1. Add the DB helper in `core/db.py` (takes `conn` as first param, returns dicts/lists)
2. Add the `@tool(...)` inside `create_vision_server()` in `chat/tools.py`
3. Import the DB helper inside the handler (lazy import pattern)
4. Register in the server's `tools` list at the bottom of `create_vision_server`
5. If it's a write tool, omit `readOnlyHint` (or set to False)

### "I need to add an external API tool"

1. Add `@tool(...)` at module level in `chat/external_tools.py`
2. Read API keys from `os.getenv()` — never hardcode
3. Handle all exceptions — return `is_error: True`, never let the handler throw
4. Register in `create_external_tools_server()` tools list
5. Add env vars to `.env`

### "I need to disable a tool temporarily"

Comment it out of the `tools` list in the server factory. Leave the `@tool` definition intact. The agent won't see it, but the code is preserved.

---

## 7. Testing

Tools wrapped with `@tool` become `SdkMcpTool` objects — they can't be called directly in Python. To test:

1. **Import verification:** Import the server factory, call it, verify no errors
2. **Env vars:** Verify all required keys are set
3. **Integration test:** Start a chat session, ask the agent to use the tool, check the result

```bash
# Quick import check
cd backend && python -c "from chat.external_tools import create_external_tools_server; create_external_tools_server()"
```

---

## 8. Known Issues

- [ ] **gpt-researcher unavailable:** `deep_research` and `write_report` gracefully error because the `gpt-researcher` package fails to build (numba/llvmlite on Apple Silicon). Tools return a clear error message to the agent.
- [ ] **Legal Brain (Neo4j) tools disabled:** All `kg_*` tools are defined but commented out of the server factory. Uncomment when Neo4j infrastructure is set up.
- [ ] **`@tool` objects not callable:** Can't test tools by calling them directly — they're SDK wrappers, not raw functions.

---

## 9. Related Domains

| Domain | Relationship | Context File |
|---|---|---|
| External Integrations | The specific tools available | `domain-contexts/external-integrations.md` |
| Database | DB helpers used by Vision tools | `core/db.py` |
| Chat Manager | Agent session + tool registration | `chat/manager.py` |
