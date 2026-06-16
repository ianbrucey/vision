# Dynamic View System — UI Specifications

> **Version:** 1.0 | **Status:** Draft | **Depends on:** `01-view-envelope-schema.json`

---

## 1. Component Architecture

```
WorkspaceTab (existing — extended)
└── Viewport
    └── Renderer Dispatch (existing — extended)
        ├── MarkdownRenderer  (existing)
        ├── DraftPreview      (existing)
        ├── html stub         (existing — inline div, no component yet)
        └── JsonViewRenderer  ★ NEW — dispatches on viewType
            └── ViewComposer      ★ NEW — renders views[] array
                ├── Section header    (inline: title + description + ViewSwitcher)
                ├── DynamicCards      ★ NEW
                ├── DynamicTable      ★ NEW
                ├── DynamicList       ★ NEW
                └── ViewSwitcher      ★ NEW — compatible type dropdown
```

---

## 2. JsonViewRenderer

**Purpose:** Entry point for all `file_type: "json_view"` workspace items. Dispatches to `ViewComposer` for multi-view envelopes or directly to the single view renderer for single-view envelopes.

**Props:**
```typescript
interface JsonViewRendererProps {
  content: ViewEnvelope;   // the full {documentMetadata, views[]} from drafts.content
  itemId: number;           // workspace item ID for save operations
  isEditing: boolean;       // global edit toggle from WorkspaceTab toolbar
}
```

**Behavior:**
- Validates `content` against the view envelope schema on mount
- If validation fails, renders an error card with the specific schema violation
- If `content.views.length === 1`, renders that single view without ViewComposer chrome
- If `content.views.length > 1`, delegates to `ViewComposer`
- Passes `itemId` down to enable inline editing saves

**States:**
| State | Trigger | Rendering |
|-------|---------|-----------|
| `validating` | On mount, before schema check | Subtle skeleton/spinner |
| `error` | Schema validation fails | Error card with violation details |
| `empty` | Valid but `views` is empty | "No views" empty state |
| `single` | Valid with 1 view | Single view rendered directly |
| `composite` | Valid with 2+ views | ViewComposer with sections |

**Tailwind classes:** `flex flex-col gap-6 p-6`

---

## 3. ViewComposer

**Purpose:** Renders an array of views as scrollable sections. Each section has a header (title, description, ViewSwitcher) and the rendered view content.

**Props:**
```typescript
interface ViewComposerProps {
  views: ViewDefinition[];  // the views[] array
  itemId: number;
  onContentChange: (updatedViews: ViewDefinition[]) => void;
}
```

**Behavior:**
- Renders each view as a `<section>` with a sticky header
- Headers show: view title (H2), optional description (muted text), ViewSwitcher (if compatible alternatives exist)
- Sections are separated by a 1px border
- Scrolling: each section is independently scrollable if content overflows

**Section styling:**
```
<section className="rounded-lg border border-[--border] bg-[--surface-1] overflow-hidden">
  <header className="px-4 py-3 border-b border-[--border] bg-[--surface-2] flex items-center justify-between">
    <div>
      <h2 className="text-lg font-semibold text-[--text-primary]">{title}</h2>
      <p className="text-sm text-[--text-secondary]">{description}</p>
    </div>
    <ViewSwitcher />   <!-- if compatible alternatives exist -->
  </header>
  <div className="p-4">
    <!-- rendered view content -->
  </div>
</section>
```

---

## 4. DynamicTable

**Purpose:** Renders `viewType: "table"` data with sortable headers and inline-editable cells.

**Data shape:**
```typescript
interface TableData {
  viewType: "table";
  title: string;
  description?: string;
  data: {
    headers: string[];
    rows: Array<{ id: string } & Record<string, string>>;
  };
}
```

### 4.1 Table Rendering

**Header row:** `bg-[--surface-2]` with bold text. Headers include a sort indicator (▲/▼) when active.

**Body rows:** Alternating stripe: `bg-[--surface-1]` / `bg-[--surface-2]`. Row hover: `bg-[--surface-3]`.

**Column widths:** Auto-sized based on content. Headers with long text get `max-w-xs truncate` with a tooltip on hover.

**Sorting:**
- Click header → sort ascending
- Click same header again → sort descending
- Click a third time → remove sort
- Sort is client-side only (all data is already in memory)
- Sorted column shows a subtle ▲ or ▼ indicator

**Empty state:** If `rows` is empty: "No data available" centered in the table body.

### 4.2 Inline Cell Editing

**Trigger:** Single click on a cell.

**While editing:**
- Cell content replaced with an `<input type="text">` or `<textarea>` (for content > 50 chars)
- Input auto-focuses and selects all text
- Input has `border-brand ring-1 ring-brand-ring` styling
- Cell expands to accommodate input (min-width preserved)

