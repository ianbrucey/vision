# Design System — "Command"

> **Purpose:** Eliminate ALL ambiguity about visual decisions. Every color, size, radius, and spacing value is defined here. AI agents reference this file — they do not invent values.
>
> **Theme:** Light. Professional. Legal-grade. Clean and readable.

---

## 1. Color Palette

### 1.1 Surface Hierarchy (lightest → darkest)

```
Surface 0 (root)       #FAFBFC   --surface-0    Viewport background
Surface 1 (primary)    #FFFFFF   --surface-1    Cards, panels, modals
Surface 2 (secondary)  #F5F6F8   --surface-2    Nested cards, hover states
Surface 3 (tertiary)   #EBEDF0   --surface-3    Code blocks, footers, dividers
Surface 4 (elevated)   #FFFFFF   --surface-4    Tooltips, dropdowns, popovers (white + shadow)
Surface 5 (active)     #E1E4E8   --surface-5    Selected/active surfaces
```

### 1.2 Text

```
Primary      #1A1D26   --text-primary     Body, headings, labels
Secondary    #5F6675   --text-secondary   Descriptions, captions, metadata
Disabled     #9DA3AE   --text-disabled    Placeholders, disabled inputs, inactive icons
Inverse      #FFFFFF   --text-inverse     Text on dark/brand backgrounds
```

### 1.3 Accent — Warm Amber

The Ross brand color. Primary actions, active states, brand elements.
Darker than the dark-theme amber — needs more contrast on white backgrounds.

```
Brand           #B8860B   --brand
Brand-hover     #9F7309   --brand-hover
Brand-active    #866007   --brand-active
Brand-bg        #FFF7EB   --brand-bg       Amber tint — very subtle on white
Brand-ring      rgba(184, 134, 11, 0.2)    Focus rings
```

### 1.4 Semantic

```
Success         #2D8A4E   --success
Success-bg      #EDF7F0   --success-bg

Warning         #B85C0A   --warning
Warning-bg      #FFF8F0   --warning-bg

Danger          #C53030   --danger
Danger-bg       #FEF2F2   --danger-bg

Info            #3B6CB5   --info
Info-bg         #F0F5FC   --info-bg
```

### 1.5 Borders

```
Border           #E1E4E8   --border          Default (matches surface-5)
Border-light     #EBEDF0   --border-light    Subtle (matches surface-3)
Border-strong    #C4C9D2   --border-strong   Emphasis
Border-accent    rgba(184, 134, 11, 0.15)    Amber at 15% opacity
```

### 1.6 Special Purpose

```
Message-user     #F0F5FC   --msg-user-bg     User chat bubble (light blue tint)
Message-system   #F5F6F8   --msg-system-bg   System message background (warm gray)
```

### 1.7 Tailwind Theme Extension

```css
/* globals.css */
@import "tailwindcss";

@theme inline {
  /* Surfaces */
  --color-surface-0: #FAFBFC;
  --color-surface-1: #FFFFFF;
  --color-surface-2: #F5F6F8;
  --color-surface-3: #EBEDF0;
  --color-surface-4: #FFFFFF;
  --color-surface-5: #E1E4E8;

  /* Text */
  --color-text-primary: #1A1D26;
  --color-text-secondary: #5F6675;
  --color-text-disabled: #9DA3AE;

  /* Accent */
  --color-brand: #B8860B;
  --color-brand-hover: #9F7309;
  --color-brand-active: #866007;
  --color-brand-bg: #FFF7EB;
  --color-brand-ring: rgba(184, 134, 11, 0.2);

  /* Semantic */
  --color-success: #2D8A4E;
  --color-success-bg: #EDF7F0;
  --color-warning: #B85C0A;
  --color-warning-bg: #FFF8F0;
  --color-danger: #C53030;
  --color-danger-bg: #FEF2F2;
  --color-info: #3B6CB5;
  --color-info-bg: #F0F5FC;

  /* Borders */
  --color-border: #E1E4E8;
  --color-border-light: #EBEDF0;
  --color-border-strong: #C4C9D2;

  /* Misc */
  --color-msg-user: #F0F5FC;
  --color-msg-system: #F5F6F8;

  /* Fonts */
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
}
```

