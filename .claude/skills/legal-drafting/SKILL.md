---
name: legal-drafting
description: Draft formal legal documents with structured blocks. Use when asked to draft a pleading, motion, letter, contract, memorandum, or any structured legal document.
---

# Legal Drafting — Structured Document Assembly

When the user asks you to draft a formal legal document, produce a `structured_draft` workspace item with the correct block types and metadata. The frontend renders each document type with appropriate formatting — court captions for pleadings, letterhead for correspondence, party signatures for contracts.

---

## Routing: Structured vs Freestyle

| Request | Route |
|---------|-------|
| Formal legal document (pleading, motion, letter, contract, memo) | **This skill** — `structured_draft` |
| Printable letter with custom formatting | `freestyle-html` skill |
| Narrative analysis, notes, research | `markdown` |
| Data tables, charts, checklists | `dynamic-views` skill |

---

## Document Types

The `document_type` field on `create_workspace_item` determines which renderer the frontend uses:

| document_type | Renderer | Chrome |
|---------------|----------|--------|
| `pleading` | PleadingRenderer | Court caption (plaintiff/defendant, case number, court), "Respectfully submitted" signature |
| `letter` | LetterRenderer | Date, recipient address, salutation, subject line, sign-off, signature |
| `contract` | ContractRenderer | Party names, effective date, dual signature block |
| `memo` | MemoRenderer | TO/FROM/DATE/RE header |
| `other` | LetterRenderer (fallback) | Basic letter format |

---

## Block Types (8)

Each block is `{"id": string, "type": BlockType, "content": string}`. Content supports basic HTML: `<strong>`, `<em>`, `<u>`, `<br>`.

| Block Type | Numbered? | Content | Rendering |
|------------|-----------|---------|-----------|
| `section_heading` | No | HTML | Bold, uppercase, centered, underlined |
| `numbered_paragraph` | **Yes** (computed) | HTML | Auto-numbered 1., 2., 3. |
| `unnumbered_paragraph` | No | HTML | Plain justified paragraph |
| `block_quote` | No | HTML | Indented, italic, left border |
| `list_item` | No | HTML | (a), (b), (c) or (i), (ii) or • — set `list_style` field |
| `signature_row` | No | Plain text | Signature line + printed name |
| `section_divider` | No | Empty | Horizontal rule |
| `raw_html` | No | Raw HTML | Pass-through — use for tables |

**List styles:** Add `"list_style": "letter"` (default), `"roman"`, or `"bullet"` to list_item blocks.

**Signature rows:** Add `"printed_name": "John Doe, Esq."` for the printed name below the signature line.

---

## Metadata

Store document-type-specific metadata in the `metadata` JSONB field when creating the workspace item:

### Pleading metadata
```json
{
  "caption": {
    "court_name": "Superior Court of California, County of Los Angeles",
    "plaintiff": "Jane Smith",
    "defendant": "Acme Corporation",
    "case_number": "2026-CV-00123",
    "document_title": "Motion for Summary Judgment"
  },
  "signature": {
    "attorney_name": "Sarah J. Martinez, Esq.",
    "bar_number": "123456",
    "firm_name": "Justice Quest Legal Group"
  }
}
```

### Letter metadata
```json
{
  "date": "June 17, 2026",
  "recipient_name": "Mr. John A. Smith",
  "recipient_address": "123 Oak Avenue\nSpringfield, ST 62704",
  "salutation": "Dear Mr. Smith:",
  "subject_line": "Representation in Smith v. Acme Corp.",
  "sign_off": "Sincerely,",
  "sender_name": "Sarah J. Martinez, Esq.",
  "sender_title": "Partner, Justice Quest Legal Group"
}
```

### Contract metadata
```json
{
  "party_a_name": "Vision Technologies, Inc.",
  "party_b_name": "Acme Corporation",
  "effective_date": "June 17, 2026",
  "document_title": "Professional Services Agreement"
}
```

### Memo metadata
```json
{
  "to": "All Attorneys",
  "from": "Sarah Martinez, Managing Partner",
  "date": "June 17, 2026",
  "re": "New Case Management Procedures"
}
```

---

## How to Create a Draft

