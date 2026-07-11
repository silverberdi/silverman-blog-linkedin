# flow-a-deployment-readiness-and-smoke-test

## ADDED Requirements

### Requirement: US-003 LinkedIn publication validation entry point

The repository SHALL document `deploy/server/run-us003-linkedin-publication-validation-smoke.sh` as the controlled operational validation entry point for first real LinkedIn publication (backlog **BL-002**, user stories **US-003**–**US-005**).

Deployment and operations documentation MUST list this script alongside existing US-001 and US-002 validation scripts as a separate gated validation — not part of default Flow A Core smoke PASS semantics.

#### Scenario: Operator discovers US-003 script from deployment docs

- **WHEN** operator reads server deployment or smoke documentation
- **THEN** they find `run-us003-linkedin-publication-validation-smoke.sh` with explicit warning that it performs real LinkedIn publication when enabled

#### Scenario: Flow A Core smoke PASS unchanged without US-003

- **WHEN** Flow A Core smoke or evidence collection passes with `distribution_scheduled` and variants still `pending`
- **THEN** overall PASS does not imply LinkedIn API publication is operationally validated

### Requirement: Evidence collector LinkedIn published state

When `deploy/server/collect-flow-a-smoke-evidence.sh` reports per-variant LinkedIn `publish_state` counts and at least one variant is `published`, the summary MUST include `linkedin_post_urn` presence yes/no per published variant (URN value only, no body text, no tokens).

#### Scenario: Evidence shows published variant URN flag

- **WHEN** evidence collection runs for a campaign with one `published` variant storing `linkedin_post_urn`
- **THEN** summary reports published count 1 and URN recorded without variant body text