---

## 2. Typography

### 2.1 Font Stack

- **Sans:** Geist Sans (from `next/font/google`, already loaded in layout)
- **Mono:** Geist Mono — code, citations, block IDs, timestamps

### 2.2 Type Scale (Tailwind classes — use these EXACTLY)

| Size | Class | Weight | Line Height | Use |
|---|---|---|---|---|
| 11px | `text-xs` | 400 | `leading-relaxed` | Captions, block IDs, footnotes |
| 13px | `text-sm` | 400 | `leading-relaxed` | Metadata, timestamps, helper text |
| 14px | `text-sm/[1.6]` | 400 | 1.6 | Form labels, secondary nav, table cells |
| 15px | `text-base` | 400 | `leading-relaxed` | **Body default** — prose, descriptions |
| 16px | `text-base/[1.6]` | 400 | 1.6 | Chat messages, list items |
| 18px | `text-lg` | 500 | `leading-snug` | Card titles, section headers |
| 22px | `text-xl` | 600 | `leading-snug` | Page section headings |
| 28px | `text-2xl` | 600 | `leading-tight` | Page titles |
| 36px | `text-3xl` | 700 | `leading-tight` | Hero, case name display |

**Rules:**
- **NEVER** use `font-light` or `font-thin` — fails on dark backgrounds.
- **NEVER** use `font-extrabold` or `font-black` — looks shouty.
- Body text is always `text-base` (15px/16px). Don't mix sizes for prose.
- Headings descend the scale: `text-2xl` → `text-xl` → `text-lg` → `text-base`.

### 2.3 Links

```html
<a class="text-info hover:text-brand underline-offset-2 hover:underline transition-colors duration-150">
```
**Rule:** Links are `--info` (steel blue) by default, shift to `--brand` (amber) on hover. Underline only on hover.

---

## 3. Spacing

**Base unit: 4px.** All gaps, padding, and margins are multiples of 4.

| Token | Tailwind | Value | Use |
|---|---|---|---|
| 0 | `gap-0 p-0` | 0 | |
| 1 | `gap-1 p-1` | 4px | Icon-label gap, tight inline |
| 2 | `gap-2 p-2` | 8px | Standard inline gap, compact padding |
| 3 | `gap-3 p-3` | 12px | Comfortable padding, card internals |
| 4 | `gap-4 p-4` | 16px | Standard padding, section gap |
| 5 | `gap-5 p-5` | 20px | Generous padding |
| 6 | `gap-6 p-6` | 24px | Section separation, modal padding |
| 8 | `gap-8 p-8` | 32px | Page padding, large sections |
| 10 | `gap-10 p-10` | 40px | Major layout separation |
| 12 | `gap-12 p-12` | 48px | Hero sections |
| 16 | `gap-16 p-16` | 64px | Page-level top/bottom |

**Rules:**
- Component internal padding: `p-3` (12px) or `p-4` (16px)
- Adjacent element gap: `gap-2` (8px) or `gap-3` (12px)
- Section separation: `gap-6` (24px) or `gap-8` (32px)
- **NEVER use arbitrary values like `p-[6px]`, `gap-[10px]`, `p-[14px]`** — multiples of 4 only.

---

## 4. Border Radius

| Token | Tailwind | Use |
|---|---|---|
| None | `rounded-none` | Tables, code blocks, sharp containers |
| Sm | `rounded-sm` (4px) | Inputs, tags, badges, small buttons |
| Md | `rounded-lg` (8px) | **DEFAULT** — cards, panels, buttons, dropdowns, modals |
| Lg | `rounded-xl` (12px) | Large containers, feature cards |
| Full | `rounded-full` | Pills, avatars, toggle chips |

**Rule:** Use `rounded-lg` (8px) as the default. Only deviate when there's a specific reason.

---

## 5. Shadows

