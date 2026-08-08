# Phase 1 — Pull SAM Notices

> Pipeline artifact · 2026-08-05 · Status: DRAFT

---

## 1. What This Phase Produces

A deduplicated set of active federal solicitations in construction, facilities, and IT — filtered to opportunities we can actually bid — with at least 7 days before the response deadline.

**Output:** CSV or database rows, one per unique notice, with: Notice ID, title, type, agency, NAICS, set-aside, response date, place of performance, attachment count, posting date.

---

## 2. Source Decision: Databank CSV vs SAM API

| Factor | Databank CSV | SAM API |
|--------|-------------|---------|
| NAICS filtering | ❌ Text descriptions only — no numeric code filter at export | ✅ Filter by numeric NAICS codes |
| Set-aside filtering | ✅ Yes, at export time | ✅ Yes |
| Date filtering | ✅ Response date range | ✅ |
| Rate limits | None (manual export) | Yes (API key required) |
| Attachment download | ❌ No | ✅ Can fetch attachment metadata + download |
| Ease of use | Download one CSV | Paginate, handle rate limits |
| Completeness | All fields except full description text | Full metadata + description + attachment links |

**Recommendation:** Start with the databank CSV for volume discovery and filtering. Use the SAM API later (Phase 3 — Enrich) to fetch full descriptions and download attachments for notices that pass triage. The databank gives us everything we need for the filter decision; the API gives us the documents for AI reading.

---

## 3. SAM.gov Databank Export Filters

### 3.1 What to set in the SAM.gov UI

| Filter | Setting | Reason |
|--------|---------|--------|
| **Status** | Active | Only open solicitations |
| **Set-Aside** | Total Small Business, SDVOSB, HUBZone, 8(a), WOSB, EDWOSB, ISBEE, Indian Economic Enterprise, Veteran-Owned Small Business, Women-Owned Small Business (Sole Source included for each) | All small-business designations. Skip "Full and Open" / blank — those aren't reserved for SB. |
| **Response Date** | From: [today] To: [today + 365] | Excludes past-due notices. The "Active" filter alone does NOT exclude past-due — 66% of "active" notices in our test pull had already passed their response date. |
| **Place of Performance** | USA only (optional — removes ~3.7% overseas) | Our subcontractor network is US-based. Can skip if too restrictive. |

### 3.2 What CANNOT be filtered in the UI (must be post-processing)

| Filter | Why it can't be done in SAM |
|--------|---------------------------|
| **NAICS** (construction/facilities/IT) | SAM databank has no NAICS filter dropdown. NAICS is exported as text descriptions, not codes. |
| **Opportunity Type** (exclude Awards/Justifications) | No type filter in databank UI |
| **Attachment presence** | No filter for "has attachments" |

---

## 4. What You're Missing in Your Current Step

You said: *"login to SAM, set the filter for active notices, filter out for our categories and any notices where response date is 7 days out."*

Four things to add:

### 4.1 "Active" does not mean "still open"

The "Active" status flag in SAM.gov means the notice hasn't been archived or cancelled. It does **not** mean the response deadline hasn't passed. In our test pull of 46,569 "active" rows, **21,759 (66%) had response dates in the past.** Some of these were posted years ago.

**Fix:** Apply a response date filter at export time: `Response Date ≥ [today's date]`. This is critical — without it, two-thirds of your pull are un-biddable.

### 4.2 Exclude non-bid opportunity types

These notice types are not something you can bid on:

| Type | Rows in Test Pull | Why Exclude |
|------|-------------------|-------------|
| Award Notice | 11,717 | Someone already won. This is an announcement, not a solicitation. |
| Justification | 664 | After-the-fact justification for sole-source. Not a bid. |
| Sale of Surplus Property | 10 | Government selling stuff, not buying. |

Combined, these are ~12,400 rows (27% of the test pull). Filter them out.

**Fix:** Exclude `Contract Opportunity Type` IN (`Award Notice`, `Justification`, `Sale of Surplus Property`).

