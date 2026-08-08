
Alright.

So,

running through the system,

the GovCon system.

Every day

we upload

SAM notices

and um

USA Spending

.gov information

uh

into our system.

Uh, for the SAM notices, the criteria is

um

construction and facilities, and IT.

Pretty much.

Uh.

So, instead of using the API, the SAM API,

we can really just do a databank.

And then the objective will be

like get a get all the

Total Small Business stuff

from

Well, see that's the thing. I don't know if I should do Total Small Business or

Full and Open

because if I do Full and Open, that means

um

anybody can bid that's just more to add on my plate. So

I guess

I'll do a test. Maybe that maybe that'll

But okay, that's also the problem, though.

Once I do, hm, okay.

All right, so here's my concern.

Well, with the databank, you cannot filter by NAICS codes. You can just

filter by like designation

and some other stuff.

So I can't like filter by

you know, construction, and

uh facilities and IT, and all that stuff, so

maybe what I'll do, hm.

See, that's the other problem, too.

I could end up getting like 150,000 results.

So maybe I just run a few tests

first see how much I get with Total Business set-asides,

probably be somewhere around 2,000.

Full and Open most recent,

maybe

um

set a filter on response date,

see how much I get with that, and then

do a subsequent filter once we actually get it into the system.

And then with the USA Spending,

I think with that one

hm, I'm a see if I documented it already, but

I think with that one

we were trying to

Let me see.

Okay, yeah. So I we're looking for a IDIQ, MATOC,

GWAC vehicles

basically using USA Spending to look at

awards for um

for to target primes.

Um

So we know with the SAM.gov stuff,

the goal is to basically

pipeline is

import

filter

and then from the filter, then we decide

um

you know

which uh

which items we want to triage.

With the USA Spending, I'm not quite sure how that one

is going to work yet.

We're going to have to use some of this data here

to decide how it's going to work.

hm

Yeah, some of this data we already did to to figure out the

sourcing

Oh, it says it right here. Let me see. Pull IDV

vehicles in construction NAICS awards

awarded with in 1 to 3 years

identify multi-award pools

uh

build a subcontracting lead per prime

name UEI UEI vehicle ID

NAICS

for each target prime pull their active SAM.gov solicitations

to extract the

actual scope and trade

oh okay, I see.

All right, so that's the first step. Like it's basically

uh sourcing.

Once we

do the sourcing and then we kind of know the volume

that we're actually dealing with

Then we can move on, then we can figure out a strategy strategy for triage.

So

that's the first step.

# Federal Opportunity Sourcing Playbook

SAM.gov & USASpending.gov  ·  Phase 1 — Opportunity Sourcing  ·  GovCon Engine  ·  Draft v0.1 — 2026-08-03

## 1 · Purpose

Sourcing is the intake layer of the GovCon Engine. It must produce  **two pipelines** :

* **Live bid feed (SAM.gov)** — active, bid-ready federal solicitations we can chase now.
* **Subcontracting leads (USASpending.gov)**
  — awarded IDIQ / MATOC / GWAC vehicles held by primes who are obligated
  (or pressured) to buy from small-business subcontractors.

Everything downstream — triage, vendor matching, quoting, award execution — consumes what this layer produces.

## 2 · The Two Engines

| Engine                              | Source                        | Answers                                                             | Cadence                 |
| ----------------------------------- | ----------------------------- | ------------------------------------------------------------------- | ----------------------- |
| **A — Live Bid Feed**        | SAM.gov opportunities API     | “What can we bid right now?”                                      | Daily (Pass 1 + Pass 2) |
| **B — Subcontracting Leads** | USASpending.gov award/IDV API | “Which primes hold active vehicles and are obligated to sub out?” | Weekly / monthly sweep  |

**Key distinction:** USASpending is a  **historical award database** , not a live solicitation feed (data lags SAM.gov by ~2–4 weeks). Treat it as the *prime-intelligence* layer, never as the bid pipeline.

## 3 · What the Data Actually Gives Us (Verified)

### 3.1 USASpending — the prime-intelligence fields

Per award, USASpending exposes:

| Field                                                               | Answers                                                 |
| ------------------------------------------------------------------- | ------------------------------------------------------- |
| Recipient name, UEI, DUNS, location                                 | Who the prime is — the identity we outreach to         |
| NAICS + PSC scope hierarchy                                         | The umbrella of what they buy                           |
| Vehicle record (IDV / MATOC / IDIQ, order window, multi-award pool) | What vehicle they hold and how long it runs             |
| **subcontracting_plan**flag — F = Individual, G = Commercial | Whether they are under a subcontracting-plan obligation |
| **subaward_count**+**total_subaward_amount**            | How much first-tier sub work they have*reported*      |

### 3.2 The two hard limits we confirmed

