# 04-ui-specs — Portal MTA Signing UI

> Tokens from `context-engine/standards/01-FRONTEND-STANDARDS/design-system.md` (Tailwind v4 `@theme`). No new UI libraries; useState only (app convention).

## Route: `/portal` (vendor dashboard)

### State A — Unsigned (warning banner, between header and cards)

```
┌────────────────────────────────────────────────────────────────────┐
│ ⚠ Master Teaming Agreement required                                │
│   Please review and sign your Master Teaming Agreement to          │
│   activate your account and receive quote requests.                │
│                                            [Review & Sign]         │
└────────────────────────────────────────────────────────────────────┘
```

- Shell: `bg-warning-bg border border-warning/20 rounded-lg p-3 md:p-4 flex gap-2 md:gap-3` (OverviewTab banner pattern)
- Icon: `AlertCircle` `text-warning shrink-0 mt-0.5` size 18
- Title: `text-sm font-medium text-warning` "Master Teaming Agreement required"
- Body: `text-xs md:text-sm text-text-secondary mt-0.5`
- CTA: `bg-brand hover:bg-brand-hover text-white px-4 py-2 rounded-lg text-sm font-medium` "Review & Sign" → opens MtaSigningModal
- Quote Requests / History cards remain `opacity-50` placeholders (gate carried by banner + future `require_mta` backend check)

### State B — Signed (success banner)

```
┌────────────────────────────────────────────────────────────────────┐
│ ✓ Master Teaming Agreement active                                  │
│   Signed {date} by {signed_name}, {signed_title}.                  │
│                                            [View signed agreement] │
└────────────────────────────────────────────────────────────────────┘
```

- Shell: `bg-success-bg border border-success/20 rounded-lg p-3 md:p-4 flex gap-2 md:gap-3`
- Icon: `CheckCircle2` `text-success shrink-0 mt-0.5` size 18
- CTA: "View signed agreement" → `DocumentPreviewModal docId={document_id} docName="Master Teaming Agreement"` (existing component, iframe PDF)
- Banner persists across sessions (server-derived state)

## Component: `MtaSigningModal`

Props: `{ open: boolean, previewUrl: string, previewName: string, businessName: string, onClose: () => void, onSigned: (a: MtaAgreement) => void }`

- **Full screen** (user-confirmed 2026-08-16): container `fixed inset-0 z-50 bg-surface-0 flex flex-col` — the modal IS the screen. Sticky header bar (h-14, border-b, matching portal header: title + businessName subtitle + close button); content `max-w-5xl w-full mx-auto px-4 py-6 flex-1 overflow-y-auto`. Escape + close button close; body scroll lock
- Preview: `<iframe src={previewUrl} className="w-full h-[62vh] rounded-lg border border-border bg-surface-1" />` (presigned URL — no auth header needed). Caption: "Preview — no signature has been captured."
- Form fields in a `grid grid-cols-1 md:grid-cols-2 gap-4` (name + title side by side on desktop)
- Form (vendor-register input classes): `mt-1 w-full px-3 py-2.5 text-sm bg-surface-1 border border-border rounded-lg text-text-primary outline-none focus:border-brand`
  - "Signed name (legal name of authorized signatory)" — text input
  - "Title" — text input
  - Consent checkbox `size-4 rounded-sm border-border-strong bg-surface-2 text-brand` + label: "I have reviewed this Master Teaming Agreement, understand its terms, and agree to be legally bound. My typed name constitutes my electronic signature (E-SIGN Act 15 U.S.C. §7001; Georgia UETA O.C.G.A. §10-12)."
- Submit: "Sign & Submit" `bg-brand hover:bg-brand-hover text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors`, `disabled:opacity-50` unless `name && title && consent && !loading` (Loader2 spinner while loading)
- Error box: `mb-4 px-3 py-2 text-xs text-danger bg-danger-bg rounded-lg` (settings page pattern)
- Success: call `onSigned(agreement)`; parent closes modal + banner flips to State B
- Presigned URL expiry (1h): iframe shows blank → surface inline error "Preview link expired — close and reopen to refresh" rather than silent blank

## Loading states

- Portal: while `getMyMtaStatus()` in flight, render neither banner (avoid banner flash) — cards render as today
- Modal submit: spinner + disabled; errors from API (`err.detail`) shown in error box
