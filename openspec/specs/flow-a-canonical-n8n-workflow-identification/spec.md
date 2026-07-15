# flow-a-canonical-n8n-workflow-identification

## Purpose

Operator-facing identification of the single canonical Flow A n8n workflow: repository export path, stable n8n id, import/configuration verification on the Ubuntu server, materialized daily Schedule Trigger (export remains inactive), and pass/fail/pending remediation — without calling LinkedIn publication APIs. Live server activation is owned by capability `flow-a-n8n-workflow-activation` (US-010); US-011 LinkedIn publication enablement remains deferred.

## Requirements

### Requirement: Canonical Flow A workflow identity

The repository and operator documentation SHALL define exactly one canonical Flow A n8n workflow with the following identity:

| Attribute | Value |
|-----------|-------|
| Repository export path | `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` |
| Workflow display name | `Silverman Blog LinkedIn Flow A Publish` |
| Stable n8n workflow id | `silvermanFlowAPublish01` |
| Expected node count | Repository constant after US-010 edits (baseline target `28` = prior `26` + Schedule Trigger + single-flight guard; exact value MUST match scripts/tests) |
| Export active flag | `false` (repository export only) |
| Live server active flag | `true` after US-010 activation (RUNTIME-STATE authority) |
| Schedule | Daily `0 9 * * *` UTC via Schedule Trigger in export |

The Flow B draft-generation workflow at `n8n/workflows/silverman-blog-linkedin-draft-generation.json` MUST NOT be identified as the canonical Flow A orchestration workflow.

#### Scenario: Operator locates canonical export in repository

- **WHEN** an operator inspects repository workflow artifacts for Flow A automatic publishing
- **THEN** documentation directs them to `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` with stable id `silvermanFlowAPublish01`

#### Scenario: Flow B workflow is not canonical Flow A

- **WHEN** an operator compares Flow A and Flow B n8n workflows
- **THEN** documentation states that `silverman-blog-linkedin-draft-generation.json` is for human-review draft generation only and is not the Flow A publish orchestration workflow

#### Scenario: Identity table records schedule and export inactivity

- **WHEN** an operator reads the canonical identity table after US-010
- **THEN** it lists Schedule Trigger daily 09:00 UTC, repository export `active: false`, and expected node count matching the repository constant

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

After successful import verification (pre-activation), the script MUST confirm:

- Workflow exists by stable id `silvermanFlowAPublish01` (lookup MUST NOT succeed on display name alone)
- Display name matches **Silverman Blog LinkedIn Flow A Publish** as a secondary assert after id resolution
- `active` is `false` immediately after import
- Node count matches the US-010 repository constant
- Exactly one Schedule Trigger is present with cron `0 9 * * *` UTC semantics
- Single-flight guard node(s) are present when required by the export
- `worker_base_url` is set to the configured worker URL (default `http://192.168.0.194:8010`)
- `worker_api_key` is configured without printing the secret value

The import script MUST NOT activate the workflow by default, MUST NOT call LinkedIn API, and MUST NOT invoke publish/package/schedule worker apply paths. Activation remains a separate US-010 step.

#### Scenario: Import script reports PASS for canonical workflow pre-activation

- **WHEN** an operator runs `deploy/server/import-flow-a-n8n-workflow.sh` on the Ubuntu server with valid source JSON and worker env
- **THEN** output includes `OVERALL: PASS` with workflow id `silvermanFlowAPublish01`, `active: false`, expected node count, and Schedule Trigger present

#### Scenario: Import script rejects name-only match

- **WHEN** post-import `export:workflow` contains a workflow with the canonical display name but id is not `silvermanFlowAPublish01` and no workflow with that stable id exists
- **THEN** import verification reports `FAIL` with remediation to re-run the import script

#### Scenario: Import script does not print secrets

- **WHEN** import verification reports API key status
- **THEN** output shows `worker_api_key: configured` or equivalent without the key value

#### Scenario: Wrong n8n container rejected

- **WHEN** the import script runs on a host where only the nginx n8n gateway container is available
- **THEN** the script fails clearly and does not attempt import against the gateway container

### Requirement: Read-only evidence verification

`deploy/server/collect-flow-a-smoke-evidence.sh` and `scripts/flow_a_readiness.py` Phase 2 MUST verify canonical workflow identity via read-only means (n8n export or HTTP probe) without mutating editorial state by default.

Evidence and readiness MUST distinguish:

- **Repository / pre-activation:** export `active: false`, Schedule Trigger required
- **Server post-activation mode:** when explicitly requested (`--expect-server-active` or dedicated activation verifier), `active: true` is PASS; when expecting inactive, `active: true` is FAIL

Scripts MUST NOT call LinkedIn publication APIs as part of identity verification.

#### Scenario: Evidence script confirms canonical workflow with schedule

- **WHEN** `collect-flow-a-smoke-evidence.sh` runs on the Ubuntu server and n8n is reachable
- **THEN** n8n export verification reports workflow id `silvermanFlowAPublish01`, expected name, expected node count, and Schedule Trigger present

#### Scenario: Readiness Phase 2 reports pending import

