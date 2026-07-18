## ADDED Requirements

### Requirement: Console-driven defer records actor and source when supplied

`POST /defer-linkedin-variant` and the defer service entry point MUST accept optional `actor` and `source` fields when provided by an authenticated caller (including the Flow A supervision console).

When supplied on a successful real defer, the worker MUST record actor and/or source on the variant’s `operator_supervision` audit surface (top-level and/or the new `deferral_history` entry) together with existing previous/new schedule timestamps, `deferred_at_utc`, reason, and idempotency proof behavior.

Omitted actor/source MUST preserve existing US-017 defer behavior (including default actor semantics already documented for operator supervision).

Defer MUST remain limited to `publish_state` `pending` variants, MUST keep `publish_state` as `pending`, MUST NOT call the LinkedIn publication API, and MUST NOT write `editorial-calendar/calendar.json` as part of defer.

#### Scenario: Defer with source from supervision console is audited

- **WHEN** a real defer succeeds with `source` `linkedin_variant_supervision_console` and a future `new_scheduled_at_utc`
- **THEN** `scheduled_at_utc` is updated, `deferral_history` records previous and new schedules, and the supplied source is present on the audit surface

#### Scenario: Defer without source remains compatible

- **WHEN** a real defer succeeds without `source` or `actor` fields
- **THEN** existing pending-only defer semantics and `deferral_history` previous/new timestamps still apply

### Requirement: Interim LinkedIn schedule saturation and duplicate-slot checks on defer

In addition to requiring `new_scheduled_at_utc` strictly in the future, defer MUST reject requests that violate interim US-040C cadence/reschedule safeguards for LinkedIn schedule **intent** (until an approved BL-021 definition supersedes them):

- duplicate slot: another variant in the same campaign already has the same `scheduled_at_utc` instant (`linkedin_supervision_defer_duplicate_slot` or equivalent stable code)
- saturation: the new time would place two or more variants of the same campaign on the same UTC day and within 72 hours of another variant’s `scheduled_at_utc` in that campaign (`linkedin_supervision_defer_saturation` or equivalent)

These checks MUST NOT call LinkedIn APIs, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, and MUST NOT change publish-time US-020 cadence enforcement (publish-time cadence remains authoritative at send).

Dry-run MUST validate these rules without mutating metadata.

#### Scenario: Duplicate scheduled instant is rejected

- **WHEN** defer requests `new_scheduled_at_utc` equal to another variant’s `scheduled_at_utc` in the same campaign
- **THEN** the operation fails with a stable duplicate-slot code and schedule is unchanged

#### Scenario: Interim same-day saturation is rejected

- **WHEN** defer would place a second campaign variant on the same UTC day within 72 hours of a sibling’s `scheduled_at_utc`
- **THEN** the operation fails with a stable saturation code and schedule is unchanged

## MODIFIED Requirements

### Requirement: HTTP endpoint POST /defer-linkedin-variant

The worker SHALL expose `POST /defer-linkedin-variant` with API key authentication.

Request body MUST include `campaign_id`, `variant`, `new_scheduled_at_utc`, optional `dry_run` (default `true`), optional `reason`, optional `idempotency_key`, and MAY include optional `actor` and `source` for audit attribution.

#### Scenario: Defer endpoint defaults to dry-run

- **WHEN** defer request omits `dry_run`
- **THEN** worker validates without mutating `scheduled_at_utc` or metadata

#### Scenario: Defer endpoint accepts optional source

- **WHEN** an authenticated defer request includes `source` `linkedin_variant_supervision_console`
- **THEN** the worker accepts the field for audit attribution without requiring a second defer endpoint
