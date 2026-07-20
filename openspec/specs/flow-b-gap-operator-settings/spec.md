# flow-b-gap-operator-settings

## Purpose

Persist, validate, authenticate, and UI-edit Flow B gap operator settings in Postgres (`silverman_linkedin_db`) with documented defaults and fail-closed `gap_trigger_enabled`. Secret-safe HTTP/API responses; saving settings MUST NOT enable LinkedIn API publish. Provides `load_gap_operator_settings()` for gap-detect (US-077), topic discovery (US-078), blog draft generation (US-079), and later consumers. Gap trigger/approve remain out of scope (US-080–US-082); discovery is owned by `flow-b-topic-discovery`; draft generation is owned by `flow-b-blog-draft-generation`.

## Requirements

### Requirement: Persist Flow B gap operator settings in Postgres

The worker SHALL persist Flow B gap operator settings in PostgreSQL database **`silverman_linkedin_db`** (or a documented sibling database on the same deployment that MUST be named explicitly in ops docs). Long-term source of truth MUST NOT be environment variables alone.

The settings document MUST support at least these keys with the stated defaults when a row is missing:

| Key | Default |
|-----|---------|
| `operator_timezone` | Valid IANA timezone (from saved row; when row missing, documented effective default MAY use a valid `SILVERMAN_OPERATOR_TIMEZONE` env value if present, otherwise a documented placeholder policy that still validates IANA on write) |
| `gap_trigger_enabled` | `false` |
| `gap_scan_mode` | `next_week` |
| `weekly_run_local_day` | `friday` |
| `weekly_run_local_time` | `15:00` |
| `min_lead_days` | `5` |
| `gap_posts_threshold` | `0` |
| `max_drafts_per_weekly_run` | `2` |
| `density_max_per_local_day` | `2` |

Connection secrets MUST come from environment only and MUST NEVER appear in HTTP responses, logs, or error bodies.

#### Scenario: Settings round-trip through the database

- **WHEN** an authenticated client saves a valid settings document and then reads settings
- **THEN** the persisted values are returned unchanged (aside from server-managed metadata such as `updated_at_utc`)
- **AND** the store target is `silverman_linkedin_db` or the documented sibling

#### Scenario: Missing row yields documented defaults

- **WHEN** no settings row exists and an authenticated client or internal loader reads settings
- **THEN** the effective document uses the documented defaults including `gap_trigger_enabled=false`
- **AND** the response indicates that defaults were applied (for example `source: defaults`)

### Requirement: Validate operator settings on write

Authenticated settings updates MUST validate:

- `operator_timezone` as a real IANA timezone (zoneinfo)
- `weekly_run_local_time` as a 24-hour `HH:MM` time-of-day
- `weekly_run_local_day` as an allowed weekday enum
- `gap_scan_mode` as an allowed enum (`next_week` in v1)
- integer knobs (`min_lead_days`, `gap_posts_threshold`, `max_drafts_per_weekly_run`, `density_max_per_local_day`) as non-negative integers
- `gap_trigger_enabled` as boolean

Invalid writes MUST fail closed with structured secret-safe errors and MUST NOT partially persist invalid values.

#### Scenario: Invalid IANA timezone is rejected

- **WHEN** a client PUTs settings with `operator_timezone` that is not a valid IANA zone
- **THEN** the worker rejects the update with a structured validation error
- **AND** any previously valid stored row remains unchanged

#### Scenario: Negative integer knob is rejected

- **WHEN** a client PUTs settings with a negative `min_lead_days` (or other integer knob)
- **THEN** the worker rejects the update with a structured validation error

### Requirement: Authenticated settings HTTP API

The worker SHALL expose authenticated HTTP endpoints to read and update Flow B gap operator settings (for example `GET` and `PUT` under `/flow-b/gap-operator-settings`). Unauthenticated requests MUST be rejected. Responses MUST be JSON and MUST NOT include API keys, OAuth tokens, database passwords, or other secrets.

