# ADR-0004: Persist Master Editorial Calendar in PostgreSQL (`silverman_linkedin_db`)

## Status

Accepted

## Context

The master editorial calendar lived at `{editorial_base}/editorial-calendar/calendar.json`. On 2026-07-18 a deploy mounted the code-sync checkout as the editorial base and `rsync --delete` wiped calendar state. LinkedIn variant Markdown could be recovered; schedule rows could not.

File-backed calendar SoT on the editorial mount shares fate with deploy mistakes. The worker already attaches to Docker network `local-ai-stack_backend`, where PostgreSQL runs for the shared stack.

## Decision

- Persist the master editorial calendar in a **new** PostgreSQL database named **`silverman_linkedin_db`** on the existing `local-ai-stack` Postgres instance.
- Do **not** place calendar tables as a schema inside another application database.
- Do **not** use SQLite (or any DB file) under the editorial mount as calendar SoT.
- Keep blog Markdown and LinkedIn variant Markdown on the filesystem (ADR-0002 unchanged).
- Keep worker ↔ n8n interaction HTTP-only (ADR-0001 unchanged).
- After cutover, `calendar.json` is non-authoritative (optional import only).

## Consequences

- Calendar survives editorial mount wipe and code rsync when Postgres data volumes are intact.
- Worker requires `SILVERMAN_CALENDAR_DATABASE_URL` (or equivalent) targeting `silverman_linkedin_db`; calendar APIs fail closed when the store is unavailable.
- BL-014 filesystem backup packages are no longer the recovery SoT for calendar schedule state; stack/Postgres backup owns calendar durability.
- Campaign metadata and content trees remain filesystem-backed until a separate approved change.
- Operators must create DB/role `silverman_linkedin_db` before enabling calendar-dependent production paths.
