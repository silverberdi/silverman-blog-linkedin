## ADDED Requirements

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

## MODIFIED Requirements

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
