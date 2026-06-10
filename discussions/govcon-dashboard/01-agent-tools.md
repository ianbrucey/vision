# Agent Tools for Tasks & Correspondence

**Status:** Straightforward

## What it is

The chat agent currently has tools for Read, Grep, Write, Edit, WebSearch, WebFetch,
and MCP vision tools. It cannot create, update, or delete tasks or correspondence
items. We need to add tool handlers so the agent can manipulate these entities
during a conversation.

## Existing infrastructure

Both entity types already have full CRUD API endpoints and frontend UIs:

**Tasks API** (`backend/api/main.py` or a routes file):
- `GET /api/cases/{case_id}/tasks` — list
- `POST /api/cases/{case_id}/tasks` — create
- `PATCH /api/tasks/{task_id}` — update
- `DELETE /api/tasks/{task_id}` — delete
- `POST /api/tasks/{task_id}/documents` — attach documents
- `DELETE /api/tasks/{task_id}/documents/{doc_id}` — detach

**Correspondence API** (`backend/api/routes/correspondence.py`):
- Full CRUD for threads, items, and attachments

## What needs to be built

### 1. Add task tools to the agent

In `backend/chat/tools.py` (the `create_vision_server` function), add MCP tool
definitions for:

```
create_task(case_id, title, notes?, assignee_id?, deadline?, priority?, document_ids?)
update_task(task_id, title?, notes?, status?, priority?, assignee_id?, deadline?)
list_tasks(case_id, status?, assignee_id?)
delete_task(task_id)
attach_task_documents(task_id, document_ids)
```

Each tool handler:
- Receives `case_id` from the closure (already captured in existing tools)
- Calls the corresponding function from `core/case.py` or inline SQL
- Returns the result as a string/JSON

### 2. Add correspondence tools to the agent

```
create_correspondence_thread(title)
list_correspondence_threads(status?)
create_correspondence_item(thread_id, sender_party_id?, receiver_party_id?, direction, notes?, date_sent?, date_received?, document_ids?)
update_correspondence_item(item_id, ...)
list_correspondence_items(thread_id)
delete_correspondence_item(item_id)
```

### 3. Register tools

Add `mcp__vision__create_task`, etc. to the `allowed_tools` list in
`backend/chat/manager.py` AgentSession configuration.

## Files to modify

- `backend/chat/tools.py` — add tool definitions + handlers (~150 lines)
- `backend/chat/manager.py` — add new tools to `allowed_tools` list (~10 lines)

## Verification

1. Start a chat session on a case that has parties and documents
2. Ask the agent: "Create a task called 'Review discovery documents' with high priority"
3. Verify the task appears in the Tasks tab
4. Ask: "List all open tasks for this case"
5. Verify the agent returns the correct list
6. Repeat for correspondence: "Log a sent correspondence to Plaintiff Counsel..."

## Estimated effort

~1-2 hours. Pure wiring — no new backend logic, just exposing existing functions
as MCP tool handlers.
