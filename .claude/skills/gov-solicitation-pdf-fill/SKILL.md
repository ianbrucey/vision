---
name: gov-solicitation-pdf-fill
description: Fill government solicitation PDF forms (SF 1449, SF 30, price schedules, etc.) using pymupdf. Use when the solicitation pipeline has produced a quote and the user needs to fill out the required forms for proposal submission.
---

# Government Solicitation PDF Form Filling

Fill out federal procurement forms — SF 1449s, SF 30s, price/cost schedules, amendment acknowledgments, and other solicitation attachments — by placing text directly into the blank fields of the original PDFs.

## When to Run

Invoke this skill when:
- The user says "fill out this form," "fill the SF 1449," "complete the price schedule," "fill all the solicitation forms," or similar
- A vendor quote has been received and the user needs to prepare the proposal package
- The solicitation pipeline (triage → deep read → vendor matching → outreach → quote) has produced data that maps to form fields

**Do not run** for:
- Creating new forms from scratch — use the Workspace (freestyle-html skill) for custom documents
- Editing form field data without producing a filled PDF — use update_workspace_item
- Forms that are not government solicitation forms — use fill_pdf_form directly

## Prerequisites

Before starting, verify the case has:

1. **Original solicitation documents** — the unfilled PDF forms must be ingested in the case. Use `list_documents` to find them. Look for documents with `source: "sam_gov"` or `source: "user_upload"` and names containing "SF", "1449", "30", "solicitation", etc.
2. **Solicitation data** — the triage should be complete (`triage_status: "complete"` on the solicitation). Use `get_case` to check.
3. **Vendor/company profile** — the case must have a company profile attached with UEI, CAGE, address, etc. Use `get_case_profile` to check.
4. **A quote or pricing** — vendor outreach should have produced a quote document or pricing data. Use `list_documents` filtered to the outreach/quote document.

If any prerequisite is missing, tell the user what's needed before proceeding.

## Available Tools

Four tools exist for the PDF form filling workflow:

| Tool | Purpose |
|---|---|
| `download_document` | Download a document's original binary from MinIO to a local temp path |
| `fill_pdf_form` | Fill form fields in a PDF by placing text over blanks/underscores |
| `upload_filled_document` | Upload a filled PDF to MinIO and register it as a new document in the case |
| `convert_docx_to_pdf` | Convert a DOCX file to PDF (for DOCX forms) |

All tools are on the `vision` MCP server (no prefix needed — they are registered alongside `list_documents`, `get_case`, etc.).

## The Workflow

```
IDENTIFY FORMS
      │
      ├── list_documents → find all PDFs in the case
      ├── identify which ones are fillable forms (SF 1449, SF 30, price schedules, etc.)
      │
      ▼
DOWNLOAD
      │
      ├── download_document(document_id) for each form PDF
      │
      ▼
ANALYZE FORM FIELDS
      │
      ├── get_document_structure(document_id) → see sections and blocks
      ├── search_blocks or get_blocks_in_section → read the form text
      ├── identify every blank/underscore/empty cell
      ├── map each blank to a data source (solicitation, vendor profile, quote)
      │
      ▼
BUILD FIELD DATA
      │
      ├── For each field, find the EXACT label text in the PDF
      ├── Map the value from:
      │   ├── Solicitation data (solicitation #, due date, NAICS, PSC)
      │   ├── Company profile (vendor name, UEI, CAGE, address, phone)
      │   ├── Quote/pricing (unit price, amount, grand total)
      │   └── Computed values (dates, totals)
      │
      ▼
FILL
      │
      ├── fill_pdf_form(local_path, field_data) for each form
      │
      ▼
UPLOAD
      │
      ├── upload_filled_document(file_path, name) for each filled PDF
      │
      ▼
VERIFY
      │
      ├── Re-read the filled documents to confirm values appear
      │
      ▼
PRESENT TO USER
```

## Field Data Format

The `field_data` parameter to `fill_pdf_form` is a dict mapping EXACT label text (as it appears in the PDF) to values:

```json
{
  "UNIT PRICE": "$48,500.00",
  "AMOUNT": "$145,500.00",
  "GRAND TOTAL": "$145,500.00",
  "30a. SIGNATURE OF OFFEROR/CONTRACTOR": "Jane Doe, CEO",
  "30b. NAME AND TITLE OF SIGNER": "Jane Doe, Chief Executive Officer",
  "30c. DATE SIGNED": "07/22/2026"
}
```

