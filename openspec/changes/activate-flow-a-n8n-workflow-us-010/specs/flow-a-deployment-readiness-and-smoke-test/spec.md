## MODIFIED Requirements

### Requirement: Flow A workflow export checks

The readiness command SHALL verify the Flow A n8n workflow export in the repository checkout without activating the live server workflow.

#### Scenario: Required workflow file present

- **WHEN** Phase 0 checks `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` in the configured repo path
- **THEN** a missing file causes Phase 0 to fail clearly

#### Scenario: Workflow export inactive

- **WHEN** Phase 0 parses the Flow A workflow JSON export
- **THEN** it requires top-level `"active": false`; if `"active": true`, Phase 0 fails clearly

#### Scenario: Workflow export includes approved schedule trigger

- **WHEN** Phase 0 parses the Flow A workflow JSON export after US-010
- **THEN** it requires exactly one Schedule Trigger configured for daily 09:00 UTC (`0 9 * * *` UTC semantics) and fails clearly if missing or incorrect

#### Scenario: Workflow export retains manual trigger

- **WHEN** Phase 0 parses the Flow A workflow JSON export
- **THEN** it requires a Manual Trigger node and fails clearly if absent

### Requirement: Repeatable n8n Flow A import on Ubuntu server

The repository SHALL provide `deploy/server/import-flow-a-n8n-workflow.sh` that imports the Flow A workflow into the real n8n container (not the nginx gateway), prepares a stable workflow id for Postgres import, configures worker URL and API key without printing secrets, and verifies the imported workflow remains inactive immediately after import.

#### Scenario: Select n8n container by image

- **WHEN** the import script runs on a host with `local-ai-stack` n8n and nginx gateway containers
- **THEN** it selects a running container whose image matches `n8nio/n8n` or `docker.n8n.io/n8nio/n8n` and does not use the nginx gateway container for `n8n import:workflow`

#### Scenario: Stable workflow id required

- **WHEN** the source workflow JSON lacks a top-level `id` or has null import-breaking metadata fields
- **THEN** the script prepares import JSON with stable id `silvermanFlowAPublish01`, removes null `createdAt`, `updatedAt`, and `versionId` when present, and sets `active: false`

#### Scenario: Import verification without activation

- **WHEN** import completes successfully
- **THEN** the script verifies via `export:workflow` that the workflow exists by stable id `silvermanFlowAPublish01` (name is a secondary assert only; name-only match without that id MUST FAIL), has the US-010 expected node count, includes the required Schedule Trigger, and `active` is false, without activating the workflow

#### Scenario: Import notes separate activation step

- **WHEN** import verification passes under US-010
- **THEN** output states that Schedule Trigger is present and that server activation (`active: true`) is a separate operator step

### Requirement: Smoke-test phase gating

Smoke testing SHALL follow phased execution with Phase 0 as a mandatory gate.

#### Scenario: Phase 0 gates later phases

- **WHEN** Phase 0 overall result is fail
- **THEN** Phases 1–4 MUST NOT proceed automatically and the CLI exits with non-zero status when invoked for `--phase all` or higher phases without `--force`

#### Scenario: Phase 1 worker endpoint contract smoke

- **WHEN** Phase 0 passes and the operator runs Phase 1
- **THEN** the command performs non-destructive worker contract checks including authenticated `POST /process-ready` when an API key is configured, without invoking publish, package generation, or scheduling apply paths that mutate production state

#### Scenario: Phase 2 n8n configuration smoke

- **WHEN** Phase 0 passes and the operator runs Phase 2
- **THEN** the command verifies n8n reachability and repository-style workflow export expectations (`active: false`, Schedule Trigger present, expected identity) and reports import/configuration pending items without activating the workflow

#### Scenario: Phase 3 full manual Flow A execution

- **WHEN** Phases 0–2 pass and the operator runs Phase 3 per documented procedure
- **THEN** documentation describes manual n8n Manual Trigger execution of the Flow A workflow, noting repository export remains `"active": false` while server may be activated under US-010 ops procedures

#### Scenario: Phase 4 idempotent rerun verification

