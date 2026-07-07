# n8n-flow-a-blog-publish-orchestration

## Purpose

Importable n8n workflow JSON that orchestrates Flow A automatic blog-to-LinkedIn distribution over HTTP only — scanning ready posts, publishing via `POST /publish-blog-post`, generating multi-variant packages via `POST /generate-linkedin-package`, and scheduling distribution via `POST /schedule-linkedin-distribution` — with structured error branching, idempotent rerun support, and inactive manual-trigger export. Implements child slice 7 under umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`.

## ADDED Requirements

### Requirement: Umbrella and dependency references

This child change SHALL implement Flow A n8n orchestration under active umbrella change `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 7).

Orchestration behavior MUST align with Flow A policy in canonical spec `editorial-canon` and artifact `content-strategy/silverman-editorial-system.md` (automatic path after validation; no human approval gate).

Orchestration MUST consume worker capabilities from canonical specs `ready-post-editorial-validation` (validation inside publish), `worker-blog-publishing-endpoint`, `linkedin-derivative-package-generation`, and `linkedin-distribution-scheduling-model` without modifying those contracts.

Campaign metadata and lifecycle semantics MUST follow canonical spec `flow-a-lifecycle`.

Flow B content and the legacy single-draft review workflow MUST NOT be conflated with this Flow A orchestration artifact.

#### Scenario: Child change cites umbrella and completed siblings