```css
/* Only two elevation levels. Colored glows are forbidden. */
--shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06);    /* Cards on surface-0 */
--shadow-md: 0 4px 16px rgba(0, 0, 0, 0.1);    /* Modals, dropdowns, popovers */
```

**Rules:**
- Cards on the root background (`surface-0`) don't need shadows — surface contrast is enough.
- Cards nested inside cards use `shadow-sm`.
- Modals and dropdowns use `shadow-md`.
- **No colored glows.** No `shadow-brand`. No gradient shadows. Restrained.

---

## 6. Transitions

| Duration | Tailwind class | Use |
|---|---|---|
| 100ms | `duration-100` | Color/background changes, icon hover |
| 150ms | `duration-150` | **DEFAULT** — hover, focus, toggle |
| 250ms | `duration-250` | Panel open/close, modal enter/exit |
| 400ms | `duration-400` | Page transitions |

**Easing:** Always `ease-out` for appearing elements, `ease-in` for disappearing, `ease-in-out` for symmetrical transitions. Use Tailwind's built-in easing classes.

**What gets animated:** `background-color`, `color`, `border-color`, `opacity`, `transform` (scale, translate).
**What does NOT:** `display`, `height: auto → 0`, text content, position changes.

---

## 7. Component Specifications

### 7.1 Buttons

```html
<!-- Base shared classes -->
inline-flex items-center justify-center gap-2
font-medium text-sm leading-none
rounded-lg transition-colors duration-150
cursor-pointer select-none whitespace-nowrap
disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none
border border-transparent

<!-- Sizes -->
<!-- sm:  px-2.5 py-1 text-xs rounded-sm -->
<!-- md:  px-4 py-2 text-sm            (DEFAULT) -->
<!-- lg:  px-6 py-3 text-base          -->

<!-- Primary (brand amber) -->
<button class="bg-brand text-white border-brand
               hover:bg-brand-hover active:bg-brand-active
               focus-visible:ring-2 focus-visible:ring-brand-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface-1
               px-4 py-2 rounded-lg text-sm font-medium">
  Primary Action
</button>

<!-- Secondary -->
<button class="bg-surface-2 text-text-primary border-border
               hover:bg-surface-3 hover:border-border-strong
               active:bg-surface-4
               px-4 py-2 rounded-lg text-sm font-medium">
  Secondary Action
</button>

<!-- Ghost -->
<button class="text-text-secondary hover:bg-surface-2 hover:text-text-primary
               active:bg-surface-3
               px-4 py-2 rounded-lg text-sm font-medium">
  Ghost Action
</button>

<!-- Danger -->
<button class="bg-danger text-white border-danger
               hover:opacity-90 active:opacity-85
               px-4 py-2 rounded-lg text-sm font-medium">
  Destructive Action
</button>

<!-- Icon-only -->
<button class="inline-flex items-center justify-center
               size-8 rounded-sm text-text-secondary
               hover:bg-surface-2 hover:text-text-primary
               transition-colors duration-150">
  <!-- icon 18px -->
</button>
```

### 7.2 Inputs

```html
<!-- Standard input -->
<input class="w-full px-3 py-2 text-sm text-text-primary
              bg-surface-2 border border-border rounded-sm
              placeholder:text-text-disabled
              focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
              disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-surface-1
              transition-colors duration-150" />

<!-- Error state -->
<input class="... border-danger focus:border-danger focus:ring-danger/20" />

<!-- Label -->
<label class="block mb-1.5 text-sm font-medium text-text-secondary">
  Field Label
</label>

<!-- Helper text -->
<p class="mt-1 text-xs text-text-disabled">Helper description</p>

<!-- Error text -->
<p class="mt-1 text-xs text-danger">Error message</p>
```

### 7.3 Textarea

```html
<textarea class="w-full px-3 py-2 text-sm text-text-primary leading-relaxed
                  bg-surface-2 border border-border rounded-sm
                  placeholder:text-text-disabled
                  focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                  min-h-[80px] resize-y
                  transition-colors duration-150" />
```

### 7.4 Select / Dropdown

