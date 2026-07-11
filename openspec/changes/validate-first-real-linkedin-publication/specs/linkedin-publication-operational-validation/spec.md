# linkedin-publication-operational-validation

## Purpose

Controlled operational validation for the first real LinkedIn API publication on the production worker — satisfies backlog **BL-002** and user stories **US-003**, **US-004**, and **US-005**. Builds on implemented `linkedin-publication-integration` and `linkedin-oauth-token-lifecycle` without changing default dry-run safety or activating n8n.

## ADDED Requirements

### Requirement: OAuth bootstrap prerequisite before validation

US-003 controlled validation MUST NOT begin until operator OAuth bootstrap is complete on the production server.

Bootstrap MUST include at minimum: host token store files created with correct permissions, Cloudflare Tunnel routing for OAuth callback, browser authorization completed, and `GET /linkedin/oauth/status` reporting `token_present` and `member_urn` without token cleartext.

The US-003 script MUST fail closed when bootstrap is incomplete and MUST reference `docs/deployment/linkedin-publication-prerequisites.md` for remediation.

#### Scenario: Validation blocked without token store

- **WHEN** operator runs US-003 script and diagnostic reports `token_present` false
- **THEN** script exits with `OVERALL: FAIL` before queue or publish-due with `dry_run: false`

#### Scenario: Bootstrap documented separately from validation run

- **WHEN** operator reads US-003 runbook
- **THEN** OAuth bootstrap steps are listed as blocking prerequisites (tasks §0 equivalent), not assumed from prior US-001/US-002 phases

### Requirement: US-003 controlled validation smoke script

The repository MUST provide `deploy/server/run-us003-linkedin-publication-validation-smoke.sh` that performs a controlled first-real-publish validation on the Ubuntu server worker.

The script MUST:

- default to failing closed when prerequisites are not met (publication disabled, missing API key, missing campaign, variant not `pending`);
- run OAuth/credential preflight via `GET /linkedin/oauth/status` (or equivalent safe diagnostic) before any real publish step;
- require explicit operator flags or environment confirmation before enabling real queue and real publish;
- exercise `POST /queue-linkedin-publication` with `dry_run: false` for exactly one operator-selected approved variant;
- exercise `POST /publish-linkedin-due-variants` with `dry_run: false` and `publish_now: true` for the same variant;
- print variant `publish_state`, `publish_after_utc`, `published_at`, and `linkedin_post_urn` before and after each step from campaign metadata;
- exercise a repeat `POST /publish-linkedin-due-variants` real request to verify idempotent behavior (no duplicate external post);
- emit `OVERALL: PASS` or `OVERALL: FAIL` summary;
- never print API keys, access tokens, refresh tokens, client secrets, or authorization codes.

The script MUST NOT activate n8n workflows, modify n8n workflow JSON, or publish variants other than the one explicitly selected.

#### Scenario: Script blocks real publish when publication disabled

