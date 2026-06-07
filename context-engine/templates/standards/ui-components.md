# UI Components

> **Purpose:** Catalog of reusable UI components  
> **Rule:** Builders must use these components. Do not invent new patterns.

---

## How to Use This File

Each component entry should include:
- **Purpose**: What the component does
- **Props**: All available properties and their types
- **Slots**: Named slots (if applicable)
- **Usage Example**: Code snippet showing how to use it
- **Variants**: Different styles or configurations

---

## Example Entry

### Button

**Purpose:** Standard clickable button with consistent styling

**Props:**
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `variant` | `'primary' \| 'secondary' \| 'danger'` | No | `'primary'` | Visual style |
| `size` | `'sm' \| 'md' \| 'lg'` | No | `'md'` | Button size |
| `disabled` | `boolean` | No | `false` | Disable interaction |
| `onClick` | `() => void` | No | - | Click handler |

**Usage:**
```jsx
<Button variant="primary" size="lg" onClick={handleSubmit}>
  Submit Form
</Button>
```

**Variants:**
- `primary` - Blue background, white text
- `secondary` - Gray background, dark text
- `danger` - Red background, white text

---

<!-- Add your components below -->

