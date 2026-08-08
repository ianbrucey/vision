# Phase 2 — Databank Processor

> Pipeline artifact · 2026-08-05 · Status: DRAFT

---

## 1. What This Phase Produces

Reads raw `sam_notices` rows, applies business filters, and feeds qualifying notices into the existing solicitation pipeline (`sam_fetch` → `solicitation_triage` → `vendor_matching`).

**Output:** Each qualifying notice becomes a `solicitations` row with a `sam_fetch` job enqueued. Non-qualifying rows are marked skipped with a reason. Previously processed notices are deduplicated.

---

## 2. Architecture Decision: Processor vs Pipeline Table

We're NOT creating a separate `pipeline_opportunities` table. The `solicitations` table IS the enriched pipeline — it already has `notice_id` (UNIQUE), `naics_code`, `set_aside_type`, `triage_status`, artifact columns, and job chaining. The databank processor is just a new intake path into that existing machinery.

```
sam_notices (raw CSV) ──[processor]──> solicitations ──> sam_fetch ──> triage ──> vendor_matching
                                            ↑
                                     (existing, unchanged)
```

---

## 3. Schema Changes

### 3.1 New columns on `sam_notices`

```sql
-- Migration 025: pipeline processing columns on sam_notices

ALTER TABLE sam_notices ADD COLUMN IF NOT EXISTS pipeline_status TEXT;
-- NULL = unprocessed, 'queued' = sent to solicitation pipeline,
-- 'skipped' = didn't pass filters, 'duplicate' = already in solicitations,
-- 'error' = processing failed

ALTER TABLE sam_notices ADD COLUMN IF NOT EXISTS pipeline_category TEXT;
-- 'construction', 'facilities', 'it', 'other'

ALTER TABLE sam_notices ADD COLUMN IF NOT EXISTS pipeline_urgency TEXT;
-- 'red' (0-7 days), 'yellow' (8-14 days), 'green' (15+ days),
-- 'unknown' (no response date), 'past_due' (before today)

ALTER TABLE sam_notices ADD COLUMN IF NOT EXISTS pipeline_skip_reason TEXT;
-- Why it was skipped (e.g. 'past_due', 'wrong_naics', 'award_notice', 'full_and_open')

ALTER TABLE sam_notices ADD COLUMN IF NOT EXISTS pipeline_solicitation_id INTEGER;
-- FK to solicitations.id — links to the created solicitation row

ALTER TABLE sam_notices ADD COLUMN IF NOT EXISTS pipeline_processed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_sam_notices_pipeline_status
    ON sam_notices (pipeline_status);
CREATE INDEX IF NOT EXISTS idx_sam_notices_pipeline_category
    ON sam_notices (pipeline_category);
CREATE INDEX IF NOT EXISTS idx_sam_notices_pipeline_urgency
    ON sam_notices (pipeline_urgency);
```

All columns are nullable. Existing rows get NULL (unprocessed). The upload route doesn't change — it doesn't touch these columns.

---

## 4. Filter Logic

### 4.1 Step order (applied in sequence)

```
Row from sam_notices
  ↓
1. EXCLUDE by type
  ↓
2. TAG category (NAICS keyword match)
  ↓
3. EXCLUDE wrong categories
  ↓
4. TAG set-aside group
  ↓
5. EXCLUDE non-SB set-asides
  ↓
6. TAG urgency (response date bucket)
  ↓
7. EXCLUDE past-due (unless Sources Sought — see §4.4)
  ↓
Qualifies → create solicitation + enqueue sam_fetch
```

### 4.2 Type filter

| Type | Action | Reason |
|------|--------|--------|
| Combined Synopsis/Solicitation | ✅ INCLUDE | Primary bid target |
| Solicitation | ✅ INCLUDE | Formal solicitation |
| Presolicitation | ✅ INCLUDE | Early notice — prep before RFP drops |
| **Sources Sought** | ✅ **INCLUDE** | **Pre-RFP market research. Respond = get on vendor list = receive formal solicitation. See §4.4.** |
| Special Notice | ✅ INCLUDE | Can contain bid info, industry days, site visits |
| Award Notice | ❌ EXCLUDE | Already awarded |
| Justification | ❌ EXCLUDE | After-the-fact sole-source justification |
| Sale of Surplus Property | ❌ EXCLUDE | Government selling, not buying |
| Consolidate/(Substantially) Bundle | ✅ INCLUDE (rare) | Only 8 in 46K — bundling notices can be bid targets |

