## ADDED Requirements

### Requirement: Topic discovery consumes max_drafts_per_weekly_run

Internal and HTTP topic-discovery paths (capability `flow-b-topic-discovery` / US-078) MUST resolve the discovery batch ceiling via `load_gap_operator_settings()` when present, applying documented defaults when a row is missing. Effective `max_drafts_per_weekly_run` (default **2**) MUST cap how many distinct topics a single discovery batch may return. Saving or loading settings MUST NOT by itself start discovery, draft generation, gap detect, gap trigger, or LinkedIn publication. Settings persist/UI HTTP contracts (`GET`/`PUT /flow-b/gap-operator-settings`) MUST remain unchanged.

#### Scenario: Discovery loader uses stored max_drafts_per_weekly_run

- **WHEN** a settings row exists with `max_drafts_per_weekly_run=1` and topic discovery runs
- **THEN** discovery applies `1` as the batch ceiling rather than the default `2`

#### Scenario: Settings save does not start discovery

- **WHEN** an authenticated client saves valid gap operator settings
- **THEN** this capability does not invoke topic discovery or create draft packages as a side effect

## MODIFIED Requirements

### Requirement: Worker and sensor paths read DB settings

Internal worker loaders used by gap sensor/trigger paths and by Flow B topic discovery MUST resolve settings via the Postgres-backed store when a row is present, and MUST apply documented defaults when a row is missing. Calendar schedule-row SoT contracts (US-041) remain authoritative for editorial calendar items and MUST NOT be replaced by settings storage.

#### Scenario: Loader prefers stored row over defaults

- **WHEN** a settings row exists with `max_drafts_per_weekly_run=1`
- **THEN** an internal settings load returns `1` for that key rather than the default `2`

#### Scenario: Calendar SoT unchanged

- **WHEN** operator settings are saved
- **THEN** editorial calendar item rows and US-041 load/save contracts are not rewritten as a side effect

### Requirement: US-076 scope excludes later Flow B runtime

This capability MUST NOT implement gap detection (US-077), gap trigger orchestration (US-082), AI discovery/draft (US-078/US-079), or blog approve/promote (US-080/US-081). Orchestration remains **n8n → worker HTTP only** (ADR-0001); this change MUST NOT introduce n8n Execute Command usage. Gap detect is owned by a separate capability (`flow-b-calendar-gap-detect`) when present. Topic discovery is owned by a separate capability (`flow-b-topic-discovery`) when present; this settings capability only supplies knobs such as `max_drafts_per_weekly_run` via `load_gap_operator_settings()`.

#### Scenario: No gap-detect or trigger routes required

- **WHEN** this capability’s requirements are evaluated
- **THEN** gap-detect, gap-trigger, discovery, and draft endpoints are not required to be implemented inside the settings capability
- **AND** discovery/draft remain owned by their separate capabilities when present
