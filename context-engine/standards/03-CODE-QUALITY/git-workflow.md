# Git Workflow and Standards

> Lightweight by design — this is a small team on a single codebase, not a
> multi-team OSS project. Optimize for clear history over ceremony.

## 1. Branching

- `main` is always deployable.
- Feature work happens on a branch cut from `main`:
  `<type>/<short-description>` — e.g. `feat/partner-matching`,
  `fix/reminder-polling-leak`, `chore/standards-audit`.
- `type` is one of: `feat`, `fix`, `chore`, `refactor`, `docs`.
- No long-lived branches other than `main`. Merge or delete — don't let
  feature branches drift for weeks.

## 2. Commit Messages

- Present tense, imperative mood, lowercase, no trailing period:
  `add partner matching endpoint`, not `Added partner matching endpoint.`
- One logical change per commit where practical. It's fine to commit schema
  + CRUD + route + frontend client together for one atomic ticket
  (Commandment IV) — don't artificially split a single ticket's diff.
- Prefix with the ticket/module when it adds clarity:
  `partners: add naics/psc match query`.

## 3. Pull Requests

- One PR per atomic ticket (see `AGENTS.md` Commandment IV) — a PR should be
  revertable on its own without breaking unrelated tickets.
- PR description: what changed, why, and how it was verified (the Verdict —
  test output, manual steps, screenshot for UI). "Looks like it works" is
  not sufficient per Commandment V.
- Squash-merge to `main` — keeps `main` history to one commit per ticket.

## 4. What Not to Commit

- `.env` files, credentials, API keys.
- Generated artifacts (`__pycache__/`, `.next/`, `tsconfig.tsbuildinfo`) —
  confirm they're in `.gitignore` before committing new tooling.
- Large binary fixtures — use the `context-engine/specs/*/03-fixtures.json`
  pattern (real but minimal JSON) instead of checked-in sample files where
  possible.
