# linkedin-publication-integration

## ADDED Requirements

### Requirement: US-003 operational validation script reference

The repository MUST provide `deploy/server/run-us003-linkedin-publication-validation-smoke.sh` as the canonical controlled-validation entry point for first real LinkedIn publication (backlog **BL-002**).

This script MUST compose the existing publication endpoints (`POST /queue-linkedin-publication`, `POST /publish-linkedin-due-variants`) and MUST NOT bypass HTTP auth, dry-run defaults in generic smoke, or publication enablement guards.

Generic `deploy/server/run-linkedin-publication-smoke.sh` remains the lower-level endpoint exerciser; US-003 script adds preflight, idempotency rerun, safeguard restoration checklist, and Phase 3 evidence hooks.

#### Scenario: US-003 script uses publication endpoints

- **WHEN** operator runs US-003 controlled validation
- **THEN** real publish path invokes worker HTTP endpoints only (ADR-0001), not direct module imports or n8n Execute Command

#### Scenario: Generic smoke remains dry-run default

- **WHEN** operator runs `run-linkedin-publication-smoke.sh` without real flags
- **THEN** behavior is unchanged — dry-run queue and publish-due with no LinkedIn API calls

### Requirement: Idempotent published variant on repeat publish-due

When `POST /publish-linkedin-due-variants` runs with `dry_run: false` for a variant already in `publish_state` `published` with a stored `linkedin_post_urn`, the worker MUST:

- NOT call LinkedIn publication API again;
- return a completed outcome indicating already published (stable code or status field documented for operators);
- preserve existing `linkedin_post_urn` and `published_at` in campaign metadata;
- NOT transition variant to `failed`.

#### Scenario: Repeat real publish-due for published variant

- **WHEN** publish-due runs with `dry_run: false` for a variant with `publish_state` `published` and existing `linkedin_post_urn`
- **THEN** no LinkedIn API call occurs, response indicates already published, and metadata URN is unchanged

#### Scenario: US-003 script asserts idempotency

- **WHEN** US-003 validation script runs repeat publish-due after successful first publish
- **THEN** script treats no-op idempotent response as pass for duplicate-prevention evidence

### Requirement: Operator documentation for first real publish validation

Operator documentation MUST describe the US-003 controlled validation procedure including:

- prerequisites (OAuth token store, member URN, publication flag enablement window);
- selection of one approved variant;
- queue → `publish_now` publish-due sequence;
- idempotency verification;
- manual LinkedIn visibility confirmation;
- mandatory restoration of `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` after validation;
- reference to Phase 3 evidence report location.

Documentation MUST distinguish **implemented** LinkedIn publication from **operationally validated** publication per `docs/CURRENT-STATE.md` completion layers.

#### Scenario: Operator finds US-003 runbook

- **WHEN** operator reads LinkedIn publication deployment documentation
- **THEN** they find the US-003 script path, enablement window rules, and safeguard restoration steps
