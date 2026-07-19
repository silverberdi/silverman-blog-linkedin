## Context

Today the master editorial calendar is a single JSON file at `{SILVERMAN_BLOG_LINKEDIN_BASE_PATH}/editorial-calendar/calendar.json`, loaded/saved by `editorial_calendar_plan.py` (`load_calendar`, `save_calendar_atomic` with SHA-256 fingerprint concurrency). Plan/status/schedule-update HTTP endpoints, schedule-visibility, pending-supervision, operational status, and Flow A calendar execution all depend on that file.

On 2026-07-18 a deploy remounted the code-sync checkout as the editorial base and `rsync --delete` removed calendar state. Content Markdown could be copied back; schedule rows could not. Product direction: calendar durability MUST live outside the editorial filesystem mount.

Constraints: ADR-0001 (HTTP only); OpenSpec before code; no secrets in responses; worker already joins Docker network `local-ai-stack_backend` (Postgres available on that stack); keep n8n/console HTTP contracts stable.

Stakeholders: content operator (console Week/Month), system operator (deploy/backup), Flow A automation (plan-due / execute-due).

## Goals / Non-Goals

**Goals:**

- Database as canonical SoT for calendar document + items in new Postgres DB **`silverman_linkedin_db`**.
- Storage volume independent of editorial mount and of worker code rsync.
- Preserve item schema semantics (statuses, optional Flow A completion fields, due times).
- Preserve optimistic concurrency (no silent overwrite of concurrent updates).
- Operator-gated one-shot import from `calendar.json` when present; empty DB when file already gone.
- Fail closed when DB unreachable for calendar-dependent operations.
- Document backup expectation for the calendar DB (stack backup-runner or equivalent).

**Non-Goals:**

- Campaigns, runs, blog/LinkedIn Markdown in DB.
- SQLite on the editorial mount (same wipe class as `calendar.json`).
- Changing LinkedIn variant schedule SoT (`linkedin_distribution` in campaign metadata) in this change.
- Automatic reconstruction of wiped historical calendar rows.
- Deploy/rsync mount harden (separate change; compose path fix may land independently).

## Decisions

### D1 — New Postgres database `silverman_linkedin_db` on `local-ai-stack`

**Choice:** Create a **new** PostgreSQL database named **`silverman_linkedin_db`** on the existing `local-ai-stack` Postgres instance, reachable via `local-ai-stack_backend`. Use a dedicated role with privileges limited to that database. Do **not** store calendar tables as a schema inside another application’s database.

**Why:** Survives editorial mount wipe and code rsync; isolates this product’s data from other stack apps; aligns with existing Postgres + backup-runner; worker already on that network. Operator-fixed name: `silverman_linkedin_db`.

**Alternatives:**

| Option | Rejected because |
|--------|------------------|
| Schema inside a shared/other app DB | Operator requires a separate database named `silverman_linkedin_db` |
| SQLite under `/data/silverman-blog-linkedin` | Same blast radius as `calendar.json` |
| SQLite under worker project dir (outside editorial) | Weaker ops story than stack Postgres backups |
| New managed cloud DB | Unnecessary complexity for LAN worker |

### D2 — Logical model: calendar document + items table

**Choice:**

- `editorial_calendar` (singleton row or keyed `calendar_id='master'`): `schema_version`, `updated_at_utc`, `row_version` (integer or UUID etag for concurrency).
- `editorial_calendar_items`: one row per `item_id`, columns for required fields + JSONB for optional/extension fields (`flow_a_completion`, notes, strategy, etc.) to avoid brittle migrations on every optional key.

**Why:** Matches current document shape; queryable by `due_at_utc` / `status`; concurrency on document or item level.

**Alternative:** Single JSONB blob column — simpler migration, weaker querying/indexing; acceptable fallback if apply prefers minimal schema, but prefer normalized items + JSONB extras.

### D3 — Adapter behind existing load/save API

**Choice:** Keep `load_calendar` / `save_calendar_atomic` (or rename internally) as the sole persistence façade used by plan, schedule-update, completion, and readers. Replace filesystem implementation with DB implementation. Callers MUST NOT open `calendar.json` directly after cutover.

**Why:** Smallest coherent diff; HTTP contracts unchanged.

### D4 — Concurrency via `row_version` / expected version

**Choice:** Replace raw-file SHA-256 fingerprint with integer `row_version` (or content hash of serialized items) checked in a transaction; conflict → same class of error as today’s `calendar_completion_concurrent_update`.