Trigger: Same border and focus styles as input.
Dropdown menu:
```html
<div class="bg-surface-4 border border-border rounded-lg shadow-md p-1 min-w-[160px]">
  <!-- options -->
</div>
```

### 7.5 Checkbox & Radio

```
size: 16px × 16px (size-4)
border: 1px solid --border-strong
bg: surface-2
checked: bg-brand border-brand
check mark: white, 2px stroke
```

```html
<input type="checkbox" class="size-4 rounded-sm border-border-strong bg-surface-2
                               text-brand focus:ring-brand-ring focus:ring-2 focus:outline-hidden
                               cursor-pointer" />
```

### 7.6 Toggle / Switch

```html
<button class="relative inline-flex items-center w-10 h-5.5 rounded-full
               transition-colors duration-150
               bg-surface-3 aria-checked:bg-brand">
  <span class="size-4 bg-white rounded-full shadow-sm transition-transform duration-150
               translate-x-0.5 aria-checked:translate-x-5.5" />
</button>
```

---

## 8. Layout Primitives

### 8.1 Card / Panel

```html
<!-- Standard card -->
<div class="bg-surface-1 border border-border rounded-lg p-4">
  ...
</div>

<!-- Hoverable card -->
<div class="bg-surface-1 border border-border rounded-lg p-4
            hover:border-border-strong transition-colors duration-150">
  ...
</div>

<!-- Clickable card -->
<div class="bg-surface-1 border border-border rounded-lg p-4 cursor-pointer
            hover:border-brand transition-colors duration-150"
     role="button" tabindex="0">
  ...
</div>

<!-- Selected card -->
<div class="bg-brand-bg border border-brand rounded-lg p-4">
  ...
</div>
```

### 8.2 Modal

```html
<!-- Overlay -->
<div class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center
            animate-in fade-in duration-250">
  <!-- Container -->
  <div class="bg-surface-1 border border-border rounded-xl shadow-md p-6
              min-w-[400px] max-w-[90vw] max-h-[85vh] overflow-y-auto
              animate-in zoom-in-95 duration-250">
    <!-- Title -->
    <h2 class="text-lg font-semibold text-text-primary mb-4">Modal Title</h2>
    <!-- Body -->
    <div class="text-text-primary">...</div>
    <!-- Actions -->
    <div class="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-border">
      <button class="/* secondary */">Cancel</button>
      <button class="/* primary */">Confirm</button>
    </div>
  </div>
</div>
```

### 8.3 Sidebar / Panel

- Icon rail: `w-12` (48px). Collapsed: `w-0`.
- Left panel: default `w-[280px]`, min `min-w-[200px]`, max `max-w-[500px]`.

### 8.4 Page Layout

```html
<div class="min-h-screen bg-surface-0 text-text-primary flex flex-col">
  <!-- Header -->
  <header class="h-14 border-b border-border bg-surface-1 flex items-center px-4 shrink-0">
    ...
  </header>
  <!-- Body -->
  <div class="flex flex-1 overflow-hidden">
    <!-- Sidebar (optional) -->
    <aside class="w-12 border-r border-border bg-surface-1 shrink-0">...</aside>
    <!-- Main content -->
    <main class="flex-1 overflow-y-auto p-6">...</main>
  </div>
</div>
```

---

## 9. Data Display

### 9.1 Tables

```html
<table class="w-full text-sm">
  <thead>
    <tr class="border-b border-border">
      <th class="text-left font-medium text-text-secondary px-3 py-2.5">Column</th>
    </tr>
  </thead>
  <tbody>
    <tr class="border-b border-border-light hover:bg-surface-2 transition-colors duration-100">
      <td class="px-3 py-2.5 text-text-primary">Data</td>
    </tr>
  </tbody>
</table>
```

### 9.2 Tags / Badges

```html
<span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-sm
             bg-surface-2 text-text-secondary">
  Default
</span>

<span class="... bg-brand-bg text-brand">Brand</span>
<span class="... bg-success-bg text-success">Success</span>
<span class="... bg-warning-bg text-warning">Warning</span>
<span class="... bg-danger-bg text-danger">Danger</span>
<span class="... bg-info-bg text-info">Info</span>
```

