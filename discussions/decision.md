Role & Objective
You are an expert full-stack software engineer and system architect. We are building a "Dynamic View System" (a context-aware visibility app) that acts like an AI-native version of Notion. The system ingests unstructured files (bank statements, legal case documents, credit reports), extracts the data into structured JSON, and dynamically renders the data into pre-built frontend components based on the context of the data.

Do not generate raw, unstyled HTML strings from the LLM. Instead, enforce a strict "Headless UI" design pattern where the AI controls the DATA and the METADATA, and the frontend handles the VISUAL PRESENTATION.

---

### System Architecture & Data Flow

1. Database Layer:
   - A Hybrid Model. Chunks/embeddings are stored in a Vector DB for semantic RAG search.
   - Clean, extracted document data is stored as a structured JSON payload in a relational/document database (e.g., PostgreSQL `JSONB` or MongoDB).
2. Backend LLM Layer:
   - Analyzes the document type or user request and returns a strict JSON payload containing a "Metadata Envelope" (`viewType`) and a structured `data` payload.
3. Frontend Layer:
   - Uses a conditional rendering engine. It reads the `viewType` envelope and dynamically maps the data payload into a corresponding, pre-designed component (e.g., `<DynamicTable />`, `<DynamicList />`, `<LetterTemplate />`).

---

### Strict JSON Response Schema

Every UI generation response from the AI must conform to this exact wrapper schema:

{
  "viewType": "string", // Options: "table" | "list" | "letter" | "spreadsheet"
  "documentMetadata": {
    "title": "string",
    "sourceId": "string",
    "lastUpdated": "string"
  },
  "data": {} // Shape dynamically shifts based on viewType
}

---

### Explicit Context & Schema Examples

#### Example 1: Financial Statements / Credit Reports (viewType: "table")

When rendering tabular data, the `data` object must provide an array of `headers` and an array of `rows` consisting of key-value objects. This ensures the frontend table component can dynamically map columns.

{
  "viewType": "table",
  "documentMetadata": {
    "title": "Negative Credit Accounts Summary",
    "sourceId": "doc_credit_001",
    "lastUpdated": "2026-06-16"
  },
  "data": {
    "headers": ["Account Name", "Balance", "Status", "DisputeStatus"],
    "rows": [
      { "id": "1", "Account Name": "Chase Bank", "Balance": "$4,230", "Status": "Delinquent", "DisputeStatus": "Unresolved" },
      { "id": "2", "Account Name": "Wells Fargo", "Balance": "$1,150", "Status": "Charge-Off", "DisputeStatus": "In-Progress" }
    ]
  }
}

#### Example 2: Corporate/Legal Letters (viewType: "letter")

To render an 8.5x11 printable letter, the LLM provides content variables. The frontend will map these into a fixed-width CSS print container with standardized margins, a professional letterhead layout, and signature lines.

{
  "viewType": "letter",
  "documentMetadata": {
    "title": "Notice of Credit Dispute Letter",
    "sourceId": "doc_letter_882",
    "lastUpdated": "2026-06-16"
  },
  "data": {
    "sender": { "name": "John Doe Enterprises", "address": "123 Main St, Atlanta, GA" },
    "recipient": { "name": "Equifax Dispute Dept", "address": "P.O. Box 740256, Atlanta, GA" },
    "date": "June 16, 2026",
    "subject": "Formal Dispute of Inaccurate Account Information",
    "salutation": "To Whom It May Concern,",
    "paragraphs": [
      "I am writing to formally dispute the inaccurate reporting of the Chase Bank account listed on my credit file...",
      "Under the Fair Credit Reporting Act, I request an immediate investigation and removal of this inaccurate balance."
    ],
    "closing": "Sincerely,",
    "signatureName": "John Doe, CEO"
  }
}

#### Example 3: Compliance Tasks / Checklists (viewType: "list")

For standard operational checklists or chronological logs.

{
  "viewType": "list",
  "documentMetadata": {
    "title": "Post-Award Onboarding Steps",
    "sourceId": "sop_mpt_01",
    "lastUpdated": "2026-06-16"
  },
  "data": {
    "listStyle": "checkbox", // Options: "checkbox" | "ordered" | "bullet"
    "items": [
      { "id": "t1", "text": "Verify Government Purchase Card (GPC) authorization limit", "completed": true },
      { "id": "t2", "text": "Execute sub-tier commercial execution agreement with vendor", "completed": false },
      { "id": "t3", "text": "Submit closeout log to Contracting Officer via WAWF", "completed": false }
    ]
  }
}

---

### The Interactive Editing Loop Requirements

We need to be able to modify this data directly on-screen. Program the following logic:

1. Inline Editing: When a user clicks on a cell in a `<Table />` or a paragraph in a `<LetterTemplate />`, switch that element into an active HTML input/textarea state bound to the frontend's local state.
2. State Syncing: As the user edits, update the active local JSON payload in memory.
3. Database Persist: When the user clicks a "Save Changes" button:
   - Fire a `PUT/PATCH` API call passing the newly modified JSON data back to the database.
   - Overwrite the existing JSON document record.
   - Trigger a background worker script that re-chunks the modified fields and re-indexes them into the Vector DB so the RAG search stays perfectly synced with user edits.

Please generate the foundational database schema, backend router logic, and the frontend dynamic conditional renderer component to implement this architecture.
