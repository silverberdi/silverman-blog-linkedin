## ADDED Requirements

### Requirement: Canonical Flow A workflow activation on Ubuntu server

The system SHALL support controlled activation of the canonical Flow A n8n workflow on Ubuntu host `192.168.0.194` with stable id `silvermanFlowAPublish01` (display name **Silverman Blog LinkedIn Flow A Publish**) after the repository export includes the Schedule Trigger and single-flight guard defined for US-010.

Activation MUST be an explicit post-import operator (or approval-gated script) step. Repository export `"active"` MUST remain `false`. Live server `"active": true` is authoritative for operational state and MUST be recorded in RUNTIME-STATE when validated.

Activation MUST NOT use n8n Execute Command nodes and MUST NOT call LinkedIn publication APIs.

#### Scenario: Server workflow is active after activation procedure

- **WHEN** an operator completes the documented import-then-activate procedure for `silvermanFlowAPublish01`
- **THEN** n8n export/API shows `active: true` for that stable id and operator evidence reports PASS for activation

#### Scenario: Repository export remains inactive

- **WHEN** the repository Flow A workflow JSON is parsed after this capability is applied
- **THEN** top-level `"active"` is `false`

#### Scenario: Activation does not invoke LinkedIn publication

- **WHEN** the activated Flow A workflow runs its HTTP chain
- **THEN** it does not call LinkedIn publication API hosts or LinkedIn n8n nodes

### Requirement: Daily Schedule Trigger at 09:00 UTC

The canonical Flow A workflow export SHALL include exactly one Schedule Trigger node configured to fire daily at **09:00 UTC** using cron expression `0 9 * * *` with timezone UTC.

The Manual Trigger node MUST remain present for operator-initiated runs. Both triggers MUST enter the same shared configuration and single-flight path before worker health checks.

#### Scenario: Export contains daily UTC schedule

- **WHEN** `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` is inspected
- **THEN** it contains a Schedule Trigger with cron `0 9 * * *` and UTC timezone semantics

#### Scenario: Manual Trigger retained

- **WHEN** the Flow A workflow export is inspected
- **THEN** a Manual Trigger node is present in addition to the Schedule Trigger

#### Scenario: Empty ready folder is a clean schedule no-op

- **WHEN** the schedule (or Manual Trigger) runs and `POST /process-ready` returns zero valid candidates
- **THEN** the workflow stops cleanly without calling publish, package, or schedule apply endpoints

### Requirement: Single-flight concurrent execution prevention

The activated Flow A workflow SHALL prevent overlapping concurrent executions of the same workflow using an orchestration-side single-flight guard (workflow static-data lock or equivalent Code/IF control nodes allowed under ADR-0001).

While a lock is held and not past TTL, a second trigger MUST take a skip branch with operator-visible outcome `skipped_already_running` and MUST NOT proceed to worker apply endpoints (`POST /publish-blog-post`, `POST /generate-linkedin-package`, `POST /schedule-linkedin-distribution`).

Lock TTL MUST be documented (default 2 hours) so a killed container cannot leave a permanent stuck lock. Existing worker idempotency (`already_published` and package/schedule completed responses) remains the safety net for completed work and MUST NOT be weakened.

#### Scenario: Second run skips while first holds lock

- **WHEN** an execution holds the single-flight lock and a second Manual or Schedule execution starts
- **THEN** the second execution exits with `skipped_already_running` without calling publish/package/schedule

#### Scenario: Expired lock does not permanently block

- **WHEN** a lock timestamp is older than the documented TTL
- **THEN** a subsequent execution may acquire the lock and proceed

#### Scenario: Idempotent completed work is not duplicated

- **WHEN** the workflow re-runs against content already published with matching worker idempotency proofs
- **THEN** worker responses remain completed/idempotent and do not create duplicate blog or LinkedIn package artifacts

### Requirement: Restart and recovery validation evidence

Operator validation for US-010 SHALL include a documented restart/recovery procedure on `192.168.0.194` that proves:

