# Component Patterns — Behavior & Interaction

> **Purpose:** How components behave. If the design-system.md defines the paint, this file defines the engineering. AI agents reference this file for interaction patterns, state management, form validation, and data flow.
>
> **Companion to:** `design-system.md` — read both before writing any component.

---

## 1. Forms

### 1.1 Default Form Layout

```tsx
// Vertical layout — use in 95% of cases
<form onSubmit={handleSubmit} className="flex flex-col gap-4">
  <div className="flex flex-col gap-1.5">
    <label htmlFor="name" className="block text-sm font-medium text-text-secondary">
      Case Name
    </label>
    <input id="name" type="text" {...register("name")} className="..." />
    {errors.name && <p className="text-xs text-danger">{errors.name.message}</p>}
  </div>
  {/* ... more fields ... */}
  <div className="flex items-center justify-end gap-3 pt-2">
    <button type="button" onClick={onCancel} className="/* secondary */">Cancel</button>
    <button type="submit" disabled={isSubmitting} className="/* primary */">
      {isSubmitting ? "Saving..." : "Save"}
    </button>
  </div>
</form>
```

### 1.2 Form Rules

1. **Label above input** — always. Never side-by-side labels except in dense settings tables.
2. **Label is `text-sm font-medium text-text-secondary`** — not bold, not primary.
3. **Error message below the input** — `text-xs text-danger`. Replaces helper text when present.
4. **Submit button is always right-aligned** — paired with a Cancel button to its left.
5. **Disable submit while submitting** — show "Saving..." or spinner text.
6. **Auto-focus the first input** on modal forms with `autoFocus`.
7. **Validation on blur + submit** — not on every keystroke. Use `mode: "onBlur"` with react-hook-form, or validate in the submit handler.

### 1.3 Form State Machine

```
IDLE → (user types) → DIRTY → (submit) → SUBMITTING → (success) → SUCCESS
                                                    → (error)   → ERROR → (retry) → SUBMITTING
```

- **IDLE:** Form rendered, untouched.
- **DIRTY:** User has modified at least one field.
- **SUBMITTING:** Request in flight. Submit button disabled, shows spinner text.
- **SUCCESS:** Show success toast/message. Close modal if applicable. Do NOT clear the form — let the parent unmount it.
- **ERROR:** Show server error near the submit button. Keep all field values intact. User can retry.

### 1.4 Field Types

#### Select / Dropdown
```tsx
// Use a headless listbox or native <select> styled.
// Native select is preferred for simplicity:
<select className="w-full px-3 py-2 text-sm text-text-primary bg-surface-2 border border-border
                   rounded-sm focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                   transition-colors duration-150">
  <option value="">Select...</option>
  {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
</select>
```

#### Checkbox Group
```tsx
<fieldset className="flex flex-col gap-2">
  <legend className="text-sm font-medium text-text-secondary mb-1">Label</legend>
  {options.map(o => (
    <label key={o.value} className="inline-flex items-center gap-2 cursor-pointer">
      <input type="checkbox" value={o.value} className="size-4 rounded-sm ..." />
      <span className="text-sm text-text-primary">{o.label}</span>
    </label>
  ))}
</fieldset>
```

#### Textarea (for narratives / long text)
```tsx
// ALWAYS give the user a generous area. Legal narratives are long.
<textarea rows={8} className="..." />
// Show character count if there's a limit:
<p className="text-xs text-text-disabled text-right mt-1">{length}/{max}</p>
```

---

## 2. Modals

### 2.1 When to Use a Modal

- **YES:** Confirm destructive action, quick form (create case, add party), detail view that needs focus.
- **NO:** Multi-step workflows (use a full page), anything with more than 6 fields, anything the user needs to reference while scrolling.

### 2.2 Modal Behavior

- **Desktop:** Centered dialog with `min-w-[400px]`.
- **Mobile (<640px):** Full-width bottom sheet. Rounded top corners. Drag handle. Taller close button (44px). Animate slide-in from bottom instead of zoom-in.
- **Both:** Close on overlay tap, close on Escape, lock body scroll, restore focus on close.

### 2.3 Modal Implementation Pattern

