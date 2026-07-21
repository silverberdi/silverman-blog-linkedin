## Why

US-049 shipped a durable optional editorial content backlog (capture fields + LinkedIn derivative planning notes) but operators still cannot record topic dependencies or systematically prioritize / reprioritize that queue. BL-020 / US-050 Story 2 closes that gap without turning the backlog into a Flow B prerequisite. Why now: US-049 Story 1 is implemented locally and the canonical `editorial-content-backlog` capability exists; dependency and reprioritization are the remaining BL-020 expected outcomes before operators can treat the hand-curated queue as a usable planning tool.

## Goals

- Persist and validate dependency edges between backlog items (stable `item_id` references; reject cycles and dangling refs with structured 4xx).
- Support prioritization and reprioritization of backlog items via authenticated worker HTTP (extend existing `priority` enum and/or explicit ordering) — n8n → worker HTTP only (ADR-0001).
- Extend the existing Authority Manager Content backlog surface so operators can see dependencies and prioritize / reprioritize with clear failure messaging (thin affordance; no new app / UI kit).
- Keep optional-enrichment semantics: empty or unused backlog MUST NOT block Flow B discover, draft, or gap-trigger.
- Ship implementation + OpenSpec cycle only — no deploy, Story accepted, or BL-020 close in this change alone.

## Non-goals

- Implementing discovery seed/override from backlog as a hard dependency (MAY document as future optional; MUST NOT require it).
- Auto-publish blog or LinkedIn; bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Packaging pipeline from LinkedIn derivative notes.
- Redesigning Authority Manager chrome or introducing PrimeReact / other UI kits.
- Changing Flow A publish/package/schedule or gap-trigger enablement defaults.
- Closing BL-020 or marking US-049 / US-050 Story accepted by proposal or implementation alone.
- Deploy / push / live Story acceptance.

## What Changes

- Extend the Postgres-backed editorial content backlog model to persist dependency edges between items (stable `item_id` references) with cycle and dangling-reference rejection.
- Extend authenticated backlog HTTP APIs so operators can set dependencies and prioritize / reprioritize items (list order reflects prioritization contract).
- Extend the existing Authority Manager Content backlog modal to show dependencies and allow prioritize / reprioritize with plain-language failure messaging.
- Reaffirm optional-enrichment: empty/unused backlog and dependency fields MUST NOT gate Flow B discover / draft / gap-trigger.
- Update CURRENT-STATE and product progress only for criteria demonstrated after apply/verify; do not mark Story accepted without operator review.

## Capabilities

### New Capabilities

- (none) — extend the existing `editorial-content-backlog` capability rather than inventing a sibling capability.

### Modified Capabilities

- `editorial-content-backlog`: Add dependency-edge persistence and validation; add prioritization / reprioritization (priority enum and/or explicit order); expose via authenticated HTTP; keep optional-enrichment and Flow B independence; retire US-049 “dependency UX out of scope” exclusion for this Story 2 slice.
- `linkedin-variant-supervision-console`: Extend the existing Content backlog surface to show dependencies and support prioritize / reprioritize (no new chrome redesign; no US-050 → discovery seed UI).
- `flow-b-topic-discovery`: Reaffirm that dependency / priority backlog enrichment MUST NOT become a discovery prerequisite or required seed input.
- `flow-b-calendar-gap-trigger`: Reaffirm that backlog dependency / priority state MUST NOT block or change gap-trigger no-op / trigger semantics.

## Impact

- **Code:** Extend `editorial_content_backlog` / `editorial_content_backlog_store`, HTTP routes in `main.py`, Authority Manager Content backlog modal + API client/types; pytest (`memory://`); Vitest for UI.
- **APIs:** Extend `/editorial/content-backlog` create/list/update (and/or a small dedicated reorder/dependency write path if clearer) — ADR-0001 only; no n8n Execute Command.
- **Deps:** Reuse `psycopg` + `SILVERMAN_CALENDAR_DATABASE_URL` → `silverman_linkedin_db`; no new external services.
- **Ops:** Idempotent schema ensure for dependency / order columns or edge table; secrets remain env-only; no deploy in this change.
- **Product:** **BL-020 / US-050** primary. Does not close BL-020; does not mark US-049 or US-050 Story accepted without operator gate.
- **Acceptance criteria addressed (US-050):** Identify dependencies; support prioritization and reprioritization; MAY later seed discovery but MUST NOT block P4 Flow B; outcome visible to intended user; failures/blocked states clear; no unintentional change to completed Flow A / Flow B work.
- **Acceptance criteria excluded:** Discovery seed/override as required wiring; Story accepted / BL-020 closed; live deploy; packaging / auto-publish.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-020 / US-050** | Primary — dependencies and prioritization / reprioritization (Story 2) |
| US-049 | Prerequisite Story 1 — capture fields + CRUD-lite (already implemented locally; not Story accepted) |
| BL-017 / US-078–US-079 | Must remain runnable without backlog (independence) |
| BL-019 / US-076–US-077 / US-082 | Must remain runnable without backlog (independence) |
| ADR-0001 / ADR-0002 | HTTP-only orchestration; blog canonical |
| ADR-0004 / US-041 | Calendar DB pattern reused for backlog persistence |
