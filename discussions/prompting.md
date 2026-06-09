All right, excellent. That gave me, um, an idea of of what direction I need to go.

So here's the next challenge. Um...

Yeah, here's the next challenge.

All right, yeah, that's right. So I'm trying to figure out... I'm I'm using the SDK, the agent SDK from from Anthropic. And previously I was using stuff like, uh, the, um, Claude Code and, uh, Augie CLI to basically manage a folder and and file-based framework, um, which works excellent, um, you know, as I need to like traverse through my documents and put put things together, but it's not, um... it's not like scalable really. I mean it is scalable if if I'm passing out single-tenant applications, um, because I'm running, you know... um... you know, basically CLI-based agents.

Um, but in this case since I'm running SDK-based agents and, um, that allows me to use utilize the API and be a little bit more, um, extendable. Although, uh, security is going to be a security yeah, security is going to be a challenge. That's something I'm going to have to think about. And I actually, uh, security like figuring out the security aspects and making sure I don't get, um, become a victim of prompt injection, let's make sure, uh, we sort of figure that out.

Um, and I'm I'm thinking to myself while we're on the subject of security, what I may have to do is, um, lock down any tools or search, uh... Zuri, come here. Yeah, what I may have to do is lock down any tools or search based on the user ID or the session ID that we're in. Um...

And that's how, that's how that'll work.

So where were we? Security... um... What what were we talking about? Oh yeah, yeah, yeah. Uh, so how to set up the, uh, the prompts and stuff.

So here's here's how we worked before. Basically, an agent was spawned within a folder that we set up. We would use like an instructions file like `agents.md` or `claud.md`. We would have all our, um... you know, it would give the agent its personality, tell it like how to operate and all of that good stuff. Um, you know, "here are your instructions, here here's where you go, here like if you encounter this situation, run this protocol, you have these skills available, these tools, etc.", right? Um...

And I'm trying to figure out the best way to set that up in in this instance. Um, before everything was file-based, now we have, you know, database. So immediately what I'm thinking is like same thing where we give it we give the agent its its personality, but now it's like we tell it, "okay, you have, uh..." you have access to this database and these tools or whatever, um, to access the database. I'm wondering if we should put the protocols, um, or we should make the skill list available, um, in the database.

I'm just I'm just wondering like what's the what's the, um, most scalable way or the most efficient way to make the agent available of all of its protocols, because the protocols can be pretty extensive, like with, for example, um, like running a strategy protocol on a motion to dismiss, for example. Um, you know, you're going to have to lay out all the doctrines, there might be multiple times where you might have to go out and go get case law, um, we have these like, uh, adversarial analysis loops. Um, you know what I mean? And so then we have sub-agents and, yeah, so I'm not really sure the best way to handle that.

How to structure it. Because, you know, let's say we this let's say this platform becomes very large, right? We got a bunch of extended features, um, there's only so much context we can put in that instructions file. You know, if we got 50 protocols, I can't put all 50 pro- protocols in that instructions file. Or, even if I do that, it's like, I mean, even if I don't put it in the instructions file and I make it like an external knowledge, it's like how do we construct, um, the instructions to the agent such that, um, you know, we we basically... just, all right, put it like this: just like if you were opening a book, a law book or something and you needed to, um, figure out what something is, like, you know, you have your table of contents and, you know, sections and blah blah blah blah blah. And that kind of helps you to narrow down what you're trying to do or the direction you're trying to, uh, or the your destination, I mean.

So this is essentially what I have to do for the agent, um, instructions and its available skills and tools and protocols. Um, and I'm not sure how to frame it, because I'm going to have to bring this to my coding agent and have it figure out like what we need to do. Um...


# gemini



The analogy of a **Table of Contents (TOC)** is exactly the industry-standard pattern for solving this problem. In enterprise AI architecture, this is known as the **Supervisor-Worker (Hierarchical) Pattern** or  **Dynamic Prompt Assembly** .

When moving from a single-user CLI (like Claude Code) to a multi-tenant SDK-based architecture, you cannot cram 50 legal or tax protocols into one system prompt. It degrades model performance, causes context drift, costs too much, and invites prompt injection.

Here is the architectural blueprint to solve both your **security isolation** and **protocol bloat** challenges, structured so you can hand it directly to your coding agent.

### Part 1: Solving Multi-Tenant Security (Implicit Scoping)

To prevent prompt injection where an adversarial prompt tells the agent to *"Search across all system databases instead of my own,"* you must implement  **Implicit Tool Scoping** .