Saving settings MUST NOT enable LinkedIn API publication and MUST NOT modify `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. With `gap_trigger_enabled=false`, automatic gap triggering remains fail-closed (no auto-trigger side effects from this capability alone).

#### Scenario: Unauthenticated read is rejected

- **WHEN** a client calls the settings GET without valid worker authentication
- **THEN** the request is rejected and no settings document is returned

#### Scenario: Save does not enable LinkedIn publish

- **WHEN** an authenticated client saves valid settings including any combination of gap knobs
- **THEN** LinkedIn API publication enablement remains governed solely by existing env guards
- **AND** the settings response does not expose secrets

#### Scenario: Disabled gap trigger stays fail-closed

- **WHEN** effective settings have `gap_trigger_enabled=false`
- **THEN** this capability does not start discovery, draft generation, or LinkedIn publication

### Requirement: Worker and sensor paths read DB settings

Internal worker loaders used by gap sensor/trigger paths and by Flow B topic discovery MUST resolve settings via the Postgres-backed store when a row is present, and MUST apply documented defaults when a row is missing. Calendar schedule-row SoT contracts (US-041) remain authoritative for editorial calendar items and MUST NOT be replaced by settings storage.

#### Scenario: Loader prefers stored row over defaults

- **WHEN** a settings row exists with `max_drafts_per_weekly_run=1`
- **THEN** an internal settings load returns `1` for that key rather than the default `2`

#### Scenario: Calendar SoT unchanged

- **WHEN** operator settings are saved
- **THEN** editorial calendar item rows and US-041 load/save contracts are not rewritten as a side effect

### Requirement: Gap detect consumes settings without requiring trigger enablement

Internal and HTTP gap-detect paths (capability `flow-b-calendar-gap-detect` / US-077) MUST resolve operator knobs via `load_gap_operator_settings()` when present, applying documented defaults when a row is missing. Detect MUST be allowed to run for inspection when effective `gap_trigger_enabled` is `false`. Saving or loading settings MUST NOT by itself start gap detect, discovery, draft generation, or LinkedIn publication.

#### Scenario: Detect loader uses stored min_lead_days

- **WHEN** a settings row exists with `min_lead_days=7` and gap detect runs
- **THEN** detect applies `7` as the lead filter rather than the default `5`

#### Scenario: Disabled trigger does not block settings-backed detect

- **WHEN** effective settings have `gap_trigger_enabled=false` and an authenticated detect consumer loads settings
- **THEN** the loader still returns the effective settings document
- **AND** detect consumers are not required to refuse inspection solely because the trigger flag is false

### Requirement: Topic discovery consumes max_drafts_per_weekly_run

Internal and HTTP topic-discovery paths (capability `flow-b-topic-discovery` / US-078) MUST resolve the discovery batch ceiling via `load_gap_operator_settings()` when present, applying documented defaults when a row is missing. Effective `max_drafts_per_weekly_run` (default **2**) MUST cap how many distinct topics a single discovery batch may return. Saving or loading settings MUST NOT by itself start discovery, draft generation, gap detect, gap trigger, or LinkedIn publication. Settings persist/UI HTTP contracts (`GET`/`PUT /flow-b/gap-operator-settings`) MUST remain unchanged.

#### Scenario: Discovery loader uses stored max_drafts_per_weekly_run

- **WHEN** a settings row exists with `max_drafts_per_weekly_run=1` and topic discovery runs
- **THEN** discovery applies `1` as the batch ceiling rather than the default `2`

#### Scenario: Settings save does not start discovery

- **WHEN** an authenticated client saves valid gap operator settings
- **THEN** this capability does not invoke topic discovery or create draft packages as a side effect

### Requirement: Blog draft generation consumes max_drafts_per_weekly_run

Internal and HTTP blog-draft-generation paths (capability `flow-b-blog-draft-generation` / US-079) MUST resolve the draft batch ceiling via `load_gap_operator_settings()` when present, applying documented defaults when a row is missing. Effective `max_drafts_per_weekly_run` (default **2**) MUST cap how many draft packages a single generation request may produce. Saving or loading settings MUST NOT by itself start draft generation, topic discovery, gap detect, gap trigger, or LinkedIn publication. Settings persist/UI HTTP contracts (`GET`/`PUT /flow-b/gap-operator-settings`) MUST remain unchanged.

#### Scenario: Draft generation loader uses stored max_drafts_per_weekly_run

- **WHEN** a settings row exists with `max_drafts_per_weekly_run=1` and blog draft generation runs with multiple topics
- **THEN** draft generation applies `1` as the batch ceiling rather than the default `2`

#### Scenario: Settings save does not start draft generation

- **WHEN** an authenticated client saves valid gap operator settings
- **THEN** this capability does not invoke blog draft generation or create `pending-approval/` packages as a side effect

### Requirement: US-076 scope excludes later Flow B runtime

This capability MUST NOT implement gap detection (US-077), gap trigger orchestration (US-082), AI topic discovery (US-078), AI blog draft generation (US-079), or blog approve/promote (US-080/US-081). Orchestration remains **n8n → worker HTTP only** (ADR-0001); this change MUST NOT introduce n8n Execute Command usage. Gap detect is owned by a separate capability (`flow-b-calendar-gap-detect`) when present. Topic discovery is owned by a separate capability (`flow-b-topic-discovery`) when present. Blog draft generation is owned by a separate capability (`flow-b-blog-draft-generation`) when present; this settings capability supplies knobs such as `max_drafts_per_weekly_run` via `load_gap_operator_settings()`.

#### Scenario: No gap-detect or trigger routes required

- **WHEN** this capability's requirements are evaluated
- **THEN** gap-detect, gap-trigger, discovery, and draft endpoints are not required to be implemented inside the settings capability
- **AND** discovery and draft generation remain owned by their separate capabilities when present