### Rules for Field Labels

1. **Use the EXACT text from the PDF.** Search the document with `search_blocks` or read the page text with `get_blocks_in_section` to find the precise label. "SIGNATURE OF OFFEROR" is not the same as "30a. SIGNATURE OF OFFEROR/CONTRACTOR" — the tool matches substrings, but longer/more specific labels match more reliably.

2. **For tables**, use column header text. The tool searches for underscores/blanks on the same row as the label. "UNIT PRICE" will find the blank cell in the UNIT PRICE column.

3. **For signature blocks**, use the full block label including the block number (e.g. "30a. SIGNATURE OF OFFEROR/CONTRACTOR").

4. **For "if equal, name here" blanks**, use the surrounding context — e.g. the item description or the blank label itself.

5. **Case sensitivity** matters less than exact word matching. "UNIT PRICE" and "Unit Price" both work, but "Price" alone will match too broadly.

### Rules for Values

1. **Dollar amounts**: Format with `$` and commas — `"$48,500.00"`
2. **Dates**: Use MM/DD/YYYY — `"07/22/2026"`
3. **Names**: Use the full legal name as it appears in the company profile
4. **UEI/CAGE**: Use the exact identifier from the company profile, no extra characters
5. **Phone numbers**: Include area code — `"(503) 555-0123"`

## Common Government Forms

### SF 1449 — Solicitation/Contract/Order for Commercial Products and Services

Page 0 (the form page) contains these blocks the offeror must complete:

| Block | Label Text | Data Source |
|---|---|---|
| 12 | "12. DISCOUNT TERMS" | Company profile / payment terms |
| 17a | "17a. CONTRACTOR/OFFEROR" | Company profile → vendor_name |
| 17a CODE | "CODE" | Company profile → CAGE code or UEI |
| 17a TEL | "TELEPHONE NO." | Company profile → contact_phone |
| 17a UEI | "UEI:" | Company profile → UEI |
| 23 | "UNIT PRICE" | Quote → unit_price |
| 24 | "AMOUNT" | Quote → total_amount |
| 26 | "TOTAL AWARD AMOUNT" | Quote → grand_total |
| 30a | "30a. SIGNATURE OF OFFEROR/CONTRACTOR" | Company profile → authorized signer name |
| 30b | "30b. NAME AND TITLE OF SIGNER" | Company profile → signer name + title |
| 30c | "30c. DATE SIGNED" | Current date |

### B.2 PRICE/COST SCHEDULE (SF 1449 continuation page)

Usually on page 3-4. Contains an itemized table:

| Column | Label Text | Data Source |
|---|---|---|
| UNIT PRICE | "UNIT PRICE" | Quote → per-unit price for each CLIN |
| AMOUNT | "AMOUNT" | Quote → extended amount (qty × unit price) |
| GRAND TOTAL | "GRAND TOTAL" | Quote → sum of all amounts |

### SF 30 — Amendment of Solicitation/Modification of Contract

A DOCX file. Convert to PDF first with `convert_docx_to_pdf`, then fill the PDF with `fill_pdf_form`.

Key fields (vary by amendment):
- Block 3: "EFFECTIVE DATE"
- Block 8: "NAME AND ADDRESS OF CONTRACTOR"
- Block 9A: "AMENDMENT OF SOLICITATION NUMBER"
- Block 10A: "MODIFICATION OF CONTRACT/ORDER NUMBER"
- Block 14: Description of amendment
- Signature blocks (15A-15C)

### Amendment Acknowledgment (in SF 1449)

Located on page 2 of the SF 1449, has a table:
"AMENDMENT NO | DATE"

Fill with amendment numbers and dates from the triage artifacts.

## Example: Complete Form Filling Session