- n8n/container restart while idle does not deactivate the intended activated workflow unexpectedly without operator action, and the next run can proceed
- mid-run or force-killed executions do not leave a permanent stuck lock beyond TTL
- concurrent triggers cannot double-apply publish/package/schedule for the same run window under the single-flight guard
- default evidence prefers empty ready folder / non-mutating paths; any live blog side effects require explicit operator approval

Evidence MUST be written to an operator report under `docs/operations/` with pass/fail per step and remediation. LinkedIn API publication MUST NOT be part of this evidence path.

#### Scenario: Idle restart evidence recorded

- **WHEN** an operator restarts the n8n container while the workflow is active and idle, then runs Manual Trigger with empty ready
- **THEN** the run completes as a clean no-op and the evidence report records PASS for idle restart

#### Scenario: Stuck lock recovery via TTL

- **WHEN** a lock is left without release and wall time exceeds TTL
- **THEN** the next execution acquires the lock successfully and the evidence report records PASS for lock recovery

#### Scenario: LinkedIn publish excluded from recovery evidence

- **WHEN** US-010 restart/recovery evidence is collected
- **THEN** no LinkedIn publication API calls are made as part of that procedure

### Requirement: Operator-visible pass fail pending for activation

Activation, concurrency, and recovery verification MUST emit human-readable overall status with distinct modes and remediation.

Supported overall states MUST include at minimum: `PASS`, `PENDING`, and `FAIL`.

Failure/pending modes MUST distinguish at minimum:

- workflow not yet re-imported with Schedule Trigger (`PENDING`)
- workflow imported but not activated (`PENDING`)
- wrong stable id (`FAIL`)
- schedule missing or wrong cron/timezone (`FAIL`)
- single-flight guard missing (`FAIL`)
- unexpected repo export `active: true` (`FAIL`)
- server expected active but inactive after activation step (`FAIL`)
- concurrent skip not observed when lock held (`FAIL`)
- secrets printed (`FAIL`)

#### Scenario: Pending when imported but inactive

- **WHEN** server export shows `silvermanFlowAPublish01` with Schedule Trigger but `active: false` and activation has not been performed
- **THEN** activation verification reports `PENDING` with remediation to activate after identity checks

#### Scenario: Pass when active with schedule and guard

- **WHEN** server shows correct id, Schedule Trigger `0 9 * * *` UTC, single-flight guard present, and `active: true`
- **THEN** activation identity verification reports `PASS`

### Requirement: Ready-folder path retained versus calendar connector

US-010 activation MUST retain the existing ready-folder orchestration body (`POST /process-ready` → publish → package → schedule). It MUST NOT require replacing that chain with `POST /editorial-calendar/execute-flow-a-due` as a condition of activation.

Documentation MUST state that Schedule Trigger is the orchestration timer and the editorial calendar connector remains the separate calendar policy entry point.

#### Scenario: Process-ready remains in activated export

- **WHEN** the activated workflow export is inspected
- **THEN** it still references `/process-ready`, `/publish-blog-post`, `/generate-linkedin-package`, and `/schedule-linkedin-distribution`

#### Scenario: Calendar connector not required for US-010 activation

- **WHEN** US-010 activation tasks complete
- **THEN** wiring `POST /editorial-calendar/execute-flow-a-due` into the canonical Flow A n8n workflow is not required for story acceptance

### Requirement: US-011 and BL-005 remain out of scope

This capability MUST NOT close US-011 (LinkedIn publication disabled until separately approved) or BL-005 (fully unattended Flow A test). It MUST NOT flip `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` as part of default US-010 implementation or evidence.

#### Scenario: US-011 not marked complete by this capability

- **WHEN** US-010 activation validation passes
- **THEN** product progress for US-011 remains incomplete unless a separate approved change validates that story

#### Scenario: LinkedIn publication flag not flipped by default

- **WHEN** default US-010 apply and evidence procedures run
- **THEN** they do not change `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
