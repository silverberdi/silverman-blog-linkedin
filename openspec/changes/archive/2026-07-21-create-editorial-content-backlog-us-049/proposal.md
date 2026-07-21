## Why

Operators who want a hand-curated topic queue today have no durable, worker-owned place to capture planned content (topic, audience, objective, format, priority, status, target date) or link blog topics to intended LinkedIn derivatives. Flow B AI discovery (BL-017 / US-078) and gap trigger (BL-019 / US-082) already run without a backlog; BL-020 Story 1 (US-049) adds that optional enrichment without becoming a prerequisite. Why now: P4 Flow B stories are Story accepted and closed; P5 BL-020 / US-049 is the next coherent product slice.

## Goals

- Give editorial operators durable capture of backlog items with the US-049 field set and LinkedIn derivative planning links.
- Persist SoT in Postgres `silverman_linkedin_db` (ADR-0004 pattern), not browser filesystem or editorial-mount JSON.
- Expose authenticated worker HTTP create/list/update (CRUD-lite) — n8n → worker HTTP only (ADR-0001).
- Prefer a thin Silverman Authority Manager list/create/edit affordance on the same HTTP SoT (or document an ops/curl path if UI is deferred within the same change coherence).
- Keep empty/unused backlog non-blocking for Flow B discover, draft, and gap-trigger paths.
- Ship implementation + OpenSpec cycle only — no deploy, Story accepted, or BL-020 close in this change alone.

## Non-goals

- US-050 dependency graph and prioritization/reprioritization UX (follow-up change).
- Seeding or overriding Flow B AI discovery from the backlog (MAY later; MUST NOT implement as required wiring here).
- Auto-publish blog or LinkedIn; bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- BL-022 metrics / BL-023 feedback loops.
- Redesigning Authority Manager chrome or introducing PrimeReact / other UI kits.
- Closing BL-020 or marking US-049 / US-050 Story accepted by proposal or implementation alone.
- Changing Flow A publish/package/schedule, cadence (BL-021), or gap-trigger enablement defaults.
- Full LinkedIn packaging pipeline from backlog links (planning notes / audience-format hints only).

## What Changes

- Add a Postgres-backed editorial content backlog store in `silverman_linkedin_db` (reuse `SILVERMAN_CALENDAR_DATABASE_URL`; `memory://` in tests), with typed fields for topic, audience, objective, format, priority, status, target date, and LinkedIn derivative link notes.
- Add authenticated worker HTTP endpoints to create, list, and update backlog items (secret-safe JSON; structured 4xx validation).
- Extend **Silverman Authority Manager** with a thin list/create/edit backlog surface consuming those endpoints (preferred); if UI is cut for coherence, document the curl/ops path against the same SoT and still satisfy visibility AC via authenticated HTTP responses.
- Encode explicit optional-enrichment semantics: empty or unused backlog MUST NOT block or alter Flow B discover / draft / gap-trigger success paths.
- Update CURRENT-STATE and product progress only for criteria actually demonstrated after apply/verify; do not mark Story accepted without operator review.

## Capabilities

### New Capabilities

- `editorial-content-backlog`: Durable Postgres-backed hand-curated topic backlog (US-049); authenticated HTTP create/list/update; typed capture fields + LinkedIn derivative planning links; validation errors; optional-enrichment semantics (MUST NOT gate Flow B); Authority Manager thin affordance or documented ops HTTP path.

### Modified Capabilities

- `linkedin-variant-supervision-console`: Extend Silverman Authority Manager shell with authenticated access to the editorial content backlog (list/create/edit navigation/surface only; no US-050 dependency UX; no Flow B seed wiring).
- `flow-b-topic-discovery`: Clarify that a present-but-empty (or unused) US-049 backlog MUST NOT become a discovery prerequisite and MUST NOT be required as seed input in this change.
- `flow-b-calendar-gap-trigger`: Clarify that backlog emptiness or absence MUST NOT block or change gap-trigger no-op / trigger semantics.

## Impact

- **Code:** New backlog store module (patterned on `flow_b_gap_operator_settings_store` / calendar store), validation models, HTTP routes in `main.py`, optional console panel + API client, pytest contracts (`memory://`); Vitest only if console affordance ships.
- **APIs:** New authenticated backlog routes under an editorial / Flow-adjacent path (e.g. `/editorial/content-backlog`); existing Flow A and Flow B contracts unchanged except independence clarifications.
- **Deps:** Reuse `psycopg` + `SILVERMAN_CALENDAR_DATABASE_URL` targeting `silverman_linkedin_db`; no new external services.
- **Ops:** Idempotent `CREATE TABLE IF NOT EXISTS`; secrets remain env-only; no deploy in this change.
- **Product:** **BL-020 / US-049** primary. Does not implement US-050; does not close BL-020; does not mark Story accepted without operator gate.
- **Acceptance criteria addressed (US-049):** Capture field set; link blog topics to LinkedIn derivatives; MUST NOT require before BL-017/BL-019; outcome visible to intended user; failures/blocked states clear; no unintentional change to completed Flow B/Flow A work.
- **Acceptance criteria excluded:** US-050 dependencies/reprioritization; discovery seed/override; Story accepted / BL-020 closed; live deploy.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-020 / US-049** | Primary — create editorial content backlog (Story 1) |
| US-050 | Explicit follow-up — dependencies / reprioritization UX |
| BL-017 / US-078–US-079 | Must remain runnable without backlog (independence) |
| BL-019 / US-076–US-077 / US-082 | Must remain runnable without backlog (independence) |
| US-041 / ADR-0004 | Calendar DB pattern reused for backlog tables |
| ADR-0001 / ADR-0002 | HTTP-only orchestration; blog canonical, LinkedIn links are planning/distribution notes only |
