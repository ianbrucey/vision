# Federal IT & Software Sourcing Guide

Based on my research, here is a breakdown of how to programmatically access federal data, identify IT opportunities outside the standard 541 family, and use granular keywords to find Sources Sought Notices (SSNs).

## 1. USAspending.gov vs SAM.gov API Access

First, a quick clarification: **USAspending.gov is for historical award data, not active opportunities.** To find active Sources Sought Notices or RFIs, you actually need the **SAM.gov API** (specifically the Contract Opportunities API). 

### USAspending.gov API (Historical Spending & Awards)
- **Base URL:** `https://api.usaspending.gov`
- **Auth:** No API key required.
- **Key Endpoint:** `/api/v2/search/spending_by_award/` allows complex filtering by NAICS, agency, and recipient to see what *has already been awarded*. This is great for competitive intelligence.

### SAM.gov API (Active Solicitations & SSNs)
- **Base URL:** `https://api.sam.gov/opportunities/v2/search`
- **Auth:** Requires a free API key from [api.data.gov](https://api.data.gov/).
- **Usage:** You can query this endpoint with `noticeType=s` (Sources Sought) or `noticeType=o` (Special Notice / RFI) combined with specific NAICS codes or keywords to pull active notices automatically.

## 2. IT / Software NAICS Codes (Outside the 541 Family)

While 541511 (Custom Computer Programming Services) and 541512 (Computer Systems Design) are the most common, software and IT work is frequently solicited under these non-541 codes. Add these to your search filters:

### Information & Publishing (51 Family)
- **513210 (formerly 511210): Software Publishers** — Used when the government wants to buy COTS (Commercial Off-The-Shelf) software, SaaS subscriptions, or enterprise licenses rather than custom development.
- **518210: Computing Infrastructure, Data Processing, and Web Hosting** — Used for AWS/cloud hosting, data center services, and managed infrastructure.

### Manufacturing & Distribution (33 and 42 Families)
- **334610: Manufacturing and Reproducing Magnetic/Optical Media** — Sometimes used for large-scale software distribution or manufacturing.
- **423430: Computer and Computer Peripheral Equipment and Software Merchant Wholesalers** — Used when the government is strictly purchasing software licenses or IT hardware through a reseller (often relevant for your Carahsoft partnership).

### Other Notable Codes
- **611420: Computer Training** — Used for IT adoption, software training, or rollout support services.
- **561110: Office Administrative Services** — Sometimes used for low-level IT helpdesk or records management tasks.
- **541611: Administrative Management and General Management Consulting Services** — (Technically 541, but non-IT) Often used for "digital transformation" or IT strategy consulting that doesn't involve actual coding.

## 3. Granular Keywords for Sourcing

Because NAICS codes can be broad, you should use granular keyword strings to filter SAM.gov opportunities down to Justice Quest LLC's specific capabilities. 

Search these exact phrases (use quotes where applicable in SAM.gov):

**For Custom Software & Modernization (CAP-01, CAP-06)**
- `"legacy modernization"`
- `"tech refresh"` OR `"technology refresh"`
- `"custom software development"`
- `Laravel` OR `PHP` OR `"Node.js"` OR `React`
- `"zero downtime migration"`

**For AI, Data & Automation (CAP-03, CAP-04, CAP-08)**
- `"artificial intelligence"` OR `"machine learning"`
- `"document processing"` OR `"OCR"`
- `"intelligent automation"` OR `"RPA"`
- `"unstructured data"`
- `"data pipeline"` OR `"data warehouse"`
- `Snowflake` OR `dbt` 

**For IT Infrastructure & Helpdesk (CAP-02, CAP-09, CAP-10)**
- `"AWS"` OR `"cloud migration"`
- `"helpdesk"` OR `"Tier 1"` OR `"Tier 2"`
- `"endpoint management"`
- `"incident response"`

**For Legal / Paralegal Operations (CAP-12)**
- `"paralegal"` OR `"legal operations"`
- `"e-discovery"` OR `"document review"`
- `"litigation support"`

> [!TIP]
> **Recommended Sourcing Strategy:** If you want to automate this, we can write a Python script that hits the SAM.gov Opportunities API daily. It can filter for `noticeType=s` (Sources Sought) and run your custom keyword list against the notice descriptions, returning only highly relevant opportunities directly into your pipeline.
