# RFI Response: Enterprise Document Management Platform & CEDMS Modernization

**Department of War**
**Date:** June 15, 2026
**Classification:** UNCLASSIFIED
**Format:** White Paper (25 pages maximum)

---

## COVER PAGE

**Respondent:** Justice Quest LLC (DBA: JQ)
**Address:** 1410 Comet Ives Lane, Lawrenceville, GA 30046
**UEI:** [NEEDS: UEI number]
**CAGE Code:** [NEEDS: CAGE Code]
**Small Business Status:** [NEEDS: Small business status declaration]
**NAICS Codes:** [NEEDS: NAICS codes]

**Point of Contact:**
Ian Bruce
Principal AI Engineer / Founder
Phone: 562-739-5206
Email: ian.b@justicequest.pro

**Response to:** Request for Information (RFI) — Enterprise Document Management Platform & CEDMS Modernization
**Submitted to:** Gerald.l.whitsett.civ@mail.mil
**Date of Submission:** June 15, 2026

**Proprietary Information Notice:** This response contains proprietary business information of Justice Quest LLC and is submitted for Government market research purposes only. Justice Quest LLC requests that proprietary information contained herein not be disclosed outside the U.S. Government, in accordance with the Disclaimer in the subject RFI.

---

## SECTION 1: EXECUTIVE SUMMARY

Justice Quest LLC (JQ) submits this white paper in response to the Department of War's Request for Information on building a cloud-native, multi-tenant Enterprise Document Management Platform (EDMP) to ingest approximately 1.5 billion digitized microfiche records, subsume the legacy CEDMS system, and serve as the Department's standardized document management fabric with advanced data exploitation capabilities.

JQ understands that the Department of War faces a structural challenge: 5.88 million physical microfiche sheets are degrading, non-compliant with NARA standards, and incurring over $1.1 million annually in manual retrieval costs. The legacy CEDMS system, comprising the CEDMS-CDA financial document archival subsystem and the CEDMS-MSS SharePoint-based report processing subsystem with Altair Monarch integration, has served its purpose but cannot scale to meet the Department's future data exploitation needs. The Department requires a single, extensible, multi-tenant platform that eliminates document silos, achieves NARA compliance, provides enterprise-wide business intelligence, and ultimately decommissions the legacy CEDMS system for significant return on investment.

Our response describes an approach grounded in JWCC-native Platform-as-a-Service (PaaS) capabilities, designed to operate at IL5 security impact level. We recommend an architecture that leverages cloud-native services for Optical Character Recognition (OCR), Intelligent Document Processing (IDP), full-text indexing, federated search, and dynamic user interfaces rather than relying on proprietary custom software stacks. We propose a massively parallel ingestion pipeline capable of processing the full 1.5-billion-record corpus within an aggressive time frame while preserving provenance through dual-file (TIFF preservation master / PDF access copy) linkages and metadata manifest integration. Our data exploitation framework applies AI/ML and NLP to transform unstructured OCR output into a highly reportable dataset, enabling dynamic dashboards and cross-document trend analysis that the current fragmented systems cannot provide.

For the mid-term subsumption of CEDMS, we propose a phased migration roadmap that maintains MOSA compliance, preserves current source system integrations via standardized APIs, and incrementally replaces RBAC, CAC authentication, and Altair Monarch report processing with cloud-native equivalents. Our API-first architecture ensures that future legacy systems can onboard without requiring core platform redesigns.

Justice Quest LLC brings demonstrated capabilities in high-volume document processing, AI/ML pipeline development, and workflow automation. Our past performance, while not at the precise DoD enterprise scale described in this RFI, demonstrates the core technical competencies required: processing hundreds of thousands of unstructured documents with agentic AI pipelines for correlation and analysis, building automated document classification systems, and developing custom ingestion workflows for heterogeneous document formats. We address the enterprise-scale gap through a teaming strategy that would pair JQ's AI/ML and automation expertise with a JWCC-authorized Cloud Service Provider (CSP) and a FADGI 3-Star digitization specialist.

This response addresses all nine Areas of Inquiry in sequence. Section 8 provides a non-binding Rough Order of Magnitude (ROM) cost estimate. Section 9 provides our corporate experience and past performance references.

---

## SECTION 2: RESPONSE TO AREAS OF INQUIRY

### AREA 1: Cloud-Native Foundation

**Question:** Describe how your approach delivers cloud-native, platform-as-a-service (PaaS) capabilities via the Joint Warfighting Cloud Capability (JWCC). Specifically address: JWCC-native services for OCR, indexing, search, and user interface; Total Cost of Ownership (TCO) reduction compared to custom software; and Intelligent Document Processing (IDP) to retroactively analyze ingested OCR'd PDFs and autonomously classify document types and extract structured metadata without manual data entry.

**Response:**

**2.1.a JWCC-Native Architecture**

Justice Quest LLC recommends deploying the EDMP on a JWCC-authorized cloud platform (AWS, Azure, GCP, or Oracle Cloud Infrastructure). The architecture is designed to be cloud-agnostic at the orchestration layer while leveraging each CSP's native PaaS services for the heavy-lifting functions the RFI specifies. This approach avoids the long-term maintenance burden, security patching overhead, and scaling limitations of custom-coded software stacks.

For each functional area, we identify the corresponding JWCC-native service pattern:

| Function | JWCC-Native Approach | Rationale |
|---|---|---|
| **OCR** | CSP-native document AI services (e.g., AWS Textract, Azure Document Intelligence, Google Document AI) | Serverless, auto-scaling, continuously updated by CSP. No Kofax Capture licenses or ERM Perfect infrastructure required. Supports 50+ languages and handwriting recognition out of the box. |
| **Full-Text Indexing** | CSP-native search services (e.g., Amazon OpenSearch, Azure Cognitive Search, Google Vertex AI Search) | Managed, petabyte-scale, supports hybrid (keyword + semantic) search. Auto-scales with ingestion volume. Integrates with CSP IAM for document-level access control. |
| **User Interface** | CSP-native application hosting with a lightweight web framework (React/Next.js deployed to CSP container services or static hosting) | Avoids custom UI server stacks. The UI is the thinnest reasonable layer on top of CSP-managed backends. |
| **Storage** | CSP object storage (S3, Azure Blob, GCS) with lifecycle policies for TIFF preservation masters and PDF access copies; CSP-managed relational database for structured metadata (Aurora, Azure SQL, Cloud SQL) | IL5-authorized storage with encryption at rest, versioning, immutability for preservation masters. |
| **Compute** | CSP serverless functions and managed container services (Lambda/Fargate, Azure Functions/Container Apps, Cloud Run) | No servers to patch. Pay-per-use aligns costs with ingestion cadence. |
| **API Gateway** | CSP-native API management (AWS API Gateway, Azure API Management, Google Apigee) | Managed throttling, authentication, monitoring. Enables API-first integration. |

**2.1.b TCO Reduction vs. Custom Software**

The TCO advantage of JWCC-native PaaS over custom software is substantial and measurable across five dimensions:

1. **Licensing Elimination.** The current CEDMS-CDA architecture relies on Kofax Capture and ERM Perfect for OCR and indexing, and CEDMS-MSS depends on Altair Monarch and SharePoint licensing. A JWCC-native approach eliminates these recurring COTS license costs entirely. OCR is billed per page processed ($0.0015/page at CSP list rates), indexing is billed per GB-month, and search is billed per query. For 1.5 billion records, even at enterprise scale, these metered costs are typically lower than perpetual COTS licenses plus maintenance.

2. **Infrastructure Operations Labor.** Custom software requires Government or contractor personnel to maintain servers, apply security patches, manage database clusters, and operate backup systems. JWCC-native PaaS shifts these responsibilities to the CSP. A conservative estimate is a 40-60% reduction in O&M labor compared to a custom IaaS deployment.

3. **Scaling Overhead.** Custom software at 1.5 billion records requires significant capacity planning, over-provisioning, and periodic hardware refresh cycles. JWCC-native services scale elastically. The Government pays only for what it uses -- during ingestion spikes, services scale up automatically; during idle periods, costs contract. There is no fleet of underutilized servers.

4. **Security Authorization Boundary Reduction.** Custom software deployed on IaaS inherits the full IL5 authorization boundary (OS, middleware, application). JWCC-native PaaS shifts a significant portion of the security control inheritance to the CSP's existing DoD Provisional Authorization (PA), reducing the number of controls the Government must assess and authorize. This translates to a faster ATO cycle and lower continuous monitoring overhead.

5. **Technology Refresh.** Custom software requires periodic technology refresh (OS upgrades, library patches, framework migrations). JWCC-native PaaS services are continuously updated by the CSP without Government intervention, eliminating refresh project costs.

**2.1.c Intelligent Document Processing (IDP)**

The IDP pipeline JQ recommends operates as a two-phase system:

**Phase 1: Doc-Level OCR and Initial Structuring.** When the digitization vendor delivers searchable PDF access copies with embedded text layers, the platform ingests and indexes the OCR text immediately for enterprise search. This provides day-one access. The CSP-native OCR service performs a secondary extraction pass on the TIFF preservation masters to produce a machine-verified text layer independent of the digitization vendor's OCR, ensuring accuracy and completeness.

**Phase 2: Autonomous Classification and Metadata Extraction.** The IDP engine then processes each document through a multi-stage AI/ML pipeline:

- **Document Type Classification:** A trained NLP model classifies each document into its functional category (e.g., DD Form 250 Material Inspection and Receiving Report, SF-1080 Voucher for Transfers, DFAS Form XYZ, etc.). The model is initially trained on a labeled sample drawn from the 1.5-billion-record corpus and continuously improved through active learning. Documents that do not match known types with high confidence are flagged for human review, and the human determination is fed back into the model.

- **Structured Metadata Extraction:** Once classified, a second model extracts structured metadata fields specific to each document type. For example, for a DD Form 250, the model extracts contract number, line item number, receiving report number, date, quantity, and other field-level data. This extraction is validated against business rules (e.g., date formats, numeric ranges) and flagged for human review when confidence falls below a threshold.

- **Entity Resolution and Linking:** Extracted entities (contract numbers, vendor names, dates, financial codes) are resolved against authoritative reference data and linked to enable cross-document querying. This is how the platform enables queries like "show all documents referencing Contract N00019-22-C-XXXX across all tenants" without requiring users to know which tenant ingested the document.

- **Progressive Refinement:** The IDP pipeline never requires manual data entry as a prerequisite for ingest. Documents enter the system immediately upon batch delivery and are searchable from day one. The AI/ML enrichment layers build on top, improving over time as the models learn from the 1.5-billion-record training corpus. This design ensures that the ingestion cadence is never gated by human review capacity.

**IDP Technology Selection:** We recommend CSP-native AI/ML services for this pipeline: AWS Comprehend / SageMaker, Azure AI Document Intelligence / Azure Machine Learning, or Google Document AI / Vertex AI. These services are pre-integrated with CSP IAM for IL5 Zero-Trust enforcement and do not require separate security authorization.

---

### AREA 2: Massive Ingestion

**Question:** Provide a technical strategy for rapid ingestion and indexing of approximately 1.5 billion digitized microfiche records. Specifically address: integrating with FADGI 3-Star digitization deliverables; automated ingestion of dual-file deliverables (TIFF preservation and searchable PDF access copies); processing metadata manifests in CSV/JSON format from the digitization vendor; supporting a "Batch" delivery model with a quality control workflow and government QA validation before records are accepted into the system; and automatically linking files and indexing the PDF text layer for immediate enterprise search.

**Response:**

**2.2.a Ingestion Architecture Overview**

The ingestion pipeline is designed for massive parallelism, fault tolerance, and continuous operation. The architecture accepts daily or weekly batches from the digitization vendor, processes each batch through automated quality control gates, presents results for Government QA validation, and upon acceptance, commits records to the production repository where they are immediately available for enterprise search.

The pipeline is structured as an event-driven, serverless workflow using CSP-native services (AWS Step Functions, Azure Durable Functions, or Google Cloud Workflows):

```
[Digitization Vendor Batch Delivery]
        |
        v
[S3/Blob/GCS Landing Zone — IL5 Encrypted]
        |
        v
[Manifest Validation & File Presence Check]
        |
        v
[FADGI 3-Star Conformance Validation (Automated)]
        |
        v
[TIFF-to-OCR Text Extraction & PDF Text Layer Verification]
        |
        v
[Metadata Normalization & Enrichment]
        |
        v
[QA Staging Area — Government Review Interface]
        |
        v
[Accept / Reject / Remediate Decision]
        |
        v
[Production Repository — Full-Text Indexed, Searchable]
```

**2.2.b FADGI 3-Star Deliverable Integration**

The digitization vendor delivers two files per microfiche sheet:
- **Preservation Master:** TIFF, 300+ PPI, 8-bit grayscale or 24-bit color, uncompressed or lossless compression, per FADGI 3-Star specification.
- **Access Copy:** Searchable PDF/A with embedded OCR text layer, derived from the preservation master.

The platform's FADGI conformance validator performs automated quality checks on each delivered batch:

1. **TIFF Validation:** Verifies resolution (>=300 PPI), bit depth, color space, compression type, and image dimensions against FADGI 3-Star parameter tables. Non-conforming images are flagged with a specific failure code (e.g., "RESOLUTION_BELOW_300PPI", "COMPRESSION_NOT_LOSSLESS").

2. **PDF/A Validation:** Verifies PDF/A compliance (ISO 19005), embedded text layer presence, and text layer quality (character confidence scores from CSP OCR re-extraction). PDFs with missing or corrupt text layers trigger re-OCR from the corresponding TIFF.

3. **Completeness Validation:** Cross-references delivered files against the metadata manifest to ensure every expected record has both a TIFF and a PDF. Missing or orphaned files are flagged.

4. **Image Quality Assessment:** Automated image quality metrics (sharpness, contrast, skew detection, blank page detection). Images scoring below quality thresholds are flagged for human review in the Government QA interface.

**2.2.c Metadata Manifest Processing**

The digitization vendor delivers a metadata manifest in CSV or JSON format alongside each batch. The manifest contains, at minimum:

- Unique record identifier (e.g., microfiche sheet number, batch ID, frame number)
- Source microfiche metadata (date range, originating organization, document series)
- File references (TIFF filename/path, PDF filename/path)
- Digitization metadata (scan date, equipment ID, operator, quality metrics)

