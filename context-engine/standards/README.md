# Project Architecture & Coding Standards

This directory contains the official architectural and coding standards for
this project. All developers and AI assistants are required to read,
understand, and adhere to these guidelines before writing or modifying any
code.

> **Stack this project actually runs on:** Next.js 16 + React 19 +
> TypeScript + Tailwind CSS 4 (frontend); Python 3.12+ + FastAPI + psycopg2 +
> PostgreSQL 16 with pgvector (backend). There is no PHP, Laravel, or
> Livewire anywhere in this codebase — if you see a reference to those in an
> old doc, it's stale; the files below are the corrected, authoritative
> versions as of the standards audit.

## Purpose

The purpose of these standards is to ensure:
- **Consistency**: Code is written in a uniform style across the entire project.
- **Quality**: We adhere to best practices for performance, security, and maintainability.
- **Clarity**: Code is easy to read, understand, and reason about.
- **Efficiency**: Developers and AI can make decisions quickly by following established patterns.

## Structure

- **`/01-FRONTEND-STANDARDS`** — Next.js/React/Tailwind:
  - `design-system.md` — colors, typography, spacing, component visual specs, mobile rules.
  - `component-patterns.md` — modal/form/toast/nav behavior, loading states, hooks-free component conventions.
  - `react-hooks-patterns.md` — custom hook structure, state ownership, polling, error handling in hooks.
- **`/02-BACKEND-STANDARDS`** — FastAPI/PostgreSQL:
  - `python-fastapi-structure.md` — directory layout, layering, how to add a new domain, route file skeleton.
  - `database-design.md` — naming, standard columns, enums-as-CHECK, migrations, indexing, `core/db.py` CRUD conventions.
- **`/03-CODE-QUALITY`**:
  - `python-standards.md` — style, error handling, DB access rules, security, performance.
  - `git-workflow.md` — branching, commit format, PR process.

**Adherence to these standards is not optional.** When writing specs
(`context-engine/specs/*`), reference the relevant standard file instead of
re-deriving conventions inline.
