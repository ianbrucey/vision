# Request for Information (RFI): Enterprise Document Management Platform & CEDMS Modernization

**BLUF:** The Department of War (DoW) is seeking information on cloud-native, platform-as-a-service (PaaS) capabilities via the Joint Warfighting Cloud Capability (JWCC) to establish a foundational Enterprise Document Management Platform. The immediate mission is the modernization of the Corporate Electronic Document Management System (CEDMS) and the digitization of 1.5 billion legacy microfiche records. The architecture must be designed from the ground up as a multi-tenant environment capable of transforming unstructured document text into highly reportable data, and eventually subsuming future document management systems across the enterprise.

---

## 1.0 Vision, Problem, and Foundational Strategy

For several years, the Department has been challenged by a complex and fragmented landscape of legacy document management systems, creating data silos and complicating enterprise-wide reporting and auditability. The goal is to move away from these siloed, custom-coded applications and toward a standardized, cloud-native data fabric.

**The platform must be built to support:**

- **Initial Mission:** Rapid ingestion, Optical Character Recognition (OCR), and management of 1.5 billion legacy microfiche records, transforming this unstructured data into a queryable asset.

- **Mid-Term Mission (CEDMS Modernization):** Completing the CEDMS modernization effort by fully subsuming all existing CEDMS functions and serving as the primary enterprise document management system for the organization.

- **Long-Term Mission:** Serving as an extensible, multi-tenant repository capable of onboarding disparate document systems across the Department while providing unprecedented, enterprise-wide business intelligence and data exploitation capabilities.

---

## 1.1 Summary of the Modernization Initiative

**The Problem:** The core issue is the 5.88 million physical microfiche sheets which are degrading, non-compliant with NARA standards, and incur over $1.1 million in annual manual retrieval costs.

**The Vision:** The project aims to execute a full digital transformation by digitizing approximately 1.5 billion records to the stringent FADGI 3-Star standard, building a new secure IL5 cloud Document Management System (DMS), and eventually decommissioning existing systems like CEDMS to achieve significant ROI.

**The Strategy:** The project is broken into two parallel efforts:

- **Digitization:** A vendor will be contracted to scan the physical microfiche, creating both preservation-quality TIFFs and searchable PDF access copies.

- **Platform Modernization:** A new, multi-tenant cloud DMS will be built on the Joint Warfighting Cloud Capability (JWCC) infrastructure to ingest these records and serve as the foundation for future enterprise document management.

---

## 1.2 CEDMS System Overview

CEDMS includes two primary sub-systems:

- **CEDMS-CDA** (Corporate Electronic Document Management System - Custom Designed Application)
- **CEDMS-MSS** (Corporate Electronic Document Management System - Monarch SharePoint Solution)

### CEDMS-CDA

CEDMS-CDA serves as a centralized, secure archival repository for a wide range of official financial and accounting documents for the Defense Finance and Accounting Service (DFAS) and other DoD organizations. Its primary purpose is to automate the conversion of hard-copy documents into a searchable electronic format, reducing dependency on paper records.

**Core Capabilities:**

1. **Document Capture and Ingestion:** The system is capable of ingesting documents from multiple sources, including batch scanning of hard copy documents, web-based uploads, and secure file transfers (SFTP). It supports various file formats such as TIF, PDF, Microsoft Office files (Word, Excel, PowerPoint), and text files.

2. **Archival and Storage:** CEDMS-CDA provides a secure, web-based repository for the permanent storage of documents. All data at rest is protected through encryption.

3. **Document Processing:** It utilizes Optical Character Recognition (OCR) technology (Kofax Capture, ERM Perfect) to make the full text of documents searchable. This includes the ability to automatically identify and index document content.

4. **Search and Retrieval:** The system provides sophisticated search capabilities, allowing users to find documents based on specific index fields or through full-text keyword searches. It offers both a basic and an advanced search module for precise document retrieval.

5. **Access Control and Security:** Access is restricted to authorized users via Common Access Card (CAC) authentication. The system enforces a role-based access control (RBAC) model, ensuring that users can only view documents based on their assigned site, organization, document category, and document type permissions.

6. **Reporting and Auditing:** CEDMS-CDA provides a variety of reports, including statistical, productivity, access level, and log event reports. It maintains an audit trail of user and system activities.

### CEDMS-MSS

CEDMS-MSS is an electronic replacement for printed financial reports. It provides a secure, web-based application for the storage, retrieval, and management of reports for DFAS and other DoD organizations, significantly improving the timeliness of financial information and generating cost savings by eliminating paper and printing costs.

**Core Capabilities:**

1. **Report Processing and Publishing:** CEDMS-MSS receives report files from various source systems. It uses Altair Monarch to automatically process and model these reports, which are then published to secure SharePoint sites.

