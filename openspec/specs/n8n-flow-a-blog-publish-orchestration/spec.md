# n8n-flow-a-blog-publish-orchestration

## Purpose

Importable n8n workflow JSON that orchestrates Flow A automatic blog-to-LinkedIn distribution over HTTP only — scanning ready posts, publishing via `POST /publish-blog-post`, generating multi-variant packages via `POST /generate-linkedin-package`, scheduling distribution via `POST /schedule-linkedin-distribution`, and completing ready-path lifecycle/calendar via `POST /complete-flow-a-ready-path` — with structured error branching, idempotent rerun support, Manual + Schedule Trigger entry points, single-flight concurrency guard, and inactive repository export. Live server activation is owned by capability `flow-a-n8n-workflow-activation`.

## Requirements

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

The exported Flow A workflow JSON MUST keep `"active": false` in the repository.

This change MUST NOT set `"active": true` in the repository export.

Live activation on the Ubuntu n8n instance is owned by capability `flow-a-n8n-workflow-activation` and MUST NOT be represented as `"active": true` in git.

#### Scenario: Exported workflow is not active

- **WHEN** the Flow A workflow JSON is parsed from the repository
- **THEN** the top-level `active` field is `false`

#### Scenario: Repository export does not encode production active state

- **WHEN** an operator compares repository export `active` with server RUNTIME-STATE after US-010 activation
- **THEN** documentation states repository remains `false` while server may be `true`

### Requirement: HTTP-only orchestration boundary

The Flow A workflow MUST orchestrate worker integration exclusively through n8n **HTTP Request** nodes (plus standard control nodes: Manual Trigger, Schedule Trigger, IF, Split Out, Set, Code for single-flight guard, No Operation).

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

The Flow A workflow SHALL include a Manual Trigger node for local and operator smoke execution.

A Schedule Trigger (daily 09:00 UTC) MAY also start the same shared path; Manual Trigger MUST remain available after US-010.

#### Scenario: Manual execution

- **WHEN** an operator clicks Execute Workflow in n8n with the Flow A workflow open
- **THEN** execution begins at Manual Trigger and proceeds to Set Configuration, single-flight guard, and worker health check without requiring the schedule clock

#### Scenario: Schedule and manual share downstream path

- **WHEN** either Manual Trigger or Schedule Trigger fires
- **THEN** execution enters the shared Set Configuration → single-flight → health → process-ready chain

### Requirement: Health check before processing

After Manual Trigger (or Schedule Trigger), **Set Configuration**, and the single-flight guard, the workflow SHALL call `GET /health` using an HTTP Request node.

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

After each authenticated worker step (`process-ready`, `publish-blog-post`, `generate-linkedin-package`, `schedule-linkedin-distribution`, `complete-flow-a-ready-path`), the workflow SHALL branch on response `status` using an IF node (or equivalent).

When `status` is `failed`, the workflow MUST follow a failure branch that exposes `errors[]` (and `warnings[]` when present) for operator visibility.

#### Scenario: Branch on publish status

- **WHEN** `POST /publish-blog-post` returns `status` `failed`
- **THEN** the workflow follows the publish failure branch and does not proceed to package generation

#### Scenario: Branch on schedule status

- **WHEN** `POST /schedule-linkedin-distribution` returns `status` `failed`
- **THEN** the workflow follows the schedule failure branch and exposes schedule `errors[]`

#### Scenario: Branch on ready-path completion status

- **WHEN** `POST /complete-flow-a-ready-path` returns `status` `failed`
- **THEN** the workflow follows the completion failure branch and exposes completion `errors[]`

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

The Flow A workflow MUST NOT move editorial source files using Execute Command, SSH, or filesystem nodes.

The Flow A workflow MUST invoke authenticated `POST /complete-flow-a-ready-path` after successful distribution scheduling so the **worker** can move sources to `blog-posts/processed/` per `flow-a-ready-path-completion` and `flow-a-source-lifecycle-completion`.

The workflow MUST NOT call worker endpoints that move sources to `blog-posts/error/` as part of the happy path.

#### Scenario: Worker lifecycle HTTP is invoked after schedule

- **WHEN** the Flow A workflow completes a successful schedule step for a candidate
- **THEN** it calls `POST /complete-flow-a-ready-path` so source Markdown is eligible to leave `blog-posts/ready/` via worker lifecycle completion

#### Scenario: Orchestration does not filesystem-move sources

- **WHEN** the Flow A workflow export is inspected
- **THEN** it does not contain Execute Command, SSH, or filesystem write nodes that move `blog-posts/` files

### Requirement: No modification to single-draft workflow

This change MUST NOT modify `n8n/workflows/silverman-blog-linkedin-draft-generation.json` or its lightweight validation expectations in `tests/test_n8n_workflow.py` except where README cross-links both workflows.

