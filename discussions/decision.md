
Here is the verbatim transcript of the audio provided, organized logically with formatting for maximum clarity and scannability.

## **Introduction and the Purpose of "Vision"**

All right, so one of the biggest um blockers for me getting organized is um just not having the tools and technology. Technology helps everything helps you in wars do everything right and I need technology. I have vision. Um... its capabilities so I originally built something called the war room turned into command AI once I realized like how many functions I could get it to orchestrate. Now it's vision.

The purpose of vision is basically... The purpose of vision is to allow a user and an agent alike to have maximum visibility into any sort of matter that they have, be it legal, be it administrative. I mean this whole world is about administration. So you should be able to upload any sort of document, any number of documents, any type of document. Um... or you should be able to, you should have some, you know, any sort of task that you have to complete that requires you to organize information or distribute information or store information. Vision should be able to help you do that.

## **Core Components and Interfaces**

Now, let's talk about the core components of the application. We have the chat, of course, that's our interface into the application.

* **Current Chat Issues:** The problem with chat right now though is that like the floating chat, it has odd behavior. Like sometimes I can't see the final message.
* **Tool Call Inflation:** Also, I get the um the chat body gets inflated with like the um with like the the tool call the tool calls. So it'll actually show the MCP server that's being called and like that's unnecessary. We don't need the user doesn't need to see what tools the agent is calling on the back end. The user just needs to see that the agent has a response. Um... But anyways.

### **Document and File Ingestion**

* **Maximum Visibility:** So yeah, the purpose is to have maximum visibility and organization with any sort of matter. The way that we accomplish that is through document and file ingestion.
* **The Entry Point:** So that like that's the entry point as well as the case narrative, right. Um... So there's a case name, there's like a narrative or description that a user gives and yeah there are the documents.

## **Establishing Agent SOPs**

And so we need to figure out the SOPs for the agent. We need to figure out how to structure the um the agent behavior. Basically, how do we put together the instruction file?

* **Case Orientation:** So like first, we need we need an SOP for how the how the agent gets oriented. So the instruction file should start with the purpose, then we need we need an SOP for case orientation, right. Um... what else?
* **Organization:** We need an SOP for um like organization. So like we have tasks, correspondences... So basically those are just tool calls.
* **Correspondence and Task Management:** If a if a user mentions that they corresponded, the agent will look through the threads and see where that correspondence belongs. If it determines that, you know, no thread exists, it will start a new thread in a correspondence. Same thing to the tasks. Like it should have it should be able to look at tasks and see, you know, where does this information go and then make a tool call to create a task.

## **Agent Skills and Knowledge Base**

* **Tool Definitions:** We should make the agent aware of its various tools. I think right, so that would be the equivalent of definitions. Like here are your tools, tool definitions, here is what they are used for. And if we can maybe group some tools and just make an inference of what exists so that, you know, so that we're not clouding the instruction file that would be good too.
* **Agent SDK Integration:** We also need to make the agent aware of its skills that it has. Um... This is agent SDK though, so it works differently from Claude. So we'll have to basically like start from the beginning and figure out how that's supposed to work.
* **Database and Preloaded Knowledge:** I also think we should let's say the user asks a question about the application. Um... there should be a knowledge base document that the agent has access to. Right. Like how do we store that? Is it like a I guess it it we should include it as like a preloaded um like a preloaded database table? Something should be preloaded, right. So certain bodies of law we might have in there, uh we're for sure going to have the FAR Federal Acquisition Regulation. We're for sure going to have um a basic knowledge base about the application. Uh... That's internal though. Uh... All right. So with all that said, what's next?

### **Document Interaction Constraints**

Documents, I mean this is pretty much straightforward, right. This is just for like ingestion. It's not really an agent it's not meant for agent interaction. But the agent should probably know like why it has these tools, you know, why it has tools to look up documents. We should probably have some internal like note that says, you know, we ingest every sort of file, OCR if possible um, you know, and make it available for for you.

## **The Workspace and Workflow Context**

Um... So the so finally, right, after all of that, we have um the workspace. And that's probably the biggest piece of information um that we need to make apparent to um the agent.

* **The Second Communication Layer:** Like the workspace is here for basically the you know, the how do I say it? Like yeah, the workspace is... it's your second communication layer. This is where we draft documents, whether it be Markdown for certain artifacts um, whether it be letters we're trying to compile to respond to someone, um whether it be, you know, a certain type of view, whether that be a chart or a table or a set of cards.
* **System Prompt Adjustments:** Um... Vision needs to know that this is a weapon at its disposal. What it's for, so that it can inform the user. I think right now our our system prompt is very generic.

### **Agent Journal and Logging**

* **Tracking Progress:** And um, you know, we also need a way to keep track of where we are. You know, what like what might be an active matter. So sort of like a an agent journal.
* **Milestone Recording:** Now this is not exposed to the user, but this would be what we could use um so as the agent is working through things uh maybe it realizes we've hit an important milestone and so it gives you know, it logs um an entry in the journal. So that way we have, you know, a visible timeline of the things that we've worked on and maybe context into why we worked on it.

### **Tool Discovery and Situational SOPs**

* **Situational Awareness:** Like we have a bunch of the right tools. The only issue is like the agent doesn't know well it knows what tools it has available but it's not clear, you know what I mean. It's it's like discovering things in real time instead of understanding like this is what we have, these are the different scenarios we might run into um which reminds me, while we're in the workspace. So...
* **Specific Document Tasks:** You know, we we have different situations, right. So we might have for example just a basic research task or a basic organization where we're producing artifacts. But we also might have like a letter that we need to write, or we might have a legal draft that we need to put together um, or we might be doing an analysis.
* **Formatting Constraints:** So we need SOPs for all of that stuff. You know, if you're just producing an an a markdown artifact, like how do you put that into the system? If you're producing a letter, how do you format it and or what are the constraints of your ability to format? And then how do you also format it so that it prints properly when it's time to print? Right? Make sure that we have 1 inch margins. um...
