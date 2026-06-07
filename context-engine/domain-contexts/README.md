# Domain Contexts

> **Purpose:** Developer onboarding guides for specific domains in your application.

---

## What Goes Here

Create one `.md` file per domain in your application. For example:

- `events.md` - Event creation, management, cancellation
- `payments.md` - Payment processing, refunds, Stripe integration  
- `users.md` - User registration, authentication, profiles
- `notifications.md` - Email, SMS, push notification systems

---

## What Domain Contexts Contain

Each file serves **two purposes**:

### 1. Business Intent (WHY)
- Business rules and constraints
- User stories and use cases
- Edge cases and exceptions

### 2. Code Navigation (WHERE/HOW)
- Key files and their purposes
- Entry points for common tasks
- Relationships between files
- Step-by-step modification guides

---

## Template

Use `templates/domain-context.md` as your starting template.

**Example starter templates** are available in `templates/domain-contexts/`:
- `api-context.md` - API design patterns
- `auth-context.md` - Authentication patterns
- `database-context.md` - Database patterns

---

## When to Create a Domain Context

Create one when:
- A domain has complex business rules that aren't obvious from code
- Multiple files work together and the relationships aren't clear
- You find yourself explaining the same thing to new developers repeatedly
- An AI agent keeps making mistakes in a particular area

---

## How They're Used

1. **By humans:** Read before working on a domain
2. **By the orchestrator:** Loaded automatically during Council workflow
3. **By AI agents:** Referenced to understand context before making changes

> ⚠️ Keep these files updated! Stale domain contexts are worse than none at all.

