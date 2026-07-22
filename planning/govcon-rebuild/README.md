# GovCon Rebuild — Planning

> Corrected intent, after discussion. `00-intent.md` is superseded on the
> "Workflow A vs. B" question — see below. Keep `00-intent.md` for the parts
> about reusable infrastructure; this file is the scope of record going
> forward.

## 1. The Actual Model

We are **always the prime**. We do not build a multi-tenant marketplace where
outside companies log in and use the platform to find their own work
(that's the TalentLynk vision — a separate, later, much bigger product).

What we're building is *our own company's* operating system for running
government solicitations end-to-end, where **teaming with outside partners is
a first-class, routine step in the pipeline** — not an edge case. Some
solicitations we may answer alone. Most, we expect to answer by pulling in
one or more partners (subcontractors, distributors, individual specialists)
from a partner database we maintain. The system needs to support both without
treating "solo bid" and "teamed bid" as different products.

The second, equally important half of the mandate: **track the full
lifecycle** of everything we bid on — not just up through submission, but
through award/no-award and into post-award execution — so nothing falls
through the cracks and we have a system of record for our pipeline.

## 2. End-to-End Lifecycle (per `scratch.md`)

1. **Ingestion** — manual (file/ZIP upload) or automatic (SAM.gov API by
   URL/Notice ID). Source type flag: `federal | state | local`, defaults to
   federal. Federal auto-ingestion can pull full metadata + documents from
   SAM.gov; state/local and any case where SAM.gov docs are incomplete falls
   back to manual upload, flagged for follow-up.
2. **Triage (AI)** — classify RFQ vs. RFP, extract informational artifacts
   (NAICS/PSC, agency, set-aside, deadlines, place of performance, scope).
   This is the existing assembly line's Phase 1.
3. **Partner Matching** — query the partner database (companies + individual
   specialists) by NAICS/PSC/capability/location to find who could fulfill
   this solicitation, in whole or in part.
4. **Outreach Queue (human-in-the-loop)** — system drafts quote-request
   emails per matched partner and stages them for review. User inspects,
   edits if needed, and approves send from the solicitation's dashboard.
   Requires an email-sending integration (Resend/Mailtrap-class).
5. **Response Tracking** — capture partner replies (ideally inbound email
   capture, deferred build) and mark the solicitation `quote_received` once
   we have what we need to price and respond.
6. **Proposal Generation & Submission** — reuses/extends the existing
   assembly line (Deep Read → Brief → Go/No-Go → Draft → Quality Gate) to
   produce the compliant response, then submit.
7. **Partner Notification** — notify teamed partners of outcome/next steps
   post-submission. Teaming agreements are optional, generated when needed.
8. **Post-Award Management** — status tracking after award/no-award. Scope
   TBD — flagged as an open design question, not yet a build target.

## 3. What This Means for Scope

- **Single tenant.** One company profile (ours). Not building
  account-per-company multi-tenancy in this rebuild.
- **Partners are data, not tenants.** A `partners` table (companies +
  individual specialists), not user accounts. They receive email; they don't
  log into the platform. No partner-facing UI/auth in this rebuild.
- **Lifecycle tracking is a core requirement, not a nice-to-have.** Every
  solicitation needs a durable status through all 8 stages above, visible on
  a dashboard, not just CLI-driven pipeline runs producing files on disk.
- **TalentLynk marketplace concepts (matching engine as a product, pricing
  engine, digital sign-off routing, financial infrastructure, multi-tenant
  partner onboarding) are out of scope.** The partner-matching and
  outreach-queue pieces we *are* building are a much smaller, internal
  version of that idea — good architecture here should not preclude growing
  toward TalentLynk later, but we are not building that platform now.

## 4. Reusable Infrastructure (from `00-intent.md`, still accurate)

- Ingestion pipeline (PDF/DOCX/XLSX/image → OCR → sections → blocks →
  embeddings/FTS); ZIP support still needs to be added.
- Solicitation assembly line (`backend/scripts/solicitation_pipeline.py`,
  8 sub-agents) — covers triage through quality gate. Needs to move from
  CLI-triggered to UI-triggered, and gain the partner-matching/outreach
  stages that don't exist yet.
- Company profile synthesis (`profile_synth.py`, `company_profiles` table)
  — extraction + verification-state model, reusable as-is for our own
  profile.
- Case infrastructure (`cases` table, tasks, documents, correspondence,
  MCP agent tools) — solicitations continue to live as cases
  (`case_type = 'rfp_response'`), per the existing schema.

## 5. Net New (nothing built yet)

- `partners` table + matching logic (query by NAICS/PSC/capability/location).
- Outreach email queue + review/approve/send UI + email provider integration.
- Inbound email capture (deferred — flagged, not committed).
- Lifecycle/status model spanning all 8 stages, exposed on a dashboard.
- Post-award tracking (undesigned).
- SAM.gov API integration for auto-ingestion.

## 6. Still Open (carried over, unresolved)

- Case → Matter rename: do it now or leave it?
- Exact status enum / state machine for the lifecycle in §2.
- Post-award management scope.
- Teaming agreement generation — trigger conditions and template source.

## 7. Next Step

Move into planning the actual build: schema changes (`partners`,
lifecycle/status fields), API surface for the outreach queue, and how the
existing assembly line gets wired into a UI-triggered, partner-aware
pipeline. This README is the scope baseline for that work.