2. **Centralized Repository:** The system provides a single, secure, and reliable centralized repository for storing and managing a large volume of DFAS and DoD reports.

3. **Web-Based Access and Retrieval:** Authorized users can access and retrieve reports through a secure SharePoint web interface. Users can search for specific reports and display them on their local workstations for viewing.

4. **"View-Only" and User-Centric Data Manipulation:** Reports stored within CEDMS-MSS are presented as "view-only" to preserve the integrity of the original report. Any data manipulation is performed by the user on their local workstation after the report has been downloaded.

5. **Security and Access Control:** Like CEDMS-CDA, access is restricted to authorized CAC holders. The system utilizes SharePoint's robust permission model to enforce access control, ensuring users can only access reports for which they have a "need-to-know."

6. **Report Retention:** Reports are retained in accordance with DFAS Retention Policy, allowing for future viewing and auditing as required.

---

## 2.0 Information Requested from Industry

Please provide detailed responses to the following areas, focusing on how your approach creates a scalable, highly reportable, long-term foundation without relying on proprietary custom software:

| # | Area of Inquiry | Specific Questions for Industry |
|---|---|---|
| 1 | **Cloud-Native Foundation** | Detail how you leverage JWCC-native services for OCR, indexing, search, and user interface. How does this approach reduce sustainment labor and TCO compared to a custom software stack? The platform must possess Intelligent Document Processing (IDP) capabilities capable of retroactively analyzing a massive backlog of ingested, basic-OCR'd PDFs (~1.5 billion records) to autonomously classify document types and extract structured metadata fields without manual human data entry. |
| 2 | **Massive Ingestion** | Provide the technical strategy for the rapid ingestion and indexing of 1.5 billion microfiche records. Describe plan for integrating the specific deliverables from the FADGI 3-Star digitization. This includes: Automated ingestion of dual-file (TIFF/PDF) deliverables. Processing of the specific metadata manifest format (CSV/JSON) that the digitization vendor will provide. A workflow for handling the "Batch" delivery and quality control process, including how the system will support the government's QA validation process before records are accepted. Process for automatically linking the files and indexing the PDF text layer for immediate enterprise search. |
| 3 | **Data Exploitation & Reporting** | How does your solution utilize native cloud analytics (e.g., AI/ML, NLP, and native BI tools) to transform 1.5B OCRed documents into a highly reportable dataset? Detail the platform's ability to support dynamic dashboards and cross-document trend analysis. |
| 4 | **Multi-Tenant Scalability** | Describe how the architecture supports multiple tenant organizations. How is data isolation maintained at scale while utilizing shared cloud-native services? |
| 5 | **API-First Integration** | How does your design utilize standardized APIs to enable future legacy systems to migrate data or "plug in" to the platform without requiring core redesigns? |
| 6 | **Zero-Trust & Records Mgmt** | How does the solution integrate native cloud Identity, Credential, and Access Management (ICAM) to enforce Zero-Trust at the document and metadata level? |
| 7 | **Future Subsumption** | Provide a detailed notional roadmap for migrating an application like CEDMS, while maintaining MOSA compliance. Respondents should describe: Their proposed methodology for analyzing, mapping, and migrating the two distinct CEDMS sub-systems (CDA and MSS). How their platform would replicate or replace core CEDMS capabilities (e.g., role-based access based on site/org/category, report processing from Altair Monarch). How their API-first approach would specifically connect to the source systems that currently feed CEDMS. |
| 8 | **Cost Estimate (ROM)** | Provide a non-binding Rough Order of Magnitude (ROM) for planning purposes. Please break this down by: (1) Initial implementation and ingestion of the 1.5B records, and (2) Estimated annual sustainment/cloud consumption costs for the steady state. |
| 9 | **Corporate Experience** | Provide a list of recent and relevant contracts from the last 3-5 years (include contract number, dollar value, period of performance, and scope). Provide CAGE code, UEI/DUNS, and small business status. |

---

## 3.0 Submission Instructions & Disclaimer

**Disclaimer:** This Request for Information (RFI) is for market research and planning purposes only and does not constitute a solicitation, Request for Proposal (RFP), or Request for Quotation (RFQ). Information received will not be disclosed outside of the U.S. Government. A response to this RFI is not an offer and cannot be accepted by the Government to form a binding contract. The Government will not reimburse any costs associated with submitting a response to this RFI.

| Detail | Instruction |
|---|---|
| **Response Format** | White paper (PDF or Word format), maximum of 25 pages. |
| **Point of Contact** | Gerald Whitsett — Gerald.l.whitsett.civ@mail.mil |
| **Suspense Date** | June 15th, 2026 at 1pm EST |
| **Classification** | All responses must be UNCLASSIFIED. |
