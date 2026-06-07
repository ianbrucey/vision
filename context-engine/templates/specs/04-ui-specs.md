# UI Specifications - Zero Ambiguity Artifact

> **Generated From:** `02-api-contract.json`  
> **Rule:** UI cannot display data not provided by the API. No client-side data invention.

---

## 1. Views / Pages

### 1.1 [View Name]

**Purpose:** [What does this view do?]

**URL Route:** `/path/to/view`

**Data Required:** (Must exist in API Contract)
| Field | Source Endpoint | Type |
|-------|-----------------|------|
| | | |

**User Actions:**
| Action | Triggers | API Endpoint |
|--------|----------|--------------|
| | | |

**States:**
- **Loading:** [What shows while data loads]
- **Empty:** [What shows when no data]
- **Error:** [What shows on API failure]
- **Success:** [Normal display]

---

## 2. Components

### 2.1 [Component Name]

**Props:** (Data passed in)
| Prop | Type | Required | Description |
|------|------|----------|-------------|
| | | | |

**Events Emitted:**
| Event | Payload | When |
|-------|---------|------|
| | | |

---

## 3. Conflict Check

> ⚠️ **MANDATORY:** Before this spec is approved, verify:

- [ ] Every field displayed exists in `02-api-contract.json`
- [ ] Every action maps to a defined endpoint
- [ ] No UI assumes data the API doesn't provide
- [ ] Loading/Empty/Error states are defined for all views

---

## 4. Approval Gate

**Status:** [ ] DRAFT  [ ] APPROVED

**Conflicts Found:** [ ] YES  [ ] NO

**Approved By:** 

**Date:**