- **WHEN** n8n is reachable but canonical workflow cannot be confirmed imported (no `--n8n-workflow-export` or export missing id)
- **THEN** readiness reports `pending_import` (or equivalent) with remediation referencing `import-flow-a-n8n-workflow.sh`, not a code failure

#### Scenario: Readiness Phase 2 passes when export confirms identity including schedule

- **WHEN** Phase 2 is given a read-only n8n workflow export containing id `silvermanFlowAPublish01` with expected name, node count, Schedule Trigger, and repository-style `active: false`
- **THEN** readiness reports PASS for n8n configuration identity confirmation

#### Scenario: Post-activation evidence expects active true

- **WHEN** an operator runs activation evidence mode expecting server-active and export shows `silvermanFlowAPublish01` with `active: true`
- **THEN** activation evidence reports PASS for active state

### Requirement: Proposed execution frequency documentation

Operator documentation SHALL record the Flow A n8n execution frequency for scheduled orchestration as **materialized** after US-010:

- **Schedule:** daily at 09:00 UTC via Schedule Trigger (`0 9 * * *`, timezone UTC) present in the repository export.
- **Rationale:** predictable polling aligned with editorial calendar due-item processing; n8n triggers orchestration, editorial calendar remains policy authority via its own connector.
- **Constraint:** repository export MUST keep `"active": false`; live server MAY be `"active": true` after explicit activation.

#### Scenario: Frequency documented as active schedule definition

- **WHEN** an operator reads deployment documentation after US-010
- **THEN** daily 09:00 UTC is documented as the Schedule Trigger configuration in the export, with repository export remaining inactive until server activation

#### Scenario: US-010 adds schedule trigger to export

- **WHEN** this change is applied
- **THEN** `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` contains a Schedule Trigger node for daily 09:00 UTC

### Requirement: Operator-visible pass fail pending outcomes

Identification and activation-adjacent verification MUST emit human-readable overall status with distinct failure modes and remediation guidance.

Supported overall states MUST include at minimum: `PASS`, `PENDING`, and `FAIL`.

Failure modes MUST distinguish at minimum:

- missing canonical export in repository
- workflow not imported (`PENDING`)
- wrong workflow id (`FAIL`) — including name-only match without id `silvermanFlowAPublish01`
- wrong display name after id resolution (`FAIL`)
- repository export unexpectedly active (`FAIL`)
- missing or incorrect Schedule Trigger (`FAIL`)
- node count mismatch (`FAIL`)
- worker API key mismatch (`FAIL`)
- n8n unreachable (`FAIL`)
- running worker stale relative to repository OpenAPI (`FAIL`)

#### Scenario: Active repository export fails identity

- **WHEN** repository export shows `silvermanFlowAPublish01` with `active: true`
- **THEN** identification reports `FAIL` with remediation to keep export inactive and activate only on server

#### Scenario: Name-only match without canonical id fails

- **WHEN** n8n export shows the canonical display name but no workflow with id `silvermanFlowAPublish01`
- **THEN** identification reports `FAIL` (not PASS) with remediation to re-run import script

#### Scenario: Missing import reports pending

- **WHEN** n8n is reachable but canonical workflow is not found
- **THEN** identification reports `PENDING` with remediation to run import script

#### Scenario: Missing schedule trigger fails after US-010

- **WHEN** canonical export or server export lacks the required Schedule Trigger
- **THEN** identification reports `FAIL` with remediation to update and re-import the US-010 export

### Requirement: No duplicate processing or unintended publication

US-010 identification/import verification (pre-activation) MUST NOT:

- activate the n8n workflow as part of default import verification
- call LinkedIn publication APIs
- run `POST /publish-blog-post`, `POST /generate-linkedin-package`, or `POST /schedule-linkedin-distribution` apply paths as part of default identification checks
- move blog posts between editorial folders as part of identification checks
- enable or flip `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`

Controlled activation and Manual/Schedule executions used for concurrency/restart evidence are documented under the `flow-a-n8n-workflow-activation` capability and MUST prefer empty-ready/no-op paths.

#### Scenario: Identification remains non-mutating by default

- **WHEN** operator runs import or identity verification entry points without activation evidence mode
- **THEN** only health, OpenAPI, n8n export, and configuration presence checks run unless the operator explicitly opts into separate smoke or evidence phases

### Requirement: HTTP-only orchestration boundary preserved

Canonical Flow A workflow identification MUST reaffirm ADR-0001: n8n orchestrates worker integration exclusively via HTTP Request nodes. Identification checks MUST fail if forbidden node types are present in the canonical export.

#### Scenario: Forbidden nodes fail lightweight validation

- **WHEN** canonical workflow export contains Execute Command or LinkedIn API nodes
- **THEN** identification validation fails with clear message

### Requirement: Backlog traceability

Implementation tasks and operator documentation MUST map to backlog **BL-004** user story **US-010** acceptance criteria and MUST defer **US-011** (LinkedIn publication guard at activation) and **BL-005** (fully unattended Flow A) to follow-up work.

#### Scenario: US-011 scope excluded

- **WHEN** this change is applied
- **THEN** no task closes US-011 or requires flipping LinkedIn publication enablement for US-010 acceptance