```tsx
"use client";
import { useEffect, useRef, useCallback } from "react";
import { X } from "lucide-react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: "sm" | "md" | "lg";
}

const SIZES = {
  sm: "sm:min-w-[320px]",
  md: "sm:min-w-[400px]",
  lg: "sm:min-w-[560px]",
};

export function Modal({ open, onClose, title, children, footer, size = "md" }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  const onKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement as HTMLElement;
    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
      previousFocus.current?.focus();
    };
  }, [open, onKeyDown]);

  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 bg-black/60 flex items-end sm:items-center justify-center p-0 sm:p-4"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div
        className={`
          bg-surface-1 border border-border rounded-t-xl sm:rounded-xl shadow-md
          w-full ${SIZES[size]} sm:max-w-[90vw]
          max-h-[90dvh] sm:max-h-[85vh] overflow-y-auto
          p-5 sm:p-6
          animate-in duration-250
          slide-in-from-bottom-4 sm:slide-in-from-bottom-0 sm:zoom-in-95
        `}
      >
        {/* Drag handle — mobile only */}
        <div className="sm:hidden w-10 h-1 bg-surface-5 rounded-full mx-auto mb-4" />

        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
          <button
            onClick={onClose}
            className="min-h-[44px] min-w-[44px] sm:size-8 rounded-sm inline-flex items-center justify-center
                       text-text-secondary hover:bg-surface-2 hover:text-text-primary
                       transition-colors duration-150"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div>{children}</div>

        {/* Footer — stacked on mobile, row on desktop */}
        {footer && (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end gap-2 sm:gap-3
                          mt-6 pt-4 border-t border-border">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
```

### 2.3 Modal Rules

1. **Close on overlay click** — but only if the click target IS the overlay, not a child.
2. **Close on Escape** — always.
3. **Lock body scroll** — `document.body.style.overflow = "hidden"` while open.
4. **Restore focus** — return focus to the trigger element on close.
5. **One modal at a time** — never stack modals.
6. **Footer buttons:** Cancel (secondary) on the left, Confirm/Primary on the right.
7. **Destructive confirms:** Use danger button for the confirm action.

---

## 3. Toast / Notifications

### 3.1 Implementation

Use a lightweight custom toast, NOT a heavy library. The toast is a fixed-position card at the bottom-right.

```tsx
// Toasts appear bottom-right, stack vertically, auto-dismiss
// Types: success | error | warning | info
// Duration: 5s default, 10s for errors, 3s for success

interface Toast {
  id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  description?: string;
}
```

### 3.2 Visual Pattern

```html
<!-- Desktop: bottom-right. Mobile: bottom-center, above tab bar. -->
<div class="fixed bottom-16 sm:bottom-4 right-4 z-[100] flex flex-col gap-2 w-[calc(100vw-2rem)] sm:w-auto max-w-[360px] pb-[env(safe-area-inset-bottom,0px)]">
  <div class="bg-surface-4 border border-border rounded-lg shadow-md p-3 flex items-start gap-3
              animate-in slide-in-from-bottom-2 sm:slide-in-from-right-2 fade-in duration-250">
    <!-- icon: success=green, error=red, warning=amber, info=blue -->
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium text-text-primary">Title</p>
      <p class="text-xs text-text-secondary mt-0.5">Description</p>
    </div>
    <button class="size-5 text-text-disabled hover:text-text-secondary shrink-0 mt-0.5"
            aria-label="Dismiss"><X size={14} /></button>
  </div>
</div>
```

### 3.3 Toast Rules

1. **Bottom-right placement** — always.
2. **Max 3 visible** — older ones auto-dismiss.
3. **Auto-dismiss:** success=3s, info=5s, warning=7s, error=10s.
4. **User can dismiss manually** via X button.
5. **No action buttons in toasts** — if the user needs to act, use a modal or inline state.

---

## 4. Navigation

### 4.1 Primary Navigation: Icon Rail

```tsx
// Left-edge vertical icon bar. Width: w-12 (48px).
// Icons are 20px, stacked vertically with gap-4.
// Active icon: bg-surface-2 + brand text color.
// Inactive icon: text-text-secondary, hover:bg-surface-2 hover:text-text-primary.

<nav className="w-12 h-full bg-surface-1 border-r border-border flex flex-col items-center py-3 gap-1 shrink-0">
  {items.map(item => (
    <button
      key={item.id}
      onClick={() => onNavigate(item.id)}
      className={cn(
        "size-10 rounded-lg inline-flex items-center justify-center transition-colors duration-150",
        item.active
          ? "bg-surface-2 text-brand"
          : "text-text-secondary hover:bg-surface-2 hover:text-text-primary"
      )}
      aria-label={item.label}
    >
      <item.icon size={20} />
    </button>
  ))}
</nav>
```

### 4.2 Breadcrumbs

```tsx
<nav className="flex items-center gap-1 text-sm text-text-secondary">
  <a href="/cases" className="hover:text-text-primary transition-colors duration-150">Cases</a>
  <ChevronRight size={14} className="text-text-disabled" />
  <span className="text-text-primary font-medium">Alhad v. Edmonds</span>
</nav>
```

