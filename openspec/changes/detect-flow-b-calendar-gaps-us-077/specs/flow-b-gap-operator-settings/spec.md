## ADDED Requirements

### Requirement: Gap detect consumes settings without requiring trigger enablement

Internal and HTTP gap-detect paths (capability `flow-b-calendar-gap-detect` / US-077) MUST resolve operator knobs via `load_gap_operator_settings()` when present, applying documented defaults when a row is missing. Detect MUST be allowed to run for inspection when effective `gap_trigger_enabled` is `false`. Saving or loading settings MUST NOT by itself start gap detect, discovery, draft generation, or LinkedIn publication.

#### Scenario: Detect loader uses stored min_lead_days

- **WHEN** a settings row exists with `min_lead_days=7` and gap detect runs
- **THEN** detect applies `7` as the lead filter rather than the default `5`

#### Scenario: Disabled trigger does not block settings-backed detect

- **WHEN** effective settings have `gap_trigger_enabled=false` and an authenticated detect consumer loads settings
- **THEN** the loader still returns the effective settings document
- **AND** detect consumers are not required to refuse inspection solely because the trigger flag is false