### 4.3 NAICS category tagging

Same keyword lists from the analysis, with Ship Building and equipment manufacturing excluded from construction:

**Construction keywords:** Construction, Building, Plumbing, HVAC, Electrical Contractors, Carpentry, Masonry, Roofing, Concrete, Painting, Welding, Excavation, Demolition, Flooring, Drywall, Fencing, Paving, Structural Steel, Fire Protection, Elevator, Asphalt, Sheet Metal, Finishing Contractors, Power and Communication Line, Water and Sewer Line, Highway/Street/Bridge, Industrial Building

**Construction excludes (manufacturing/supply, not trades):** Ship Building, Machinery Manufacturing, Equipment Manufacturing, Mining, Equipment Rental, Sand and Gravel, Prefabricated Metal Building, Construction Machinery

**Facilities keywords:** Facilities Support, Janitorial, Custodial, Landscaping, Security Guards, Security Systems, Waste Collection, Waste Treatment, Pest Control, Laundry, Food Service, Cafeteria

**IT keywords:** Software, Computer Programming, Computer Systems Design, Electronic Computer, Computing Infrastructure, Data Processing, Custom Computer, Cloud, Cybersecurity, Information Technology, Telecom, Wireless, Satellite, Internet

**Everything else:** `pipeline_category = 'other'` → skipped with reason `wrong_naics`

### 4.4 Sources Sought — Special Handling

Sources Sought are NOT bid opportunities. They're agency market research — "who out there can do this work?" Responding with a capability statement gets your company on the **interested vendor list**. When the formal solicitation drops, you're notified. This is the Eric Coffie strategy — **"stop trying to be the whole contract, be a line item"** — applied at the sourcing level.

| Field | Sources Sought Handling |
|-------|------------------------|
| Type filter | ✅ INCLUDED |
| Urgency | Always `red` (highest priority) regardless of response date — you want to respond BEFORE the deadline, and the window is usually short |
| Past-due | DON'T exclude past-due Sources Sought if they closed within the last 30 days — the agency may still accept late responses, or the info is useful for the upcoming RFP |
| Triage workflow | Different prompt: extract "what capabilities are they looking for?" rather than "how do we bid?" |
| Response type | Capability statement, not priced proposal |

### 4.5 Set-aside filter

Include all small-business designations (case-insensitive match against `current_set_aside`):

```
Total Small Business
SDVOSB (Service-Disabled Veteran-Owned Small Business)
HUBZone (Historically Underutilized Business Zone)
8(a)
WOSB (Women-Owned Small Business)
EDWOSB (Economically Disadvantaged WOSB)
ISBEE (Indian Small Business Economic Enterprise)
Indian Economic Enterprise (IEE)
Veteran-Owned Small Business
```

Include both "Set-Aside" and "Sole Source" variants of each.

Exclude: blank/empty (Full and Open), Partial Small Business (ambiguous — we're the prime, not a sub on someone else's bid).

### 4.6 Urgency bucketing

Based on `current_response_date` relative to today:

| Days Until Deadline | Bucket | Label |
|--------------------|--------|-------|
| 0–7 | `red` | Urgent — triage within 24 hours |
| 8–14 | `yellow` | Active — triage within 48 hours |
| 15+ | `green` | Pipeline — triage within the week |
| NULL (no date) | `unknown` | Flag for manual review, don't skip |
| < 0 (past) | `past_due` | Skip (unless Sources Sought ≤30 days past) |

### 4.7 Past-due policy

| Situation | Action |
|-----------|--------|
| Past-due, any type except Sources Sought | Skip — can't bid |
| Past-due, Sources Sought, >30 days past | Skip — too stale |
| Past-due, Sources Sought, ≤30 days past | Include with `pipeline_urgency = 'red'` and a note to check if still accepting responses |

---

## 5. Processing Logic (Pseudocode)

