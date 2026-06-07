# The Standards Enforcer Guide

> **Purpose:** Automate the creation and maintenance of coding standards to prevent the "Tower of Babel Effect"

---

## The Problem: Tower of Babel Effect

When delegating coding to AI (or teams), entropy is the default state. Without rigid, shared standards, every new feature introduces chaos:

- **Scenario A (Legacy Mess)**: AI sees 5 different button implementations, picks the worst one
- **Scenario B (Missing Piece)**: AI hallucinates a new library instead of using your component system
- **Scenario C (Blank Slate)**: AI defaults to generic patterns because you haven't defined your preferences

**The Goal:** A Standards Engine that ingests code, extracts patterns, and enforces them automatically.

---

## The Three Workflows

### Workflow 1: AUDIT (Mining the Gold)

Extract standards from existing code.

**When to use:**
- You have an existing codebase
- You want to freeze current patterns into law
- You need to document what already exists

**Command:**
```bash
python scripts/standards.py audit <directory> [file_pattern]
```

**Examples:**
```bash
# Audit all Blade components
python scripts/standards.py audit resources/views/components "*.blade.php"

# Audit all Python modules
python scripts/standards.py audit src/services "*.py"

# Audit all React components
python scripts/standards.py audit src/components "*.tsx"
```

**What it does:**
1. Scans all files matching the pattern
2. Sends each file to Auggie with: "Extract reusable patterns"
3. Appends documentation to `context-engine/standards/ui-components.md` or `coding-patterns.md`

---

### Workflow 2: GENESIS (The Constitution Convention)

Define standards from scratch via approved reference implementations.

**When to use:**
- Starting a new project
- No existing code to audit
- Want to establish patterns before writing code

**Command:**
```bash
python scripts/standards.py genesis "<tech_stack_description>"
```

**Examples:**
```bash
python scripts/standards.py genesis "Laravel, Livewire, Tailwind, Alpine.js"
python scripts/standards.py genesis "React, TypeScript, TailwindCSS, Zustand"
python scripts/standards.py genesis "FastAPI, SQLAlchemy, Pydantic, PostgreSQL"
```

**What it does:**
1. Generates a "Golden Sample" (reference UI component + backend pattern)
2. Shows you the sample and asks for approval
3. If approved, extracts the patterns into `coding-patterns.md`
4. Saves the reference implementation to `reference-implementations.md`

**The Loop:**
- Agent generates example code
- You review and approve (or reject and refine)
- Agent extracts rules from approved code
- Rules become law for all future development

---

### Workflow 3: FREEZE (Just-in-Time Legislation)

Create a new component and immediately freeze it as a standard.

**When to use:**
- Building a new feature that needs a component that doesn't exist
- Want to ensure consistency before the component is used elsewhere
- Expanding your component library

**Command:**
```bash
python scripts/standards.py freeze "<component_name>"
```

**Examples:**
```bash
python scripts/standards.py freeze "DatePicker"
python scripts/standards.py freeze "Modal"
python scripts/standards.py freeze "DataTable"
```

**What it does:**
1. Reads existing standards for context
2. Generates code + documentation for the new component
3. Shows you both and asks where to save the code
4. Appends documentation to `ui-components.md`

**The Result:** The standard is created *before* the feature uses it.

---

## Output Files

All standards are saved to `context-engine/standards/`:

| File | Purpose |
|------|---------|
| `ui-components.md` | Catalog of reusable UI components (props, slots, usage) |
| `coding-patterns.md` | Backend patterns (error handling, typing, architecture) |
| `reference-implementations.md` | Approved "Golden Samples" from Genesis workflow |

---

## Integration with Council Workflow

The Standards Enforcer works alongside the Council Orchestrator:

```
1. Genesis/Audit → Define standards
2. Council → Generate specs (Brief, Schema, API, Fixtures, Plan)
3. Execution → Build code (using standards from step 1)
```

**During Execution (State 4):**
- The Builder agent loads `context-engine/standards/` files
- These files are injected into every prompt
- The agent cannot deviate from documented patterns

---

## Enforcement Strategy

Standards are enforced through **context injection**:

1. **Frontend tasks** → Load `ui-components.md`
2. **Backend tasks** → Load `coding-patterns.md`
3. **All tasks** → Load `reference-implementations.md` (if exists)

The Master Context Engine (AGENTS.md) already includes this directive:
> "Consult standards in `context-engine/standards/` before writing any code."

---

## Related Files

- `scripts/standards.py` - The automation script
- `context-engine/standards/` - Where standards are stored
- `AGENTS.md` - References standards enforcement