**Why:** Preserves existing conflict semantics for schedule-update and completion writers.

### D5 — Migration: import once, then DB wins

**Choice:**

1. Migrations create empty schema.
2. Operator-gated import: if DB has zero items and `calendar.json` exists and validates → import all items, set `updated_at_utc`, bump version.
3. If DB empty and file missing → empty calendar (valid SoT); status/plan report empty/missing-items appropriately — not `calendar_file_not_found` as permanent SoT failure.
4. After successful import, do **not** dual-write by default. Optional export CLI for disaster recovery later.

**Why:** Live environment already lost the file; import path still helps Mac/dev and any future restore of a JSON copy. Avoid split-brain dual-write.

### D6 — Config and secrets

**Choice:** Env vars only, e.g. `SILVERMAN_CALENDAR_DATABASE_URL` whose path/database name MUST be `silverman_linkedin_db` (or discrete host/port/`silverman_linkedin_db`/user/password). Fail closed if unset in production path when calendar APIs are invoked. Never log credentials; never return them in `/health` beyond `calendar_store=postgres`, `database=silverman_linkedin_db`, `configured=true|false` / reachability.

**Why:** Matches project secret rules; health may expose store kind + DB name + reachability boolean only.

### D7 — `GET /health` and `editorial-calendar/` folder

**Choice:** Keep requiring the `editorial-calendar/` **directory** for folder layout readiness if CURRENT-STATE/health still list it; directory MAY be empty. Calendar content readiness is DB reachability + schema migrated, reported as additive health fields (`calendar_store_ready`), not presence of `calendar.json`.

**Why:** Avoid breaking folder_ready while decoupling SoT from the file.

### D8 — HTTP surface

**Choice:** No new public mutation routes required for v1. Optional additive read-only diagnostics on `GET /editorial-calendar/status` (`store: postgres`, `item_count`, `updated_at_utc`). Import remains CLI or authenticated admin endpoint only if tasks choose CLI-first (prefer CLI/module to avoid expanding HTTP surface without need).

**Why:** ADR-0001; smallest API churn for n8n/console.

### D9 — ADR

**Choice:** Add `docs/decisions/ADR-000X-editorial-calendar-database-persistence.md` (number assigned at apply) accepting Postgres database **`silverman_linkedin_db`** as calendar SoT and forbidding editorial-mount files as sole calendar durability.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Postgres down → calendar ops fail | Fail closed with structured errors; health shows `calendar_store_ready=false`; do not silently fall back to file |
| Split-brain if someone edits leftover `calendar.json` | After cutover, file is non-authoritative; document; optional import only when DB empty |
| Migration complexity / new deps | Pin driver + migration tool; unit tests with Postgres testcontainer or SQLite-for-tests only if dialect-safe — prefer real Postgres in CI/dev when available |
| Schema drift vs JSON optionals | JSONB for extensions; validate same rules as today’s `load_calendar` |
| Backup gap (DB not in BL-014 packages) | Document stack backup-runner ownership; update backup-scope spec |
| Scope creep into campaigns DB | Explicit non-goal; reject in review |

## Migration Plan

1. On stack Postgres: `CREATE DATABASE silverman_linkedin_db` (+ role/grants); confirm volume is outside editorial/rsync paths.
2. Land schema + adapter behind feature flag or hard cutover after tests (prefer hard cutover once flag proven in dry env — single SoT).
3. Deploy worker with URL pointing at `silverman_linkedin_db`; run migrations.
4. Import from `calendar.json` if present; else start empty.
5. Verify plan/status/schedule-visibility against `silverman_linkedin_db`.
6. Update CURRENT-STATE / RUNTIME-STATE / product BL-031 US-041.
7. Rollback: previous image still expects file — only viable if file mirror was kept; **prefer forward-fix** and restore of `silverman_linkedin_db` from backup rather than file rollback. If dual-read fallback is needed temporarily, it MUST be time-boxed and removed in the same change’s follow-up task — default design is no fallback.

## Open Questions

1. Exact Postgres **role** name and password provisioning on `local-ai-stack` for `silverman_linkedin_db` — resolve at apply with operator (database **name** is fixed: `silverman_linkedin_db`).
2. Whether import is CLI-only or authenticated `POST /editorial-calendar/import-from-file` — default **CLI/module** unless operator wants HTTP.
3. Whether `/health` should go unhealthy when DB is down vs remain process-healthy with `calendar_store_ready=false` — recommend **degraded signal, not necessarily fail whole health** so Docker does not restart-loop; calendar APIs still fail closed.