- **WHEN** this capability is documented or implemented
- **THEN** it references umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` and completed worker children for validation, blog publish, package generation, and distribution scheduling

#### Scenario: Flow B workflow remains separate

- **WHEN** this child change is applied
- **THEN** `n8n/workflows/silverman-blog-linkedin-draft-generation.json` is not modified and continues to serve single-draft human-review orchestration

### Requirement: Importable Flow A workflow artifact location

The repository SHALL include a dedicated importable n8n workflow export at `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`.

The JSON MUST be valid n8n workflow format suitable for import through the n8n UI.

The workflow name MUST clearly identify Flow A automatic publishing (distinct from draft-generation workflow naming).

#### Scenario: Flow A workflow file present for import

- **WHEN** an operator opens the n8n import workflow dialog
- **THEN** they can import `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` without manual reconstruction of Flow A publish → package → schedule nodes

#### Scenario: Workflow JSON is parseable

- **WHEN** the Flow A workflow JSON file is parsed as JSON
- **THEN** parsing succeeds and the document contains n8n workflow node definitions

### Requirement: Workflow export remains inactive

The exported Flow A workflow JSON MUST keep `"active": false`.

This change MUST NOT activate the workflow in the repository export.

This change MUST NOT add Cron, Webhook, or Schedule Trigger nodes for production polling.

#### Scenario: Exported workflow is not active

- **WHEN** the Flow A workflow JSON is parsed
- **THEN** the top-level `active` field is `false`

#### Scenario: No production scheduling trigger

- **WHEN** the Flow A workflow export is inspected
- **THEN** it does not contain Cron, Webhook, or Schedule Trigger node types

### Requirement: HTTP-only orchestration boundary

The Flow A workflow MUST orchestrate worker integration exclusively through n8n **HTTP Request** nodes (plus standard control nodes: Manual Trigger, IF, Split Out, Set, No Operation).

The workflow MUST NOT use Execute Command, SSH, Read/Write Binary File, local filesystem nodes, GitHub nodes, LinkedIn nodes, or direct LLM provider HTTP calls.

The workflow MUST NOT publish to LinkedIn via API.

The workflow MUST NOT perform git commit or git push against any repository.

The workflow MUST treat the worker as the only filesystem, validation, LLM, and publishing boundary.

#### Scenario: Flow A worker calls use HTTP Request nodes

- **WHEN** the workflow invokes `GET /health`, `POST /process-ready`, `POST /publish-blog-post`, `POST /generate-linkedin-package`, or `POST /schedule-linkedin-distribution`
- **THEN** each invocation is performed by an HTTP Request node targeting the configured worker base URL

#### Scenario: No LinkedIn API nodes

- **WHEN** the Flow A workflow export is inspected
- **THEN** it does not contain LinkedIn node types or HTTP Request nodes targeting LinkedIn API hosts

#### Scenario: No forbidden orchestration nodes

- **WHEN** the Flow A workflow export is inspected
- **THEN** it does not contain Execute Command, SSH, filesystem, GitHub, OpenAI, or direct DeepSeek provider nodes

### Requirement: Configurable worker base URL and API key without hardcoded secrets

The workflow MUST make the worker base URL configurable from a single **Set Configuration** node (or equivalent documented pattern).

The workflow JSON MUST NOT contain real API keys, Bearer tokens, or other production secrets.

Worker API authentication for `POST /process-ready`, `POST /publish-blog-post`, `POST /generate-linkedin-package`, and `POST /schedule-linkedin-distribution` MUST use a placeholder `worker_api_key` in **Set Configuration** (for example `CHANGE_ME_WORKER_API_KEY`) and Bearer header expressions referencing that field — not literal production tokens in the exported JSON.

#### Scenario: API key is configuration not hardcoded secret

- **WHEN** the Flow A workflow JSON is reviewed in git
- **THEN** authenticated HTTP nodes reference `worker_api_key` from **Set Configuration** via expression and do not embed literal production Bearer tokens

#### Scenario: Exported JSON has placeholder API key

- **WHEN** the Flow A workflow JSON is reviewed before operator post-import configuration
- **THEN** **Set Configuration** includes `worker_api_key` with a non-production placeholder safe for version control

### Requirement: Manual trigger entry point

The Flow A workflow SHALL start with a Manual Trigger node for local and operator smoke execution.

#### Scenario: Manual execution

- **WHEN** an operator clicks Execute Workflow in n8n with the Flow A workflow open
- **THEN** execution begins at Manual Trigger and proceeds to worker health check without requiring cron or webhook

### Requirement: Health check before processing

After Manual Trigger and **Set Configuration**, the workflow SHALL call `GET /health` using an HTTP Request node.

The workflow MUST fail fast when health response indicates worker or editorial layout is not ready.

#### Scenario: Health check precedes process-ready

- **WHEN** the Flow A workflow runs from Manual Trigger
- **THEN** `GET /health` is invoked before `POST /process-ready`

### Requirement: Ready-folder scan via process-ready

The workflow SHALL call authenticated `POST /process-ready` after a successful health check.

When `POST /process-ready` returns `status` `failed`, the workflow MUST stop without calling publish, package, or schedule endpoints.

When `POST /process-ready` completes with `valid_count` 0, the workflow MUST stop cleanly without error attributable to missing files.

#### Scenario: Process-ready supplies candidate paths

- **WHEN** `POST /process-ready` returns `valid_files` with entries containing `relative_path`
- **THEN** the workflow iterates those candidates for per-item publish steps

#### Scenario: No candidates clean stop

- **WHEN** `POST /process-ready` returns `status` `completed` with `valid_count` 0
- **THEN** the workflow does not call `POST /publish-blog-post` and ends without failure state attributable to an empty ready folder

### Requirement: Ready post path passed to blog publish endpoint

For each candidate from `valid_files`, the workflow SHALL call authenticated `POST /publish-blog-post` with JSON body containing `source_relative_path` set to the candidate `relative_path`.

The workflow MUST NOT call `POST /generate-linkedin-package` or `POST /schedule-linkedin-distribution` when `POST /publish-blog-post` returns `status` `failed`.

#### Scenario: Publish receives ready relative path

- **WHEN** a candidate has `relative_path` `blog-posts/ready/01-why-i-did-not-start-with-the-database.md`
- **THEN** `POST /publish-blog-post` is called with that exact `source_relative_path` in the JSON body

#### Scenario: Publish failure stops downstream chain

- **WHEN** `POST /publish-blog-post` returns `status` `failed` for a candidate
- **THEN** the workflow does not call package or schedule endpoints for that candidate and exposes `errors[]` from the response

#### Scenario: Validation failure surfaces on publish step

- **WHEN** editorial validation fails inside publish flow
- **THEN** the workflow exposes publish `errors[]` (including validation failure codes) on the publish failure branch without a separate validation HTTP call

### Requirement: Blog publish completed response feeds package generation

When `POST /publish-blog-post` returns `status` `completed`, the workflow SHALL call authenticated `POST /generate-linkedin-package` for the same campaign.

The package request MUST prefer `campaign_id` from the publish response; when absent, it MUST use `source_relative_path` from the publish response.

Optional `topic_theme` and `site_url` from **Set Configuration** MUST be included only when non-empty after trimming.

The workflow MUST NOT call `POST /schedule-linkedin-distribution` when package generation returns `status` `failed`.

#### Scenario: Package generation uses publish campaign_id

- **WHEN** publish returns `status` `completed` with `campaign_id` `flow-a-2026-07-06-why-i-did-not-start-with-the-database`
- **THEN** `POST /generate-linkedin-package` is called with that `campaign_id` in the JSON body

#### Scenario: Package failure stops schedule step

- **WHEN** `POST /generate-linkedin-package` returns `status` `failed`
- **THEN** the workflow does not call `POST /schedule-linkedin-distribution` and exposes package `errors[]`

### Requirement: Package generation completed response feeds distribution scheduling

When `POST /generate-linkedin-package` returns `status` `completed`, the workflow SHALL call authenticated `POST /schedule-linkedin-distribution`.

The schedule request MUST prefer `campaign_id` from the package response.

Optional `strategy` and `start_at_utc` from **Set Configuration** MUST be included only when non-empty after trimming.

#### Scenario: Schedule uses package campaign_id

- **WHEN** package generation returns `status` `completed` with `campaign_id`
- **THEN** `POST /schedule-linkedin-distribution` is called with that `campaign_id`

#### Scenario: Schedule success exposes pending publish state

- **WHEN** `POST /schedule-linkedin-distribution` returns `status` `completed`
- **THEN** the workflow success branch exposes `variant_schedules[]` with `publish_state` `pending` and does not call LinkedIn API

### Requirement: Worker failure response branches to error path

After each authenticated worker step (`process-ready`, `publish-blog-post`, `generate-linkedin-package`, `schedule-linkedin-distribution`), the workflow SHALL branch on response `status` using an IF node (or equivalent).

When `status` is `failed`, the workflow MUST follow a failure branch that exposes `errors[]` (and `warnings[]` when present) for operator visibility.

#### Scenario: Branch on publish status

- **WHEN** `POST /publish-blog-post` returns `status` `failed`
- **THEN** the workflow follows the publish failure branch and does not proceed to package generation

#### Scenario: Branch on schedule status

- **WHEN** `POST /schedule-linkedin-distribution` returns `status` `failed`
- **THEN** the workflow follows the schedule failure branch and exposes schedule `errors[]`

### Requirement: Idempotent rerun allowed

The workflow MUST treat worker `status` `completed` responses from idempotent re-runs as success and continue or complete the chain appropriately.

Re-running the workflow against the same ready post MUST NOT require n8n-side deduplication beyond worker response branching.

#### Scenario: Already published proceeds to package

- **WHEN** `POST /publish-blog-post` returns `status` `completed` with `blog_publish.status` `already_published`
- **THEN** the workflow follows the publish success branch and may call package generation

#### Scenario: Idempotent schedule returns completed

- **WHEN** `POST /schedule-linkedin-distribution` returns `status` `completed` on a repeat run with matching schedule idempotency proof
- **THEN** the workflow follows the schedule success branch without requiring operator intervention

### Requirement: No source blog file moves from orchestration

The Flow A workflow MUST NOT invoke worker endpoints or n8n actions that move source blog posts to `blog-posts/processed/` or `blog-posts/error/`.

#### Scenario: Source remains in ready after Flow A run

- **WHEN** the Flow A workflow completes processing all candidates
- **THEN** source blog Markdown files remain in `blog-posts/ready/` unchanged by this workflow

### Requirement: No modification to single-draft workflow

This change MUST NOT modify `n8n/workflows/silverman-blog-linkedin-draft-generation.json` or its lightweight validation expectations in `tests/test_n8n_workflow.py` except where README cross-links both workflows.

#### Scenario: Draft-generation workflow unchanged

- **WHEN** this child change is applied
- **THEN** the draft-generation workflow file and its dedicated tests remain valid without structural changes required by Flow A orchestration

### Requirement: Workflow documentation in README

The repository README SHALL document:

- path to the Flow A workflow JSON file
- distinction from draft-generation (review) workflow
- import and configuration steps (`worker_base_url`, `worker_api_key`, optional `site_url`, `topic_theme`, `start_at_utc`)
- node flow summary: health → process-ready → publish → package → schedule
- explicit note that workflow does not call LinkedIn API and export remains inactive
- end-to-end smoke test steps on Ubuntu server

#### Scenario: Operator can configure Flow A from README

- **WHEN** a new operator follows README Flow A instructions
- **THEN** they can import the workflow, configure worker URL and API key, and run a manual execution against a healthy worker

### Requirement: Lightweight workflow validation

The repository MUST include lightweight automated validation that the Flow A workflow JSON exists, parses as JSON, contains expected node types and worker endpoint fragments, asserts `"active": false`, asserts no forbidden nodes or obvious secrets, and asserts authenticated calls use Bearer expressions from `worker_api_key`.

Validation MUST NOT require a live n8n instance in CI.

#### Scenario: CI catches inactive export violation

- **WHEN** the Flow A workflow JSON has `"active": true`
- **THEN** the validation test fails

#### Scenario: CI catches missing publish endpoint

- **WHEN** the Flow A workflow JSON does not reference `/publish-blog-post`
- **THEN** the validation test fails

#### Scenario: CI catches hardcoded production API key

- **WHEN** the Flow A workflow JSON contains a literal production Bearer token in an Authorization header
- **THEN** the validation test fails