* **The Rule:** The LLM should **never** be responsible for passing the `user_id` or `session_id` to a tool.
* **The Implementation:** Your backend infrastructure must wrap or intercept all tool calls. When the agent invokes `search_documents(query="motion to dismiss")`, your backend application layer automatically injects the active session's `user_id` before hitting the database.

**Python**

```
# Backend application code (Not visible to the LLM prompt)
def execute_tool_safely(session_context, tool_call):
    if tool_call.name == "search_documents":
        # Force the user_id from the verified JWT/session, ignoring any LLM inputs
        return db.vector_search(
            user_id=session_context.user_id, 
            query=tool_call.args["query"]
        )
```

By binding tool permissions to the runtime context rather than the LLM's instructions, you entirely eliminate cross-tenant data leaks via prompt injection.

### Part 2: Solving Protocol Bloat (The "Table of Contents" Patterns)

To handle 50+ complex protocols (like running an adversarial analysis loop or fetching case law), you have two scalable design options using the Anthropic SDK.

#### Pattern A: The Hierarchical Agent / Router Pattern (Recommended)

Instead of one massive agent, build a tree structure.

1. **The Supervisor (The Table of Contents):** This is a lightweight, fast coordinator agent. Its *only* job is to look at the user's request, look at a high-level registry of available specialized sub-agents, and delegate the task.
2. **Specialized Worker Agents:** These are independent agent instances spawned on demand. For example, a `LitigationProtocolAgent` is only spun up if the supervisor detects a legal motion requirement. It *only* loads the instructions and tools relevant to running a motion-to-dismiss strategy.

**Why this scales:** The context window for each agent remains incredibly small, clean, and highly optimized for its specific task.

#### Pattern B: Just-In-Time (JIT) Dynamic Prompt Assembly

If you prefer to keep a single agent actor, you must build an external **Protocol Registry** (stored in a standard database or JSON config) and fetch instructions dynamically.

1. **Step 1:** The user sends a message: *"I need to draft a response to this motion to dismiss."*
2. **Step 2:** Your backend runs a fast, cheap semantic search or keyword match against your Protocol Registry to find matches for "motion to dismiss".
3. **Step 3:** The backend pulls the exact 2-3 Markdown instruction files needed for that protocol and injects them into the Anthropic API call under the `system` parameter  *for that turn only* .

### Part 3: The Blueprint for Your Coding Agent

Copy and paste the framework specification below into your coding agent to have it build out the architecture using the Anthropic SDK.

**Markdown**

```
# Architecture Specification: Scalable Multi-Agent Protocol Router

## Goal
Implement a hierarchical multi-agent system using the Anthropic SDK to handle diverse, complex workflows (Legal, Tax, RFPs) without context bloat or prompt cross-contamination.

## Component 1: Protocol Registry Schema
Create a centralized database or registry config to catalog skills dynamically.
{
  "protocol_id": "legal_motion_adversarial_loop",
  "name": "Adversarial Motion Analysis",
  "trigger_keywords": ["motion to dismiss", "summary judgment", "opposition"],
  "system_instructions_path": "/protocols/legal/motion_dismiss.md",
  "allowed_tools": ["fetch_case_law", "analyze_argument"]
}

## Component 2: The Supervisor Agent (TOC Router)
- Initialize a lightweight Anthropic client session.
- System prompt: "You are the Vision AI Director. Your sole job is to assess the user's matter and call the `delegate_to_specialist` tool with the correct protocol ID. Do not answer the core problem yourself."

## Component 3: Session-Wrapped Tool Executor
- Design a tool execution wrapper that intercepts all sub-agent tool emissions.
- Every data access tool (Vector Search, File Reads) must explicitly map to a hardcoded `tenant_id` and `session_id` passed from the application state, preventing prompt injection from jumping user boundaries.

## Component 4: Worker Lifecycle Manager
- When `delegate_to_specialist` is invoked, dynamically construct a new Anthropic agent session.
- Pull the markdown instructions from the Protocol Registry matching the ID.
- Provide only the restricted tools allowed for that specific protocol.
- Stream the response back to the main UI conversation block.
```

### Next Step

Tell your coding agent: *"Review this architecture blueprint. Let's start by coding Component 1 and Component 2 using the Anthropic SDK, setting up a mock registry with 2 distinct protocols (e.g., one Tax protocol and one Legal protocol) to prove the routing logic works."*