### 4.3 Tabs (Within a Page)

```tsx
<div className="flex border-b border-border gap-0">
  {tabs.map(tab => (
    <button
      key={tab.id}
      className={cn(
        "px-4 py-2.5 text-sm font-medium border-b-2 transition-colors duration-150",
        tab.active
          ? "border-brand text-brand"
          : "border-transparent text-text-secondary hover:text-text-primary hover:border-border-strong"
      )}
    >
      {tab.label}
    </button>
  ))}
</div>
```

---

## 5. Data Loading Patterns

### 5.1 Page-Level Data Fetch (Server Component)

```tsx
// Next.js App Router — fetch in server component, pass to client components
export default async function CasePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const case = await api.getCase(id);  // throws to error boundary on failure
  return <CaseView case={case} />;
}
```

### 5.2 Client-Side Fetch (for mutations and interactive data)

```tsx
// State machine: idle → loading → loaded | error
function useData<T>(fetcher: () => Promise<T>) {
  const [state, setState] = useState<{
    status: "idle" | "loading" | "loaded" | "error";
    data: T | null;
    error: Error | null;
  }>({ status: "idle", data: null, error: null });

  const execute = useCallback(async () => {
    setState({ status: "loading", data: null, error: null });
    try {
      const data = await fetcher();
      setState({ status: "loaded", data, error: null });
    } catch (error) {
      setState({ status: "error", data: null, error: error as Error });
    }
  }, [fetcher]);

  return { ...state, execute, isLoading: state.status === "loading" };
}
```

### 5.3 Loading States

- **Page load:** Skeleton (not spinner). Spinners for full-page loads look broken.
- **Button action:** Replace button text with "Saving..." or a small spinner + "Loading".
- **Inline refresh:** Subtle opacity pulse on the stale section.
- **Initial page load (SSR):** The server renders the loading state — no client flash.

### 5.4 Error Handling

- **Server errors in forms:** Display below the submit button: `bg-danger-bg border border-danger/20 rounded-lg p-3 text-sm text-danger`.
- **Page-level errors:** Use Next.js `error.tsx` boundary. Show error message + retry button.
- **Network errors:** "Unable to connect. Check your connection and try again." + retry button.
- **404:** "Case not found. It may have been deleted or you may not have access."

---

## 6. Confirmation Dialogs

### 6.1 Destructive Actions

Always confirm before: delete, archive, remove, disconnect.

```tsx
// Use the Modal component with a danger-styled confirm button
<Modal open={showConfirm} onClose={() => setShowConfirm(false)} title="Delete Case">
  <p className="text-sm text-text-secondary">
    This will permanently delete <strong className="text-text-primary">Alhad v. Edmonds</strong> and all associated documents, evidence, and workspaces. This action cannot be undone.
  </p>
  {/* Modal footer passed as prop */}
</Modal>
```

### 6.2 Unsaved Changes

```tsx
// Warn before navigating away from a dirty form
useEffect(() => {
  if (!isDirty) return;
  const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); };
  window.addEventListener("beforeunload", handler);
  return () => window.removeEventListener("beforeunload", handler);
}, [isDirty]);
```

---

## 7. File Upload

### 7.1 Upload Zone

```tsx
<div
  onDragOver={...} onDrop={...}
  className="border-2 border-dashed border-border rounded-lg p-8
             flex flex-col items-center justify-center gap-3
             hover:border-brand hover:bg-brand-bg/30 transition-colors duration-150
             cursor-pointer"
>
  <Upload size={32} className="text-text-disabled" />
  <div className="text-center">
    <p className="text-sm text-text-primary">
      <span className="text-brand font-medium">Click to upload</span> or drag and drop
    </p>
    <p className="text-xs text-text-disabled mt-1">PDF, DOCX, or TXT up to 50MB</p>
  </div>
</div>
```

### 7.2 Upload Progress

```tsx
<div className="flex items-center gap-3 p-3 bg-surface-2 rounded-lg">
  <FileText size={18} className="text-text-secondary shrink-0" />
  <div className="flex-1 min-w-0">
    <p className="text-sm text-text-primary truncate">medical-records.pdf</p>
    <p className="text-xs text-text-disabled">2.4 MB — Uploading...</p>
  </div>
  {/* Progress bar */}
  <div className="w-24 h-1.5 bg-surface-3 rounded-full overflow-hidden">
    <div className="h-full bg-brand rounded-full transition-all duration-300" style={{ width: "60%" }} />
  </div>
</div>
```

---

## 8. Keyboard Shortcuts

