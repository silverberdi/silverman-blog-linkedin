# flow-a-deployment-readiness-and-smoke-test (delta)

## MODIFIED Requirements

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
- **THEN** the script verifies via `export:workflow` that the workflow exists by stable id `silvermanFlowAPublish01` (name is a secondary assert only; name-only match without that id MUST FAIL), has 26 nodes, and `active` is false, without activating the workflow or adding cron/webhook triggers

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
- **AND** reports latest metadata and generated LinkedIn artifacts under the resolved editorial base path
- **AND** reports published `_posts` and `assets/images` matches for the slug fragment under the public GitHub Pages repo host mount (or inside the container at `/public-blog` when the host mount cannot be resolved), not under the editorial base path
- **AND** exports n8n workflows from the real n8n container and confirms workflow id `silvermanFlowAPublish01` with expected name, `active: false`, and 26 nodes (name-only match without that stable id MUST FAIL)

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

## ADDED Requirements

### Requirement: Canonical Flow A workflow identity constants in readiness tooling

`scripts/flow_a_readiness.py` SHALL define documented canonical Flow A n8n workflow identity constants matching:

- export path `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`
- stable id `silvermanFlowAPublish01`
- display name `Silverman Blog LinkedIn Flow A Publish`
- expected node count `26`

Phase 0 and Phase 2 checks MUST use these constants when reporting workflow export and import status.

#### Scenario: Readiness reports canonical path on export check

- **WHEN** Phase 0 verifies the Flow A workflow export in the repository checkout
- **THEN** the report references `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` and stable id `silvermanFlowAPublish01`

#### Scenario: Phase 2 references canonical id in remediation

- **WHEN** Phase 2 reports `pending_import` for n8n workflow import
- **THEN** remediation text references `deploy/server/import-flow-a-n8n-workflow.sh` and expected id `silvermanFlowAPublish01`

### Requirement: Canonical identity section in evidence collector output

`deploy/server/collect-flow-a-smoke-evidence.sh` SHALL print a labeled canonical workflow identity summary including workflow id, name, node count, and `active` state before overall status.

When workflow id does not match the canonical id `silvermanFlowAPublish01`, the script MUST report `FAIL` with remediation to re-run import script (name-only matches MUST NOT succeed).

#### Scenario: Evidence collector prints identity summary

- **WHEN** evidence collection runs and n8n export succeeds
- **THEN** output includes canonical id `silvermanFlowAPublish01`, node count, and `active: false` in a dedicated identity section

#### Scenario: Wrong workflow id fails evidence collection

- **WHEN** n8n export shows a workflow matching name but wrong id and no `silvermanFlowAPublish01` present
- **THEN** evidence collection reports `FAIL` with remediation to re-import canonical export

### Requirement: Import script canonical identity assertion in output

`deploy/server/import-flow-a-n8n-workflow.sh` SHALL print explicit canonical identity fields in verification output (path, id, name, node count, active state, worker_base_url, worker_api_key configured flag) to satisfy US-009 operator visibility. Post-import verification MUST resolve the workflow by stable id (name is a secondary assert only).

#### Scenario: Import verification prints identity block

- **WHEN** import completes successfully
- **THEN** output includes a canonical identity summary with id `silvermanFlowAPublish01`, 26 nodes, and `active: false`

### Requirement: Phase 2 can confirm imported identity via read-only export

`scripts/flow_a_readiness.py` Phase 2 SHALL:

- FAIL when `--n8n-base-url` is set and n8n is unreachable
- PENDING (`pending_import` / confirmation needed) when n8n is reachable but `--n8n-workflow-export` is not provided
- PASS when `--n8n-workflow-export` is provided and the export contains workflow id `silvermanFlowAPublish01` with expected name, `active: false`, and 26 nodes
- FAIL when the export is provided but id/name/active/node count mismatches canonical identity

#### Scenario: Phase 2 pending without export confirmation

- **WHEN** Phase 2 runs with n8n reachable and no `--n8n-workflow-export`
- **THEN** readiness reports PENDING with remediation referencing `import-flow-a-n8n-workflow.sh` and expected id `silvermanFlowAPublish01`

#### Scenario: Phase 2 passes with confirmed export

- **WHEN** Phase 2 runs with n8n reachable and `--n8n-workflow-export` containing id `silvermanFlowAPublish01`, expected name, `active: false`, and 26 nodes
- **THEN** readiness reports PASS for n8n configuration identity confirmation
