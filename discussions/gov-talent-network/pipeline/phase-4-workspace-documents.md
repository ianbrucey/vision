# Phase 4 — Documents in Workspace

> Pipeline artifact · 2026-08-07 · Status: SPEC

---

## 1. Goal

Uploaded documents (PDFs, DOCX) appear in the Workspace file explorer so they can be viewed alongside drafts and notes. This is the first step toward filling out proposal forms within the workspace.

**Out of scope for this phase:** Form filling, drag-and-drop, AI auto-fill, editing documents.

---

## 2. What Changes

### 2.1 Sidebar structure

```
┌─────────────────────────┐
│ 📎 Uploaded Documents ▷ │  ← NEW: collapsible, default COLLAPSED, at TOP
│                         │
│ 🏠 Workspace ▼         │  ← Existing: workspace selector
│ 📁 Artifacts      ▶    │
│ 📁 Drafts         ▼    │
│   📝 Proposal v2.md    │
└─────────────────────────┘
```

When expanded:
```
│ 📎 Uploaded Documents ▼ │
│   📄 SF-1449.pdf       │  ← Clicking opens as read-only tab
│   📄 SOW.docx          │
│   📄 Past Perf.pdf     │
│   📄 Amendment 3.pdf   │
```

- Documents sorted by `created_at` (newest first, matching Documents tab)
- No folder hierarchy — flat list
- Icon based on `document_type` (PDF vs DOCX vs other)
- No rename, no delete from here (those stay in Documents tab)
- No right-click context menu for documents in this phase

### 2.2 Interaction

| Action | Behavior |
|--------|----------|
| Click section header | Toggle expand/collapse. Default: collapsed. |
| Click a document | Opens as a read-only tab in the workspace content area |
| PDF document | Renders using existing PdfRenderer (iframe with presigned URL) |
| DOCX document | Renders using new DocxRenderer (TBD — see §4) |
| Other document types | Renders filename + "Preview not available" placeholder |

### 2.3 Tab behavior

Document tabs work like workspace item tabs but are read-only:
- Show filename in the tab bar
- No "Edit" button in the toolbar
- No save functionality
- Toolbar shows: filename, document type badge, "Open in new tab" link
- Close button (X) works normally

---

## 3. Backend Changes

### 3.1 New endpoint

`GET /api/cases/{case_id}/documents-summary`

Returns a lightweight list of documents shaped to match workspace items so the FileExplorer can consume them without changes to its data model:

```json
{
  "documents": [
    {
      "id": 47,
      "name": "SF-1449.pdf",
      "document_type": "pdf",
      "page_count": 3,
      "source": "sam_gov",
      "created_at": "2026-08-05T12:00:00Z"
    }
  ]
}
```

**Why a new endpoint instead of modifying `/workspace`?** Documents and workspace items are fundamentally different things — different tables, different IDs, different behaviors. Merging them into one list would require synthetic negative IDs or string prefixes to avoid collisions. A separate endpoint keeps the data models clean and lets the frontend compose them.

### 3.2 No schema changes

No new tables, no new columns. The `documents` table already has everything we need.

---

## 4. Frontend Changes

### 4.1 File: `frontend/src/lib/api.ts`

Add:
```ts
export interface DocumentSummary {
  id: number;
  name: string;
  document_type: string;
  page_count: number | null;
  source: string;
  created_at: string;
}

export const listDocumentsSummary = (caseId: number): Promise<{ documents: DocumentSummary[] }> =>
  fetchAPI(`/api/cases/${caseId}/documents-summary`);
```

### 4.2 File: `frontend/src/components/FileExplorer.tsx`

Add new props:
```ts
interface FileExplorerProps {
  // ... existing props ...
  documents: DocumentSummary[];          // NEW
  activeDocumentId: number | null;       // NEW
  onSelectDocument: (docId: number) => void;  // NEW
}
```

Add `UploadedDocumentsSection` rendered at the top of the sidebar, before the workspace selector:
- Collapsible header with `ChevronRight`/`ChevronDown` toggle
- Default collapsed: `useState(false)`
- When expanded, renders a flat list of document items
- Each item: icon + filename (truncated) + page count badge
- Active state: highlight if `activeDocumentId === doc.id`

### 4.3 File: `frontend/src/app/cases/[id]/tabs/WorkspaceTab.tsx`

**Data fetching:** Add `listDocumentsSummary(caseId)` call alongside existing `listWorkspaceItems` in `refreshList`. Store documents in state.

**Tab management:** When `onSelectDocument` fires:
1. Create a synthetic tab entry (not persisted to drafts table)
2. The tab ID is the document ID (documents and drafts have separate ID namespaces in practice — if they collide, we can offset)

**Content rendering:** Add a new renderer dispatch case for document tabs:
- PDF: `PdfRenderer` with `content: [{document_id: docId}]`
- DOCX: `DocxRenderer` (see §4.4)
- Other: placeholder

**Toolbar:** For document tabs, render a read-only toolbar:
- Filename (not editable)
- Document type badge
- "Open in new tab" link
- No edit button, no status dropdown, no delete

### 4.4 File: `frontend/src/components/DocxRenderer.tsx` (NEW)

Same pattern as PdfRenderer but for DOCX files. The preview endpoint already handles DOCX (it converts to PDF for preview or returns the file directly). If the preview URL returns a PDF, render in iframe. If it returns the raw DOCX, show a download link.

For phase 1, the simplest approach: use the same `getDocumentPreviewUrl(docId)` and render in an iframe. The backend's MinIO presigned URL serves whatever format the file is in — browsers can't natively render DOCX in an iframe, so we may need the backend to convert. Check: does the `/api/documents/{id}/preview` endpoint already handle DOCX?

If not, DocxRenderer shows: filename, page count, and a "Download to view" button that opens the presigned URL in a new tab.

---

## 5. Build Order

| Step | File | What |
|------|------|------|
| 1 | `backend/api/main.py` | Add `GET /api/cases/{case_id}/documents-summary` endpoint |
| 2 | `frontend/src/lib/api.ts` | Add `DocumentSummary` type + `listDocumentsSummary()` function |
| 3 | `frontend/src/components/FileExplorer.tsx` | Add `UploadedDocumentsSection` at top, new props |
| 4 | `frontend/src/app/cases/[id]/tabs/WorkspaceTab.tsx` | Fetch documents, handle document tab selection, render document content |
| 5 | `frontend/src/components/DocxRenderer.tsx` | New component for DOCX preview (or placeholder) |

---

## 6. Edge Cases

- **Case has zero documents:** Section header shows "Uploaded Documents (0)" and doesn't expand
- **Case has 50+ documents:** Flat list, scrollable within the section. No pagination needed (the workspace sidebar has its own scroll)
- **Document deleted while open in workspace:** Tab shows an error state. User closes the tab.
- **PDF fails to load (expired presigned URL):** PdfRenderer already handles this with error state
- **Non-PDF, non-DOCX files (images, CSVs, audio):** Show filename + "Preview not available" with download link
