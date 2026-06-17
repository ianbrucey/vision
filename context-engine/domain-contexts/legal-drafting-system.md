# Legal Drafting System — Architecture & Port Guide

> **Purpose:** Complete reference for the legal drafting rendering system. Use this to understand how structured_draft blocks become court-formatted documents, and to port the war-room-1 drafting pipeline to Vision.
> **Last Updated:** 2026-06-17
> **Related:** `.claude/skills/legal-drafting/SKILL.md`

---

## 1. Data Model — DRAFT.json

Legal drafts are stored as `structured_draft` workspace items in the `drafts` table. The `content` column is a JSONB block array. Document-type-specific metadata goes in the `metadata` JSONB column.

### Block Types (mirrors war-room-1)

```typescript
type Block = {
  id: string;
  type: "section_heading" | "numbered_paragraph" | "unnumbered_paragraph"
      | "block_quote" | "list_item" | "signature_row"
      | "section_divider" | "raw_html";
  content: string;       // HTML — supports <strong>, <em>, <u>, <br>
  list_style?: "letter" | "roman" | "bullet";  // list_item only
  printed_name?: string;  // signature_row only
}
```

### Metadata by Document Type

**Pleading** (`document_type: "pleading"`):
```json
{
  "caption": {
    "court_name": "IN THE SUPERIOR COURT OF FULTON COUNTY\nSTATE OF GEORGIA",
    "plaintiff": "JANE ROBINSON,\n\n  Plaintiff,",
    "defendant": "ACME CORPORATION, and\nJOHN DOE,\n\n  Defendants.",
    "case_number": "Case No. 2026-CV-00192",
    "document_title": "MOTION FOR SUMMARY JUDGMENT"
  },
  "signature": {
    "attorney_name": "Ian Bruce",
    "bar_number": "GA Bar No. 123456",
    "firm_name": "Bruce Law Group LLC"
  }
}
```

The caption format uses manual line breaks (`\n`) for multi-line party names. The renderer preserves these as `<br>`.

**Letter** (`document_type: "letter"`):
```json
{
  "date": "June 17, 2026",
  "recipient_name": "Mr. John A. Smith",
  "recipient_address": "123 Oak Avenue\nSpringfield, ST 62704",
  "salutation": "Dear Mr. Smith:",
  "subject_line": "Representation in Smith v. Acme Corp.",
  "sign_off": "Sincerely,",
  "sender_name": "Sarah J. Martinez, Esq.",
  "sender_title": "Partner"
}
```

**Contract** (`document_type: "contract"`):
```json
{
  "party_a_name": "Vision Technologies, Inc.",
  "party_b_name": "Acme Corporation",
  "effective_date": "June 17, 2026",
  "document_title": "Professional Services Agreement"
}
```

**Memo** (`document_type: "memo"`):
```json
{
  "to": "All Attorneys",
  "from": "Sarah Martinez",
  "date": "June 17, 2026",
  "re": "New Case Management Procedures"
}
```

---

## 2. CSS — BASE_DRAFT_STYLES

The rendering uses a single CSS block ported from war-room-1's `generateHtml.ts`. These styles apply to BOTH screen and print — the same CSS is used for the React component rendering and the print blob window.

**Key formatting rules (non-negotiable):**
- Font: Times New Roman, 14pt (pleadings), 12pt (letters)
- Line height: 2.0 (double-spaced for pleadings), 1.7 (letters)
- Document container: max-width 8.5in, 1in padding, white background, border + shadow
- Court caption: centered bold text, then a 2-column table (plaintiff left 50%, case info right 50% with left border)
- Section headers: centered, bold, underlined — NO borders above or below
- Paragraph numbers: bold, computed at render time, NOT stored in content
- Signature: border-top line (not border-bottom), max-width 300px
- Block quotes: left 3px border, italic, indented
- Section dividers: 1px #eee, no visible border

**The CSS file:** `frontend/src/components/drafting/draftStyles.css`

---

## 3. Component Architecture