| Shortcut | Action | Scope |
|---|---|---|
| `Escape` | Close modal / deselect / blur input | Global (when modal open) |
| `Enter` | Submit form (when focus is in form) | Form |
| `Cmd+Enter` | Submit main form / send chat message | Chat, main forms |
| `Cmd+K` | Open command palette / search | Global |
| `Tab` | Navigate between form fields | Form |
| `Space` | Toggle checkbox / activate button | Focused element |

---

## 9. Focus Management

1. **Modal opens →** focus the first focusable element (usually the close button or first input).
2. **Modal closes →** return focus to the trigger element.
3. **Form error →** focus the first field with an error.
4. **New page →** focus the `<main>` content area (skip nav) with `tabIndex={-1}`.
5. **Visible focus rings on all interactive elements** — `focus-visible:ring-2 focus-visible:ring-brand-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface-1 focus-visible:outline-hidden`.

---

## 10. React-Specific Conventions

### 10.1 Component File Structure

```
components/
├── CaseCard.tsx          # Single component? One file.
├── CaseCard/             # Multiple files? Folder.
│   ├── index.tsx         # Public API
│   ├── CaseCard.tsx      # Main component
│   ├── CaseCardSkeleton.tsx
│   └── CaseCard.test.tsx
```

### 10.2 "use client" Boundaries

- **Server component by default.** Only add `"use client"` when you need: `useState`, `useEffect`, `useContext`, event handlers (`onClick`), browser APIs.
- **Push `"use client"` down** — mark the leaf component, not the page.
- **Data fetching in server components** — pass data as props to client components.

### 10.3 Props Naming

```tsx
interface CaseCardProps {
  case: Case;           // The data object (always required unless skeleton)
  onSelect?: (id: string) => void;  // Event handlers: on + Verb
  isSelected?: boolean;  // Boolean states: is/has prefix
  variant?: "default" | "compact";  // Visual variants
  className?: string;    // Always accept className for composition
}
```

### 10.4 State Management

- **Local state:** `useState` — form inputs, toggle states, UI-only concerns.
- **URL state:** `useSearchParams` — filters, pagination, selected tab, search queries. Shareable.
- **Context:** Only for truly global concerns: auth, theme, current case ID.
- **No Redux / Zustand / Jotai** — not needed at this scale. Add only when the pain is real.

---

## 11. API Client Pattern

```tsx
// lib/api.ts — centralized API client
const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || body.message || res.statusText);
  }
  return res.json();
}

export const api = {
  cases: {
    list: () => request<Case[]>("/api/cases"),
    get: (id: string) => request<Case>(`/api/cases/${id}`),
    create: (data: CreateCase) => request<Case>("/api/cases", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: UpdateCase) => request<Case>(`/api/cases/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/api/cases/${id}`, { method: "DELETE" }),
  },
  documents: {
    upload: (caseId: string, file: File) => { /* FormData, no JSON header */ },
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}
```

### 11.1 Error Handling Convention

```tsx
// Server components: let errors propagate to error.tsx boundary
// Client mutations: try/catch + set error state
const handleSubmit = async () => {
  try {
    setStatus("submitting");
    await api.cases.create(data);
    toast.success("Case created");
    onClose();
  } catch (err) {
    setStatus("error");
    setError(err instanceof ApiError ? err.message : "Something went wrong");
  }
};
```

---

## 12. Mobile-Specific Patterns

### 12.1 Touch vs. Hover

Every interactive element must handle both:

```tsx
// Hover for desktop, active for touch — BOTH required
<button className="hover:bg-surface-2 active:bg-surface-3
                   hover:text-brand active:text-brand
                   transition-colors duration-150">
```

**Rule:** `hover:` and `active:` must always be paired. A `hover:` without an `active:` is a desktop-only component.

### 12.2 Touch Target Enforcement

```html
<!-- Inline icon buttons: expand hit area without changing visual size -->
<button class="relative size-8 sm:size-8 min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0
               inline-flex items-center justify-center rounded-sm">
  <Icon size={18} />
</button>

<!-- Expand checkbox/label hit area -->
<label class="inline-flex items-center gap-2 p-2 -m-2 cursor-pointer rounded-sm
              hover:bg-surface-2 active:bg-surface-3">
  <input type="checkbox" class="size-4 shrink-0 ..." />
  <span class="text-sm text-text-primary">Remember me</span>
</label>
```

### 12.3 Mobile Viewport Height (`dvh`)

```css
/* Use dvh for full-screen panels — accounts for mobile browser chrome */
.full-panel { height: 100dvh; }
.min-full  { min-height: 100dvh; }
```