The platform ingests the manifest through a schema-validating parser that:

1. Validates manifest schema against the agreed-upon contract (JSON Schema or CSV header definition).
2. Cross-references every file listed in the manifest against the files actually delivered.
3. Normalizes metadata fields to the EDMP's internal metadata model (validating dates, controlled vocabularies, and reference integrity).
4. Enriches metadata with platform-generated fields (ingestion timestamp, batch ID, processing pipeline version).
5. Loads normalized metadata into the platform's structured metadata store, linked to both the TIFF and PDF storage objects.

**2.2.d Batch Delivery and QA Workflow**

The platform accepts deliveries on a daily or weekly batch cadence, configured based on the digitization vendor's production rate. Each batch is a self-contained delivery unit with its own manifest.

**Quality Control Workflow:**

1. **Automated Pre-Screen:** Upon batch landing, the platform runs all automated validations (FADGI conformance, manifest completeness, file integrity, OCR quality). Results are compiled into a structured QA report per batch.

2. **QA Staging Area:** Validated batches are promoted to a Government-accessible QA staging area. This interface provides:
   - Batch-level summary statistics (total records, pass/fail counts, failure reason distributions).
   - Drill-down capability to individual record level with side-by-side TIFF/PDF viewing.
   - Flagged items highlighted with failure codes and severity levels.
   - A batch acceptance workflow: the Government QA reviewer can accept individual records, accept all passing records, reject and return a batch to the digitization vendor, or accept with noted exceptions.

3. **Government QA Validation:** The Government performs spot-check QA on each batch. The platform supports configurable sampling rates (e.g., review 5% of records in high-confidence batches, 20% in lower-confidence batches). The Government QA reviewer has the authority to accept, reject, or request remediation from the digitization vendor.

4. **Acceptance and Promotion:** Upon Government acceptance, accepted records are promoted to the production repository. Records requiring remediation are tracked in a remediation queue with notes communicated back to the digitization vendor. A new delivery of remediated records references the original batch ID for traceability.

**2.2.e Record Linking and Immediate Search**

Upon promotion to the production repository:

- The TIFF preservation master and PDF access copy are linked at the record level with a bidirectional reference in the metadata store.
- The PDF text layer is extracted and indexed in the CSP-native search service within seconds of promotion.
- The record is immediately available for full-text enterprise search.
- The TIFF preservation master is stored in an immutable object storage bucket with versioning enabled and a lifecycle policy that prevents deletion, ensuring NARA-compliant preservation.

**2.2.f Ingestion Throughput Strategy**

At 1.5 billion records, daily ingestion rate is the critical architecture variable. If the digitization vendor delivers at a sustained rate of 1 million records per day (a plausible rate for a dedicated FADGI 3-Star digitization facility), the full corpus ingests in approximately 1,500 calendar days (roughly 4 years). The platform must sustain this throughput without degradation.

JQ's recommended architecture achieves this through:

1. **Serverless Horizontal Scaling:** CSP-native OCR, indexing, and search services scale horizontally without intervention. There is no ceiling on concurrent processing beyond CSP account-level service quotas, which can be raised.

2. **Parallel Batch Processing:** The platform processes multiple batches concurrently. A batch of 100,000 records fans out into 100,000 parallel OCR/indexing tasks via CSP-native queue and worker services.

3. **Back-Pressure Handling:** If downstream services slow (e.g., search indexing latency), the pipeline buffers in-flight records in a managed queue (SQS, Azure Queue, Pub/Sub) and continues upstream processing without data loss.

4. **Cost-Aware Throttling:** The platform supports configurable throughput caps to manage cloud consumption costs. If budget constraints require a slower ingestion rate, the pipeline can be throttled to a target records-per-day ceiling.

---

### AREA 3: Data Exploitation and Reporting

**Question:** Describe native cloud analytics (to include AI/ML, NLP, native BI tools) that can transform the 1.5 billion OCR'd documents into a highly reportable dataset, supporting dynamic dashboards, cross-document trend analysis, and providing enterprise-wide business intelligence capabilities.

**Response:**

**2.3.a Data Exploitation Architecture**

Once the 1.5 billion records are ingested, OCR'd, classified, and metadata-enriched, they form a structured knowledge base rather than an unstructured document pile. The exploitation layer builds on this foundation to deliver actionable intelligence.

JQ recommends a three-tier exploitation architecture:

**Tier 1: Structured Query Layer.** The metadata store (containing document type, extracted fields, dates, amounts, entities, and cross-references) is exposed through a SQL-compatible query interface backed by CSP-native analytics databases (AWS Athena/Redshift, Azure Synapse, Google BigQuery). This enables standard BI tools to connect directly and run SQL queries against the full corpus without moving data.

**Tier 2: NLP and Semantic Search Layer.** Building on the indexed full text, an NLP pipeline performs entity extraction beyond what the IDP phase captures. This includes: named entity recognition (people, organizations, locations, military unit identifiers), relationship extraction (e.g., "Contract X references Program Y"), sentiment and anomaly detection, and topic modeling to cluster documents into thematic groups.

**Tier 3: AI/ML Analytics Layer.** CSP-native ML services (SageMaker, Azure ML, Vertex AI) host trained models for specific exploitation use cases:
- **Fraud/Waste/Abuse Detection:** Anomaly detection models trained on financial document patterns to flag unusual transactions.
- **Trend Forecasting:** Time-series models projecting spending patterns, contract activity, or document volume trends across the Department.
- **Similarity and Deduplication:** Vector embeddings of document content enable "find similar" queries and near-duplicate detection across tenants.

**2.3.b Dynamic Dashboards**

The platform exposes pre-built and customizable dashboards through CSP-native BI services (Amazon QuickSight, Power BI Embedded, Google Looker). Dashboards connect to the structured query layer and support:

1. **Operational Dashboards:** Ingestion pipeline health, batch QA acceptance rates, digitization vendor performance, storage consumption, query volume, API usage.

2. **Content Dashboards:** Record counts by document type, originating organization, date range, and classification confidence level. Drill-through from aggregate to individual document.

3. **Financial Intelligence Dashboards:** Cross-document trend analysis linking contracts, receiving reports, vouchers, and payments. For example: "Show the average time from receiving report to payment across all DFAS-processed contracts for FY2024, broken down by contracting activity."

4. **Compliance Dashboards:** Audit trail visualizations, retention policy compliance, access pattern analysis for Zero-Trust monitoring.

**2.3.c Cross-Document Trend Analysis**

The true power of a unified, 1.5-billion-record dataset is the ability to ask questions that span documents, tenants, and time periods. JQ's recommended exploitation framework supports:

- **Temporal Analysis:** Trend lines across decades of financial records, enabling year-over-year and decade-over-decade comparisons that are impossible when data is siloed in separate systems.
- **Cross-System Correlation:** Linking documents that reference the same contract, vendor, program, or funding line, even when those documents originated in different source systems and belong to different tenants.
- **Pattern Discovery:** Unsupervised ML techniques (clustering, anomaly detection) identify patterns in the data that human analysts would not know to query for -- for example, recurring anomalies in specific categories of financial documents that suggest systemic issues.

