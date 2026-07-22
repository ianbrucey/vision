# Solicitation Ingestion — UI Specifications (Minimal)

> **Scope:** List + create only, matching the Brief's Success Verdict ("visible in a list view"). No Claim in 00-Brief.md requires document viewing, editing, or detail-page polish beyond ingestion status — those are deferred to the AI-triage module (out of scope). Per Option A (solicitations is the real domain model, cases is demoted to plumbing), **Solicitations becomes the landing page** at `/`. The existing Cases dashboard moves to `/cases` unchanged (same component, same behavior, new route).

---

## 1. Component Tree

```
SolicitationsPage (frontend/src/app/page.tsx — the new landing page)
├── Header (branding + nav link to "Cases", matches existing page.tsx header)
├── CreateSolicitationPanel (inline card, desktop) / FAB + modal (mobile)
│   └── SourceTypeSelector (segmented buttons: Federal | State | Local)
├── FilterBar (source_type pills + ingestion_status select)
└── SolicitationList
    └── SolicitationRow (card) × N
        ├── StatusBadge (ingestion_status)
        ├── SourceTypeBadge
        └── MissingDocsFlag (if has_missing_docs)

CasesDashboard (frontend/src/app/cases/page.tsx — moved verbatim from current page.tsx)
```

## 2. Navigation

- `frontend/src/app/page.tsx` is **replaced** with the new `SolicitationsPage`.
- The current contents of `page.tsx` (Cases dashboard) move verbatim to `frontend/src/app/cases/page.tsx` — same component, same imports, same behavior, no functional changes.
- Add a link in the Solicitations header (where "Profile" currently lives) pointing to `/cases`, and correspondingly add a link back to `/` ("Solicitations") in the moved Cases dashboard header:

```tsx
<button onClick={() => router.push("/cases")}
        className="text-xs text-text-secondary hover:text-brand transition-colors flex items-center gap-1">
  <FolderOpen size={14} />
  <span className="hidden sm:inline">Cases</span>
</button>
```

No `TabNav.tsx` change — Cases is a sibling top-level route (`/cases`), not a case tab.

## 3. SolicitationsPage Layout

Reuses the current `frontend/src/app/page.tsx` structure exactly: `max-w-5xl mx-auto`, sticky header, desktop inline create card, mobile FAB + bottom-sheet modal (per `component-patterns.md`). Since `page.tsx` is being replaced by this new component, its structure/classes are the direct template — only the data model (solicitations instead of cases) and fields change.

```html
<main class="min-h-dvh bg-surface-0 text-text-primary flex flex-col">
  <header class="sticky top-0 z-30 bg-surface-0/80 backdrop-blur-sm border-b border-border">
    <!-- "Vision" branding + back-to-cases link, mirrors page.tsx -->
  </header>
  <div class="flex-1 max-w-5xl mx-auto w-full px-4 py-6">
    <!-- Create panel (desktop) / FAB (mobile) -->
    <!-- FilterBar -->
    <!-- SolicitationList -->
  </div>
</main>
```

## 4. Create Panel — Source Type Selector

Segmented buttons (matches the `typeFilter` pill pattern in `page.tsx`, not a `<select>` — the fork in required fields makes a visible 3-way toggle clearer than a dropdown):

```tsx
{(["federal", "state", "local"] as const).map((t) => (
  <button key={t} onClick={() => setSourceType(t)}
    className={`text-[11px] px-3 py-1.5 rounded-md border transition-colors ${
      sourceType === t
        ? "bg-brand-bg border-brand text-brand"
        : "border-border text-text-secondary hover:border-border-strong"
    }`}>
    {t === "federal" ? "Federal (SAM.gov)" : t[0].toUpperCase() + t.slice(1)}
  </button>
))}
```

**Fields shown below the selector:**
- `url` — always visible, required. Placeholder: `"Paste SAM.gov opportunity URL..."` (federal) or `"Paste solicitation URL..."` (state/local).
- `title` — hidden for `federal` (optional there; omit from the form entirely — API defaults it). Shown and **required** for `state`/`local`.

```tsx
{sourceType !== "federal" && (
  <input required placeholder="Solicitation title..." value={title}
         onChange={(e) => setTitle(e.target.value)}
         className="/* same input classes as page.tsx name input */" />
)}
<input required placeholder={urlPlaceholder} value={url}
       onChange={(e) => setUrl(e.target.value)}
       className="/* same input classes as page.tsx name input */" />
<button onClick={handleCreate} disabled={creating} className="/* primary, same as page.tsx Create button */">
  {creating ? "Creating..." : "Create"}
</button>
```

