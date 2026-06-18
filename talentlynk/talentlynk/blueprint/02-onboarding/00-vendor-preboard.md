# Vendor Preboard — Zero-Touch Data Gathering

## Purpose
Before a prospective vendor even sees a form, we pull every piece of publicly available information about their business from the internet. The vendor's onboarding experience becomes: "We looked you up. Confirm what's correct, fix what's not, fill in the few things we couldn't find." This is the onboarding conversion moat — minimal admin burden.

## The Concept

```
Traditional onboarding: Vendor fills in 30 fields from scratch.
TalentNyk preboard:    Vendor enters Name + Website → we return a pre-filled profile.
                       They confirm/correct. They add pricing + licenses. Done.
```

## The Input (All We Ask Upfront)

| Field | Required? | Purpose |
|-------|:---------:|---------|
| Company name | Yes | Seed for all searches |
| Website URL | No (but high value) | Goldmine — scrape everything |
| City + State | No (helps disambiguation) | Narrows searches, especially for common names |
| Phone number | No | Google Business lookup, SAM.gov cross-reference |

Every field the vendor doesn't enter here, we try to find ourselves.

## What We Can Pull & Where From

### Tier 1: High Confidence, Fully Automated

| Data Point | Source | Method |
|------------|--------|--------|
| Logo | Website (favicon, header image, meta tags) | Scrape `<link rel="icon">`, `<meta property="og:image">`, common logo paths |
| Business description | Website (About page, meta description, homepage hero) | Scrape + LLM extract: "Summarize what this business does in 2 sentences" |
| Services offered | Website (services page, navigation, homepage) | Scrape + LLM extract → feeds NAICS auto-classifier |
| Phone number | Website (header, footer, contact page) | Regex patterns, structured data |
| Email address | Website (contact page, footer) | Regex, `mailto:` links |
| Physical address | Website (contact page, footer), Google Maps API | Regex + Places API |
| Social media links | Website (footer, social icons) | Scrape hrefs matching known social domains |
| Employee count (range) | LinkedIn company page | Scrape public page or LinkedIn API |
| Years in business | Website (About page - "since 1985", "30 years"), state SOS | Regex patterns + SOS lookup |
| Entity type (LLC, Inc, etc.) | State Secretary of State business search | Per-state scraping or OpenCorporates API |
| Formation date | State Secretary of State | Same as above |
| Good standing status | State Secretary of State | Same as above |

### Tier 2: Medium Confidence, Needs Confirmation

| Data Point | Source | Method |
|------------|--------|--------|
| Service area | Website (service area page), Google Business Profile | LLM extraction + Places API coverage check |
| Past clients/projects | Website (portfolio, case studies, testimonials), Yelp reviews | LLM extract project descriptions → feeds past performance DB |
| Review sentiment & volume | Google Business Profile, Yelp, HomeAdvisor, Angi, BBB | Scrape ratings, review count, sentiment |
| Photos of work | Website portfolio, Instagram, Google Business Profile photos | Download + tag by service type |
| NAICS code guesses | Service description → NAICS auto-classifier | LLM embedding match |
| Insurance claims hint | Website ("fully insured", "licensed and insured") | Keyword detection — flags existence but not specifics |
| License mentions | Website ("License #XYZ", "Licensed in GA"), state license lookup | Regex + per-state license DB lookup |
| Minority/Woman-owned claims | Website ("woman-owned", "veteran-owned"), third-party directories | Keyword + directory cross-reference |

### Tier 3: Federal-Specific (Only If Vendor Does Government Work)

| Data Point | Source | Method |
|------------|--------|--------|
| UEI | SAM.gov | Search by company name |
| CAGE code | SAM.gov | Returned with UEI lookup |
| NAICS on SAM | SAM.gov | Returned with UEI lookup |
| Socioeconomic certifications | SAM.gov, SBA certify | UEI-dependent |
| Past federal contracts | FPDS (Federal Procurement Data System) | Search by company name or UEI |
| CPARS ratings | CPARS (if access available) | UEI-dependent |
| Federal exclusions/debarment | SAM.gov exclusions | Name search |

## The Preboard Pipeline

