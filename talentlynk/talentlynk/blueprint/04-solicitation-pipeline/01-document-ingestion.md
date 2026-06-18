# Document Ingestion

## Purpose
The entry point for federal solicitation packages into the TalentNyk system. Handles file upload, extraction, and triggering the downstream processing pipeline. Users drop raw solicitation packages (ZIP files containing PDFs, Word docs, Excel sheets) and the system kicks off automated analysis.

## Inputs
- Solicitation package files (ZIP, PDF, DOCX, XLSX)
- Upload method: S3 bucket trigger, manual upload via dashboard, or email forwarding
- Solicitation source: SAM.gov download, eBuy, agency portal, or direct email from CO

## Outputs
- Extracted individual files stored in structured document repository
- Pipeline trigger event with solicitation ID
- Metadata: source, upload timestamp, file count, file types
- Initial processing status: "Ingested — Awaiting Classification"

## Processing Flow

### 1. File Reception
- **S3 Bucket Upload:** Watched prefix triggers Lambda/queue message
- **Manual Upload:** Dashboard upload widget with drag-and-drop
- **Email Forwarding:** Parsed attachment extraction (optional channel)

### 2. Archive Extraction
- Detect and extract ZIP archives
- Handle nested archives
- Identify file types: PDF, DOCX, XLSX, TXT, images

### 3. File Organization
- Parse document into individual pages/sections
- Detect multi-document packages (common in federal solicitations)
- Group related files: SF-1449 form, SOW document, wage determination attachment, evaluation criteria, etc.

### 4. Initial Metadata Capture
- Solicitation number (from upload context or auto-detected)
- Upload date/time
- Source
- Total file count and types

### 5. Pipeline Trigger
- Create solicitation record in database with status "Ingested"
- Queue downstream processing: classification engine

## Technical Considerations

### Supported File Types
| Format | Handling |
|--------|----------|
| PDF (text-based) | Direct text extraction |
| PDF (scanned/image) | OCR pipeline → text |
| DOCX | Direct text extraction |
| XLSX | Sheet-by-sheet parsing |
| ZIP | Recursive extraction |
| Images (PNG, TIFF) | OCR pipeline |

### Scale & Performance
- Solicitation packages vary: single-page RFQ to 500+ page RFP
- Expected volume: TBD (10/month? 100/month?)
- Async processing: ingestion initiates background pipeline; user sees status updates

## Dependencies
- [[classification-engine]]
- [[sow-extraction]]
- [[../12-platform-admin/dashboard-analytics]]

## Key Rules & Compliance
- Solicitation documents are procurement-sensitive — access must be restricted
- FAR 3.104: procurement integrity — protect source selection information
- Document retention: keep all solicitation versions and amendments for audit/protest purposes

## Open Questions
- AWS Lambda + SQS for pipeline, or monolithic processing?
- How to handle password-protected solicitation attachments?
- Should the system proactively pull solicitations from SAM.gov (scheduled fetch), or rely on manual upload?