- **WHEN** operator runs the US-003 script with real publish flags but `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not `true`
- **THEN** script exits with `OVERALL: FAIL`, prints remediation to enable publication for the validation window, and does not call LinkedIn publication API

#### Scenario: Script completes controlled first publish

- **WHEN** operator runs the US-003 script with valid OAuth token store, publication enabled, one approved `pending` variant on a `distribution_scheduled` Flow A campaign, and real queue + real publish flags
- **THEN** variant transitions `pending` → `queued` → `published` (API publish occurs while variant is `queued`; there is no persisted `publish_state` `publishing`), response and metadata include `linkedin_post_urn`, and script reports `OVERALL: PASS`

#### Scenario: Script verifies idempotent repeat publish

- **WHEN** US-003 script runs a second real publish-due for an already `published` variant
- **THEN** worker does not create a duplicate LinkedIn post, response includes `linkedin_publish_already_published` (or equivalent completed outcome), variant remains `published`, and script records idempotent outcome as pass

### Requirement: OAuth and member identity preflight

Before real queue or publish steps, the US-003 validation script MUST call the safe OAuth diagnostic (`GET /linkedin/oauth/status` or documented equivalent) and verify at minimum:

- token store configured and token present;
- member URN present;
- access token not expired or refresh path available (diagnostic reports actionable state, not token values);
- publication enabled flag matches validation window intent.

Preflight failure MUST abort before real queue or publish and MUST NOT mutate variant `publish_state`.

#### Scenario: Preflight passes with valid token store

- **WHEN** diagnostic reports token present, member URN set, and publication enabled for validation window
- **THEN** script proceeds to real queue step

#### Scenario: Preflight fails on action_required OAuth state

- **WHEN** diagnostic reports reauthorization required or missing member URN
- **THEN** script aborts with `OVERALL: FAIL` and remediation guidance without calling queue or publish-due with `dry_run: false`

### Requirement: LinkedIn visibility confirmation checklist

The repository MUST document a manual operator checklist to confirm the published post is visible on LinkedIn after successful real publish.

The checklist MUST require the operator to record (in the Phase 3 report):

- `linkedin_post_urn` from worker response/metadata;
- approximate `published_at` UTC;
- confirmation that the post appears on the operator's LinkedIn profile feed or activity (human verification; no automated scraping requirement in v1);
- optional link to the LinkedIn post URL if obtainable from the URN without secrets.

The checklist MUST NOT require storing LinkedIn session cookies or credentials in the repository.

#### Scenario: Operator records visibility evidence

- **WHEN** real publish succeeds and operator completes the visibility checklist
- **THEN** Phase 3 report includes URN and human-confirmed visibility statement suitable for US-004 acceptance

### Requirement: Safeguard restoration after validation

The repository MUST document and the US-003 script MUST include a post-validation safeguard restoration step that:

- sets `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` (or documents operator confirmation that it was restored);
- recreates the worker container if required so the disabled flag is active;
- verifies via `GET /linkedin/oauth/status` or health metadata that publication is disabled after restoration;
- records restoration timestamp in the Phase 3 report.

Restoration MUST occur after evidence is captured, even when validation passes.

#### Scenario: Safeguards restored after successful validation

- **WHEN** US-003 validation completes with `OVERALL: PASS`
- **THEN** operator restores `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false`, worker reflects disabled state, and Phase 3 report documents restoration

#### Scenario: Safeguards restored after failed validation

- **WHEN** US-003 validation fails mid-run
- **THEN** operator documentation requires restoration of publication disabled state before leaving the server

### Requirement: Phase 3 validation evidence report

The repository MUST use a dated operational report under `docs/operations/` (for example `phase3-us003-linkedin-publication-validation-YYYY-MM-DD.md`) capturing:

- server host and validation date;
- `BUILD_REVISION` from `/health` when available;
- campaign id and variant id used;
- preflight diagnostic summary (no secrets);
- queue and publish-due outcomes with `publish_state` transitions;
- `linkedin_post_urn` and idempotency rerun outcome;
- LinkedIn visibility confirmation;
- safeguard restoration confirmation;
- explicit mapping to US-003, US-004, and US-005 acceptance criteria pass/fail.

The report MUST NOT contain tokens, API keys, or client secrets.

#### Scenario: Phase 3 report supports BL-002 closure review

- **WHEN** operator completes US-003 validation with real LinkedIn evidence
- **THEN** Phase 3 report provides sufficient traceability to mark US-003, US-004, and US-005 complete without inferring success from code deployment alone

### Requirement: Campaign and variant selection constraints

US-003 validation MUST use exactly one approved LinkedIn variant on a Flow A campaign in state `distribution_scheduled` with valid artifact and `publish_state` `pending`.

The validation MUST NOT use Flow B campaigns.

The validation SHOULD prefer an operator-approved variant tied to real editorial content (for example an existing validated Flow A campaign) rather than synthetic smoke content when operator approves; isolated smoke campaigns MAY be used only when documented and approved for validation.

#### Scenario: Reject Flow B campaign

- **WHEN** US-003 script is invoked with a Flow B campaign id
- **THEN** script fails before real publish with clear error and does not mutate variant state

#### Scenario: Reject variant not pending

- **WHEN** selected variant `publish_state` is already `published` or `queued` without operator override flag
- **THEN** script fails preflight with clear message before unintended publication
