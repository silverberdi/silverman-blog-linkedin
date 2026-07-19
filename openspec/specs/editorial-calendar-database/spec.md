# editorial-calendar-database

## Purpose

PostgreSQL-backed durable persistence for the master editorial calendar in database `silverman_linkedin_db` (BL-031 / US-041 / ADR-0004): schema, load/save concurrency, legacy `calendar.json` import, and fail-closed behavior when the store is unavailable. Calendar SoT is outside the editorial filesystem mount.

## Requirements

### Requirement: Calendar database as durable store

The worker SHALL persist the master editorial calendar in a **new** PostgreSQL database named exactly **`silverman_linkedin_db`** on the existing `local-ai-stack` Postgres instance. The worker MUST NOT use a schema inside another application database as the calendar SoT.

Data files for that Postgres instance MUST NOT reside on the editorial filesystem mount (`SILVERMAN_BLOG_LINKEDIN_BASE_PATH`) and MUST NOT share a volume with worker code sync / `rsync` deploy targets.

Connection configuration MUST come from environment variables only and MUST target database `silverman_linkedin_db`. Secrets MUST NOT appear in HTTP responses, logs, or error bodies.

#### Scenario: Calendar survives editorial mount wipe

- **WHEN** the editorial filesystem mount is emptied or replaced while `silverman_linkedin_db` remains intact
- **THEN** subsequent authenticated calendar status and plan reads still return the previously persisted calendar items from that database

#### Scenario: Missing database configuration fails closed

- **WHEN** calendar load or save is requested and the connection to `silverman_linkedin_db` is not configured
- **THEN** the operation fails with a structured secret-safe error and does not invent calendar items from the filesystem

#### Scenario: Canonical database name is silverman_linkedin_db

- **WHEN** an operator inspects deploy/config documentation for the calendar store
- **THEN** the documented database name is `silverman_linkedin_db` and not a shared other-app database name

### Requirement: Calendar schema and item fidelity

The database schema MUST preserve the editorial calendar document contract used by planning and schedule-update:

- document fields: `schema_version`, `updated_at_utc`
- per-item required fields: `item_id`, `title`, `status`, `due_at_utc`, `source_folder`, `flow_type`, `content_mode`, `target_audience`, `topic_theme`, plus document resolution fields as defined by editorial-calendar-orchestration
- allowed statuses: `planned`, `scheduled`, `due`, `in_progress`, `completed`, `skipped`, `failed`
- optional Flow A completion fields when present (`completed_at_utc`, `processed_source_relative_path`, `flow_a_completion`, and other orchestration-allowed optionals)

Invalid documents or items MUST be rejected before commit using the same validation rules as the calendar loader.

#### Scenario: Valid items round-trip through the database

- **WHEN** a valid calendar with one or more items is saved and then loaded
- **THEN** required fields and allowed statuses are unchanged and `updated_at_utc` reflects the save instant

#### Scenario: Invalid item is rejected

- **WHEN** a save attempt includes an item missing a required field or using a disallowed status
- **THEN** the database state is not updated and the operation returns a schema/validation failure

### Requirement: Optimistic concurrency for calendar writes

Calendar writes MUST use transactional optimistic concurrency (document `row_version` or equivalent). When the caller's expected version does not match the stored version, the write MUST NOT apply, MUST leave stored rows unchanged, and MUST return the concurrent-update failure class used by calendar completion/schedule-update callers.

#### Scenario: Concurrent update is rejected

- **WHEN** two writers attempt to save with the same expected version and the first commit succeeds
- **THEN** the second save fails with concurrent-update semantics and does not overwrite the first writer's items

### Requirement: One-time import from legacy calendar.json

The system SHALL provide an operator-gated import that, when the database calendar has no items and a valid `{editorial_base}/editorial-calendar/calendar.json` exists, copies all validated items into the database and sets document metadata accordingly.

When the database already contains items, import MUST NOT overwrite them without an explicit destructive operator action defined in a future approved change (default: refuse).

When the database is empty and `calendar.json` is missing or invalid, the database remains the SoT (empty or prior valid state); the worker MUST NOT treat missing `calendar.json` as permanent calendar SoT failure after cutover.

#### Scenario: Import from valid legacy file into empty database

- **WHEN** the database has zero calendar items and a valid `calendar.json` is present
- **THEN** import loads those items into the database and subsequent loads read from the database

#### Scenario: Import refuses to clobber non-empty database

- **WHEN** the database already has one or more calendar items and import is requested without an approved destructive mode
- **THEN** import is refused and database items remain unchanged

#### Scenario: Empty database without legacy file is valid SoT

- **WHEN** the database has zero items and `calendar.json` is absent
- **THEN** calendar load succeeds as an empty calendar (or status reports empty) and does not require recreating `calendar.json` for SoT

### Requirement: Database unavailability fails closed

When the calendar database is unreachable or schema is not migrated, calendar read and write entry points MUST fail closed with structured secret-safe errors. The worker MUST NOT silently fall back to `calendar.json` as authoritative SoT after cutover.

#### Scenario: Unreachable database blocks plan-due

- **WHEN** `POST /editorial-calendar/plan-due` is called and the calendar database cannot be reached
- **THEN** the endpoint returns a structured failure and does not plan from a filesystem calendar file