```python
def process_batch(batch_id: str, user_id: str) -> dict:
    """
    Read unprocessed rows from a sam_notices upload batch,
    apply filters, create solicitations for qualifying notices.
    """
    rows = get_unprocessed_rows(batch_id)  # WHERE pipeline_status IS NULL
    results = {"queued": 0, "skipped": 0, "duplicate": 0, "errors": []}

    for row in rows:
        # Step 1: Type exclusion
        if row.type in EXCLUDED_TYPES:
            mark_skipped(row, "excluded_type")
            results["skipped"] += 1
            continue

        # Step 2: NAICS category
        category = classify_naics(row.naics_description)
        if category == "other":
            mark_skipped(row, "wrong_naics")
            results["skipped"] += 1
            continue

        # Step 3: Set-aside
        set_aside_group = classify_set_aside(row.current_set_aside)
        if set_aside_group == "full_and_open":
            mark_skipped(row, "full_and_open")
            results["skipped"] += 1
            continue

        # Step 4: Urgency
        urgency = bucket_urgency(row.current_response_date, row.type)
        if urgency == "past_due":
            mark_skipped(row, "past_due")
            results["skipped"] += 1
            continue

        # Step 5: Create solicitation (dedup via notice_id UNIQUE constraint)
        try:
            sol = solicitation_mgr.create(
                source_type="federal",
                url=f"https://sam.gov/opp/{row.notice_id}/view",
                notice_id=row.notice_id,
                title=row.opportunity_title,
            )
        except DuplicateNoticeError:
            mark_processed(row, "duplicate")
            results["duplicate"] += 1
            continue

        # Step 6: Enqueue sam_fetch
        enqueue_job(
            case_id=sol["case_id"],
            job_type="sam_fetch",
            metadata={
                "solicitation_id": sol["id"],
                "notice_id": row.notice_id,
                "pipeline_category": category,
                "pipeline_urgency": urgency,
            },
        )

        mark_processed(row, "queued", sol["id"], category, urgency)
        results["queued"] += 1

    return results
```

---

## 6. Route Spec

### `POST /api/pipeline/process-batch`

Trigger processing for a specific upload batch.

**Request:**
```json
{
    "batch_id": "uuid-from-sam-notices-upload",
    "dry_run": false
}
```

**Response:**
```json
{
    "batch_id": "uuid",
    "dry_run": false,
    "total_rows": 1247,
    "queued": 892,
    "skipped": 310,
    "duplicate": 45,
    "skipped_breakdown": {
        "past_due": 180,
        "wrong_naics": 95,
        "excluded_type": 20,
        "full_and_open": 15
    },
    "errors": []
}
```

When `dry_run: true`, runs all filters and returns counts but does NOT create solicitations or enqueue jobs. Used to preview before committing.

### `GET /api/pipeline/batch-status/{batch_id}`

Returns processing status for a batch — how many queued, skipped, duplicate, still pending.

---

## 7. What Sources Sought Changes

| Component | Change |
|-----------|--------|
| `solicitation_triage.py` | Detect `contract_opportunity_type = 'Sources Sought'` → use a different extraction prompt: focus on required capabilities, NAICS, evaluation factors, and "how to respond" instructions rather than bid terms |
| `pipeline_urgency` logic | Sources Sought are always `red` regardless of days remaining — they're short-window, high-value for early positioning |

---

## 8. Open Questions

1. **Trigger:** Does processing run automatically after CSV upload, or is it manual (click a button)? Recommendation: manual trigger with `dry_run` preview. Automation comes after the filter rules are proven over 2-3 batches.

2. **Re-processing:** If we change filter rules, can we re-process a batch? Yes — set `pipeline_status = NULL` on the batch and run again. Need a `POST /api/pipeline/reset-batch/{batch_id}` endpoint.

3. **Rate limit throttle:** The existing worker processes one job at a time with `SKIP LOCKED`. For an initial backlog of ~900 notices, the `sam_fetch` jobs will queue up and process sequentially. Do we want a configurable delay between jobs? At 1 request/second, 900 notices × ~4 API calls = 3,600 calls over ~1 hour. Well within the 10,000/day limit. No throttle needed for now.

4. **Notice ID validation:** Some databank rows might have malformed notice IDs (not 32-char hex). Validate format before enqueuing. Skip with reason `invalid_notice_id`.

---

## 9. Exit Condition

**Complete when:**
- [ ] Migration 025 applied to add pipeline columns to `sam_notices`
- [ ] `POST /api/pipeline/process-batch` endpoint operational
- [ ] `GET /api/pipeline/batch-status/{batch_id}` endpoint operational
- [ ] `dry_run` mode returns accurate counts without side effects
- [ ] Test run against the 46K-row CSV produces results matching the analysis (~900–1,200 queued, rest skipped with documented reasons)
- [ ] Sources Sought notices are included and flagged correctly
- [ ] At least one `sam_fetch` job successfully completes from a databank-sourced notice

---

> **Previous phase:** [Phase 1 — Pull SAM Notices](phase-1-pull-sam.md)
> **Next phase:** Phase 3 — Triage Adaptation (Sources Sought handling, urgency prioritization)