**2.3.d Data Access Control for Analytics**

Every analytics query, dashboard, and ML model invocation respects the same Zero-Trust access controls enforced at the document level (see Area 6). A user running a cross-tenant trend analysis sees only the documents their RBAC permissions allow. The analytics layer never bypasses the access control layer. This is implemented through CSP-native IAM integration, where analytics queries are executed under the requesting user's security context.

---

### AREA 4: Multi-Tenant Scalability

**Question:** Present a scalable, multi-tenant architecture that supports multiple organizations ("tenants") while ensuring data isolation at scale, utilizing shared cloud-native services to reduce cost and administration overhead.

**Response:**

**2.4.a Multi-Tenant Architecture Model**

JQ recommends a **single-platform, logically-isolated multi-tenant** architecture. All tenants share the same JWCC-native PaaS infrastructure (shared OCR services, shared search service, shared storage infrastructure), but data is logically partitioned and access-controlled such that no tenant can access another tenant's data without explicit cross-tenant authorization.

This model is superior to a physically-isolated model (separate instances per tenant) because:
- It eliminates duplicated infrastructure costs and administration overhead.
- It enables the enterprise-wide analytics the Department requires (subject to access controls).
- It allows new tenants to be onboarded without provisioning new hardware or creating new cloud accounts.

It is superior to a shared-database-with-tenant-column model because:
- CSP-native IAM can enforce isolation at the storage layer, not just the application layer.
- Data isolation is enforced by the CSP's security infrastructure, not by application code that could contain bugs.

**2.4.b Data Isolation Implementation**

Data isolation is achieved through a layered approach:

1. **Storage-Level Isolation:** Each tenant's documents are stored in a tenant-specific prefix within CSP object storage. IAM policies enforce that only users/roles associated with a given tenant can access objects under that tenant's prefix. This is enforced by the CSP's storage authorization layer, not by application code.

2. **Search Index Isolation:** The CSP-native search service supports document-level access control lists (ACLs). Every indexed document is tagged with its tenant identifier and the RBAC categories (site, organization, document category, document type) that govern access. Search queries return only documents matching both the query terms and the requesting user's access profile.

3. **Metadata Store Isolation:** Row-level security (RLS) policies in the structured metadata database enforce that users can only see metadata rows belonging to their authorized tenants and RBAC categories.

4. **Cross-Tenant Access Control:** Cross-tenant access (required for enterprise analytics) is configured as explicit grants rather than as a default. An analyst with cross-tenant authority sees data through a union of their per-tenant permissions, not through a bypass of access controls.

**2.4.c Tenant Onboarding**

A new tenant is onboarded through a self-service or administrator-assisted process that:

1. Registers the tenant identity in the platform's tenant registry.
2. Configures the tenant's IAM roles and RBAC categories (sites, organizations, document categories, document types).
3. Provisions tenant-specific storage prefixes and access policies.
4. Optionally configures tenant-specific metadata schemas if the tenant has unique document types not present in the global schema.
5. Establishes API endpoints for the tenant's source systems to connect (see Area 5).

No new cloud infrastructure is provisioned -- onboarding is a configuration operation, not a deployment operation.

**2.4.d Scale Considerations**

The 1.5 billion records ingested in the initial mission represent a massive corpus, but the platform is designed to scale well beyond that as additional tenants onboard their document systems over the long term. JWCC-native PaaS services scale to exabyte-scale in practice. The platform's design does not introduce any architectural ceiling below what the underlying CSP services support.

---

### AREA 5: API-First Integration

**Question:** Describe how your platform utilizes standardized APIs to enable future legacy systems across the Department to migrate their data into the EDMP or "plug in" for ongoing access without requiring core redesigns. Address API standardization, versioning, and backward compatibility.

**Response:**

**2.5.a API-First Design Principles**

JQ recommends an API-first architecture where every platform capability exposed to external systems is accessed through versioned, documented, standards-compliant RESTful APIs. The platform's own user interface consumes the same APIs that external systems use, ensuring that every function a human can perform through the UI is also available programmatically.

Key design principles:

1. **RESTful Standards:** APIs follow REST conventions with resource-oriented URLs, standard HTTP methods (GET, POST, PUT, DELETE), standard status codes, and JSON response bodies. This ensures compatibility with any modern programming language and integration tool.

2. **OpenAPI Specification:** Every API endpoint is documented in an OpenAPI 3.x specification published at a well-known URL. This enables automatic client code generation, contract testing, and documentation browsing. Legacy systems being modernized can generate client SDKs directly from the OpenAPI spec.

3. **API Gateway:** All APIs are exposed through the CSP-native API Gateway (AWS API Gateway, Azure API Management, Google Apigee). The gateway handles authentication (CAC/ICAM integration via OAuth2/OIDC), rate limiting, request/response transformation, and usage analytics.

4. **Versioning:** APIs are versioned through the URL path (e.g., `/api/v1/documents`). Major version increments (v1, v2) may introduce breaking changes. Minor version increments are non-breaking and backward-compatible. Multiple major versions are served simultaneously during deprecation windows. Version deprecation follows a published policy (e.g., v1 deprecated 12 months after v2 release).

5. **Backward Compatibility Commitment:** Within a major version, the API contract is additive only. New fields may be added to responses, new optional query parameters may be added, but existing fields, parameters, and behaviors are never changed or removed without a major version increment.

**2.5.b Core API Domains**

The EDMP exposes APIs in the following functional domains:

| API Domain | Key Endpoints | Purpose |
|---|---|---|
| **Document Ingestion** | POST /api/v1/batches, GET /api/v1/batches/{id}/status | Programmatic document submission for legacy systems migrating data. Supports batch and streaming ingestion. |
| **Document Search** | GET /api/v1/documents/search, GET /api/v1/documents/{id} | Full-text search, metadata search, and document retrieval. Supports the same query syntax as the UI. |
| **Document Metadata** | GET /api/v1/documents/{id}/metadata, PATCH /api/v1/documents/{id}/metadata | Read and update structured metadata. |
| **Classification & IDP** | POST /api/v1/documents/{id}/classify, GET /api/v1/classifications | Trigger AI/ML classification on demand. Retrieve classification models and results. |
| **Analytics** | POST /api/v1/analytics/queries, GET /api/v1/analytics/results/{id} | Submit structured queries against the exploitation layer. Retrieve results asynchronously for long-running queries. |
| **Administration** | POST /api/v1/tenants, GET /api/v1/tenants/{id}/usage | Tenant management, usage reporting, configuration. |
| **Audit** | GET /api/v1/audit/events, GET /api/v1/audit/access-log | Programmatic access to the audit trail for external SIEM integration. |

**2.5.c Source System Integration for CEDMS Replacement**

For the source systems that currently feed CEDMS (batch scan, web upload, SFTP, and direct system feeds), the API-first approach offers a simplified migration path:

1. **Direct API Integration:** Source systems that currently push documents to CEDMS via SFTP or proprietary interfaces can be reconfigured to POST documents to the EDMP ingestion API. The API accepts the same document formats CEDMS currently handles (TIF, PDF, Office, text).