Use `create_workspace_item`:

```
create_workspace_item(
  name="Motion for Summary Judgment",
  file_type="structured_draft",
  document_type="pleading",
  folder="artifacts",
  workspace_id=<active_workspace_id>,
  content=[
    {"id":"h1","type":"section_heading","content":"<strong>PRELIMINARY STATEMENT</strong>"},
    {"id":"p1","type":"numbered_paragraph","content":"This motion seeks summary judgment on the grounds that..."},
    {"id":"h2","type":"section_heading","content":"<strong>STATEMENT OF FACTS</strong>"},
    {"id":"p2","type":"numbered_paragraph","content":"Plaintiff Jane Smith entered into a contract with Defendant..."},
    {"id":"h3","type":"section_heading","content":"<strong>ARGUMENT</strong>"},
    {"id":"h4","type":"section_heading","content":"<strong>I. The Court Lacks Subject Matter Jurisdiction</strong>"},
    {"id":"p3","type":"numbered_paragraph","content":"Under Federal Rule of Civil Procedure 12(b)(1)..."},
    {"id":"p4","type":"numbered_paragraph","content":"In the instant case, Plaintiff has failed to allege..."},
    {"id":"div1","type":"section_divider","content":""},
    {"id":"h5","type":"section_heading","content":"<strong>CONCLUSION</strong>"},
    {"id":"p5","type":"numbered_paragraph","content":"For the foregoing reasons, Defendant respectfully requests..."},
    {"id":"sig1","type":"signature_row","content":"Sarah J. Martinez, Esq.","printed_name":"Sarah J. Martinez, Esq."}
  ],
  metadata={...caption and signature as shown above...}
)
```

**To update** an existing draft: use `get_workspace_item` to read it, modify the blocks array, then `update_workspace_item`.

---

## Block ID Conventions

Use descriptive, stable IDs: `h1`, `h2` for headings; `p1`, `p2` for paragraphs; `sig1` for signatures. Do NOT use random UUIDs — the user and agent both reference these IDs.

---

## Rules

1. **Never put paragraph numbers in content.** Numbering is computed at render time. `"content": "1. The Court lacks..."` is wrong. Let the renderer add the "1.".
2. **Content is HTML, not markdown.** Use `<strong>`, `<em>`, `<u>`, `<br>`. No `#`, `**`, `*`.
3. **Never invent block types.** Only the 8 defined types.
4. **Never invent facts or citations.** Ground every factual assertion in source documents. Cite block text verbatim.
5. **Always populate metadata.** The renderer needs caption/header/address fields to produce proper formatting.
6. **Section headings in ALL CAPS with `<strong>`.** Legal convention for formal documents.

---

## Document Structure Pattern

### Pleading (motion, complaint, opposition, reply)
```
section_heading: PRELIMINARY STATEMENT (or INTRODUCTION)
numbered_paragraph: [one paragraph stating what this document is and why]
section_heading: STATEMENT OF FACTS (or BACKGROUND)
numbered_paragraph: [fact paragraphs — one per key fact]
section_heading: ARGUMENT
section_heading: I. [First Argument Title]
numbered_paragraph: [argument paragraphs]
section_heading: II. [Second Argument Title]
numbered_paragraph: [argument paragraphs]
section_divider
section_heading: CONCLUSION
numbered_paragraph: [conclusion + prayer for relief]
signature_row: [attorney signature]
```

### Letter
```
numbered_paragraph: [opening — purpose of the letter]
numbered_paragraph: [body paragraphs]
unnumbered_paragraph: [closing remarks]
signature_row: [sender signature]
```

### Contract
```
section_heading: RECITALS
unnumbered_paragraph: WHEREAS, ...
section_heading: AGREEMENT
section_heading: 1. Definitions
numbered_paragraph: [definition]
section_heading: 2. [Article Title]
numbered_paragraph: [clause]
signature_row (×2 for both parties)
```

### Memo
```
section_heading: INTRODUCTION
numbered_paragraph: [purpose]
section_heading: DISCUSSION
numbered_paragraph: [analysis]
section_heading: RECOMMENDATION
numbered_paragraph: [recommended action]
```
