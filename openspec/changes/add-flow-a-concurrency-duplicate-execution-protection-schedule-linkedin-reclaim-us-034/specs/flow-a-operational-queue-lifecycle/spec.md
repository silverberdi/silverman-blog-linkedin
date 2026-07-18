## ADDED Requirements

### Requirement: Abandoned-claim stale detect and reclaim are operator-visible US-034 deliverables

Stale processing detection and reclaim MUST be treated as US-034 story deliverables with operator-visible outcomes, using the existing execution vocabulary (`processing`, `stale`, `idle`) and recovery classifications without inventing a parallel queue ontology.

`detect_stale_flow_a_execution` (or equivalent) MUST:

- complete with `execution_state=stale` and `recovery_classification=retryable` when a `processing` claim is past `last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`;
- skip without mutation when the claim is not yet stale or not in `processing`;
- leave physical `source_file_status.location` unchanged.

`claim_flow_a_execution` reclaim from `stale` MUST complete with `execution_state=processing`, a new `execution_attempt_id`, incremented `attempt_count`, and `reclaimed_from_stale=true` (or equivalent structured field) so operators can distinguish reclaim from a first claim.

Non-stale `processing` claims MUST continue to fail closed with `flow_a_execution_already_claimed` and `recovery_classification=manual_intervention_required`.

Reclaim and subsequent resume MUST use existing campaign evidence and completed-stage markers and MUST NOT create duplicate LinkedIn schedule slots or duplicate LinkedIn API publications when durable evidence already exists.

#### Scenario: Stale detect completed is operator-visible

- **WHEN** stale detection runs for an abandoned non-progressing `processing` claim past the configured inactivity threshold
- **THEN** the result status is completed, `execution_state` is `stale`, and `recovery_classification` is `retryable`

#### Scenario: Stale detect skipped when claim still active

- **WHEN** stale detection runs for a `processing` claim that is not past the inactivity threshold
- **THEN** the result is skipped (or equivalent non-mutating outcome), `execution_state` remains `processing`, and `recovery_classification` remains `manual_intervention_required` for duplicate-claim guidance

#### Scenario: Reclaim from stale is operator-visible

- **WHEN** claim runs for a campaign with `execution_state=stale`
- **THEN** claim completes with `execution_state=processing`, a new `execution_attempt_id`, and `reclaimed_from_stale=true` (or equivalent)

#### Scenario: Reclaim does not duplicate completed schedule or LinkedIn evidence

- **WHEN** a stale campaign that already has matching distribution schedule proof and/or published LinkedIn URN evidence is reclaimed and resumed
- **THEN** resume does not create duplicate schedule slots or a second LinkedIn API publication for identities that already have durable evidence