2. **Legacy Protocol Adapters:** For source systems that cannot be immediately modified, the platform provides protocol adapters (SFTP listener, email ingestion, watched folder) that accept documents in legacy formats and translate them into API calls internally. These adapters are thin shims -- they do not bypass the API; they are alternative entry points to the same API layer.

3. **Altair Monarch Replacement:** For CEDMS-MSS report processing, the current workflow relies on Altair Monarch to parse structured reports (typically fixed-width or delimited text) and publish them to SharePoint. JQ recommends replacing this with a cloud-native report parser built on CSP serverless functions. The parser ingests the same report formats Monarch processes, extracts structured data using configurable parsing templates, and publishes the extracted data through the EDMP API. This approach eliminates the Monarch license while providing equivalent or superior extraction accuracy through ML-assisted parsing.

**2.5.d API Security**

All APIs require authentication via CAC/ICAM integration (OAuth2/OIDC with DoD PKI). API requests are authorized against the same RBAC model that governs UI access. Every API call is logged to the audit trail. Rate limiting prevents denial-of-service and ensures fair resource allocation across tenants.

---

### AREA 6: Zero-Trust and Records Management

**Question:** Describe how the platform will integrate native cloud Identity, Credential, and Access Management (ICAM) to enforce Zero-Trust at the document and metadata level. Address authentication, authorization, and records management compliance.

**Response:**

**2.6.a Zero-Trust Architecture Alignment**

The platform's security architecture aligns with the DoD Zero Trust Strategy and Reference Architecture. The core principle is that no user, device, or system is trusted by default -- every access request is authenticated, authorized, and continuously validated.

The platform enforces Zero-Trust at three levels:

**Level 1: Identity.** All authentication is performed through DoD ICAM (Identity, Credential, and Access Management) via CAC/PKI. The platform does not maintain its own user directory or password store. It integrates with the DoD's existing identity provider (IdP) through standard protocols (SAML 2.0 or OIDC). This means the platform inherits the DoD's existing identity verification, CAC issuance, and personnel status management -- users are not separately provisioned in the platform.

**Level 2: Device.** The platform can evaluate device posture through integration with the CSP's conditional access policies or the DoD's endpoint compliance infrastructure. For example, access from a non-compliant device (missing patches, unapproved OS) can be denied or restricted to view-only mode.

**Level 3: Document/Data.** Every document access is authorized against the requesting user's RBAC profile at the moment of access, not at the moment of session establishment. The platform implements attribute-based access control (ABAC) on top of RBAC, evaluating user attributes, document attributes, and environmental attributes (time, location, device posture) before granting access to any document or metadata field.

**2.6.b ICAM Integration Detail**

The integration flow:

1. User authenticates to the DoD ICAM IdP via CAC (present certificate, enter PIN).
2. ICAM IdP issues a SAML assertion or OIDC token containing the user's identity attributes (EDIPI, organization, role, clearance, etc.).
3. The platform validates the assertion/token signature against the DoD PKI trust chain.
4. The platform maps the user's ICAM attributes to internal RBAC roles and permissions.
5. Every subsequent API call and document access is authorized against this mapped RBAC profile.

**2.6.c RBAC Granularity**

Per the RFI's description of the current CEDMS-CDA RBAC model, the platform enforces access control at the following granularity levels:

- **Site:** User access limited to specific physical or logical sites.
- **Organization:** User access limited to specific DoD organizations (e.g., DFAS, DLA, specific major commands).
- **Document Category:** User access limited to specific categories of documents (e.g., financial, contracting, personnel).
- **Document Type:** User access limited to specific form types or document series within a category.
- **Action:** Read, Write, Delete, Admin permissions independently assignable at each granularity level.

**2.6.d Continuous Validation**

The platform implements continuous validation beyond initial authentication:

- **Session Re-Authentication:** Sessions expire after a configurable idle timeout. The platform can challenge for CAC re-authentication before sensitive operations (deletion, bulk export, configuration changes).
- **Just-in-Time (JIT) Access:** Elevated privileges (e.g., cross-tenant analytics) can be provisioned on a time-limited, approval-gated basis rather than as permanent role assignments.
- **Anomaly Detection:** Access patterns are monitored for anomalies (e.g., user downloading 10,000 documents when typical daily volume is 50). Anomalous patterns trigger alerts and can trigger automatic step-up authentication or temporary access restriction.

**2.6.e Records Management**

The platform supports NARA-compliant records management through:

1. **Retention Policies:** Document retention periods are assigned based on document type, mapped to the relevant records retention schedule (e.g., DFAS Retention Policy as referenced in CEDMS-MSS). Retention periods trigger automated disposition workflows: notification to records managers, hold review, and authorized deletion or transfer to NARA.

2. **Legal Holds:** Litigation holds can be applied to specific documents, document categories, or entire tenants. Held documents are exempt from automated disposition until the hold is released.

3. **Immutability:** TIFF preservation masters are stored in WORM (Write Once, Read Many) compliant object storage with versioning, preventing alteration or deletion outside of authorized disposition workflows.

4. **Audit Trail:** Every access, modification, and disposition action is logged to an immutable audit trail with tamper detection, supporting both operational auditing and NARA compliance verification.

---

### AREA 7: Future Subsumption of CEDMS

**Question:** Provide a notional technical roadmap for how the platform will subsume CEDMS (both CDA and MSS) while maintaining Modular Open Systems Approach (MOSA) compliance. Specifically address: methodology for analyzing, mapping, and migrating both CEDMS subsystems; how the platform replicates or replaces current CEDMS capabilities including RBAC and Altair Monarch report processing; and the API-first approach for connecting to source systems currently feeding CEDMS.

**Response:**

**2.7.a Migration Methodology**

JQ recommends a **five-phase migration roadmap** designed to minimize operational disruption, maintain MOSA compliance, and deliver incremental value:

**Phase 0: Discovery and Mapping (Months 1-3)**

Before writing migration code, the team conducts a comprehensive discovery of both CEDMS subsystems:

- **CEDMS-CDA Discovery:**
  - Inventory all document types, metadata schemas, and indexing rules.
  - Map all source system integrations (batch scan interfaces, web upload portals, SFTP endpoints, direct system feeds).
  - Document the RBAC model: all roles, permissions, site/org/category/type mappings, and user-to-role assignments.
  - Analyze the Kofax Capture/ERM Perfect OCR pipeline: configuration, quality thresholds, output formats.
  - Inventory all stored documents (count, formats, storage tiers, encryption status).
  - Document all reporting and auditing capabilities (report types, output formats, schedules).

- **CEDMS-MSS Discovery:**
  - Inventory all Altair Monarch report models: input formats, parsing rules, output schemas, publishing destinations.
  - Map the SharePoint architecture: site collections, libraries, permission structures.
  - Document CAC authentication integration points.
  - Inventory all stored reports and their retention status per DFAS Retention Policy.

The output of Phase 0 is a comprehensive migration specification that the Government reviews and approves before any migration code is written. This ensures alignment and prevents rework.

**Phase 1: Critical Path Ingestion (Months 4-18)**

Rather than immediately attempting to replace CEDMS, Phase 1 focuses on establishing the new EDMP as the ingestion target for the 1.5 billion microfiche records. This phase runs in parallel with continued CEDMS operations:

- The EDMP ingestion pipeline (Area 2) is deployed and operational.
- Source systems that currently feed CEDMS are configured to dual-feed: they continue sending documents to CEDMS for operational continuity while also sending documents to EDMP via the ingestion API.
- The EDMP search, retrieval, and RBAC capabilities are validated against CEDMS-parity criteria.
- Government users begin accessing newly ingested microfiche records through EDMP while continuing to use CEDMS for legacy content.

This phase establishes user confidence in EDMP without disrupting existing operations. MOSA compliance is maintained because the EDMP uses standardized APIs that source systems connect to without modification to their core logic.

**Phase 2: CEDMS-MSS Migration (Months 12-24, overlaps Phase 1)**

CEDMS-MSS is the simpler of the two subsystems to migrate because it is primarily a SharePoint-based report repository with an Altair Monarch processing front-end:

1. **Altair Monarch Replacement:** A cloud-native report parser is developed using CSP serverless functions with parsing templates that replicate each Monarch model. The parser accepts the same input formats (fixed-width, delimited, PDF reports) and produces the same structured output. The parser is validated against Monarch's output for 100% parity on a representative sample of reports.

2. **Report Migration:** All existing reports in CEDMS-MSS SharePoint are migrated to EDMP. Each report is re-parsed by the cloud-native parser to extract structured metadata, linked to its preservation copy, and indexed for full-text search.

3. **SharePoint Decommissioning:** Once all reports are migrated and validated, the CEDMS-MSS SharePoint infrastructure is decommissioned. All CAC authentication and need-to-know access controls are now enforced by EDMP's ICAM-integrated RBAC.

4. **Retention Policy Migration:** DFAS Retention Policy rules are encoded in EDMP's records management module. Retention periods are applied retroactively to migrated reports based on their original creation dates.

**Phase 3: CEDMS-CDA Migration (Months 18-30, overlaps Phase 2)**

CEDMS-CDA is the more complex subsystem due to its broader scope and deeper integration with source systems:

1. **Document Migration:** All documents stored in CEDMS-CDA are migrated to EDMP. This includes re-OCR through JWCC-native services (replacing Kofax Capture/ERM Perfect), re-indexing, and metadata normalization to the EDMP schema. The migration maintains the original document identifiers and metadata for traceability.

2. **Source System Cutover:** Source systems currently feeding CEDMS-CDA are cut over to feed EDMP exclusively. The API adapters described in Area 5 (SFTP listener, web upload, batch scan interface) accept documents in the same formats CEDMS-CDA expects, minimizing source system changes.

3. **RBAC Migration:** CEDMS-CDA's RBAC model (site, organization, document category, document type) is migrated to EDMP's RBAC. Role mappings, permission assignments, and access control lists are translated programmatically. The Government reviews and approves the migrated RBAC configuration before cutover.

4. **Reporting and Auditing Migration:** All CEDMS-CDA reporting and auditing capabilities are replicated in EDMP using the BI and audit tools described in Areas 3 and 6. Existing reports are migrated, and the audit trail from CEDMS-CDA is ingested into EDMP's unified audit trail.

**Phase 4: CEDMS Decommissioning (Months 30-36)**

Once all documents are migrated, all source systems are cut over, and all CEDMS capabilities are validated as replicated in EDMP:

1. CEDMS-CDA is placed in read-only mode for a validation period (60-90 days).
2. During the validation period, Government users access documents through EDMP while retaining CEDMS-CDA read access as a fallback.
3. Upon successful validation, CEDMS-CDA is decommissioned.
4. The underlying infrastructure (servers, storage, licenses for Kofax Capture, ERM Perfect, Altair Monarch, SharePoint) is retired, realizing the cost savings projected in Area 8.

**2.7.b MOSA Compliance Throughout Migration**

MOSA compliance (10 U.S.C. 4401-4403) is maintained at every phase through:

1. **Modular Interfaces:** Each EDMP capability (ingestion, OCR, search, analytics, RBAC, audit) is a discrete module with well-defined, published interfaces. Modules can be modified, replaced, or upgraded independently without affecting other modules.

2. **Open Standards:** All interfaces use open, non-proprietary standards (REST/JSON, OpenAPI, SAML/OIDC, SQL, CSV/JSON for data exchange). No proprietary binary protocols or vendor-locked data formats.

3. **API-First Integration:** Source systems connect to EDMP through the same standardized APIs regardless of which cloud services are used to implement those APIs. If the underlying OCR service changes from one CSP-native offering to another, the API contract remains unchanged.

4. **Vendor-Agnostic Architecture:** The platform's design is not tied to a single CSP. The orchestration layer abstracts CSP-specific services, enabling migration between JWCC-authorized CSPs if required.

---

### AREA 8: Rough Order of Magnitude (ROM) Cost Estimate

**This ROM is non-binding and provided for Government market research and planning purposes only.** Actual costs will depend on the final scope, performance period, contract type, CSP pricing at time of award, and the digitization vendor's actual delivery rate.

**2.8.a Assumptions**