```
User: "Fill out the SF 1449 and price schedule for this solicitation"

Step 1 — Identify forms:
  → list_documents() 
  → Found: "S02+36C26026Q0847.pdf" (doc_id=42, 31 pages)

Step 2 — Get data:
  → get_case_profile() 
  → {vendor_name: "Vision Technologies LLC", uei: "ABC123DEF456", ...}
  → search_blocks("solicitation number") or get_document_structure(42)
  → {solicitation_number: "36C26026Q0847", due_date: "08-04-2026", ...}

Step 3 — Download:
  → download_document(42)
  → {local_path: "/tmp/vision-downloads/S02+36C26026Q0847.pdf"}

Step 4 — Fill page 0 (SF 1449 form):
  → fill_pdf_form(
      local_path="/tmp/vision-downloads/S02+36C26026Q0847.pdf",
      field_data={
        "17a. CONTRACTOR/OFFEROR": "Vision Technologies LLC",
        "30a. SIGNATURE OF OFFEROR/CONTRACTOR": "Jane Doe, CEO",
        "30b. NAME AND TITLE OF SIGNER": "Jane Doe, Chief Executive Officer",
        "30c. DATE SIGNED": "07/22/2026"
      }
    )

Step 5 — Fill page 3 (price schedule):
  → fill_pdf_form(
      local_path="...",  (same file — fills are cumulative)
      field_data={
        "UNIT PRICE": "$48,500.00",
        "AMOUNT": "$145,500.00",
        "GRAND TOTAL": "$145,500.00"
      }
    )

Step 6 — Upload:
  → upload_filled_document(
      file_path="/tmp/vision-downloads/S02+36C26026Q0847_filled.pdf",
      name="SF 1449 — Filled — 36C26026Q0847",
      document_type="filled_form"
    )
  → {document_id: 43}

Step 7 — Present results:
  "✅ SF 1449 filled and uploaded as document #43.
   Filled fields: 17a CONTRACTOR, 30a SIGNATURE, 30b NAME, 30c DATE,
   UNIT PRICE ($48,500), AMOUNT ($145,500), GRAND TOTAL ($145,500).
   
   Download and review the filled PDF in the Documents tab."
```

## Hard Constraints

> **NEVER fill a form without human confirmation of the values.** Present the field data mapping to the user before calling fill_pdf_form. Say: "I'll fill these fields: [list with values]. Confirm these are correct?"

> **ALWAYS download before filling.** The fill_pdf_form tool requires a local file path. Call download_document first. Never try to fill a document by its doc_id alone.

> **ALWAYS upload after filling.** Filled PDFs sitting in /tmp are lost on restart. Call upload_filled_document to persist them to the case.

> **ALWAYS verify.** After filling and uploading, re-read the filled document (wait for the ingest job to complete, then use get_document_structure or search_blocks) to confirm the values appear in the expected locations.

> **NEVER modify the original.** download_document gives you a copy for filling. The original document in MinIO is unchanged. The filled version gets a new document_id.

> **Use EXACT label text.** Fuzzy field matching is unreliable. Read the document text with search_blocks or get_blocks_in_section to find the precise label text before building the field_data dict.

> **Present the results clearly.** After uploading, tell the user:
> - Which fields were filled (and which were not found)
> - The new document_id and name
> - A link or instruction to view it in the Documents tab

## Troubleshooting

### "fields_not_found" includes labels I expected to work
The label text didn't match anything in the PDF. Use `search_blocks` or `get_blocks_in_section` to find the exact text as it appears in the document. Look for:
- Different spacing or line breaks
- Special characters (e.g. periods, slashes)
- The label might be split across multiple lines
- The label might use a different abbreviation

### Values appear in the wrong place
The underscore/blank detection found a blank area near the label, but it might not be the RIGHT blank area. Try:
- Use a more specific label that appears closer to the target blank
- Add a `page` parameter to restrict searching to a specific page
- If a label appears on multiple pages, specify `page` to target the right one

### DOCX forms
For DOCX files (like SF 30 amendments):
1. `download_document(doc_id)` → get the .docx locally
2. `convert_docx_to_pdf(local_path)` → convert to PDF
3. `fill_pdf_form(converted_pdf_path, field_data)` → fill the PDF
4. `upload_filled_document(filled_pdf_path, name)` → persist

### Complex multi-line forms
If the form has dense fields or overlapping text:
1. Try filling one field at a time (call fill_pdf_form per field)
2. Use the `page` parameter to isolate each page
3. If the PDF has fillable AcroForm fields, those take priority — the tool works best on flat/text-based forms

## Integration with Solicitation Pipeline

This skill is typically invoked AFTER:
1. The solicitation pipeline has completed through Phase 4 (Go/No-Go = GO)
2. Vendor matching has identified subcontractors
3. Outreach has produced quotes
4. The user has decided to proceed with proposal submission

The form filling is the bridge between "we have a quote" and "the proposal is ready to submit." The filled forms, combined with the response narrative (from the response-drafter agent in the solicitation pipeline), constitute the complete proposal package.
