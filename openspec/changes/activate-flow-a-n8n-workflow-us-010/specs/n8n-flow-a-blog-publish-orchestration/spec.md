## MODIFIED Requirements

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

### Requirement: Manual trigger entry point

The Flow A workflow SHALL include a Manual Trigger node for local and operator smoke execution.

A Schedule Trigger (daily 09:00 UTC) MAY also start the same shared path; Manual Trigger MUST remain available after US-010.

#### Scenario: Manual execution

- **WHEN** an operator clicks Execute Workflow in n8n with the Flow A workflow open
- **THEN** execution begins at Manual Trigger and proceeds to Set Configuration, single-flight guard, and worker health check without requiring the schedule clock

#### Scenario: Schedule and manual share downstream path

- **WHEN** either Manual Trigger or Schedule Trigger fires
- **THEN** execution enters the shared Set Configuration → single-flight → health → process-ready chain

### Requirement: Canonical workflow identity documented in README

The repository README Flow A section SHALL document the canonical workflow identity table:

| Attribute | Value |
|-----------|-------|
| Export path | `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` |
| Workflow name | `Silverman Blog LinkedIn Flow A Publish` |
| Stable n8n id | `silvermanFlowAPublish01` |
| Node count | US-010 repository constant (baseline target 28) |
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

### Requirement: Lightweight workflow validation

The repository MUST include lightweight automated validation that the Flow A workflow JSON exists, parses as JSON, contains expected node types and worker endpoint fragments, asserts `"active": false`, asserts exactly one Schedule Trigger with daily 09:00 UTC cron semantics, asserts Manual Trigger is present, asserts single-flight guard presence, asserts no forbidden orchestration nodes or obvious secrets, and asserts authenticated calls use Bearer expressions from `worker_api_key`.

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

#### Scenario: CI requires schedule trigger after US-010

- **WHEN** the Flow A workflow JSON lacks a Schedule Trigger configured for daily 09:00 UTC
- **THEN** the validation test fails

#### Scenario: CI requires manual trigger retained

- **WHEN** the Flow A workflow JSON lacks a Manual Trigger
- **THEN** the validation test fails

### Requirement: US-009 identification defers activation

Historical US-009 identification deferred production activation. Under US-010, deferral of schedule materialization is lifted, but the repository export MUST keep `"active": false`. Live server activation and concurrency/restart evidence SHALL be owned by capability `flow-a-n8n-workflow-activation` and MUST NOT be encoded as `"active": true` in the git export.

#### Scenario: US-010 keeps repository export inactive

- **WHEN** US-010 implementation completes
- **THEN** workflow export `active` field remains `false` in git while Schedule Trigger nodes are present

#### Scenario: Live activation is out of repository export

- **WHEN** US-010 implementation completes
- **THEN** turning the server workflow `active: true` is performed as an operational activation step, not by committing `"active": true` to the export

## ADDED Requirements

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