### 4.3 Which set-asides exactly?

You need to decide which set-aside types to include. The data says:

| Approach | Approx. SB Notices (30-day window) | Trade-off |
|----------|-----------------------------------|-----------|
| Total Small Business only | ~830 | Simplest. Misses SDVOSB/HUBZone/8(a)/WOSB opportunities. |
| All SB types combined | ~1,073 | Full coverage. +29% more opportunities than Total SB alone. |

**Recommendation:** Include all SB types. SDVOSB alone adds 224 facilities notices and 453 construction notices. That's real volume you'd miss otherwise.

### 4.4 The NAICS filtering has to happen in code

Since the databank doesn't filter by NAICS at export time, you'll export everything matching your set-aside + date + status filters, then apply NAICS keyword matching post-export. This means:

1. Your CSV will include all NAICS codes (manufacturing, healthcare, agriculture, etc.)
2. A post-processing step tags each row as construction / facilities / IT / other
3. "Other" rows are dropped from the bid pipeline (but kept in the raw archive for auditing)

The keyword match lists from [01-sam-databank-analysis.md §9.1](../01-sam-databank-analysis.md#91-filter-configuration) handle this.

---

## 5. The "7 Days Out" Question

You said filter for notices where the response date is "7 days out." Clarification needed:

| Interpretation | Meaning | Result |
|---------------|---------|--------|
| `response_date ≥ today + 7` | Must have at least 7 full days to respond | ~558 SB notices across all categories |
| `response_date > today + 7` | Strictly more than 7 days | Same as above minus edge cases |
| `response_date ≥ today` and flagged if < 7 days | Pull everything, flag urgency | ~1,073 SB notices, with ~515 flagged as "urgent" |

**Recommendation:** Option C — pull everything where `response_date ≥ today`, then bucket by urgency (0–7 days = red, 8–14 days = yellow, 15+ days = green). This way you don't miss an opportunity that posted late or got amended. The AI triage step can prioritize the urgent ones.

---

## 6. Deduplication Strategy

If you pull daily, the same notice will appear in multiple pulls (it stays "active" for weeks/months). You need:

| Field | Purpose |
|-------|---------|
| `Notice ID` | Primary dedup key — unique per SAM.gov notice |
| `Last Updated Date` | Track changes — if a notice was amended, re-process it |
| `imported_at` | When we first saw it |
| `last_seen_at` | Most recent pull it appeared in |

**Logic:**
- If `Notice ID` is new → insert and queue for triage
- If `Notice ID` exists AND `Last Updated Date` changed → update and re-queue for triage
- If `Notice ID` exists AND `Last Updated Date` unchanged → skip (already processed)

---

## 7. Open Questions to Resolve

1. **Cadence:** Daily? Twice daily? The data suggests ~30–50 new postings/day. Daily is probably sufficient for an initial pipeline, but if response windows are tight (some close within 7–10 days), a morning + evening pull may catch more.

2. **Databank export automation:** The databank is a manual CSV export. At some point, this needs to become a script hitting the SAM API. When do we make that switch? Recommended trigger: when the manual process is stable and the filter rules are validated.

3. **Archive strategy:** Do we keep the raw CSV for every pull, or just the filtered results? Raw CSVs are 24MB each — negligible. Keep them for audit.

---

## 8. Phase 1 Exit Condition

**Complete when:**
- [ ] SAM.gov databank filter configuration is documented and reproducible
- [ ] A CSV pull exists with the correct filters applied (status, set-aside, response date, type exclusions)
- [ ] Post-processing script tags each row with category (construction/facilities/IT/other)
- [ ] Deduplication logic is defined and ready for Phase 2
- [ ] Filtered row counts match expected volumes from the analysis (~1,000–2,000 active SB opportunities)

---

> **Next phase:** Phase 2 — Filter & Classify (NAICS keyword matching, urgency bucketing, dedup)