### 9.3 Code & Citations

```html
<!-- Inline code -->
<code class="font-mono text-[13px] bg-surface-3 text-text-primary px-1.5 py-0.5 rounded-sm">
  block_id
</code>

<!-- Code block -->
<pre class="bg-surface-3 border border-border rounded-lg p-4 overflow-x-auto
            font-mono text-[13px] leading-relaxed text-text-primary">
  ...
</pre>

<!-- Citation link -->
<a class="text-info font-medium hover:text-brand hover:underline underline-offset-2
          transition-colors duration-150 cursor-pointer">
  Lewis v. Nicholas Financial, 300 Ga. App. 888 (2009)
</a>
```

### 9.4 Status Dots

```html
<!-- Dot + label pattern -->
<span class="inline-flex items-center gap-2 text-sm">
  <span class="size-2 rounded-full bg-success shrink-0" />
  <span class="text-text-primary">Active</span>
</span>

<!-- Dot classes: bg-success | bg-warning | bg-danger | bg-text-disabled -->
```

### 9.5 Dividers

```html
<hr class="border-border" />  <!-- horizontal -->
<div class="w-px bg-border self-stretch" />  <!-- vertical -->
```

### 9.6 Avatars

```html
<div class="size-8 rounded-full bg-surface-3 border border-border flex items-center justify-center
            text-sm font-medium text-text-secondary shrink-0">
  IB
</div>
```

---

## 10. Loading & Empty States

### 10.1 Spinner

```html
<svg class="animate-spin size-5 text-text-disabled" viewBox="0 0 24 24" fill="none">
  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" class="opacity-25" />
  <path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" stroke-linecap="round"
        class="opacity-75" />
</svg>
```

### 10.2 Skeleton

```html
<div class="animate-pulse bg-surface-3 rounded-lg">
  <div class="h-4 w-3/4" />  <!-- or use fixed heights -->
</div>
```

### 10.3 Empty State

```html
<div class="flex flex-col items-center justify-center gap-4 py-16 px-6 text-center">
  <div class="size-12 rounded-full bg-surface-2 flex items-center justify-center text-text-disabled">
    <!-- icon 24px -->
  </div>
  <div>
    <p class="text-sm font-medium text-text-secondary">No cases yet</p>
    <p class="text-xs text-text-disabled mt-1">Create your first case to get started.</p>
  </div>
  <button class="/* primary */">Create Case</button>
</div>
```

### 10.4 Error State

```html
<div class="bg-danger-bg border border-danger/20 rounded-lg p-4">
  <div class="flex items-start gap-3">
    <span class="size-5 text-danger shrink-0 mt-0.5"><!-- icon --></span>
    <div>
      <p class="text-sm font-medium text-danger">Upload failed</p>
      <p class="text-xs text-text-secondary mt-1">The file exceeds the 50MB limit.</p>
      <button class="/* secondary sm */ mt-3">Retry</button>
    </div>
  </div>
</div>
```

---

## 11. Responsive Design

### 11.1 Breakpoints

| Breakpoint | Width | Use |
|---|---|---|
| Default | 0+ | Mobile-first base (phones) |
| `sm` | 640px+ | Large phones / small tablets |
| `md` | 768px+ | Tablets, panel visibility switch |
| `lg` | 1024px+ | Desktop — sidebar visible, multi-column |
| `xl` | 1280px+ | Wide layouts |

### 11.2 Mobile-First Rules (Non-Negotiable)