#### Scenario: Draft-generation workflow unchanged

- **WHEN** this child change is applied
- **THEN** the draft-generation workflow file and its dedicated tests remain valid without structural changes required by Flow A orchestration

### Requirement: Workflow documentation in README

The repository README SHALL document:

- path to the Flow A workflow JSON file
- distinction from draft-generation (review) workflow
- import and configuration steps (`worker_base_url`, `worker_api_key`, optional `site_url`, `topic_theme`, `start_at_utc`, `git_publication`, `live_site_confirmation`)
- node flow summary: health → process-ready → publish → package → schedule → complete-flow-a-ready-path
- explicit note that workflow does not call LinkedIn API and export remains inactive
- end-to-end smoke test steps on Ubuntu server

#### Scenario: Operator can configure Flow A from README

- **WHEN** a new operator follows README Flow A instructions
- **THEN** they can import the workflow, configure worker URL and API key, and run a manual execution against a healthy worker

### Requirement: Lightweight workflow validation

The repository MUST include lightweight automated validation that the Flow A workflow JSON exists, parses as JSON, contains expected node types and worker endpoint fragments (including `/publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`, and `/complete-flow-a-ready-path`), asserts `"active": false`, asserts exactly one Schedule Trigger with daily 09:00 UTC cron semantics, asserts Manual Trigger is present, asserts single-flight guard presence, asserts no forbidden orchestration nodes or obvious secrets, and asserts authenticated calls use Bearer expressions from `worker_api_key`.

Validation MUST NOT require a live n8n instance in CI.

#### Scenario: CI catches inactive export violation

- **WHEN** the Flow A workflow JSON has `"active": true`
- **THEN** the validation test fails

#### Scenario: CI catches missing publish endpoint

- **WHEN** the Flow A workflow JSON does not reference `/publish-blog-post`
- **THEN** the validation test fails

#### Scenario: CI catches missing ready-path completion endpoint

- **WHEN** the Flow A workflow JSON does not reference `/complete-flow-a-ready-path`
- **THEN** the validation test fails

#### Scenario: CI catches hardcoded production API key

- **WHEN** the Flow A workflow JSON contains a literal production Bearer token in an Authorization header
- **THEN** the validation test fails

#### Scenario: CI requires schedule trigger after US-010

- **WHEN** the Flow A workflow JSON lacks a Schedule Trigger configured for daily 09:00 UTC
- **THEN** the validation test fails

#### Scenario: CI requires manual trigger retained

- **WHEN** the Flow A workflow JSON lacks a Manual Trigger
- **THEN** the validation test fails

### Requirement: Publish opt-in for git publication and live-site confirmation

**Set Configuration** MUST include boolean fields `git_publication` and `live_site_confirmation` (default `false` in the repository export).

When either field is true after coercion, `POST /publish-blog-post` JSON body MUST include the corresponding boolean field(s).

When a field is false or absent, the publish body MUST omit that field or set it false so worker fail-closed defaults apply.

#### Scenario: Both opt-ins forwarded when configured true

- **WHEN** Set Configuration has `git_publication=true` and `live_site_confirmation=true`
- **THEN** `POST /publish-blog-post` includes both booleans as true alongside `source_relative_path`

#### Scenario: Export defaults keep opt-ins false

- **WHEN** the repository Flow A workflow export is inspected
- **THEN** Set Configuration defaults for `git_publication` and `live_site_confirmation` are false (or equivalent non-true) so import without server tuning does not request git/live side effects

### Requirement: Schedule success feeds ready-path completion

When `POST /schedule-linkedin-distribution` returns `status` `completed`, the workflow SHALL call authenticated `POST /complete-flow-a-ready-path` with `campaign_id` from the schedule (or package) response and `update_calendar` true unless Set Configuration explicitly disables calendar update.

The workflow MUST branch on completion response `status` using an IF node (or equivalent).

When completion returns `status` `failed`, the workflow MUST follow a failure branch exposing `errors[]`.

When completion returns `status` `completed` or `skipped`, the workflow MUST follow the success path to lock release.

When completion returns `status` `partial`, the workflow MUST treat the run as a non-silent degraded outcome visible to operators (failure branch or dedicated partial branch that does not claim unconditional full success).

#### Scenario: Completion called after successful schedule

- **WHEN** schedule returns `status` `completed` with `campaign_id`
- **THEN** `POST /complete-flow-a-ready-path` is invoked with that `campaign_id` before lock release

#### Scenario: Completion failure is visible

- **WHEN** `POST /complete-flow-a-ready-path` returns `status` `failed`
- **THEN** the workflow does not claim unconditional Flow A success and exposes completion `errors[]`

### Requirement: No LinkedIn publication endpoints on completion path

