# ZIP File Ingestion

**Status:** Straightforward

## What it is

The current ingestion pipeline handles individual files (PDF, DOCX, TXT, CSV,
XLSX, images). It cannot handle ZIP archives. GovCon solicitations often come as
ZIP downloads containing multiple file types. The ingestion endpoint should
detect ZIP files, extract their contents, and recursively ingest each extracted
file.

## Existing infrastructure

- `POST /api/cases/{case_id}/ingest` — uploads a single file to MinIO, enqueues
  an ingest job
- `ingestion/jobs.py` — background worker picks up jobs, routes to the correct
  handler based on file extension
- `ingestion/` directory — handlers for PDF, DOCX, XLSX, etc.

## What needs to be built

### 1. ZIP detection in the upload endpoint

In `backend/api/main.py` `ingest_document()`:
- Check if `file.content_type` is `application/zip` or filename ends with `.zip`
- If ZIP: save to temp file, extract contents, iterate over extracted files,
  upload each one individually to MinIO, enqueue a job per file
- Return `{ job_ids: [...], file_count: N }` instead of `{ job_id: N }`
- If not ZIP: existing single-file flow unchanged

### 2. Recursive folder traversal within ZIP

Yes — the extraction must walk the entire ZIP directory tree, not just
root-level files. A typical GovCon solicitation ZIP looks like:

```
solicitation_spe4a8-25-r-0001.zip
├── RFP_SPE4A8-25-R-0001.pdf
├── Attachments/
│   ├── Attachment_1_PWS.pdf
│   ├── Attachment_2_Pricing.xlsx
│   ├── Attachment_3_TP_Exhibit.docx
│   └── Drawings/
│       ├── dwg_001.pdf
│       └── dwg_002.pdf
├── QandA/
│   ├── QA_Round1.xlsx
│   └── QA_Round2.xlsx
└── Past_Performance_Template.xlsx
```

The extraction must:

- Walk all entries in the ZIP's central directory
- Skip directory entries themselves (they have no data)
- For each file entry, preserve the relative path context but flatten or
  namespace the document name (e.g., `Attachments/Drawings/dwg_001.pdf`
  becomes document name `dwg_001.pdf` with metadata `{ "zip_path":
  "Attachments/Drawings/dwg_001.pdf" }`)
- Process all supported file types (PDF, DOCX, XLSX, CSV, TXT, images)
  regardless of how deep they are in the folder tree
- Skip unsupported file types with a warning logged

### 3. Nested ZIP handling

- ZIPs within the folder tree (e.g., `Attachments/supporting_docs.zip`)
  are extracted recursively
- Depth limit of 3 to prevent zip bombs
- Each nested ZIP's contents are flattened and ingested

### 4. Frontend handling

In `DocumentsTab.tsx` and `DocumentAttachButton.tsx`:
- The `uploadFile` return type changes for ZIPs — handle the `job_ids` array
- Show progress for multiple files: "Extracting ZIP... → Ingesting 5 files..."
- Each file gets its own upload progress entry

### 3. Nested ZIP handling

- Recursively handle ZIPs within ZIPs (rare but possible)
- Depth limit of 3 to prevent zip bombs

## Files to modify

- `backend/api/main.py` — `ingest_document()` endpoint (~30 lines)
- `backend/ingestion/jobs.py` — maybe a `ingest_zip` job type (~20 lines)
- `frontend/src/lib/api.ts` — update `uploadFile` return type (~5 lines)
- `frontend/src/app/cases/[id]/tabs/DocumentsTab.tsx` — handle multi-file upload result (~15 lines)
- `frontend/src/components/DocumentAttachButton.tsx` — handle multi-file (~10 lines)

## Potential edge cases

- Large ZIPs (>100MB): streaming extraction vs temp file
- Password-protected ZIPs: skip with warning
- Non-file entries (directories, symlinks): skip
- Duplicate filenames across ZIP entries: append suffix

## Verification

1. Create a ZIP containing a PDF, a DOCX, and a CSV
2. Upload via the Documents tab or the correspondence "Upload" button
3. Verify 3 ingestion jobs are created, all 3 files appear in the documents list
4. Verify each file is OCR'd/indexed correctly
5. Upload a nested ZIP (ZIP within ZIP) — verify all files extracted

## Estimated effort

~2-3 hours. Well-scoped, clear boundaries.