1. **Single panel at a time <768px.** No side-by-side layouts. One view fills the screen.
2. **Bottom tab bar, not hamburger.** Navigation lives at the bottom for thumb reach. Never hide critical nav behind a drawer icon.
3. **Touch targets ≥44px.** Every interactive element (buttons, links, checkboxes, toggles, dropdown triggers) must be at least `size-11` on mobile. Use `min-h-[44px] min-w-[44px]` for inline elements.
4. **Input font-size ≥16px.** Prevents iOS Safari auto-zoom when focusing inputs.
5. **Safe areas.** Always account for `env(safe-area-inset-bottom)` and `env(safe-area-inset-top)` on notched devices. Add padding to bottom containers and the tab bar.
6. **No hover-dependent interactions.** Hover states are invisible on touch. Every hover effect must have a visible `active:` equivalent. Dropdown menus open on tap, not hover.
7. **Forms: full-width buttons on mobile.** Stack form actions vertically. Cancel above Submit.
8. **Tables: horizontal scroll wrapper.** Wrap all tables in `<div class="overflow-x-auto">`.
9. **Modals become sheets on mobile <640px.** Full-width, bottom-anchored, taller touch-friendly close button.
10. **One-handed thumb zone.** Primary actions in the bottom half of the screen. Don't put critical buttons in the top-right corner.

### 11.3 Responsive Layout Patterns

```html
<!-- Stack on mobile, row on desktop — standard column layout -->
<div class="flex flex-col lg:flex-row gap-4">...</div>

<!-- Sidebar: hidden mobile, icon rail desktop -->
<aside class="hidden lg:flex flex-col w-12 border-r border-border shrink-0">...</aside>

<!-- Content: full-width mobile, constrained desktop -->
<div class="w-full lg:max-w-[720px] mx-auto">...</div>

<!-- Card grid: 1→2→3 columns -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">...</div>

<!-- Page padding: compact mobile, generous desktop -->
<div class="p-4 lg:p-6">...</div>
```

### 11.4 Mobile Navigation: Bottom Tab Bar

```html
<!-- Fixed bottom, always visible. Replaces icon rail on mobile. -->
<nav class="fixed bottom-0 inset-x-0 z-40 lg:hidden
            bg-surface-1 border-t border-border
            flex items-center justify-around
            pb-[env(safe-area-inset-bottom,0px)] h-14">
  {tabs.map(tab => (
    <button class="flex flex-col items-center justify-center gap-0.5 min-w-0 flex-1 h-full
                   text-[10px] font-medium transition-colors duration-150
                   aria-[current=page]:text-brand text-text-secondary">
      <tab.icon size={22} strokeWidth={tab.active ? 2.5 : 2} />
      {tab.label}
    </button>
  ))}
</nav>

<!-- Don't forget: page content needs bottom padding when tab bar is visible -->
<main class="pb-14 lg:pb-0">...</main>
```

**Bottom tab bar rules:**
- Max 4 tabs + 1 "More" overflow (5 total).
- Labels are 10px — no truncation needed at this size.
- Active tab uses brand color + slightly bolder stroke.
- Never hide the tab bar on scroll. Navigation must stay accessible.

### 11.5 Mobile Modal / Sheet

```html
<!-- On mobile (<640px): full-width bottom sheet -->
<!-- On desktop: centered dialog -->
<div class="fixed inset-0 z-50 bg-black/60 flex items-end sm:items-center justify-center">
  <div class="bg-surface-1 border border-border rounded-t-xl sm:rounded-xl shadow-md
              w-full sm:min-w-[400px] sm:max-w-[90vw] max-h-[90dvh] sm:max-h-[85vh]
              overflow-y-auto p-5 sm:p-6
              animate-in slide-in-from-bottom-4 sm:zoom-in-95 duration-250">
    <!-- Drag handle (mobile only) -->
    <div class="sm:hidden w-10 h-1 bg-surface-5 rounded-full mx-auto mb-4" />
    <!-- Close button: 44px on mobile -->
    ...
  </div>
</div>
```

### 11.6 Touch-Aware Interactive Elements

```html
<!-- Card: hover for desktop, active for touch -->
<div class="... hover:border-border-strong active:border-brand
            transition-colors duration-150 cursor-pointer"
     role="button" tabindex={0}>

<!-- Button: minimum touch target on mobile -->
<button class="min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 ...">

<!-- Dropdown: tap to open (never hover-triggered) -->
<!-- Checkbox/Radio: expand hit area with padding or ::before pseudo-element -->
<label class="inline-flex items-center gap-2 p-2 -m-2 cursor-pointer">
  <input type="checkbox" class="size-4 ..." />
  <span class="text-sm">Label</span>
</label>
```

