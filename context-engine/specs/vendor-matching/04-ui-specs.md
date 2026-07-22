# Vendor Matching — UI Specifications

> **Scope:** One new case tab (`VendorMatchesTab.tsx`) per Brief CLAIM-09. Reuses `TriageTab.tsx`'s status-badge/spinner/polling/trigger-button structure verbatim where the shape matches (Brief §5 "Reuse pattern"). Does **not** touch `VendorsTab.tsx` (global directory search, tab id `vendors`) — this is a new, separate tab id `vendor_matches`.

---

## 1. Component Tree

```
VendorMatchesTab (frontend/src/app/cases/[id]/tabs/VendorMatchesTab.tsx — new)
├── Header (status badge + "Run/Re-run Matching" trigger button — mirrors TriageTab header)
├── OutreachEmailPanel (subject/body card, shown only when matching_status='complete')
└── VendorMatchList
    └── VendorMatchRow × ≤25
        ├── ScoreBadge (match_score 0-100)
        ├── NaicsMatchTypeBadge (exact | family | capability_only)
        ├── SetAsideFlags (reuses VendorsTab.tsx's Flags component pattern)
        └── CopyEmailButton (per-row, client-side placeholder substitution)
```

## 2. Navigation

- `TabNav.tsx`: add `"vendor_matches"` to the `TabId` union, add a `TabDef` entry (icon: `Mail` is already used by `correspondence` — use `Users` from `lucide-react` to stay distinct), inserted immediately after `"triage"` in `BASE_TABS`.
- Gating: same `showTriage` boolean gates this tab too — solicitation-backed cases only. Rename the prop `showTriage` → keep as-is (no rename; out of scope) and reuse its value for a new `showVendorMatches` pass-through, since both tabs require `hasSolicitation` from `page.tsx`. Simplest: pass the same `hasSolicitation` boolean into a new `TabNavProps.showVendorMatches` param, filtered the same way `showTriage` filters `"triage"`.
- `page.tsx`: add `"vendor_matches"` to the `tabParam ===` allow-list (line 50), add `{activeTab === "vendor_matches" && <VendorMatchesTab caseId={Number(id)} />}` alongside the existing tab renders, add `<VendorMatchesTab caseId={Number(id)} />` import.

## 3. Header (mirrors TriageTab.tsx lines 128–172)

```tsx
<div className="shrink-0 px-4 py-3 border-b border-border flex items-center gap-3 flex-wrap">
  <span className={`text-[11px] px-2 py-0.5 rounded-sm font-medium ${STATUS_COLORS[sol.matching_status]}`}>
    {sol.matching_status}
  </span>
  {sol.matching_status === "failed" && sol.matching_error && (
    <span className="text-[11px] text-danger truncate max-w-xs" title={sol.matching_error}>
      {sol.matching_error}
    </span>
  )}
  <button onClick={handleTrigger} disabled={!canTrigger} title={triggerDisabledReason}
          className="ml-auto inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-border
                     bg-surface-1 hover:bg-surface-3 text-text-primary transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed">
    {triggering || sol.matching_status === "running" ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
    {sol.matching_status === "complete" ? "Re-run Matching" : "Run Matching"}
  </button>
</div>
```

`STATUS_COLORS` reuses the exact same map as `TriageTab.tsx` (`pending`/`running`/`complete`/`failed` → identical color classes) — copy the constant, do not import (avoids cross-tab coupling for a 4-line const).

**`canTrigger` gating (CLAIM-06 preconditions surfaced client-side, not just server-side):**
```tsx
const canTrigger =
  sol.triage_status === "complete" &&
  sol.quick_kill === false &&
  !!sol.naics_code &&
  sol.matching_status !== "running" &&
  !triggering;
```
`triggerDisabledReason` — first truthy string wins: `sol.triage_status !== "complete"` → `"Triage must complete first"`; `sol.quick_kill` → `"Solicitation was quick-killed during triage"`; `!sol.naics_code` → `"No NAICS code available for matching"`; else `undefined`. The 400 responses in `02-api-contract.json` are the source of truth for this wording — client-side check is a UX shortcut, not a substitute for server validation.

## 4. Body States

