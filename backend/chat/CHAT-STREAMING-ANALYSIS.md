# Chat Streaming Pipeline — Analysis

## Architecture at a Glance

```
User types message
  │
  ▼
ChatTab.tsx: handleSend()
  ├─ Creates user message card
  ├─ Creates empty assistant placeholder card
  └─ Calls streamChatMessage() → SSE fetch to :8400
       │
       ▼
routes/chat.py: send_message()
  └─ manager.stream_message(session_id, user_message) → AsyncIterator[SSE string]
       │
       ▼
manager.py: ChatManager.stream_message()
  ├─ Persists user message to DB
  ├─ Gets or creates AgentSession (long-lived ClaudeSDKClient)
  ├─ await agent.send_message(user_message)  → client.query(raw_text)
  └─ async for event in agent.receive():     → client.receive_response()
       │
       ▼
manager.py: AgentSession.receive()
  └─ Iterates SDK message types, yields SSE-ready dicts:
       StreamEvent       → {"type":"assistant","content":"partial text"}
       AssistantMessage  → TextBlock: {"type":"assistant","content":"final text"}
                          → ToolUseBlock: {"type":"tool_call","name":"Bash","inputs":{...}}
       UserMessage       → ToolResultBlock: {"type":"tool_result","content":"..."}
       ResultMessage     → {"type":"done","cost":0.01}
       │
       ▼
SSE over HTTP (text/event-stream)
  data: {"type":"assistant","content":"Let me search..."}\n\n
  data: {"type":"tool_call","name":"Bash","inputs":{...}}\n\n
  data: {"type":"tool_result","content":"..."}\n\n
  data: {"type":"assistant","content":"Based on the results..."}\n\n
  data: {"type":"done","cost":0.01}\n\n
       │
       ▼
api.ts: streamChatMessage()
  └─ ReadableStream reader, splits buffer on \n\n, parses "data: " prefix,
     calls onEvent(parsed_json) for each event
       │
       ▼
ChatTab.tsx: onEvent callback (inside setMessages)
  └─ Mutates messages array based on event.type
```

---

## The Message Array State Machine (Frontend)

### Initial state (after user sends message)

```
Messages array: [...prev, user_msg, assistant_empty]
                                   │              │
                                   │              └─ {role:"assistant", content:""}
                                   └─ {role:"user", content:"Analyze case 3"}
```

`copy[copy.length - 1]` = `assistant_empty` (last element)
`last.role === "assistant"` = **TRUE** ← text deltas will append here

### 🔴 BUG: After a tool call is pushed

The frontend's `onEvent` callback pushes `tool_call` and `tool_result` as **new array elements**:

```
Messages array: [...prev, user_msg, assistant("Let me search..."), tool_call, tool_result]
                                   │                                │          │
                                   │                                │          └─ last element now
                                   │                                └─ role !== "assistant"
                                   └─ {role:"assistant", content:"Let me search..."}
```

`copy[copy.length - 1]` = `tool_result`
`last.role === "assistant"` = **FALSE** ← text deltas are silently dropped

**The agent continues streaming text after tool results, but the frontend cannot find the assistant placeholder because tool cards were inserted between the placeholder and the end of the array.**

### Three observed failure modes

| Mode | Trigger | Visible symptom |
|------|---------|-----------------|
| **Partial text** | Agent streams text → calls tool → streams more text | Pre-tool text renders; post-tool synthesis text is blank |
| **Empty bubble** | Agent calls tool first, then streams text | Empty white assistant bubble; text appears only on refresh |
| **Missing entirely** | Agent calls tool, gets results, ends without final text synthesis | Only tool cards visible; the answer is inside the collapsed `tool_result` |

### Why refresh fixes it

On refresh, `getChatMessages(session_id)` loads from the DB:

```sql
SELECT id, role, content, ... FROM chat_messages WHERE session_id = ? ORDER BY sequence
```

The backend persists the **complete** assistant text (manager.py `_save_message` catches the full AssistantMessage text, not just stream deltas). So after refresh, each `chat_messages` row maps 1:1 to a `UIMessage` — no interleaving issue.

---

## Backend: How the SDK actually sequences messages

### The interleaving pattern

The Claude Agent SDK sends messages in this order for a response with tool use:

```
StreamEvent("Let me look at")      ← partial delta
StreamEvent(" the case...")        ← partial delta
AssistantMessage {                 ← complete message
  TextBlock("Let me look at the case..."),      ← same text, now final
  ToolUseBlock("Bash", {command: "python3 ..."}),
}
UserMessage {                      ← tool result comes back
  ToolResultBlock(tool_use_id, "JSON output from CLI"),
}
StreamEvent("Based on ")           ← MORE deltas AFTER the tool result
StreamEvent("the evidence...")     ← agent continues writing
AssistantMessage {                 ← final version
  TextBlock("Based on the evidence, the case shows..."),
}
ResultMessage(subtype="success")   ← end of turn
```

### Backend's `streamed_text` flag

In `AgentSession.receive()` (manager.py:82-139):

```python
streamed_text = False  # reset per turn

for msg in client.receive_response():
    if StreamEvent:
        streamed_text = True
        yield {"type": "assistant", "content": delta_text}  # emit deltas

    if AssistantMessage:
        for block in content:
            if TextBlock and not streamed_text:
                yield {"type": "assistant", "content": text}  # fallback if no deltas
            if ToolUseBlock:
                yield {"type": "tool_call", ...}  # emit tool call
```

The `streamed_text` flag prevents double-emitting text (once as deltas, once as final). But it doesn't help with the **post-tool-call** text because the frontend can't route those deltas to the right message card.

---

## Root Cause Summary

The frontend assumes a **linear** message structure:
```
[user] → [assistant] → [user] → [assistant]
```

But the SDK produces an **interleaved** structure:
```
[assistant delta] → [tool_call] → [tool_result] → [assistant delta] → [done]
```

The frontend's `tool_call` and `tool_result` handlers push **new cards** to the array, which displaces the assistant placeholder from the `last` position. Subsequent `assistant` deltas have nowhere to land.

---

## Required Fix

The frontend needs to route `assistant` text to the **most recent assistant-role message** regardless of what tool cards come after it. Two approaches:

### Approach A: Find last assistant, not last element

```typescript
case "assistant":
  // Find the last assistant message, not the last element
  const lastAssistIdx = findLastIndex(copy, m => m.role === "assistant");
  if (lastAssistIdx >= 0) {
    copy[lastAssistIdx] = {
      ...copy[lastAssistIdx],
      content: copy[lastAssistIdx].content + (event.content || ""),
    };
  }
  break;
```

### Approach B: Single turn message with sub-blocks

Instead of pushing tool cards as separate array elements, attach them as sub-blocks on the current assistant message:

```typescript
interface UIMessage {
  role: "user" | "assistant" | "error";
  content: string;
  toolBlocks?: Array<{type:"tool_call"|"tool_result", ...}>;
}
```

This keeps the assistant message at `last` position, and tool calls/tool results become inline children. Text deltas always find the right parent.

**Approach A is simpler and matches the existing data model.** Approach B is a larger refactor but would allow inline tool display (like the simple-chatapp does).
