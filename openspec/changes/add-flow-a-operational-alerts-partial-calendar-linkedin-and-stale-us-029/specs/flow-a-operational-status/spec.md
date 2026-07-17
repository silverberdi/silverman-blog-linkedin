## MODIFIED Requirements

### Requirement: US-027 scope and verification

Implementation SHALL extend the existing `flow-a-operational-status` capability for US-027 stage-duration and dependency-failure observability without creating a parallel status endpoint or duplicating US-026 classification semantics.

Focused behavioral tests MUST cover completed and open stage intervals, execution durations, each dependency bucket plus unclassified codes, invalid/inverted clocks, deterministic ordering of new collections, safe output, API-key authentication, and byte-for-byte zero mutation. Existing US-026 classification, calendar-delay, LinkedIn progress, confinement, and partial-result tests MUST continue to pass without weakened assertions.

This capability MUST remain a read-only observation surface: it MUST NOT send notifications, call webhooks, or write alert ledgers. BL-011 / US-028 and US-029 alerting is owned by the separate `flow-a-operational-alerts` capability. This capability MUST NOT implement US-030 alert behavior or BL-015 UI behavior, MUST NOT deploy or mutate live systems as part of a status-only change, and MUST NOT add n8n workflow changes as part of status observation.

Operator documentation MUST describe stage-duration derivation, dependency-bucket mapping, open-stage observation relativity, and the distinction between execution duration and lifecycle stage duration.

`docs/CURRENT-STATE.md` and product progress MUST be updated only to the level actually implemented and demonstrated. This capability MUST NOT mark US-026 accepted solely because US-027 is implemented, and MUST NOT close BL-010 until US-026 and US-027 are separately satisfied and accepted.

#### Scenario: US-027 regression suite passes
- **WHEN** the change is verified
- **THEN** focused operational-status tests covering stage durations and dependency failures pass, and existing US-026 operational-status assertions remain intact

#### Scenario: Out-of-scope behavior remains absent from status endpoint
- **WHEN** `GET /flow-a/operational-status` is called
- **THEN** the status endpoint does not send notifications, call alert webhooks, write alert ledgers, or provide BL-015 UI behavior

#### Scenario: Single consolidated status surface is preserved
- **WHEN** an authenticated operator requests Flow A operational status
- **THEN** stage durations and dependency failures are returned from `GET /flow-a/operational-status` together with the existing US-026 fields

### Requirement: US-026 scope and verification

US-026 behavior remains part of this capability and MUST continue to identify successful and failed persisted executions, blocked or stale campaigns, and delayed calendar items with the classifications defined in this spec.

Implementation SHALL preserve behavioral service and HTTP tests for successful and failed persisted executions, campaign success/failure/block/stale combinations, delayed calendar boundaries, LinkedIn progress summaries, malformed and confined path handling, API-key authentication, invalid `now_utc`, deterministic ordering, safe output, and zero mutation.

The implementation MUST preserve existing Flow A lifecycle, queue, calendar, scheduling, and LinkedIn publication behavior and tests.

US-027 stage-duration and dependency-failure requirements are specified separately in this capability and MUST NOT regress US-026 classifications. BL-011 alerting is not implemented by this observation capability; US-028 and US-029 alert evaluation and emission are owned by `flow-a-operational-alerts`. BL-015 UI behavior remains out of scope for this capability.

Operator documentation MUST continue to explain the endpoint contract, classification rules, legacy run-record limitation, campaign lifecycle versus LinkedIn publication distinction, and read-only guarantee, and MUST additionally cover US-027 fields when implemented.

`docs/CURRENT-STATE.md` and product progress MUST be updated only to the level actually implemented and demonstrated. Proposal or code completion alone MUST NOT mark US-026 accepted or BL-010 closed; BL-010 remains incomplete until US-026 and US-027 are separately satisfied and accepted.

#### Scenario: US-026 regression suite passes
- **WHEN** the change is verified
- **THEN** focused operational-status tests and existing affected Flow A regression tests pass without weakened assertions or new warnings

#### Scenario: US-026 classifications remain authoritative
- **WHEN** stage-duration and dependency-failure fields are present in the response
- **THEN** successful/failed execution, blocked/stale/in-progress campaign, and delayed-calendar classifications still follow the US-026 rules without reinterpretation

#### Scenario: Status observation does not perform alerting side effects
- **WHEN** the operational-status endpoint reports failed, blocked, delayed, stale, or dependency-failure items
- **THEN** it does not emit alerts, call webhooks, or write `metadata/operational-alerts/` as part of the status request
