# Classification Engine

## Purpose
Parse solicitation headers, keywords, and structure to determine document type — RFI (Sources Sought), RFQ (Request for Quote), or RFP (Request for Proposal). This classification drives the entire downstream workflow: RFIs are for market research, RFQs are price-focused, RFPs require full technical proposals.

## Inputs
- Raw solicitation text (extracted from PDFs, DOCX, etc.)
- Document metadata (form numbers, subject lines, agency)

## Outputs
- Solicitation type: RFI | RFQ | RFP | Combined (RFP/RFQ) | Sources Sought | Special Notice | Amendment
- Confidence score
- Document type routing: which downstream pipeline modules to activate
- Key metadata: solicitation number, agency, NAICS, due date, set-aside status

## Classification Logic

### Document Type Detection

| Indicator | Likely Type |
|-----------|-------------|
| SF-1449 form present | RFQ (supply/service) |
| SF-1442 form present | RFP / IFB (construction) |
| "Request for Proposal" in header | RFP |
| "Request for Quote" / "Request for Quotation" | RFQ |
| "Sources Sought" / "Request for Information" | RFI |
| Section L (Instructions) + Section M (Evaluation) | RFP (combined) |
| "Combined Synopsis/Solicitation" | Combined RFP/RFQ |
| FAR 52.212-1 + 52.212-2 | Commercial item solicitation |
| SF-30 form | Amendment to existing solicitation |

### LLM-Assisted Classification
1. Extract first 5-10 pages (headers, cover page, Section A)
2. Feed to LLM with classification prompt
3. LLM returns: type, confidence, key metadata
4. System validates against form detection (e.g., SF-1449 = RFQ regardless of LLM output)

### Pipeline Routing

| Type | Modules Activated |
|------|-------------------|
| RFI | SOW extraction, NAICS extraction (lightweight — info gathering only) |
| RFQ | SOW extraction, pricing engine, limited technical narrative |
| RFP | Full pipeline: all modules activated |
| Amendment | [[../08-review-submission/amendment-handling]] |
| Combined | Full pipeline (treat as RFP with RFQ elements) |

## Metadata Extraction

From the classified document, extract:
- **Solicitation Number:** e.g., W912HN-24-R-0001
- **Agency:** e.g., Department of the Army, GSA
- **NAICS Code(s):** Primary and any referenced secondary codes
- **Set-Aside:** Total Small Business, WOSB, SDVOSB, 8a, HUBZone, Full & Open
- **Response Due Date:** Proposal submission deadline
- **Place of Performance:** Where the work will be performed
- **Contract Type:** FFP, T&M, Cost-Plus, IDIQ, etc.
- **Estimated Value:** If disclosed

## Dependencies
- [[document-ingestion]]
- [[sow-extraction]]
- [[section-l-parser]]
- [[section-m-parser]]

## Key Rules & Compliance
- Misclassification can lead to wrong proposal format → non-responsive → thrown out
- Amendment handling is critical: if a solicitation is amended, the original classification may change
- RFIs are NOT proposals — submitting pricing to an RFI can be a strategic error

## Open Questions
- Classification model: fine-tuned classifier, few-shot LLM, or rule-based + LLM hybrid?
- How to handle "evergreen" solicitations (open continuous, multiple award)?
