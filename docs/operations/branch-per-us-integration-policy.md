# Branch-per-US integration policy (BL-038 / US-105)

**Status:** Policy **published**; **US-105 Story accepted** (operator-accepted 2026-07-21). Integrate to `main` via PR from the US-105 branch.
**Authority:** Product [BL-038](../product/backlog.md); Cursor rules; [CONTEXT-AUTHORITY.md](../CONTEXT-AUTHORITY.md).
**Related:** [BL-029](../product/backlog.md) (CI + UAT→prod PR promotion) builds automation on top of this human discipline.

## Rule (normative from 2026-07-21)

1. **Every change starts on a new git branch** off the current integration tip (`main` until BL-029 replaces the promotion model). Do not commit product or application work directly on `main`.
2. **One primary user story owns the branch** (name the branch after the US when practical, e.g. `docs/us-105-…` or `feat/us-093-…`). A single OpenSpec change MAY cover multiple stories in one BL only when product docs already group them that way — still **no merge to `main` until every US in that change that this branch claims is Story accepted** (or explicitly waived).
3. **Integrate to `main` only when the owning user story is closed** — meaning **Story accepted** (operator-accepted) with acceptance criteria demonstrated. Implementation commits may exist on the branch before acceptance; **merge/PR to `main` is the integration gate**, not the first commit.
4. Prefer **pull request** into `main` (required once BL-029 Actions/branch protection land). Until then, operator-approved merge after Story accepted is allowed but still MUST NOT skip the branch-first rule.
5. Hotfixes that touch production behavior still use a branch + Story (or an emergency US) — no silent `main` commits.

## What this is not

- Not classic GitFlow (no mandatory `develop`/`release` unless BL-029 docs say otherwise).
- Not a substitute for OpenSpec approval before application code.
- Not permission to push, deploy, or mutate live systems without explicit operator approval.

## Agent / Cursor obligations

- Create or switch to the owning US branch before editing for that story.
- Refuse to treat direct-to-`main` commits as normal for new work after this policy’s effective date.
- When reporting “done,” distinguish **branch complete / Story accepted** from **merged to `main`**.
