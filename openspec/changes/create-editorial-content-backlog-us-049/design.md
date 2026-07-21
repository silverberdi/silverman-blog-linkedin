## Context

BL-020 / US-049 asks for an optional hand-curated editorial content backlog. Flow B AI discovery (US-078) and gap trigger (US-082) are already Story accepted and MUST remain runnable when the backlog is empty or unused. Postgres `silverman_linkedin_db` already hosts calendar (US-041) and Flow B gap settings/batches via `SILVERMAN_CALENDAR_DATABASE_URL` (ADR-0004). Silverman Authority Manager is the Vite React console at `GET /flow-a/console/linkedin-variant-supervision`.

Constraints: ADR-0001 (n8n → HTTP only); ADR-0002 (blog canonical; LinkedIn derivative notes are planning/distribution links only); no browser filesystem SoT; no secrets in responses; no deploy or Story accepted in this change alone; US-050 dependency/reprioritization UX out of scope.

Stakeholders: editorial manager (capture/plan topics); system operator (same Postgres DB); Flow B maintainers (independence from backlog).

## Goals / Non-Goals

**Goals:**

- Durable backlog rows in `silverman_linkedin_db` with US-049 capture fields + LinkedIn derivative planning links.
- Authenticated HTTP create/list/update with typed validation and actionable 4xx errors.
- Thin Authority Manager list/create/edit affordance on the same HTTP SoT (preferred).
- Explicit optional-enrichment: empty/unused backlog MUST NOT block Flow B discover/draft/gap-trigger.
- Pytest contracts with `memory://`; Vitest only if console UI ships.

**Non-Goals:**

- US-050 dependency graph / reprioritization UX.
- Seeding or overriding Flow B discovery from backlog.
- Packaging pipeline, auto-publish, LinkedIn enablement changes.
- Redesigning console chrome / new UI kits.
- Closing BL-020 or marking US-049 Story accepted without operator review.

## Decisions

### D1 — Postgres `silverman_linkedin_db`, new table(s)

**Choice:** Persist backlog in **`silverman_linkedin_db`** via existing `SILVERMAN_CALENDAR_DATABASE_URL`, new table e.g. `editorial_content_backlog_items` (plus optional child table or JSONB for LinkedIn derivative links). Tests use `memory://` like gap settings / calendar stores.

**Why:** ADR-0004 already rejected mount-backed SoT for durable operator planning state; same DB avoids a second secret/URL and shares backup fate with calendar/settings.

**Alternatives:**

| Option | Rejected because |
|--------|------------------|
| Editorial-mount JSON / Markdown | Wipe class of pre-US-041 calendar; browser/filesystem SoT forbidden |
| Separate sibling DB by default | Extra ops for a small CRUD table |
| Browser localStorage / File System Access | Not durable SoT; violates HTTP worker ownership |
| Campaign metadata filesystem | Wrong lifecycle; mixes planning with campaign evidence |

### D2 — Item model (US-049 field set)

**Choice:** One backlog item row with typed columns:

| Field | Type / notes |
|-------|----------------|
| `item_id` | Stable opaque id (UUID or ULID string), server-assigned on create |
| `topic` | Non-empty trimmed string |
| `audience` | Non-empty trimmed string |
| `objective` | Non-empty trimmed string |
| `format` | Enum: `blog`, `linkedin`, `both` (v1; blog-canonical planning still applies when `both`) |
| `priority` | Enum: `low`, `medium`, `high` (or small integer 1–3 — pick enum for clarity) |
| `status` | Enum: `idea`, `planned`, `in_progress`, `done`, `dropped` |
| `target_date` | Optional ISO calendar date (`YYYY-MM-DD`) or null |
| `linkedin_derivatives` | JSON array of planning objects: `{ "audience_hint", "format_hint", "notes" }` (0..N); enough for Story 1 link model |
| `created_at_utc` / `updated_at_utc` | Server-managed UTC ISO |
| `row_version` | Optimistic concurrency for updates |

No dependency edges (US-050). No foreign keys into campaigns or Flow B drafts in Story 1.

**Why:** Matches US-049 AC literally; LinkedIn links are notes, not package generation.