**Save:**
- `Enter` key or `blur` event triggers save
- `Escape` cancels edit, reverts to original value
- On save: deep clone the view data, update the cell value, call `PATCH /api/workspace/{itemId}` with the full updated `content`
- While saving: cell shows a subtle pulse animation
- On error: cell border flashes `danger` for 500ms, reverts to original value

**Edit mode indicator:** An edited cell shows a subtle edit icon on hover (pencil). After save, the cell briefly flashes a success background.

### 4.3 Row ID Column

The `id` column (first column in `rows[].id`) is **not editable.** It renders in muted text with a lock icon on hover. The `id` is the stable key for React and for future citation linking.

---

## 5. DynamicList

**Purpose:** Renders `viewType: "list"` data with configurable list style and inline-editable items.

**Data shape:**
```typescript
interface ListData {
  viewType: "list";
  title: string;
  description?: string;
  data: {
    listStyle: "checkbox" | "ordered" | "bullet";
    items: Array<{
      id: string;
      text: string;
      completed?: boolean;
      notes?: string;
    }>;
  };
}
```

### 5.1 List Rendering

**Checkbox style:**
- Each item: `<div>` with checkbox input, text label, and optional notes
- Checked items: `line-through text-[--text-disabled]`
- Checkbox uses brand color when checked: `accent-[--brand]`
- Clicking checkbox toggles `completed` and immediately saves

**Ordered style:**
- `<ol>` with auto-numbering
- Numbers styled: `text-[--text-secondary] font-mono text-sm`
- No checkbox interaction

**Bullet style:**
- `<ul>` with `list-disc`
- Bullets styled: `text-[--text-secondary]`

**Empty state:** "No items" — centered, muted text.

### 5.2 Inline Item Editing

**Trigger:** Double-click on item text (single click on checkbox style toggles completion).

**While editing:**
- Text replaced with `<textarea>` (items can be multi-line)
- Auto-focuses, selects all
- Same border/ring styling as table cells

**Save/Cancel:** Same as DynamicTable — Enter/blur saves, Escape cancels.

### 5.3 Item Notes

When `notes` is present, rendered as a smaller muted line below the item text: `<p className="text-xs text-[--text-secondary] ml-6">{notes}</p>`. Notes are also inline-editable (double-click).

---

## 6. DynamicCards

**Purpose:** Renders `viewType: "cards"` data as a responsive grid of key-value cards.

**Data shape:**
```typescript
interface CardsData {
  viewType: "cards";
  title: string;
  description?: string;
  data: {
    pairs: Array<{
      key: string;
      value: string;
      emphasis?: "default" | "warning" | "danger" | "success" | "info";
    }>;
  };
}
```

### 6.1 Card Grid

**Grid layout:**
```css
grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4
```

**Individual card:**
```
<div className="rounded-lg border p-4 flex flex-col gap-2 bg-[--surface-1]">
  <span className="text-xs font-medium text-[--text-secondary] uppercase tracking-wide">{key}</span>
  <span className="text-2xl font-semibold text-[--text-primary]">{value}</span>
</div>
```

**Emphasis styling (left border + value color):**
| Emphasis | Border Left | Value Color |
|----------|-------------|-------------|
| `default` | `border` | `--text-primary` |
| `warning` | `border-warning border-l-2` | `--warning` |
| `danger` | `border-danger border-l-2` | `--danger` |
| `success` | `border-success border-l-2` | `--success` |
| `info` | `border-info border-l-2` | `--info` |

### 6.2 Inline Value Editing

**Trigger:** Single click on the value.

**While editing:**
- Value replaced with `<input type="text">`
- Key label remains visible above the input
- Input sizing matches the card width

**Save/Cancel:** Same pattern as table/list.

