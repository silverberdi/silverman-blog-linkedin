## ADDED Requirements

### Requirement: Variant operator_supervision traceability at package and schedule boundaries

Campaign `variants[]` entries MUST support optional `operator_supervision` metadata for US-017 persisted supervision decisions.

`operator_supervision` is additive metadata and MUST NOT be required for Flow A package generation or distribution scheduling to succeed.

Package generation and schedule operations MUST NOT strip existing `operator_supervision` when rewriting campaign metadata unless an explicit supervision action replaces it.

After distribution scheduling, each variant entry MUST remain eligible to receive `operator_supervision` updates via supervision worker routes while `publish_state` is `pending`.

#### Scenario: Schedule does not preclude later supervision

- **WHEN** distribution scheduling completes for a Flow A campaign
- **THEN** each `variants[]` entry has `publish_state` `pending` and may later gain `operator_supervision` without re-running package or schedule

#### Scenario: Supervision metadata is additive

- **WHEN** an operator inspects campaign metadata after package generation and before any supervision action
- **THEN** `operator_supervision` MAY be absent and the variant is still valid at `pending`
