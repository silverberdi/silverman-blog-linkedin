## ADDED Requirements

### Requirement: Umbrella child change reference

This capability SHALL be implemented as child OpenSpec change `flow-a-deployment-readiness-and-smoke-test` under active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`. It SHALL complete operational verification after slice 7 and before umbrella archive. Slice 8 (`linkedin-publication-integration`) remains deferred.

#### Scenario: Child cites umbrella

- **WHEN** an operator inspects `openspec/changes/flow-a-deployment-readiness-and-smoke-test/proposal.md`
- **THEN** it references `flow-a-automatic-blog-linkedin-publishing-roadmap` for Flow A policy, lifecycle, and sequencing

#### Scenario: Umbrella not ready to archive until verification completes

- **WHEN** `flow-a-deployment-readiness-and-smoke-test` is not completed and archived
- **THEN** the umbrella MUST remain active and MUST NOT be marked ready to archive solely because slices 1–7 are complete

### Requirement: Primary readiness entry point

The repository SHALL provide a repeatable local command entry point at `scripts/flow_a_readiness.py` that performs deployment readiness and phased smoke verification for Flow A without requiring ad-hoc diagnostic curl sequences as the primary workflow.

#### Scenario: CLI invocation

- **WHEN** an operator runs `python scripts/flow_a_readiness.py` with valid arguments
- **THEN** the command executes Phase 0 deployment readiness checks and prints a human-readable pass/fail summary

#### Scenario: JSON report option

- **WHEN** an operator runs `python scripts/flow_a_readiness.py --json`
- **THEN** the command emits a machine-readable JSON report including per-check status and overall result on stdout

### Requirement: Repository state verification

The readiness command SHALL verify repository state independently of the running worker.

#### Scenario: Repo HEAD equals origin/main and expected commits present

- **WHEN** the configured repo path is a git checkout, `git rev-parse HEAD` equals `git rev-parse origin/main`, and each configured expected commit (default: `79f5345`, `962ba2f`, `53708eb`) is an ancestor of HEAD
- **THEN** Phase 0 reports pass for repository state checks

#### Scenario: Required Flow A files exist in checkout

- **WHEN** Phase 0 runs against the configured repo path
- **THEN** it verifies the Flow A file manifest exists, including at minimum `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`, `content-strategy/silverman-editorial-system.md`, and the worker modules for publish, package generation, distribution scheduling, and ready-post validation

### Requirement: Running worker state verification

The readiness command SHALL verify the running worker HTTP surface independently of repository git state.

#### Scenario: Worker health healthy

- **WHEN** Phase 0 performs `GET {worker_base_url}/health`
- **THEN** it expects HTTP 200 and records worker reachability as pass; on non-200 or connection failure it records fail with remediation guidance

#### Scenario: OpenAPI exposes required Flow A endpoints

- **WHEN** Phase 0 performs `GET {worker_base_url}/openapi.json` and parses paths
- **THEN** it verifies presence of `/health`, `/process-ready`, `/publish-blog-post`, `/generate-linkedin-package`, and `/schedule-linkedin-distribution`
- **AND** if any required path is missing, Phase 0 fails with a message indicating the running worker may be stale relative to the repository

#### Scenario: Repo current but running worker stale

- **WHEN** repository state checks pass but OpenAPI does not expose all required Flow A endpoint paths
- **THEN** Phase 0 overall result is fail and the report states clearly that the checkout may be current while the running worker has not been redeployed or restarted

### Requirement: Flow A workflow export checks

The readiness command SHALL verify the Flow A n8n workflow export in the repository checkout without activating the workflow.

#### Scenario: Required workflow file present

- **WHEN** Phase 0 checks `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` in the configured repo path
- **THEN** a missing file causes Phase 0 to fail clearly

#### Scenario: Workflow export inactive

- **WHEN** Phase 0 parses the Flow A workflow JSON export
- **THEN** it requires top-level `"active": false`; if `"active": true`, Phase 0 fails clearly

### Requirement: n8n reachability and import status

The readiness command SHALL check n8n reachability when configured and SHALL distinguish code/readiness failures from pending operator import work.

#### Scenario: n8n container reachable

- **WHEN** `--n8n-base-url` (or equivalent configuration) is provided
- **THEN** Phase 0 or Phase 2 performs a non-destructive reachability probe and records pass or fail for n8n connectivity

#### Scenario: n8n reachable but workflow not imported

- **WHEN** n8n is reachable but the Flow A workflow cannot be confirmed as imported (no API credentials or inconclusive probe)
- **THEN** the report status is `pending_import` (or equivalent pending status), not a code failure, with manual import checklist guidance

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
- **THEN** the command verifies n8n reachability and workflow export inactivity and reports import/configuration pending items without activating the workflow

#### Scenario: Phase 3 full manual Flow A execution

- **WHEN** Phases 0–2 pass and the operator runs Phase 3 per documented procedure
- **THEN** documentation describes manual n8n manual-trigger execution of the Flow A workflow with `"active": false` import, without cron or webhook activation

#### Scenario: Phase 4 idempotent rerun verification

- **WHEN** Phase 3 has been executed successfully
- **THEN** documentation and checklist require a second manual run confirming idempotent worker responses and no duplicate blog or LinkedIn artifacts

### Requirement: Security and safety constraints

The readiness and smoke capability MUST NOT print secrets, perform destructive operations, call the LinkedIn API, or automatically deploy or restart services.

#### Scenario: No secrets printed

- **WHEN** the readiness command loads API keys or tokens from environment or env files
- **THEN** output reports only whether credentials are configured, never the secret values

#### Scenario: No LinkedIn API call

- **WHEN** any phase of the readiness or smoke command runs
- **THEN** it does not call LinkedIn publication APIs or implement slice 8 behavior

#### Scenario: Stale worker after deploy

- **WHEN** Phase 0 detects OpenAPI missing Flow A paths while repository checks pass
- **THEN** remediation references `deploy/server/deploy-worker.sh` and `deploy/server/verify-worker-deploy.sh`, notes that deploy must run on the Ubuntu server and recreate the container on port `8010`, and does not execute deploy automatically

#### Scenario: No automatic deploy or restart

- **WHEN** Phase 0 detects a stale worker
- **THEN** it may print remediation text referencing `deploy/server/deploy-worker.sh` but does not execute deploy, restart, or destructive filesystem operations

### Requirement: Expected failure clarity

The readiness report SHALL surface distinct failure modes with actionable messages.

#### Scenario: Wrong port or base URL

- **WHEN** the worker base URL is misconfigured
- **THEN** health or OpenAPI checks fail with connection or HTTP error context indicating wrong port or base URL

#### Scenario: API key mismatch in Phase 1

- **WHEN** Phase 1 performs an authenticated probe with a configured API key and receives HTTP 401
- **THEN** the report fails clearly indicating likely API key mismatch between worker and n8n configuration

#### Scenario: Worker unhealthy

- **WHEN** `GET /health` does not return HTTP 200
- **THEN** Phase 0 fails clearly before any smoke phase proceeds

### Requirement: Tests and documentation

The change SHALL include automated tests for readiness parsing and checking logic and operator documentation for phased smoke execution.

#### Scenario: Unit tests for parsers

- **WHEN** CI runs the test suite
- **THEN** tests cover OpenAPI required-path detection, workflow `active` flag parsing, commit presence logic, and JSON report structure without requiring a live Ubuntu server

#### Scenario: Operator documentation

- **WHEN** an operator reads README or `docs/deployment/` after apply
- **THEN** documentation explains Phase 0–4, default URLs, and that Phase 0 must pass before Flow A smoke execution

### Requirement: Apply scope boundaries

Archive, commit, and push SHALL be out of scope for the apply phase of this change unless explicitly requested in a separate operator action.

#### Scenario: No archive or commit in apply

- **WHEN** `/opsx-apply flow-a-deployment-readiness-and-smoke-test` completes implementation tasks
- **THEN** it does not archive the umbrella, does not activate the n8n workflow, and does not commit or push repository changes as part of the change tasks