**Key editing:** Keys are NOT editable inline (they're labels, not data). If the user needs to change a key, they ask the agent to regenerate.

---

## 7. ViewSwitcher

**Purpose:** Dropdown that lets the user switch between compatible view types without an agent call.

**Props:**
```typescript
interface ViewSwitcherProps {
  currentViewType: "table" | "list" | "cards";
  currentData: Record<string, unknown>;
  viewIndex: number;  // index in the views[] array
  onSwitch: (newViewType: "table" | "list" | "cards", viewIndex: number) => void;
}
```

### 7.1 Compatibility Matrix

```typescript
const COMPATIBLE_VIEWS: Record<string, string[]> = {
  table: ["cards"],        // table data can render as cards (key-value pairs from rows)
  cards: ["table"],        // cards can render as a 2-column table (key, value)
  list: [],                // list has no compatible alternatives (structural)
};
```

### 7.2 Switching Logic

**Table → Cards:**
- Take the first row from `rows[]`
- Map each key-value pair to a `{key, value}` pair
- Preserve the `title` and `description`
- Adjust `viewType` to `"cards"`

**Cards → Table:**
- Convert `pairs[]` to a 2-column table: headers = `["Key", "Value"]`
- Each pair becomes a row: `{id: crypto.randomUUID(), Key: pair.key, Value: pair.value}`
- Preserve `title` and `description`
- Adjust `viewType` to `"table"`

### 7.3 UI

**Dropdown trigger:** A small button next to the view title:
```html
<button className="text-xs px-2 py-1 rounded border border-[--border] bg-[--surface-1] hover:bg-[--surface-3] flex items-center gap-1">
  <ViewIcon /> View as ▼
</button>
```

**Dropdown menu:** Popover listing compatible view types:
```html
<div className="absolute right-0 top-full mt-1 rounded-lg border border-[--border] bg-[--surface-4] shadow-lg z-10 min-w-40">
  <button>📊 Table</button>
  <button>🃏 Cards</button>
</div>
```

**Save behavior:** On switch, the transformed view immediately saves via `PATCH /api/workspace/{itemId}`. No "Save" button needed — it's a one-click action.

---

## 8. useInlineEdit Hook

**Purpose:** Shared inline editing logic used by all three view renderers.

```typescript
function useInlineEdit(
  itemId: number,
  content: ViewEnvelope,
) {
  return {
    editingCell: string | null,           // "{viewIndex}-{dataPath}" or null
    editValue: string,
    startEdit: (cellKey: string, currentValue: string) => void,
    updateEditValue: (value: string) => void,
    commitEdit: () => Promise<void>,      // saves to API, updates local state
    cancelEdit: () => void,
    isSaving: boolean,
    saveError: string | null,
  };
}
```

### Behavior

- `startEdit(cellKey, currentValue)`: Sets `editingCell` and `editValue`. The `cellKey` encodes the path: `"0-rows-r1-Balance"` = view[0].data.rows[id=r1].Balance.
- `commitEdit()`: Deep clones content, walks the cellKey path to update the value, calls `PATCH /api/workspace/{itemId}` with `{content: updatedEnvelope}`. On success, updates local state. On error, sets `saveError` and reverts.
- `cancelEdit()`: Clears `editingCell` and restores original value.
- Auto-save on blur: when `editingCell` is set and the input loses focus to a non-editable element, auto-commits. If focus moves to another editable cell, commits current then starts next.
- Debounce: rapid successive keystrokes don't trigger saves. Only blur/Enter triggers the API call.

---

## 9. WorkspaceTab Integration

**File:** `frontend/src/app/tabs/WorkspaceTab.tsx`

### Changes Required

1. In the renderer dispatch switch/case, add:
```typescript
case "json_view":
  return <JsonViewRenderer content={item.content} itemId={item.id} isEditing={isEditing} />;
```

2. The toolbar "Edit" toggle behavior: matches the existing pattern for all file types. `editMode` defaults to `false` (read-only). User clicks the Edit button in the toolbar to enable inline editing. When `editMode` is `true`, cells/items become clickable-to-edit. When `false`, the view is display-only. This is the same toggle used by `markdown` and `structured_draft` renderers.

3. The `content` prop passed to `JsonViewRenderer` is the raw JSONB from `drafts.content`. The renderer handles validation internally.

---

## 10. Mobile Considerations

- **Table:** On screens < 768px, table becomes a card stack (one card per row). Each card shows: header = column name, value = cell content. This uses the same responsive pattern as the existing data tables.
- **Cards:** Grid reduces: 4-col → 3-col → 2-col → 1-col as viewport narrows.
- **List:** No changes needed — lists are already mobile-friendly.
- **ViewComposer:** Section headers become less sticky on mobile to avoid covering too much screen real estate.
- **Inline editing:** On mobile, editing opens a full-width input below the cell rather than replacing text inline (prevents keyboard from obscuring content).

---

## 11. Design Token Usage

All components must use the existing design system tokens from `design-system.md`:

| Purpose | Token |
|---------|-------|
| View section backgrounds | `--surface-1`, `--surface-2` |
| Cell hover | `--surface-3` |
| Borders and dividers | `--border` (Default #E1E4E8) |
| Body text | `--text-primary` |
| Metadata/descriptions | `--text-secondary` |
| Disabled/empty text | `--text-disabled` |
| Edit focus ring | `--brand-ring` (rgba 184, 134, 11, 0.2) |
| Edit border | `--brand` |
| Success flash | `--success` / `--success-bg` |
| Error flash | `--danger` / `--danger-bg` |
| Warning emphasis | `--warning` / `--warning-bg` |
| Info emphasis | `--info` / `--info-bg` |
| Font | Geist Sans (headings + body), Geist Mono (monospace values) |

**No new colors, no new fonts, no new spacing values.** This is a strict extension of the existing design system.
