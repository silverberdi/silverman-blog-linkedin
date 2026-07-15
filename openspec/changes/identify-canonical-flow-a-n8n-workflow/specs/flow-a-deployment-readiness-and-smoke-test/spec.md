# flow-a-deployment-readiness-and-smoke-test (delta)

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

When workflow id or name does not match canonical values, the script MUST report `FAIL` with remediation to re-run import script.

#### Scenario: Evidence collector prints identity summary

- **WHEN** evidence collection runs and n8n export succeeds
- **THEN** output includes canonical id `silvermanFlowAPublish01`, node count, and `active: false` in a dedicated identity section

#### Scenario: Wrong workflow id fails evidence collection

- **WHEN** n8n export shows a workflow matching name but wrong id and no `silvermanFlowAPublish01` present
- **THEN** evidence collection reports `FAIL` with remediation to re-import canonical export

### Requirement: Import script canonical identity assertion in output

`deploy/server/import-flow-a-n8n-workflow.sh` SHALL print explicit canonical identity fields in verification output (path, id, name, node count, active state, worker_base_url, worker_api_key configured flag) to satisfy US-009 operator visibility.

#### Scenario: Import verification prints identity block

- **WHEN** import completes successfully
- **THEN** output includes a canonical identity summary with id `silvermanFlowAPublish01`, 26 nodes, and `active: false`