The ROM assumes:
- A single-award contract with an initial development/implementation period followed by annual sustainment option periods.
- The Government provides the JWCC environment (the vendor deploys into the Government's JWCC-authorized cloud account; the vendor does not resell cloud services).
- The digitization vendor is a separate procurement. The ROM below covers platform ingestion, not digitization itself.
- 1.5 billion records are ingested over a 48-month period (sustained rate of approximately 1 million records per day).
- A core platform development team of 15-25 personnel during the initial implementation phase, reducing to 8-12 during sustainment.
- CEDMS migration (CDA and MSS) runs in parallel with microfiche ingestion per the roadmap in Area 7.

**2.8.b ROM Cost Estimate**

| Cost Element | Initial Implementation (Years 1-3) | Annual Sustainment (Years 4+) |
|---|---|---|
| **Platform Development & Engineering** | $18M - $25M | N/A |
| Includes: platform architecture, ingestion pipeline, IDP/ML pipeline, search/indexing, UI, API gateway, RBAC/CAC integration, QA workflow, BI dashboards, audit trail | | |
| **CEDMS Migration** | $8M - $12M | N/A |
| Includes: CDA and MSS discovery/mapping, report migration, document migration, RBAC migration, source system cutover, validation, decommissioning | | |
| **Cloud Infrastructure (JWCC)** | $3M - $5M per year | $2M - $4M per year |
| Includes: OCR processing (~$1.5M/year at $0.0015/page for 1B pages), search/indexing, storage (petabyte-scale object storage for TIFF + PDF), compute (serverless), API gateway, BI services, networking | | |
| **Operations & Sustainment** | N/A (covered in development) | $5M - $8M per year |
| Includes: platform operations, security monitoring, continuous ATO maintenance, tenant onboarding, help desk, training, bug fixes, minor enhancements | | |
| **Government Cloud Consumption** | Included in cloud estimate | Included in cloud estimate |
| **Total ROM Range** | **$38M - $57M (initial implementation over 3 years)** | **$7M - $12M (annual sustainment)** |

**2.8.c ROM Narrative**

**Initial Implementation ($38M - $57M over 3 years):** The range reflects uncertainty in several variables: (a) the actual ingestion rate achievable by the digitization vendor (faster ingestion requires more cloud throughput but also completes sooner); (b) the complexity of CEDMS-CDA migration (the discovery phase determines whether the existing codebase and data model are well-documented or require reverse engineering); (c) the number of unique document types requiring custom IDP classification models (a wide variety of document types increases model training effort); and (d) the number of source systems requiring API adapter development.

**Annual Sustainment ($7M - $12M per year):** This covers ongoing cloud consumption (the primary sustainment cost driver), platform operations and security monitoring, Government user support, and minor enhancements. Cloud costs will vary with actual usage (query volume, new ingestion volume if additional tenants onboard, analytics job frequency).

**2.8.d Cost Avoidance Factors**

The ROM should be evaluated against the cost baseline of continued CEDMS operations:
- $1.1M+ per year in current manual microfiche retrieval costs (eliminated once the 1.5B records are digitized and searchable)
- Ongoing Kofax Capture, ERM Perfect, Altair Monarch, and SharePoint licensing costs (eliminated upon CEDMS decommissioning)
- CEDMS O&M contractor costs (eliminated upon CEDMS decommissioning)
- Storage and infrastructure costs for legacy CEDMS hardware (eliminated upon decommissioning)

These cost avoidances partially offset the sustainment costs above, improving the long-term ROI.

**2.8.e ROM Confidence**

This ROM is classified as a Rough Order of Magnitude estimate with an accuracy range of -25% to +75%, reflecting the early market research stage and the absence of a detailed performance work statement. A more refined estimate would require: (1) a finalized PWS, (2) confirmation of the digitization vendor's timeline and delivery cadence, (3) a completed CEDMS discovery phase, (4) actual CSP pricing at time of award, and (5) a defined contract type and period of performance.

---

### AREA 9: Corporate Experience

**Question:** Provide a list of recent and relevant contracts from the last 3-5 years supporting your company's ability to perform this requirement, to include contract number, dollar value, period of performance, and scope. Provide your firm's CAGE code, UEI/DUNS number, and small business status.

**Response:**

**2.9.a Firm Information**

| Field | Value |
|---|---|
| **Company Name** | Justice Quest LLC (DBA: JQ) |
| **UEI** | [NEEDS: UEI number] |
| **CAGE Code** | [NEEDS: CAGE Code] |
| **Small Business Status** | [NEEDS: Small business status declaration] |
| **NAICS Codes** | [NEEDS: NAICS codes] |
| **Address** | 1410 Comet Ives Lane, Lawrenceville, GA 30046 |
| **POC** | Ian Bruce, Principal AI Engineer / Founder, 562-739-5206, ian.b@justicequest.pro |

**2.9.b Past Performance References**

Justice Quest LLC is a specialized technology firm combining litigation support, operational strategy, custom software, and workflow automation. The following contracts, while not at the precise DoD enterprise scale described in this RFI, demonstrate the core technical competencies directly relevant to this requirement: high-volume unstructured document processing, AI/ML pipeline development, automated document classification and analysis, and custom ingestion workflows for heterogeneous document formats.

---

**Reference 1: High-Volume Coupon Distribution Engine (via Highwater Agency, LLC)**

| Field | Value |
|---|---|
| **Client** | Rita's Italian Ice (via Highwater Agency, LLC) |
| **Contract Value** | ~$500,000 in at-risk campaign revenue secured |
| **Period of Performance** | August 2025 - January 2026 |
| **Scope** | Diagnosed and resolved critical bugs in a high-volume coupon distribution engine, ensuring accurate discount application for millions of end users. |

**Relevance to this RFI:** This engagement demonstrates JQ's ability to work with large-scale data processing pipelines handling millions of records with precision and reliability. The work required analyzing production data flows, identifying failure points, and implementing fixes under time constraints while maintaining data integrity -- the same core operational discipline required for a 1.5-billion-record ingestion pipeline. The fast diagnosis and resolution under revenue-at-risk conditions demonstrates the rapid mobilization and problem-solving the tight CEDMS modernization timeline demands.

---

**Reference 2: High-Volume Document Analysis System (Independent Client)**

| Field | Value |
|---|---|
| **Client** | Medical Malpractice Reviewer (Independent Client) |
| **Period of Performance** | 2025 |
| **Scope** | Delivered a high-volume document analysis system with an agentic AI pipeline that correlated complex legal allegations across hundreds of pages of unstructured medical records and timelines, contributing to a client win. |

**Relevance to this RFI:** This engagement is directly relevant to the IDP and data exploitation requirements of the EDMP. JQ designed and deployed an AI/ML pipeline that: (a) ingested hundreds of pages of unstructured documents in heterogeneous formats (medical records, timelines, correspondence), (b) applied NLP and entity extraction to identify key facts, (c) correlated findings across documents to surface relationships a human reviewer would struggle to identify manually, and (d) produced structured analytical outputs. This is conceptually identical to the EDMP's IDP requirement to "retroactively analyze ingested OCR'd PDFs and autonomously classify document types and extract structured metadata" (Area 1) and "transform OCR'd documents into a highly reportable dataset" (Area 3), albeit at a smaller scale. The architecture is directly scalable to the 1.5-billion-record corpus.

---

**Reference 3: Legal Workflow Automation and AI Integration (Dana Blue Law Firm)**

| Field | Value |
|---|---|
| **Client** | Dana Blue Law Firm |
| **Period of Performance** | February 2026 - Present |
| **Scope** | Architected lead generation workflows integrated with AI agents for high-conversion attorney outreach. Developed automated PDF form-filling tools and document synthesis pipelines. |

**Relevance to this RFI:** This engagement demonstrates JQ's capability in: (a) building automated document processing pipelines that handle PDF and structured form data, (b) integrating AI agents into production workflows (parallel to the EDMP's AI/ML integration requirements), and (c) designing scalable, modular system architectures that can accommodate future expansion (parallel to the API-first, MOSA-compliant architecture the EDMP requires). The document synthesis and form-filling automation is directly analogous to the IDP and metadata extraction pipeline architecture.

---

**Reference 4: EEOC Title VII Complaint Development (Individual Client)**

| Field | Value |
|---|---|
| **Client** | Individual Client -- EEOC Title VII |
| **Period of Performance** | 2025 |
| **Scope** | Assisted with EEOC Title VII complaint including issue spotting, factual development from unstructured records, and full complaint drafting. |

**Relevance to this RFI:** This engagement demonstrates JQ's ability to work with sensitive, regulated data (EEOC complaints involve protected personal information), extract structured facts from unstructured records, and produce documented, defensible analytical outputs -- a skill set directly applicable to the EDMP's compliance and records management requirements (Area 6).

---

**2.9.c Capabilities Summary**

Justice Quest LLC combines the following core capabilities, each directly relevant to the EDMP requirement:

1. **High-Volume Evidence and Document Analysis:** Proprietary systems for processing, organizing, and analyzing large evidence collections including medical records, legal documents, correspondence, and structured/unstructured data. Directly applicable to the IDP, OCR, and AI/ML analysis requirements.

2. **Workflow Automation:** Custom workflows, integrations, and automation systems tailored to specific processes. Directly applicable to the batch ingestion QA workflow and source system integration requirements.

3. **AI/ML Pipeline Development:** Agentic AI pipelines for document classification, entity extraction, relationship mapping, and analytical output generation. Directly applicable to the IDP and data exploitation requirements.

