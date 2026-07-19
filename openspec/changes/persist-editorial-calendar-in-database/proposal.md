## Why

A code deploy with `rsync --delete` against a wrongly mounted editorial checkout wiped `editorial-calendar/calendar.json` and left the supervision console without schedule facts, even though LinkedIn variant Markdown files could be recovered. Master calendar planning state is durable operational data and MUST NOT share fate with code sync or content trees. Why now: the 2026-07-18 incident proved file-only calendar persistence is an unacceptable loss mode for Flow A supervision and due-item planning.

## Goals

- Persist the master editorial calendar (items, due times, statuses, Flow A completion summaries) in a **new** PostgreSQL database named **`silverman_linkedin_db`** on the existing `local-ai-stack` Postgres instance (not a schema bolted onto another app DB). Storage MUST be **outside** the editorial filesystem mount and **outside** any deploy/rsync target.
- Keep existing worker HTTP contracts for calendar plan/status/schedule-update, schedule-visibility, and console reads/mutations stable for callers (n8n, console) unless a delta explicitly requires additive fields.
- Provide a one-time / operator-gated migration path from `editorial-calendar/calendar.json` when a file still exists, plus clear behavior when the file is already gone.
- Fail closed when the database is unavailable for calendar reads/writes that today require a valid calendar.
- Update product backlog/stories for the new durability outcome (proposed **BL-031** / **US-041**).

## Non-goals

- Migrating campaign metadata (`metadata/campaigns/`), runs, blog Markdown, or LinkedIn variant Markdown into a database (follow-up).
- Replacing BL-014 editorial file backup for remaining filesystem scope; calendar DB backup is owned by DB/ops policy, not by packing `calendar.json` as the sole SoT.
- BL-021 publishing-cadence policy (frequency/windows/density rules).
- Deploy/rsync harden of the editorial mount (compose/mount safety) — related operational fix, separate change.
- Public hosting, BFF, user management, Google/OIDC activation, Flow B implementation.
- n8n Execute Command or any non-HTTP orchestration (ADR-0001 unchanged).

## What Changes

- **BREAKING (internal SoT):** Canonical master calendar source of truth moves from `{editorial_base}/editorial-calendar/calendar.json` to PostgreSQL database **`silverman_linkedin_db`**. The file MAY remain as optional import/export or deprecated mirror only if design chooses; it MUST NOT remain the sole durability layer.
- Create the new database `silverman_linkedin_db` (plus dedicated role as needed) on the stack Postgres; add worker connectivity, schema/migrations, and a persistence adapter behind existing calendar load/save APIs.
- Migrate / adapt calendar atomicity and concurrency controls from file fingerprint replace to DB transactions / optimistic concurrency.
- Update backup-scope language so calendar durability is DB-backed; filesystem `editorial-calendar/` is no longer the recovery SoT for schedule state.
- Document env/config for DB URL/credentials (secrets in env only; never in responses).
- Add proposed backlog item **BL-031** and user story **US-041** in product docs when this change is approved for apply (proposal references them; docs update is an apply/sync task).

## Capabilities

### New Capabilities

- `editorial-calendar-database`: Persistence for the master editorial calendar in new Postgres DB `silverman_linkedin_db` (create DB/role, schema, migrations, load/save/concurrency, migration-from-file, fail-closed availability, secret-safe config).

### Modified Capabilities

- `editorial-calendar-orchestration`: Canonical store requirement changes from `calendar.json` filesystem artifact to database-backed persistence; atomic file-save and “MUST NOT introduce a database” constraints are replaced; HTTP plan/status/schedule-update behavior preserved at the contract level where possible.
- `editorial-backup-scope-retention-integrity`: Calendar SoT moves out of included filesystem scope as primary recovery class; document DB backup expectation and any residual `editorial-calendar/` role (empty folder for health vs optional export).

## Impact

- **Code:** `editorial_calendar_plan.py`, schedule-update, Flow A calendar execute/completion paths, schedule-visibility / pending-supervision / operational-status calendar loaders, tests, Docker/compose env for reachability of `silverman_linkedin_db` on `local-ai-stack_backend`.
- **APIs:** Prefer stable paths (`POST /editorial-calendar/plan-due`, `GET /editorial-calendar/status`, `POST /editorial-calendar/update-item-schedule`, schedule-visibility). Additive health/diagnostic fields MAY report calendar-store backend (`postgres` / `silverman_linkedin_db`).
- **Deps:** DB driver + migration tool (Postgres + SQLAlchemy/Alembic or equivalent already compatible with project Python constraints).
- **Ops:** Create DB `silverman_linkedin_db` on stack Postgres; new secrets (URL or discrete host/user/password targeting that DB only); backups via stack backup-runner; deploy must not wipe Postgres data volume.
- **Product:** Proposed **BL-031 — Persist Editorial Calendar in a Database** / **US-041**; does not close BL-015 or advance US-040I–K.
- **Acceptance criteria addressed (proposed US-041):** Calendar survives code deploy and editorial mount wipe; worker reads/writes calendar via DB; HTTP callers unchanged in happy path; missing legacy file does not block empty or migrated DB calendar; secrets never exposed.
- **Acceptance criteria excluded:** Campaign/LinkedIn file recovery; live restore of pre-incident wiped calendar rows (data already lost unless an external copy appears); cadence policy (BL-021).

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-031 / US-041** (proposed) | Primary — durable calendar in DB |
| BL-014 | Precedent — editorial durability; filesystem backup remains for non-calendar trees |
| BL-015 / US-040* | Consumers of calendar via schedule-visibility; HTTP stability protects console |
| BL-021 | Out of scope — cadence policy, not persistence |