### 11.7 Mobile Tables

```html
<!-- Never let a table overflow the viewport -->
<div class="overflow-x-auto -mx-4 px-4 lg:mx-0 lg:px-0">
  <table class="w-full text-sm min-w-[600px] lg:min-w-0">
    ...
  </table>
</div>

<!-- Or: card-list pattern on mobile (preferred for data-heavy tables) -->
<!-- On mobile: each row becomes a card. On desktop: standard table. -->
<div class="lg:hidden flex flex-col gap-3">
  {rows.map(row => <Card key={row.id} {...row} />)}
</div>
<table class="hidden lg:table w-full">...</table>
```

### 11.8 Mobile Forms

```html
<!-- Buttons: full-width, stacked on mobile -->
<div class="flex flex-col sm:flex-row sm:justify-end gap-2 sm:gap-3">
  <button class="/* secondary */ order-2 sm:order-1 w-full sm:w-auto">Cancel</button>
  <button class="/* primary */ order-1 sm:order-2 w-full sm:w-auto">Save</button>
</div>
```

### 11.9 Safe Area Utilities

```css
/* Add to globals.css */
.pb-safe {
  padding-bottom: env(safe-area-inset-bottom, 0px);
}
.pt-safe {
  padding-top: env(safe-area-inset-top, 0px);
}
```

### 11.10 Mobile Anti-Patterns (NEVER Do These)

1. **Hamburger menu as primary nav.** Buries navigation, reduces discoverability.
2. **Hover-triggered dropdowns.** Invisible on touch. Use `onClick` toggle.
3. **Side-by-side panels below 768px.** Not enough width. Full-screen panels, one at a time.
4. **Fixed header + fixed footer + scrollable middle without `dvh`.** Use `100dvh` (dynamic viewport height) for full-screen panels to account for mobile browser chrome.
5. **`user-select: none` on content.** Let users select text to copy. Only disable selection on drag handles and decorative elements.
6. **`overflow: hidden` on body without testing.** Can break iOS scroll behavior and the Safari address bar collapse.

---

## 12. Iconography

- **Library:** Lucide React (`lucide-react`) — consistent 24px stroke-based icons.
- **Inline size:** `size-[18px]` or `size-4.5` (18px — matches text line height).
- **Standalone size:** `size-5` (20px) for buttons and nav.
- **Large:** `size-6` (24px) for empty states.
- **Stroke:** `stroke-2` on Lucide components (the default).
- **Color:** Inherit from parent text color via `currentColor`.

---

## 13. Design Principles

1. **Light first.** Professional legal tool. High contrast for document reading. White surfaces, clean typography.
2. **Restrained, not dramatic.** No glowing borders. No gradient cards. No colored shadows. Elegance through restraint.
3. **Hierarchy through weight, not color.** Use `font-medium` and `font-semibold` for emphasis. Reserve color for semantic meaning.
4. **Consistent spacing.** Every value is a multiple of 4px. No arbitrary values.
5. **Geist everywhere.** Sans for UI, Mono for code and citations. No third font.
6. **Hover subtle, active clear.** Hover: surface darken. Active/selected: brand border or background.
7. **No opacity-only state changes.** Always pair opacity with a color shift.

---

## 14. What AI Agents Must NEVER Do

1. **Invent new color values.** If `--brand` doesn't work, the design is wrong — not the color.
2. **Use arbitrary Tailwind values** like `p-[7px]`, `w-[342px]`, `text-[#abc123]`. Stay on the defined scale.
3. **Add custom fonts.** Geist Sans + Geist Mono. No third font.
4. **Use `font-light` or `font-extrabold`.** The defined weights are 400, 500, 600, 700.
5. **Add new shadow levels.** `shadow-sm` and `shadow-md` only.
6. **Change border-radius from the three defined sizes** (`rounded-sm`, `rounded-lg`, `rounded-xl`).
7. **Use colored shadows or glow effects.** Never.
8. **Hardcode colors in components.** Every color must reference a CSS custom property or a Tailwind semantic token.
