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
- **THEN** the report status is `pending_import` (or equivalent pending status), not a code failure, with manual import checklist guidance referencing `deploy/server/import-flow-a-n8n-workflow.sh`

#### Scenario: Manual import script satisfies pending evidence

- **WHEN** an operator runs `deploy/server/import-flow-a-n8n-workflow.sh` on the Ubuntu server and the script reports `OVERALL: PASS` with workflow id `silvermanFlowAPublish01`, `active: false`, and 26 nodes
- **THEN** manual import verification evidence is satisfied even if Phase 0 `n8n_workflow_import` remains pending from HTTP-only probes

### Requirement: Repeatable n8n Flow A import on Ubuntu server

The repository SHALL provide `deploy/server/import-flow-a-n8n-workflow.sh` that imports the Flow A workflow into the real n8n container (not the nginx gateway), prepares a stable workflow id for Postgres import, configures worker URL and API key without printing secrets, and verifies the imported workflow remains inactive.

#### Scenario: Select n8n container by image

- **WHEN** the import script runs on a host with `local-ai-stack` n8n and nginx gateway containers
- **THEN** it selects a running container whose image matches `n8nio/n8n` or `docker.n8n.io/n8nio/n8n` and does not use the nginx gateway container for `n8n import:workflow`

#### Scenario: Stable workflow id required

- **WHEN** the source workflow JSON lacks a top-level `id` or has null import-breaking metadata fields
- **THEN** the script prepares import JSON with stable id `silvermanFlowAPublish01`, removes null `createdAt`, `updatedAt`, and `versionId` when present, and sets `active: false`

#### Scenario: Import verification without activation

- **WHEN** import completes successfully
- **THEN** the script verifies via `export:workflow` that the workflow exists by id or name, has 26 nodes, and `active` is false, without activating the workflow or adding cron/webhook triggers

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

### Requirement: Post-smoke evidence collection script

The repository SHALL provide a repeatable server-side script at `deploy/server/collect-flow-a-smoke-evidence.sh` that collects read-only Flow A post-smoke evidence on the Ubuntu server without ad-hoc SSH heredoc commands.

#### Scenario: Evidence script resolves editorial base path

- **WHEN** an operator runs the evidence script on the Ubuntu server without `BASE_PATH` set
- **THEN** the script resolves the editorial root from container env `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`, Docker mounts, `GET /health`, or known host candidates
- **AND** prints how the base path was resolved
- **AND** if unresolved, reports `OVERALL: FAIL` with remediation guidance and no stack trace

#### Scenario: Evidence script collects worker, file, and n8n checks

- **WHEN** the evidence script runs successfully against a deployed environment
- **THEN** it verifies worker `GET /health` and `GET /openapi.json` include Flow A paths `/publish-blog-post`, `/generate-linkedin-package`, and `/schedule-linkedin-distribution`
- **AND** reports latest metadata and generated LinkedIn artifacts under the resolved base path
- **AND** exports n8n workflows from the real n8n container and confirms workflow id or name match with `active: false` and 26 nodes

#### Scenario: Evidence script safety constraints

- **WHEN** the evidence script runs
- **THEN** it does not print API keys or secret env values, does not activate the n8n workflow, does not call the LinkedIn API, and does not deploy or restart services

#### Scenario: Evidence script overall status

- **WHEN** worker, public blog repo, and n8n checks pass and campaign metadata or generated LinkedIn artifacts exist
- **THEN** the script reports `OVERALL: PASS`
- **WHEN** worker, public blog repo, and n8n checks pass but smoke artifacts are not found yet
- **THEN** the script reports `OVERALL: PENDING`
- **WHEN** base path is unresolved, Flow A OpenAPI paths are missing, public blog repo is not mounted or incomplete, the workflow is active, or n8n is missing
- **THEN** the script reports `OVERALL: FAIL`
- **WHEN** worker and n8n checks pass but public blog repo is missing or incomplete
- **THEN** the script reports `OVERALL: FAIL` with remediation (not `PENDING`) because publish would fail with `blog_publish_public_repo_not_configured`

### Requirement: Public blog repo deployment readiness

The worker deployment artifacts SHALL mount and configure the public GitHub Pages repository checkout required for Flow A `POST /publish-blog-post`.

#### Scenario: Compose mounts public blog repo at /public-blog

- **WHEN** an operator inspects `deploy/server/silverman-worker.compose.yaml`
- **THEN** it sets `SILVERMAN_GITHUB_PAGES_REPO_PATH=/public-blog`, `SILVERMAN_SITE_URL` (default `https://silverman.pro`), and mounts `${SILVERMAN_PUBLIC_BLOG_REPO_PATH:-/home/silverman/silverberdi.github.io}:/public-blog` alongside the existing editorial mount

#### Scenario: Deploy script verifies public repo checkout before compose up

- **WHEN** `deploy-worker.sh` runs on the Ubuntu server before `docker compose up`
- **THEN** it verifies the configured host path exists and contains `_posts/` and `assets/images/`
- **AND** prints remediation to clone or sync the GitHub Pages repo manually
- **AND** does not clone the repo automatically
- **WHEN** `SKIP_PUBLIC_BLOG_REPO_CHECK=1` is set
- **THEN** the deploy script skips the public repo check for non-publishing deploys

#### Scenario: Post-deploy verification checks public repo inside container

- **WHEN** `verify-worker-deploy.sh` runs after deploy
- **THEN** it confirms container env `SILVERMAN_GITHUB_PAGES_REPO_PATH=/public-blog` and paths `/public-blog/_posts` and `/public-blog/assets/images` exist inside the worker container

#### Scenario: blog_publish_public_repo_not_configured indicates worker config not n8n failure

- **WHEN** Flow A publish validation passes but apply fails with `blog_publish_public_repo_not_configured`
- **THEN** operator documentation explains the public blog repo is not mounted or configured in the worker container, not that n8n orchestration failed

### Requirement: Apply scope boundaries

Archive, commit, and push SHALL be out of scope for the apply phase of this change unless explicitly requested in a separate operator action.

#### Scenario: No archive or commit in apply

- **WHEN** `/opsx-apply flow-a-deployment-readiness-and-smoke-test` completes implementation tasks
- **THEN** it does not archive the umbrella, does not activate the n8n workflow, and does not commit or push repository changes as part of the change tasks
