# flow-a-canonical-n8n-workflow-identification (delta)

## ADDED Requirements

### Requirement: Canonical Flow A workflow identity

The repository and operator documentation SHALL define exactly one canonical Flow A n8n workflow with the following identity:

| Attribute | Value |
|-----------|-------|
| Repository export path | `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` |
| Workflow display name | `Silverman Blog LinkedIn Flow A Publish` |
| Stable n8n workflow id | `silvermanFlowAPublish01` |
| Expected node count | `26` |
| Export active flag | `false` |

The Flow B draft-generation workflow at `n8n/workflows/silverman-blog-linkedin-draft-generation.json` MUST NOT be identified as the canonical Flow A orchestration workflow.

#### Scenario: Operator locates canonical export in repository

- **WHEN** an operator inspects repository workflow artifacts for Flow A automatic publishing
- **THEN** documentation directs them to `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` with stable id `silvermanFlowAPublish01`

#### Scenario: Flow B workflow is not canonical Flow A

- **WHEN** an operator compares Flow A and Flow B n8n workflows
- **THEN** documentation states that `silverman-blog-linkedin-draft-generation.json` is for human-review draft generation only and is not the Flow A publish orchestration workflow

### Requirement: Canonical workflow distinction from Flow B

Operator-facing identification output MUST list distinguishing characteristics:

- Flow A canonical workflow calls `POST /publish-blog-post`, `POST /generate-linkedin-package`, and `POST /schedule-linkedin-distribution`.
- Flow B draft workflow calls `POST /process-file` and `POST /generate-linkedin-draft` only.
- Only the Flow A canonical workflow uses stable id `silvermanFlowAPublish01`.

#### Scenario: Endpoint fragments distinguish workflows

- **WHEN** lightweight workflow validation or identification checks run against both workflow exports
- **THEN** Flow A export references `/publish-blog-post` and Flow B export does not

### Requirement: Import and configuration verification on Ubuntu server

The change SHALL use `deploy/server/import-flow-a-n8n-workflow.sh` as the primary server-side import and post-import verification entry point on Ubuntu host `192.168.0.194`.

After successful import verification, the script MUST confirm:

- Workflow exists by id `silvermanFlowAPublish01` or canonical name
- `active` is `false`
- Node count is `26`
- `worker_base_url` is set to the configured worker URL (default `http://192.168.0.194:8010`)
- `worker_api_key` is configured without printing the secret value

The script MUST NOT activate the workflow, add schedule triggers, call LinkedIn API, or invoke publish/package/schedule worker apply paths.

#### Scenario: Import script reports PASS for canonical workflow

- **WHEN** an operator runs `deploy/server/import-flow-a-n8n-workflow.sh` on the Ubuntu server with valid source JSON and worker env
- **THEN** output includes `OVERALL: PASS` with workflow id `silvermanFlowAPublish01`, `active: false`, and 26 nodes

#### Scenario: Import script does not print secrets

- **WHEN** import verification reports API key status
- **THEN** output shows `worker_api_key: configured` or equivalent without the key value

#### Scenario: Wrong n8n container rejected

- **WHEN** the import script runs on a host where only the nginx n8n gateway container is available
- **THEN** the script fails clearly and does not attempt import against the gateway container

### Requirement: Read-only evidence verification

`deploy/server/collect-flow-a-smoke-evidence.sh` and `scripts/flow_a_readiness.py` Phase 2 MUST verify canonical workflow identity via read-only means (n8n export or HTTP probe) without activating the workflow or mutating editorial state.

#### Scenario: Evidence script confirms inactive canonical workflow

- **WHEN** `collect-flow-a-smoke-evidence.sh` runs on the Ubuntu server and n8n is reachable
- **THEN** n8n export verification reports workflow id or name matching `silvermanFlowAPublish01`, `active: false`, and 26 nodes

#### Scenario: Readiness Phase 2 reports pending import

- **WHEN** n8n is reachable but canonical workflow cannot be confirmed imported
- **THEN** readiness reports `pending_import` (or equivalent) with remediation referencing `import-flow-a-n8n-workflow.sh`, not a code failure

### Requirement: Proposed execution frequency documentation

Operator documentation SHALL record a **proposed** Flow A n8n execution frequency for scheduled orchestration:

- **Proposed schedule:** daily at 09:00 UTC via Schedule Trigger (to be added in US-010 activation change).
- **Rationale:** predictable polling aligned with editorial calendar due-item processing; n8n triggers orchestration, editorial calendar remains policy authority.
- **Constraint:** repository export and server import MUST remain without Cron, Webhook, or Schedule Trigger nodes until US-010 explicitly activates scheduling.

#### Scenario: Frequency documented as proposal only

- **WHEN** an operator reads deployment documentation after this change
- **THEN** proposed execution frequency is labeled as not yet active and workflow export remains `"active": false` without schedule trigger nodes

#### Scenario: US-009 does not add schedule trigger

- **WHEN** this change is applied
- **THEN** `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` does not gain Cron, Webhook, or Schedule Trigger node types

### Requirement: Operator-visible pass fail pending outcomes

Identification verification MUST emit human-readable overall status with distinct failure modes and remediation guidance.

Supported overall states MUST include at minimum: `PASS`, `PENDING`, and `FAIL`.

Failure modes MUST distinguish at minimum:

- missing canonical export in repository
- workflow not imported (`PENDING`)
- wrong workflow id or name (`FAIL`)
- workflow unexpectedly active (`FAIL`)
- node count mismatch (`FAIL`)
- worker API key mismatch (`FAIL`)
- n8n unreachable (`FAIL`)
- running worker stale relative to repository OpenAPI (`FAIL`)

#### Scenario: Active workflow fails identification

- **WHEN** n8n export shows `silvermanFlowAPublish01` with `active: true`
- **THEN** identification reports `FAIL` with remediation to deactivate before US-010

#### Scenario: Missing import reports pending

- **WHEN** n8n is reachable but canonical workflow is not found
- **THEN** identification reports `PENDING` with remediation to run import script

### Requirement: No duplicate processing or unintended publication

US-009 identification and verification MUST NOT:

- activate the n8n workflow
- add schedule triggers to export or server workflow
- call LinkedIn publication APIs
- run `POST /publish-blog-post`, `POST /generate-linkedin-package`, or `POST /schedule-linkedin-distribution` apply paths as part of default identification checks
- move blog posts between editorial folders
- enable `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`

#### Scenario: Identification is read-only by default

- **WHEN** operator runs US-009 identification verification entry points
- **THEN** only health, OpenAPI, n8n export, and configuration presence checks run unless operator explicitly opts into separate smoke phases documented outside US-009

### Requirement: HTTP-only orchestration boundary preserved

Canonical Flow A workflow identification MUST reaffirm ADR-0001: n8n orchestrates worker integration exclusively via HTTP Request nodes. Identification checks MUST fail if forbidden node types are present in the canonical export.

#### Scenario: Forbidden nodes fail lightweight validation

- **WHEN** canonical workflow export contains Execute Command or LinkedIn API nodes
- **THEN** identification validation fails with clear message

### Requirement: Backlog traceability

Implementation tasks and operator documentation MUST map to backlog **BL-004** user story **US-009** acceptance criteria and MUST defer **US-010** (activation) and **US-011** (LinkedIn publication guard at activation) to follow-up changes.

#### Scenario: US-010 scope excluded

- **WHEN** this change is applied
- **THEN** no task activates the workflow or validates restart/recovery behavior (US-010 criteria)