Branch on `matching_status` + `matches.length`, in this priority order (matches `TriageTab.tsx`'s `quick_kill` → `triage_status` branching style):

1. **`pending` + no prior run:** Centered `CheckCircle2` icon (text-disabled) + `"Vendor matching hasn't run yet for this solicitation."` — same as `TriageTab.tsx`'s triage-not-run-yet state (lines 221–228).
2. **`running`:** Centered `Loader2` spin + `"Finding matching vendors…"`.
3. **`failed`:** Centered danger text `"Vendor matching failed. Try running it again."` (error detail already shown in header per §3).
4. **`complete` + `matches.length === 0`:** Centered `"No eligible vendors were found for this solicitation's NAICS code and set-aside requirements."` — this is a legitimate outcome per `02-api-contract.json`'s notes field, not an error.
5. **`complete` + `matches.length > 0`:** Render `OutreachEmailPanel` + `VendorMatchList` (§5, §6).

```tsx
{error && <div className="shrink-0 px-4 py-2 text-xs text-danger bg-danger-bg">{error}</div>}
```
(identical pattern to `TriageTab.tsx` line 174–176, placed the same way.)

## 5. OutreachEmailPanel

```tsx
<div className="shrink-0 p-4 border-b border-border bg-surface-1">
  <p className="text-[10px] font-semibold text-text-disabled uppercase tracking-wide mb-2">Outreach Email Template</p>
  <p className="text-sm font-medium text-text-primary mb-1">{sol.outreach_email_subject}</p>
  <p className="text-xs text-text-secondary whitespace-pre-wrap line-clamp-4">{sol.outreach_email_body}</p>
</div>
```
Read-only display of the shared template — no edit UI in v1 (Brief §7: shared template, client-side substitution only). Per-row substitution happens in `CopyEmailButton` (§6.4), not here.

## 6. VendorMatchList

Table on desktop (≥sm), stacked cards on mobile — same responsive pattern as `VendorsTab.tsx`'s table (lines 251–260), wrapped `overflow-x-auto` per `component-patterns.md` §12.8.3.

```tsx
<table className="w-full text-sm">
  <thead className="sticky top-0 bg-surface-1 border-b border-border">
    <tr className="text-left text-[10px] font-semibold text-text-disabled uppercase tracking-wide">
      <th className="px-3 py-2">Rank</th>
      <th className="px-3 py-2">Vendor</th>
      <th className="px-3 py-2 hidden md:table-cell">Score</th>
      <th className="px-3 py-2 hidden lg:table-cell">Match Type</th>
      <th className="px-3 py-2 hidden sm:table-cell">Set-aside</th>
      <th className="px-3 py-2 hidden xl:table-cell">Contact</th>
      <th className="px-3 py-2">Action</th>
    </tr>
  </thead>
  <tbody className="divide-y divide-border">
    {matches.map((m) => <VendorMatchRow key={m.id} match={m} template={sol} />)}
  </tbody>
</table>
```

### 6.1 VendorMatchRow

```tsx
<tr className="hover:bg-surface-2 transition-colors">
  <td className="px-3 py-2 text-text-disabled">#{m.rank}</td>
  <td className="px-3 py-2 min-w-0">
    <p className="text-text-primary truncate">{m.vendor_name}</p>
    <p className="text-[10px] text-text-disabled truncate" title={m.match_rationale}>{m.match_rationale}</p>
  </td>
  <td className="px-3 py-2 hidden md:table-cell"><ScoreBadge score={m.match_score} /></td>
  <td className="px-3 py-2 hidden lg:table-cell"><NaicsMatchTypeBadge type={m.naics_match_type} /></td>
  <td className="px-3 py-2 hidden sm:table-cell"><SetAsideFlags match={m} /></td>
  <td className="px-3 py-2 hidden xl:table-cell text-text-secondary truncate">
    {m.contact_email || <span className="text-text-disabled italic">hidden</span>}
  </td>
  <td className="px-3 py-2"><CopyEmailButton match={m} subject={sol.outreach_email_subject} body={sol.outreach_email_body} /></td>
</tr>
```
`match_rationale` is truncated with `title=` tooltip (full text on hover/long-press) rather than a modal — consistent with "no Claim requires a detail view" scoping precedent set in `solicitation-ingestion/04-ui-specs.md`.

### 6.2 ScoreBadge

```tsx
function ScoreBadge({ score }: { score: number }) {
  const cls = score >= 80 ? "bg-success-bg text-success"
    : score >= 50 ? "bg-warning-bg text-warning"
    : "bg-danger-bg text-danger";
  return <span className={`text-[11px] px-2 py-0.5 rounded-sm font-medium ${cls}`}>{score}</span>;
}
```
Thresholds (≥80 / 50–79 / <50) are a UI-only display convention — not a re-derivation of the LLM's scoring logic, and not persisted anywhere. No Claim depends on the exact cutoffs; flagged here as the concrete values used rather than left undefined.

### 6.3 NaicsMatchTypeBadge / SetAsideFlags

```tsx
const NAICS_MATCH_COLORS: Record<string, string> = {
  exact: "bg-brand-bg text-brand",
  family: "bg-info-bg text-info",
  capability_only: "bg-surface-2 text-text-secondary",
};
```
`SetAsideFlags` reuses `VendorsTab.tsx`'s existing `FLAG_DEFS`/`Flags` component verbatim (same `is_8a`/`is_sdvosb`/`is_woman_owned`/`is_hubzone`/`is_veteran_owned`/`is_small_business` keys, same color map) — import/extract if not already exported, otherwise duplicate the ~15-line const (matches the existing precedent of `STATUS_COLORS` being copied rather than shared across tabs in this codebase).

### 6.4 CopyEmailButton

```tsx
function CopyEmailButton({ match, subject, body }: { match: VendorMatch; subject: string | null; body: string | null }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    const text = `Subject: ${subject}\n\n${(body || "").replace(/\{\{vendor_name\}\}/g, match.vendor_name).replace(/\{\{match_reason\}\}/g, match.match_rationale)}`;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={handleCopy} disabled={!body}
            className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded border border-border
                       bg-surface-1 hover:bg-surface-3 text-text-secondary transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px] sm:min-h-0">
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}
```
No toast dependency — inline button-label swap (`"Copy" → "Copied"` for 2s) is used instead, since no global toast system exists yet in the codebase (only documented in `component-patterns.md`, not implemented — confirmed absent from the codebase). This keeps the feature self-contained without introducing a new shared primitive as an unrequested side effect.

## 7. Loading / Empty / No-Solicitation States

Identical structure to `TriageTab.tsx` lines 104–122: `Loader2` spinner centered while `loading`; `"This case has no associated solicitation."` (or fetch error) if `sol === null`. Copy verbatim.

## 8. Polling

Same pattern as `TriageTab.tsx` lines 76–102: poll `GET /api/solicitations/{id}/vendor-matches` every 3s (`POLL_MS = 3000`) only while `matching_status === "running"`; after `triggerVendorMatching()`, poll every 500ms up to 10 times waiting for `matching_status` to leave `"pending"`.

## 9. API Client Additions (`frontend/src/lib/api.ts`)

```tsx
export interface VendorMatch {
  id: number;
  external_id: string;
  solicitation_id: number;
  vendor_id: number;
  rank: number;
  match_score: number;
  match_rationale: string;
  naics_match_type: "exact" | "family" | "capability_only";
  vendor_name: string;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  state: string | null;
  city: string | null;
  naics_code_primary: string | null;
  is_small_business: boolean;
  is_sdvosb: boolean;
  is_hubzone: boolean;
  is_8a: boolean;
  is_woman_owned: boolean;
  is_veteran_owned: boolean;
  created_at: string;
}

export interface VendorMatchesResponse {
  matching_status: "pending" | "running" | "complete" | "failed";
  matching_error: string | null;
  outreach_email_subject: string | null;
  outreach_email_body: string | null;
  matches: VendorMatch[];
}

export const getVendorMatches = (solicitationId: number): Promise<VendorMatchesResponse> =>
  fetchAPI(`/api/solicitations/${solicitationId}/vendor-matches`);

export const triggerVendorMatching = (
  solicitationId: number,
): Promise<{ job_id: number; matching_status: string }> =>
  fetchAPI(`/api/solicitations/${solicitationId}/vendor-matching`, { method: "POST" });
```

Also extend the existing `Solicitation` interface (already in `api.ts`) with the four new columns from `01-schema.sql`: `matching_status`, `matching_error`, `outreach_email_subject`, `outreach_email_body` — required since `VendorMatchesTab` reads them off the same `SolicitationWithDocuments` object returned by `getSolicitationByCase` (per `02-api-contract.json`'s design: the trigger/status fields live on `solicitations`, only the ranked rows come from the dedicated endpoint).

## 10. Design System Compliance

Same checklist as `solicitation-ingestion/04-ui-specs.md` §10 / `component-patterns.md` §12.8 applies unchanged: 44px touch targets on `CopyEmailButton`/trigger button, `hover:`+`active:` pairs, table wrapped `overflow-x-auto`, skeleton-free (spinner acceptable here per `TriageTab.tsx` precedent for this tab shape).
