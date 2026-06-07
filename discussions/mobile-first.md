# gemini

Here is the clean transcription of your audio recording, followed by a structured prompt tailored for a coding agent to create your HTML/CSS UX/UI mockups.

### Part 1: Audio Transcription

"Okay, so right now, we have the initial UI built for Vision AI, and I am making some decisions right now about how the dashboard should function. So we have authentication set up so far, and then once you do that, you go into your cases—your case list—and then from there, you select an individual case and go into the case details dashboard. The challenge right now is how do we handle the case details dashboard or the individual case dashboard.

Now, the way that I want it to work... well, let's just talk through some of the necessities. So, the number one priority is context establishment, right? So we do that through capturing a user narrative and any relevant documents. Both the user narrative and the case files, evidence, etc., they all get ingested, go into the database, and get captured into the context of the agent, which is really just a large database that the agent can navigate as it needs to to understand information. And that's pretty much it.

I think at a minimum, we need a user narrative. Why? Because we need to know what the case is about. So we require that. Any documents are optional. [Speaking to dogs: Zuri, come here... Come here...] Yeah, so at minimum, the agent needs to know what the case is—the purpose of the case. And, you know, we might even low-key block—nah, I don't think we should block everything off based off that. But we need to establish a UI and some elements for that particular case. After that, what else is important?

Really, it's the ability to chat with an agent. It's also the ability to... hold on. All right, back to what I was saying. So yeah, there's that. There's chatting with the agent, and then there's looking at the files that are being produced. The major files are going to be like drafts and stuff; we're going to have to figure out how to format that. But I think right now we should just focus on the case loading and making sure the context is... because we pretty much already developed a system for drafting, we just have to translate it into the new system and incorporate the SDK and all of that.

Yeah, so context loading, being able to view and preview your documents for sure. I low-key think the document upload should be its own screen, just so we can monitor the progress, pagination... I don't want it to be a modal or anything like that. I mean, in the original design, that's what we had: we had the dashboard, we had the document preview, we had the agent chat, we had the explorer for the file system—but this time we're not using files, so we're going to have to defer that until we figure out what it's actually supposed to look like. [Speaking to dogs: Bentley, come here...]

Um, the exhibit thing... not too much, but the primary goal right now is getting the chat working. Um yeah, document dashboard for the cases, chat, and what else did we say? I don't remember. But the question is like, all right, so should the user narrative and document dashboard be in the same place? Should it be considered like, you know, context?

Yeah, so once we figure out the design, then we can worry about the back-end and all of that good stuff. I think that's it."

### Part 2: Prompt for the Coding Agent

**Role:** UI/UX Frontend Prototyping Specialist

**Project:** Vision AI - Case Details & Individual Case Dashboard Layout Brainstorming

**Objective:** Create high-fidelity, clean HTML mockups (using Tailwind CSS via CDN for rapid styling) to experiment with layouts, user flows, and components for an individual case view. Do not worry about backend integration or database connections right now; focus entirely on the presentation tier, visual hierarchy, and component spacing.

#### User Flow Context

1. **Authentication:** (Already handled)
2. **Case List View:** User selects a specific case.
3. **Case Details Dashboard:** The target UI to be designed.

#### Layout & UI Requirements to Mock Up:

1. **Context Establishment Panel (The Core Focus):**
   * **Mandatory User Narrative:** Include a dedicated text area input where a user must define the case details and purpose. (This is a required field before the AI agent can process the case).
   * **Layout Experiment:** Design this panel to explore whether the *User Narrative* text input and the *Document Dashboard/Metadata* feel cohesive when placed together in a single "Context Loading" zone.
2. **Dedicated Document Upload & Management Screen (NOT a Modal):**
   * Provide a view or tab representing a completely separate full-screen interface (not a popup/modal) for handling files, evidence, and legal documents.
   * Include visual placeholders for monitoring document ingestion/upload progress bars.
   * Include UI elements for pagination and handling large lists of optional case files.
   * Include a document preview pane where uploaded files/evidence can be quickly inspected.
3. **AI Agent Chat Interface (High Priority):**
   * Build a prominent panel dedicated to real-time conversation with the AI agent.
   * Design it to handle a standard chat history stream (user messages vs. agent responses) with an active text input block.
4. **Produced Files / Drafts Panel:**
   * Create a clean placeholder section to display artifacts generated by the system (e.g., system-generated legal drafts, graphs, text briefs). Ensure the layout allows for structured document previews.

#### Technical Guidelines:

* Deliver the prototype as a single-file or highly modular set of static HTML files using Tailwind CSS for clean spacing, dark/light contrast elements, and a modern dashboard feel.
* Use basic JavaScript to handle tab switching or mock navigation so we can evaluate the UX transitions between the main case dashboard, the separate document upload screen, and the chat components.

# me

All right, now something else to take into consideration. One of my um goals is for ultimately for a person to be able to like navigate the entire case on their phone. Um this includes drafting, you know, whatever. And again, we like we've already figured out how to handle drafting for the most part, which we do through a combination of JSON files and HTML renderers. Um the the complexity lies behind like how we actually uh produce the draft content. So um but yeah, so that's my primary goal like yes, I want it to be um available on desktop. That's standard, but like a person should be able to go outside and do their work while taking a walk. And so the those are the um the guiding design principles.


# gemini