Never use `100vh` for full-screen mobile layouts. Mobile browsers show/hide the address bar, and `100vh` doesn't account for this. `100dvh` (dynamic viewport height) does.

### 12.4 Mobile File Upload

```tsx
// Drag-and-drop on desktop, tap-to-browse on mobile.
// Both use the same hidden <input type="file">.
function UploadZone({ onFiles }: { onFiles: (files: File[]) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.txt,.png,.jpg"
        className="hidden"
        onChange={(e) => {
          if (e.target.files) onFiles(Array.from(e.target.files));
          e.target.value = ""; // allow re-upload of same file
        }}
      />
      <button
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          if (e.dataTransfer.files) onFiles(Array.from(e.dataTransfer.files));
        }}
        className={`
          border-2 border-dashed rounded-lg p-8 w-full
          flex flex-col items-center justify-center gap-3
          transition-colors duration-150 cursor-pointer
          ${isDragOver ? "border-brand bg-brand-bg/30" : "border-border hover:border-brand active:border-brand"}
        `}
      >
        <Upload size={32} className="text-text-disabled" />
        <div className="text-center">
          <p className="text-sm text-text-primary">
            <span className="text-brand font-medium">Click to upload</span>
            {" "}or drag and drop
          </p>
          <p className="text-xs text-text-disabled mt-1">PDF, DOCX, or TXT up to 50MB</p>
        </div>
      </button>
    </>
  );
}
```

**Rules:**
- The entire zone is a `<button>` — works on tap and click.
- The hidden `<input>` handles the native file picker on both platforms.
- Drag-and-drop is a progressive enhancement — the tap flow always works.
- Reset `e.target.value = ""` after selection so the user can re-upload the same file.

### 12.5 Dropdown Menu (Tap-to-Open)

```tsx
// Never use hover to open dropdowns. Use click/tap toggle.
function Dropdown({ trigger, children }: { trigger: React.ReactNode; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div ref={ref} className="relative inline-block">
      <button onClick={() => setOpen(!open)} className="min-h-[44px] sm:min-h-0 ...">
        {trigger}
      </button>
      {open && (
        <div className="absolute top-full right-0 mt-1 z-50
                        bg-surface-4 border border-border rounded-lg shadow-md p-1 min-w-[180px]
                        animate-in fade-in zoom-in-95 duration-150">
          {/* Menu items: 44px min-height on mobile */}
          {children}
        </div>
      )}
    </div>
  );
}

// Menu item
<button className="w-full text-left px-3 py-2 min-h-[44px] sm:min-h-0 text-sm text-text-primary
                   hover:bg-surface-3 active:bg-surface-5 rounded-sm transition-colors duration-100">
  Action
</button>
```

### 12.6 Loading Skeletons (Mobile)

```html
<!-- Skeleton cards instead of spinner for page loads -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4 lg:p-6">
  {Array.from({ length: 6 }).map((_, i) => (
    <div key={i} class="bg-surface-1 border border-border rounded-lg p-4 animate-pulse">
      <div class="h-5 bg-surface-3 rounded w-2/3 mb-3" />
      <div class="h-4 bg-surface-3 rounded w-full mb-2" />
      <div class="h-4 bg-surface-3 rounded w-4/5" />
    </div>
  ))}
</div>
```

**Rule:** Use skeletons for page/panel loads, spinners only for button actions and inline refreshes.

### 12.7 Preventing iOS Overscroll / Bounce

```css
/* globals.css — prevent the elastic bounce on fixed full-screen panels */
body.modal-open {
  overscroll-behavior: none;
  -webkit-overflow-scrolling: auto;
}
```

Apply `body.modal-open` class when a modal or full-screen panel is visible. Remove it on close.

### 12.8 Mobile Check: Before Marking Any Component "Done"

Every component must pass this checklist before it's considered complete:

1. **Touch target ≥44px** on all interactive elements in the mobile layout (`min-h-[44px] min-w-[44px]`).
2. **No hover-only interactions.** Every `hover:` has a matching `active:`.
3. **Tables wrapped** in `overflow-x-auto` with `-mx-4 px-4` for full-bleed scroll.
4. **Modals are bottom sheets** on screens <640px.
5. **Toast/notifications are above the bottom tab bar** (`bottom-16` not `bottom-4`).
6. **`100dvh` not `100vh`** for full-screen panels.
7. **Safe area padding** on bottom-fixed elements (`pb-[env(safe-area-inset-bottom,0px)]`).
8. **Form buttons are full-width and stacked** on mobile.
9. **Font size ≥16px** on all form inputs (prevents iOS zoom).
10. **No `user-select: none`** on text content — users must be able to select and copy.