- **WHEN** Phase 3 has been executed successfully
- **THEN** documentation and checklist require a second manual run confirming idempotent worker responses and no duplicate blog or LinkedIn artifacts

### Requirement: Post-smoke evidence collection script

The repository SHALL provide a repeatable server-side script at `deploy/server/collect-flow-a-smoke-evidence.sh` that collects read-only Flow A post-smoke evidence on the Ubuntu server without ad-hoc SSH heredoc commands.

The script MUST support distinguishing pre-activation (`active: false` expected) from post-activation verification (`active: true` expected when an explicit activation-evidence flag/mode is set). Default historical behavior that treated any `active: true` as FAIL MUST be replaced by mode-aware expectations after US-010.

#### Scenario: Evidence script resolves editorial base path

- **WHEN** an operator runs the evidence script on the Ubuntu server without `BASE_PATH` set
- **THEN** the script resolves the editorial root from container env `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`, Docker mounts, `GET /health`, or known host candidates
- **AND** prints how the base path was resolved
- **AND** if unresolved, reports `OVERALL: FAIL` with remediation guidance and no stack trace

#### Scenario: Evidence script collects worker, file, and n8n checks

- **WHEN** the evidence script runs successfully against a deployed environment
- **THEN** it verifies worker `GET /health` and `GET /openapi.json` include Flow A paths `/publish-blog-post`, `/generate-linkedin-package`, and `/schedule-linkedin-distribution`
- **AND** reports latest metadata and generated LinkedIn artifacts under the resolved editorial base path
- **AND** reports published `_posts` and `assets/images` matches for the slug fragment under the public GitHub Pages repo host mount (or inside the container at `/public-blog` when the host mount cannot be resolved), not under the editorial base path
- **AND** exports n8n workflows from the real n8n container and confirms workflow id `silvermanFlowAPublish01` with expected name, expected node count, and required Schedule Trigger (name-only match without that stable id MUST FAIL)

#### Scenario: Evidence script safety constraints

- **WHEN** the evidence script runs
- **THEN** it does not print API keys or secret env values, does not call the LinkedIn API, and does not deploy or restart services by default

#### Scenario: Evidence script overall status

- **WHEN** worker, public blog repo, and n8n checks pass and campaign metadata or generated LinkedIn artifacts exist
- **THEN** the script reports `OVERALL: PASS`
- **WHEN** worker, public blog repo, and n8n checks pass but smoke artifacts are not found yet
- **THEN** the script reports `OVERALL: PENDING`
- **WHEN** base path is unresolved, Flow A OpenAPI paths are missing, public blog repo is not mounted or incomplete, active-state expectation is violated for the selected mode, or n8n is missing
- **THEN** the script reports `OVERALL: FAIL`
- **WHEN** worker and n8n checks pass but public blog repo is missing or incomplete
- **THEN** the script reports `OVERALL: FAIL` with remediation (not `PENDING`) because publish would fail with `blog_publish_public_repo_not_configured`

#### Scenario: Pre-activation mode expects inactive

- **WHEN** evidence runs in pre-activation mode and `silvermanFlowAPublish01` is `active: true`
- **THEN** the script reports `FAIL` with remediation to deactivate or switch to post-activation mode after intentional activate

#### Scenario: Post-activation mode expects active

- **WHEN** evidence runs in post-activation mode and `silvermanFlowAPublish01` is `active: true` with Schedule Trigger present
- **THEN** the active-state check reports PASS

## ADDED Requirements

### Requirement: Activation evidence entry point

The repository SHALL provide an operator-facing activation verification path (dedicated script or documented mode of existing evidence/import tools) that reports PASS/PENDING/FAIL for US-010 activation criteria: server `active: true`, Schedule Trigger `0 9 * * *` UTC, single-flight guard present, expected node count, and clear remediation without printing secrets.

#### Scenario: Activation verifier pending before activate

- **WHEN** the workflow is imported with Schedule Trigger but still inactive
- **THEN** activation verification reports `PENDING` with remediation to activate after identity checks

#### Scenario: Activation verifier pass after activate

- **WHEN** the workflow is active with required schedule and single-flight guard
- **THEN** activation verification reports `PASS`