**(a) Sub-award reporting is thin for construction.** Empirical sweep: of the top-40 construction awards by value (2023–26), only **Weston Solutions** reported any sub-awards. Dragados ($3.1B), Hensel Phelps ($760M), Whiting-Turner ($400M) and Kiewit ($515M) all report  **zero** . Construction primes under-report first-tier subs to FFATA/FSRS — treat sub-award totals as a  *bonus signal* , never a reliable measure of their sub spend.

**(b) Required goal percentages are NOT in USASpending.**
 Only the plan flag exists. Negotiated SB/SDB/WOSB/HUBZone/SDVOSB goal
percentages are reported to SBA eSRS / Summary Subcontract Reports, not
to USASpending’s public API. If we ever need exact goals, that is a
separate SBA data pull.

### 3.3 So the division of labor is:

**USASpending = “who + vehicle + obligation”**
Prime rosters on IDIQ pools, plan flags, scope umbrella, UEI.

**SAM.gov = “what they need”**
Active solicitations under each vehicle → SOW, specs, trades, volumes, bonding. This is where sub scope becomes concrete.

## 4 · Regulatory Rules to Encode (Verified)

**FAR 19.702(a)** — A subcontracting plan is required for contracts expected to exceed  **$900,000** , or  **$2,000,000 for construction** . *Small business concerns are exempt* from the plan requirement.

**FAR 52.219-14 — Limitations on Subcontracting** (small-business set-asides). A small prime may not pay non-“similarly situated” subcontractors more than:

| Contract type                | Max subbed out        | Must self-perform |
| ---------------------------- | --------------------- | ----------------- |
| General construction         | 85% (excl. materials) | ≥ 15%            |
| Specialty trade construction | 75% (excl. materials) | ≥ 25%            |
| Services                     | 50%                   | ≥ 50%            |
| Supplies                     | 50% (excl. materials) | ≥ 50%            |
| Mentor-protégé / 8(a) JV   | —                    | Protégé ≥ 40%  |

**Lead filter** A prime whose vehicle records carry **plan = F (Individual)** or **G (Commercial)** is under a subcontracting obligation — these are our  **highest-value outreach targets** .

## 5 · Sourcing Runbook

1. **Pass 1 — SAM.gov metadata pull (daily).**
   Query active opportunities filtered by construction NAICS families (236
   / 237 / 238), small-business set-asides (SBA, SDVOSBC, HZC, 8A, WOSB),
   and a response-date window. Write solicitation metadata (number, title,
   agency, deadline, NAICS, set-aside, resource links) to the opportunity
   table.
2. **Pass 2 — Attachment retrieval & OCR (async).**
   Decoupled worker downloads solicitation attachments (PDF/DOCX/SOW),
   runs OCR, and stores extracted text for triage and vector embedding.
   Decoupling protects against SAM.gov rate limits.
3. **USASpending IDIQ sweep (weekly).**
   Pull IDV vehicles in construction NAICS awarded within the last 1–3
   years. Identify multi-award pools (same base contract + sequential
   awardee suffixes + identical order-window = one MATOC/IDIQ pool). Build a
   **subcontracting lead** per prime: name, UEI, vehicle ID, NAICS scope, plan flag, reported sub volume.
4. **Enrichment (on-demand).**
   For each target prime, pull their active SAM.gov solicitations to
   extract the actual scope, trades, and bonding requirements — the
   concrete “what they need from subs” layer.
5. **Hand off to Phase 2.** Both pipelines feed AI triage and classification.

## 6 · Current Targeting Filters & Pipeline

| Filter                     | Value                                                                                                                         |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| NAICS families             | Construction 236 / 237 / 238 (IT 5415 later)                                                                                  |
| Set-asides                 | SBA · SDVOSBC · HZC · 8A · WOSB                                                                                           |
| Status / timing            | Active, response date within window                                                                                           |
| Live pipeline (2026-08-03) | **248**active construction SB set-asides — 176 SBA, 37 SDVOSBC, ~15 HUBZone/8(a)/WOSB;**162 due within 30 days** |
| Identified IDIQ pools      | USAF**FA442726G**pool (9+ primes) · Army**W519TC26GA**pool (6 primes) · FAA**692M1526G**pool              |

## 7 · Decisions & Exclusions

* **DLA / DIBBS — held.**
  No modern REST API; cFolder authenticated access; high engineering
  overhead for low relative margin vs. standard service/construction
  contracts.
* **Municipal portals — Phase 2+.** Defer until the federal pipeline is stable.
* **USASpending is never a live-bid source.** Leads only.

## 8 · Next Steps

1. Encode the **subcontracting-lead schema** (prime, UEI, vehicle, NAICS, plan flag, sub volume, status).
2. Run the **enrichment pass** on the three identified IDIQ pools — pull each prime’s active SAM.gov solicitations and mark plan-obligated primes as priority.
3. Wire **Pass 2 attachment ingestion** for the live bid feed so triage has full documents.

GovCon
 Engine — Phase 1 · Sourcing Playbook · Draft v0.1 · Figures verified
against USASpending API and FAR (acquisition.gov) as of 2026-08-03.