**Submit behavior:** `createSolicitation({ source_type, url, title })` → on `201`, refresh list. On `409`, show inline error: `"Already ingested — see existing solicitation"` (no navigation; user can find it in the list by `notice_id` match, per API contract `existing_external_id`). On `400`, show inline validation error (matches `createError` pattern in `page.tsx`).

## 5. FilterBar

Same pill pattern as `page.tsx`'s `typeFilter`, plus one native `<select>` for `ingestion_status` (4 values doesn't warrant a pill row):

```tsx
{(["all", "federal", "state", "local"] as const).map((t) => ( /* pill, same as source type selector */ ))}
<select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
        className="/* same select classes as page.tsx case_type select */">
  <option value="">All statuses</option>
  <option value="pending">Pending</option>
  <option value="fetching">Fetching</option>
  <option value="complete">Complete</option>
  <option value="failed">Failed</option>
</select>
```

## 6. SolicitationRow (Card)

Matches `TasksTab.tsx` card row pattern: `bg-surface-1 border border-border rounded-lg p-3 hover:bg-surface-2 transition-colors`.

```tsx
<div className="flex items-center gap-3 p-3">
  <div className="flex-1 min-w-0">
    <p className="text-sm text-text-primary truncate">{title}</p>
    <p className="text-[10px] text-text-disabled truncate">{agency || url}</p>
  </div>
  <SourceTypeBadge type={source_type} />
  <StatusBadge status={ingestion_status} />
  {has_missing_docs && (
    <span title="Some attachments failed to download">
      <AlertTriangle size={14} className="text-warning" />
    </span>
  )}
</div>
```

### 6.1 Badge Color Maps

```typescript
const STATUS_COLORS: Record<string, string> = {
  pending: "bg-surface-2 text-text-disabled",
  fetching: "bg-warning-bg text-warning",
  complete: "bg-success-bg text-success",
  failed: "bg-danger-bg text-danger",
};

const SOURCE_TYPE_COLORS: Record<string, string> = {
  federal: "bg-info-bg text-info",
  state: "bg-brand-bg text-brand",
  local: "bg-surface-2 text-text-secondary",
};
```

Rendered as `<span className={`text-[11px] px-2 py-0.5 rounded-sm font-medium ${map[value]}`}>{value}</span>` — same shape as `DraftsTab.tsx` `badgeClass`.

## 7. Polling for Federal Ingestion

While any visible row has `ingestion_status IN ('pending', 'fetching')`, poll `GET /api/solicitations` (the list endpoint, not per-job) every 3s — this list already reflects worker-updated status, so no separate `useJobPolling` hook is needed. Reuse the existing `refresh()` + `setInterval` pattern from `frontend/src/app/page.tsx` (lines 42–58), not `DocumentAttachButton.tsx`'s per-job polling (which tracks upload state, not row state). Stop polling (clear interval) when no row is `pending`/`fetching`.

## 8. Empty State

```tsx
<div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
  <FileSearch size={32} className="text-text-disabled" />
  <p className="text-sm text-text-secondary">No solicitations yet</p>
  <p className="text-xs text-text-disabled">Paste a SAM.gov URL above to get started.</p>
</div>
```

## 9. API Client Additions (`frontend/src/lib/api.ts`)

```tsx
export const listSolicitations = (params?: { source_type?: string; ingestion_status?: string }) => {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  return fetchAPI(`/api/solicitations${qs ? `?${qs}` : ""}`);
};

export const createSolicitation = (data: { source_type: string; url: string; title?: string }) =>
  fetchAPI("/api/solicitations", { method: "POST", body: JSON.stringify(data) });

export const getSolicitation = (id: number) => fetchAPI(`/api/solicitations/${id}`);
```

`createSolicitation` errors (400/409) surface via the existing `err.message` thrown by `fetchAPI` — same pattern as `handleCreate` in `page.tsx`. For 409 specifically, `err.message` is the `detail` string from the API contract's error body (no special-casing needed in the client — the component reads `err.message`).

## 10. Design System Compliance

Same checklist as `calendar-system/04-ui-specs.md` §14 applies unchanged (44px touch targets, `active:` on every `hover:`, `text-[16px]` inputs on mobile, etc.) — not restated here to avoid duplication.