### D3 — HTTP surface (create / list / update)

**Choice:**

- `GET /editorial/content-backlog` — authenticated list (optional filters: `status`, `priority`; default newest-updated first; bounded page size).
- `POST /editorial/content-backlog` — authenticated create; returns created item.
- `GET /editorial/content-backlog/{item_id}` — authenticated detail (optional but useful for edit forms).
- `PUT /editorial/content-backlog/{item_id}` — authenticated full-document update of mutable fields; `expected_row_version` or `If-Match` for concurrency when cheap.
- Soft-delete via `status=dropped` preferred over hard DELETE in Story 1 (optional hard DELETE out of scope unless trivial).

Unauthenticated → reject. Validation failures → **4xx** with stable codes and actionable messages. Store unavailable → **5xx** / structured unavailable code. Responses MUST NOT include secrets.

**Why:** ADR-0001; n8n and console share one SoT; path under `/editorial/` keeps Flow B routes free of implied prerequisite wiring.

### D4 — Optional enrichment / Flow B independence

**Choice:** Backlog store and routes MUST NOT be imported as hard dependencies by `flow_b_topic_discovery`, `flow_b_blog_draft_generation`, or `flow_b_calendar_gap_trigger` in this change. Spec deltas reaffirm: empty table, missing rows, or unused API MUST leave discover / draft / gap-trigger behavior unchanged. No “seed from backlog” request fields required.

**Why:** US-049 AC #3 and BL-020 “MUST NOT block BL-017/BL-019.”

### D5 — Authority Manager thin affordance

**Choice:** Prefer a modal/panel in `frontend/linkedin-variant-supervision-console` (header affordance beside Gap settings / Flow B drafts) that lists items and supports create/edit of the capture fields + derivative notes. Reuse session / `canMutate` patterns. Do **not** introduce PrimeReact or redesign chrome.

**Fallback:** If UI risks incoherence, ship HTTP + pytest first and document curl/ops against the same SoT; product AC “visible to intended user” is then satisfied by authenticated JSON + ops doc until UI lands in a tight follow-up within the same OpenSpec change preference is still UI-in-scope.

**Why:** Glossary: Silverman Authority Manager extends the existing console; operators already work there.

### D6 — Schema ensure

**Choice:** Idempotent `CREATE TABLE IF NOT EXISTS` on first store access (match calendar / gap settings). No Alembic unless project already mandates it for these tables (it does not).

### D7 — Tests and docs

**Choice:**

- Pytest: validation, auth required, create/list/update round-trip (`memory://`), concurrency/conflict, secret-free responses, empty-list success, independence regression (discovery/gap-trigger still succeed with empty backlog store — smoke via existing tests unchanged or thin guard test that backlog module is not required).
- Vitest: list/create/edit + error display if console ships.
- CURRENT-STATE / progress-checklist / user-stories: update only after demonstrated criteria; never mark Story accepted or BL-020 closed by implementation alone.

### D8 — Secrets and LinkedIn publish

**Choice:** Handlers MUST NOT read/return API keys, OAuth tokens, or DB passwords. Create/update MUST NOT enable LinkedIn API publication or mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operators treat backlog as required for Flow B | Spec + UI copy: “optional enrichment”; no wiring into discover/trigger |
| Scope creep into US-050 dependencies | Explicit non-goal; no dependency columns |
| Format/priority enum bikeshed | Lock small enums in design/spec; change later via OpenSpec |
| UI expands console chrome | Thin modal only; match Gap settings pattern |
| Store unavailable confuses operators | Clear structured errors; empty list ≠ store failure |

## Migration Plan

1. Apply schema ensure on first access after deploy (future; not in this change’s apply).
2. No data migration — new empty table.
3. Rollback: remove routes/UI; table may remain empty (harmless) or drop in a follow-up ops step.
4. No change to Flow B enablement flags or n8n exports.

## Open Questions

- Exact enum literals for `format` / `priority` / `status` — locked in D2 unless product prefers different labels during apply review.
- Whether soft-delete-only is enough for Story 1 (assumed yes).
- Detail GET vs list-only for edit — prefer detail GET if edit form needs it; otherwise list payload may be sufficient.