```
[Vendor enters: Name, Website (optional)]
              │
              ▼
[Phase 1: Concurrent Web Scraping]
    ├── Scrape website: all pages, extract text, images, structured data
    ├── Google Business Profile: Places API lookup
    ├── State SOS: name match → entity type, formation date, status
    ├── Social: LinkedIn company page, Instagram (optional)
    ├── Review sites: Google rating, Yelp, HomeAdvisor
    └── SAM.gov: name search → UEI, NAICS, certs (if found)
              │
              ▼
[Phase 2: LLM Synthesis]
    ├── From all scraped text → generate business summary, service list, capability tags
    ├── Extract past performance hints from testimonials/case studies
    ├── Flag: "This appears to be a woman-owned roofing contractor serving metro Atlanta"
    └── Confidence score per extracted field
              │
              ▼
[Phase 3: Profile Assembly]
    ├── Pre-populate all fields with what we found
    ├── Mark each field: [HIGH confidence / MEDIUM — please confirm / NOT FOUND — please enter]
    └── Vendor reviews, corrects, adds the unfindable (pricing, licenses, insurance)
```

## The Vendor Experience

The vendor receives a link:
> "Hi John — we've put together a preliminary profile for Atlanta Commercial Landscaping based on your website, Google listing, and public records. Can you take 5 minutes to confirm everything looks right and fill in a few gaps?"

They see:
- **Green checkmark fields:** Pre-filled, high confidence. "Looks right? Just leave it."
- **Yellow caution fields:** Pre-filled, but we're not sure. "Is this correct? Confirm or fix."
- **Empty fields:** We couldn't find it. "Please add your pricing, license details, and insurance."

They confirm profile → sign MOU + NDA → onboarded. Target: **<10 minutes of vendor effort.**

## What We NEVER Auto-Fill (Legal/Trust Boundaries)

- **Signatures** — obviously
- **Pricing** — proprietary, must come from vendor
- **Insurance specifics** — policy numbers, limits must be verified by vendor
- **License numbers** — we can hint ("we noticed you mention a pesticide applicator license"), but the vendor must provide the actual number and upload the document
- **Banking details** — must come directly from vendor with verification
- **SBA certification claims** — we can flag what we found on SAM.gov, but vendor must attest

## Technical Notes

### Website Scraping
- Fire-and-forget: async job. Vendor doesn't wait for scraping to complete.
- Respect robots.txt? For onboarding purposes with vendor consent — arguably not required (we're acting on their behalf), but respect it as a courtesy.
- Rate limiting: be a good citizen. Don't hammer their server.
- Fallback: if scraping fails (JS-heavy SPA, bot protection), flag for manual entry.

### LLM Extraction
- Feed scraped text to LLM with structured extraction prompts
- Return JSON with extracted fields + confidence scores
- "Extract the company's physical address from this webpage text. Return null if not found."
- "List the services this business offers, based on their website. Return as an array of strings."

### De-duplication vs. Existing Profiles
- Before creating: check if this company already exists in our database
- Fuzzy name + address matching to prevent duplicates
- "We found a profile for a similar company. Is this the same business?"

## Dependencies
- [[01-vendor-profile-schema]] — the target we're pre-filling
- [[03-naics-auto-classifier]] — fed by the service descriptions we extract
- [[../13-integrations/sam-gov-api]] — for federal data cross-reference
- Google Places API (not yet spec'd) — for Business Profile and address data
- State SOS scraping infrastructure (not yet spec'd)

## Key Rules & Compliance
- Public data only — no pretexting, no fake accounts, no private databases without consent
- Vendor owns their data — they can reject any pre-filled field
- If vendor is already in our network, treat as profile update, not duplicate creation
- Data retention: if vendor abandons onboarding, delete scraped data after X days
- Privacy: scraping is done on TalentNyk's servers; vendor's website sees normal traffic

## Open Questions
- Scraping infrastructure: AWS Lambda functions? Dedicated scraping service (ScrapingBee, Apify)?
- State SOS lookup: build per-state, or use aggregator (OpenCorporates API)?
- Should we show the vendor "where we found this" for each field? (Builds trust)
- Preboard for vendors WITH a UEI vs. WITHOUT — different data paths. Should UEI be the first question after name?
- How to handle vendors who are NOT online (no website, no Google listing) — common in trades?