The ready-path completion HTTP step MUST NOT call `/queue-linkedin-publication`, `/publish-linkedin-due-variants`, or `/cancel-linkedin-publication`.

#### Scenario: Completion path has no LinkedIn publication URLs

- **WHEN** the Flow A workflow export is inspected
- **THEN** it does not add LinkedIn publication endpoint URLs for the post-schedule completion step

### Requirement: Canonical workflow identity documented in README

The repository README Flow A section SHALL document the canonical workflow identity table:

| Attribute | Value |
|-----------|-------|
| Export path | `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` |
| Workflow name | `Silverman Blog LinkedIn Flow A Publish` |
| Stable n8n id | `silvermanFlowAPublish01` |
| Node count | `35` (repository constant; ready-path completion nodes included) |
| Export active | `false` |
| Schedule | Daily 09:00 UTC (`0 9 * * *`) |
| Distinction from Flow B | `silverman-blog-linkedin-draft-generation.json` is draft review only |

#### Scenario: README identifies canonical Flow A workflow

- **WHEN** an operator reads README Flow A orchestration section
- **THEN** they find canonical path, stable id, schedule, export inactivity, and explicit note that Flow B draft workflow is not Flow A orchestration

### Requirement: Proposed execution frequency documented without activation

The repository README and deployment documentation SHALL document the Flow A n8n scheduled execution frequency as configured in the export:

- Daily at 09:00 UTC (Schedule Trigger cron `0 9 * * *`, timezone UTC).
- Editorial calendar remains the policy authority for due calendar items; n8n scheduling is the orchestration timer for the ready-folder Flow A path.
- Repository export remains `"active": false`; server activation is a separate operator step (US-010 activation capability).

#### Scenario: README labels frequency as configured schedule

- **WHEN** an operator reads execution frequency in documentation
- **THEN** text states daily 09:00 UTC is configured in the export Schedule Trigger and repository export remains inactive until server activation

#### Scenario: Export contains schedule trigger after US-010

- **WHEN** this change is applied under US-010 scope
- **THEN** `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` contains a Schedule Trigger node for daily 09:00 UTC

### Requirement: US-009 identification defers activation

Historical US-009 identification deferred production activation. Under US-010, deferral of schedule materialization is lifted, but the repository export MUST keep `"active": false`. Live server activation and concurrency/restart evidence SHALL be owned by capability `flow-a-n8n-workflow-activation` and MUST NOT be encoded as `"active": true` in the git export.

#### Scenario: US-010 keeps repository export inactive

- **WHEN** US-010 implementation completes
- **THEN** workflow export `active` field remains `false` in git while Schedule Trigger nodes are present

#### Scenario: Live activation is out of repository export

- **WHEN** US-010 implementation completes
- **THEN** turning the server workflow `active: true` is performed as an operational activation step, not by committing `"active": true` to the export

### Requirement: Schedule Trigger allowed for Flow A publish orchestration

The Flow A workflow export SHALL include a Schedule Trigger node (`n8n-nodes-base.scheduleTrigger` or equivalent) configured for daily 09:00 UTC (`0 9 * * *`, timezone UTC) in addition to Manual Trigger.

Cron, Webhook, and other Schedule/Cron variants beyond this single approved Schedule Trigger MUST NOT be added without a new OpenSpec change.

#### Scenario: Single approved schedule trigger present

- **WHEN** the Flow A workflow export is inspected after US-010
- **THEN** exactly one Schedule Trigger exists with daily 09:00 UTC configuration

### Requirement: Single-flight guard in orchestration graph

The Flow A workflow export SHALL include an orchestration-side single-flight guard on the shared path after Set Configuration and before Health Check so concurrent Manual and Schedule executions cannot overlap apply steps.

#### Scenario: Guard precedes health check

- **WHEN** the Flow A workflow graph is inspected
- **THEN** the single-flight guard executes before the Health Check HTTP Request node on the shared path

### Requirement: Publication enablement independent of Flow A schedule success

Flow A n8n orchestration success through Schedule Trigger or Manual Trigger (ready-folder path through publish → package → schedule) MUST NOT require `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` and MUST NOT call LinkedIn publication APIs.

Operators MUST treat LinkedIn API publication as a separately approved step governed by `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` and LinkedIn publication endpoints — documented under capability `flow-a-linkedin-publication-guard` for US-011 acceptance.

#### Scenario: Schedule success without LinkedIn publication enabled

- **WHEN** the Flow A workflow completes a clean empty-ready or schedule no-op while LinkedIn publication is disabled
- **THEN** orchestration stops successfully without calling LinkedIn publication endpoints

#### Scenario: Workflow does not depend on LinkedIn enablement flag

- **WHEN** the Flow A workflow export and worker HTTP chain are inspected for LinkedIn publication enablement coupling
- **THEN** no workflow step requires `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` to be `true` for publish/package/schedule success