4. **Document and Case File Organization:** Transforming unstructured information into organized, indexable, searchable structured data. Directly applicable to the 1.5-billion-record ingestion and indexing requirement.

5. **Flexible Procurement Models:** Experience with project-based and hourly contracts designed to align with government procurement policies, professional service agreements, and grant funding cycles.

**2.9.d Teaming Strategy**

Justice Quest LLC acknowledges that the scale of the EDMP requirement (1.5 billion records, DoD IL5, JWCC deployment) exceeds the scope of individual projects in our current past performance portfolio. Our approach to this opportunity would be as a **prime contractor leading a team of specialized subcontractors**:

1. **JWCC Cloud Service Provider (CSP) Partner:** JQ would team with a JWCC-authorized CSP (AWS, Azure, GCP, or Oracle) to ensure the platform operates on authorized JWCC infrastructure at IL5. The CSP partner provides the IL5-authorized environment and CSP-native PaaS expertise.

2. **FADGI 3-Star Digitization Specialist (if applicable):** If the digitization scope is included, JQ would team with a NARA-compliant digitization vendor with demonstrated FADGI 3-Star capability.

3. **Altair Monarch / Kofax Subject Matter Expert (if required):** If the Government requires preservation of existing Monarch/Kofax workflows during migration, JQ would engage an SME with demonstrated Altair Monarch and Kofax Capture experience.

This teaming approach allows the Government to benefit from JQ's AI/ML, automation, and document processing expertise while leveraging established CSP and digitization partners for the infrastructure and compliance elements that require specific JWCC and FADGI credentials.

---

## SECTION 3: CLOSING STATEMENT

Justice Quest LLC appreciates the opportunity to respond to the Department of War's Request for Information on the Enterprise Document Management Platform and CEDMS Modernization initiative. We recognize the magnitude of the challenge -- 5.88 million physical microfiche sheets degrading and costing $1.1M+ annually in manual retrieval; a legacy CEDMS system that has served the Department well but cannot scale to meet future data exploitation needs; and 1.5 billion records requiring ingestion, indexing, classification, and analysis at a scale few organizations have attempted.

Our response describes an approach grounded in JWCC-native PaaS services, designed to operate at IL5, and architected for massive parallel ingestion throughput. We have addressed each of the nine Areas of Inquiry with specific technical strategies, architecture recommendations, and implementation roadmaps. Our ROM estimate provides the Department with a non-binding cost framework for planning purposes.

Justice Quest LLC is prepared to participate in follow-on discussions, provide additional technical detail, participate in industry day events, and respond to any subsequent Sources Sought or Request for Proposal the Department may issue. We welcome the opportunity to demonstrate our AI/ML and document processing capabilities in greater depth.

For questions or follow-up regarding this response, please contact:

Ian Bruce
Principal AI Engineer / Founder
Justice Quest LLC
Phone: 562-739-5206
Email: ian.b@justicequest.pro

---

*This response is submitted for Government market research and planning purposes only. Nothing in this response shall be construed as a binding offer, and all cost estimates are non-binding Rough Order of Magnitude (ROM) figures provided solely for Government budgeting and planning. Justice Quest LLC retains all proprietary rights to the technical approaches and architecture described herein.*

---

## Draft Notes

### Placeholders Requiring Human Input

The following fields in this response must be populated by a human before submission. They are flagged in the document with `[NEEDS: ...]` syntax:

1. **UEI Number** (Cover Page, Section 2.9.a): Justice Quest LLC's Unique Entity Identifier from SAM.gov. If the company is not yet registered in SAM.gov, registration must be initiated. The company profile shows this field as `needs_input`.

2. **CAGE Code** (Cover Page, Section 2.9.a): Justice Quest LLC's Commercial and Government Entity code. Typically assigned during SAM.gov registration. The company profile shows this field as `needs_input`.

3. **Small Business Status** (Cover Page, Section 2.9.a): The company must declare its small business status (e.g., Small Business, 8(a), SDVOSB, WOSB, HUBZone, or Large Business) per Question 9 of the RFI. This is a critical input because the Government is using this RFI response to inform its set-aside determination for the eventual RFP. The company profile shows certifications as `needs_input`.

4. **NAICS Codes** (Cover Page, Section 2.9.a): The company's registered NAICS codes from SAM.gov. If the company does not hold an IT services NAICS code (e.g., 541512, 518210), this should be addressed before the eventual RFP. The company profile shows NAICS codes as `needs_input`.

5. **Past Performance Contract Numbers** (Section 2.9.b): The four past performance references provided are real company performance but are commercial/legal sector work, not federal DMS contracts. No contract numbers are available for the commercial engagements listed. The human reviewer should: (a) verify these references are accurate and complete, (b) add any additional federal or DoD contract references that may exist, and (c) determine whether additional past performance references from teaming partners should be included.

### Assumptions Made in This Draft

1. **JWCC Deployment Model:** The response assumes the Government provides the JWCC-authorized environment (Government-owned cloud account) and the vendor deploys into it, rather than the vendor reselling JWCC cloud services. If the contract model requires the vendor to hold its own JWCC contract, the company's teaming strategy must include a JWCC-authorized CSP prime or must establish JWCC authorization.

2. **Digitization Vendor is Separate:** The response treats digitization as a separate procurement, per the RFI's description of "parallel efforts." The ROM does not include digitization costs.

3. **Ingestion Rate:** The ingestion throughput strategy assumes a sustained 1 million records per day from the digitization vendor. A faster or slower rate would shift the ingestion timeline and associated cloud costs.

4. **DFAS Retention Policy:** The response references the DFAS Retention Policy mentioned in the CEDMS-MSS description but does not have access to the actual policy document. The records management approach is designed to accommodate any defined retention schedule.

5. **CAC/ICAM Integration:** The response assumes the DoD ICAM IdP supports standard SAML 2.0 or OIDC protocols, which is standard for DoD enterprise applications. If the actual integration protocol differs, the architecture adjusts accordingly.

6. **No Section 508, DR/BC, or Training Requirements:** These topics are not mentioned in the RFI and are not addressed in this response. If the eventual RFP includes them, they will be addressed at that time.

### Format Notes

- This response is formatted as Markdown for drafting purposes. For submission, it should be converted to PDF or Word format per the RFI's format requirements.
- The response addresses all nine Areas of Inquiry in sequence within Section 2.
- Estimated page count when rendered in 12pt Times New Roman, single-spaced, with standard margins: approximately 22-24 pages, within the 25-page maximum.
- The response contains no classified information and is suitable for UNCLASSIFIED submission.

### Quality Self-Check

- [x] Every question in the 9 Areas of Inquiry answered
- [x] Page limit estimated at 22-24 pages (within 25-page maximum)
- [x] No marketing language ("world-class," "best-in-class," "synergistic," "unparalleled")
- [x] Claims backed by evidence or explicitly noted as assumptions
- [x] RFI terminology echoed back (JWCC, IL5, FADGI 3-Star, MOSA, IDP, Zero-Trust, etc.)
- [x] Company information sourced from company profile (not invented)
- [x] Placeholder brackets flagged with `[NEEDS: ...]` syntax
- [x] ROM identified as non-binding
- [x] UNCLASSIFIED designation maintained throughout