```
DraftPreview.tsx (dispatcher — reads document_type)
├── draftStyles.css (shared CSS — imported once)
├── PleadingRenderer.tsx   — court caption + motion title + body + signature
├── LetterRenderer.tsx     — date/recipient/salutation + body + sign-off
├── ContractRenderer.tsx   — party names + body + dual signature
├── MemoRenderer.tsx       — TO/FROM/DATE/RE header + body
└── UniversalBodyRenderer.tsx — block→DOM engine (shared by all renderers)
```

Each renderer:
1. Renders its document-specific chrome (caption, letterhead, etc.)
2. Passes body blocks to UniversalBodyRenderer
3. Uses the shared CSS classes from draftStyles.css
4. Supports inline editing via onClick → textarea

### Rendering Rules

**Screen:** React components render with CSS class names matching the stylesheet. The document container uses `.document` class with white background + shadow.

**Print:** When the user clicks Print, the renderer captures the document's innerHTML (via `.document` selector), wraps it in a complete HTML page with the same CSS, opens a blob window, and calls `window.print()`. The printed output is IDENTICAL to screen.

---

## 4. Key Differences from Tailwind Approach

| Aspect | Wrong (Tailwind) | Correct (Legal CSS) |
|--------|-----------------|---------------------|
| Font | System font | Times New Roman 14pt |
| Line spacing | Normal | Double-spaced (2.0) |
| Section headers | Border-bottom | Underlined, no borders |
| Caption | Plain text | 2-column table with left border |
| Paragraph numbers | Inline span | Bold, computed, `.para-num` class |
| Signature line | border-bottom | `border-top` on `.signature-line` |
| Document width | Tailwind max-w | `8.5in` with `1in` padding |
| Print output | Different from screen | Identical CSS in blob window |

---

## 5. Data Flow

```
Agent: create_workspace_item(
  file_type="structured_draft",
  document_type="pleading",
  content=[{id, type, content}, ...],
  metadata={caption: {...}, signature: {...}}
)
  ↓
WorkspaceTab: activeItem = get_workspace_item(id)
  ↓
DraftPreview:
  - reads activeItem.document_type → dispatches renderer
  - reads activeItem.metadata → passes caption/signature/header
  - reads activeItem.content → extracts Block[] array
  ↓
Renderer (e.g., PleadingRenderer):
  - Renders caption from metadata.caption
  - Renders body via UniversalBodyRenderer
  - Renders signature from metadata.signature
  ↓
User clicks block → inline textarea → Save → updateWorkspaceBlock
User clicks Print → capture innerHTML → blob window with CSS → print
```

---

## 6. Files Reference

| File | Purpose |
|------|---------|
| `frontend/src/components/DraftPreview.tsx` | Dispatcher — reads document_type, renders correct component |
| `frontend/src/components/drafting/draftStyles.css` | Complete legal CSS (ported from war-room-1 generateHtml.ts) |
| `frontend/src/components/drafting/UniversalBodyRenderer.tsx` | Block→DOM engine with live numbering |
| `frontend/src/components/drafting/PleadingRenderer.tsx` | Court caption + motion title + signature |
| `frontend/src/components/drafting/LetterRenderer.tsx` | Date/recipient/salutation/sign-off |
| `frontend/src/components/drafting/ContractRenderer.tsx` | Party names + dual signature |
| `frontend/src/components/drafting/MemoRenderer.tsx` | TO/FROM/DATE/RE header |
| `frontend/src/components/drafting/printUtils.ts` | Blob-window print with same CSS |
| `frontend/src/lib/api.ts` | Block type, document_type field |
| `.claude/skills/legal-drafting/SKILL.md` | Agent instructions for producing drafts |
| `backend/chat/prompt.py` | System prompt dispatch table |

---

## 7. Verification Checklist

- [ ] Pleading renders with court caption (plaintiff left, case number right, border between)
- [ ] Section headers are centered, bold, underlined — no visible border lines
- [ ] Paragraphs are double-spaced with computed numbers
- [ ] Signature has border-top line, max-width 300px
- [ ] Block quote has left 3px border, italic
- [ ] Click any block → inline textarea → save persists
- [ ] Hover between blocks → + Insert button appears
- [ ] Print output looks identical to screen (same CSS)
- [ ] Letter, contract, memo render with correct chrome
