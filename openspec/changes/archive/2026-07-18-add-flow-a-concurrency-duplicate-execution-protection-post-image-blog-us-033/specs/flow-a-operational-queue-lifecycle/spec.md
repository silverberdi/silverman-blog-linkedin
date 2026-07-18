## ADDED Requirements

### Requirement: Concurrent execution claim uses atomic metadata compare-and-swap

`claim_flow_a_execution` MUST persist the transition to `execution_state=processing` using an atomic compare-and-swap (or equivalent) against the on-disk campaign metadata document so that two overlapping claim attempts cannot both successfully write a new active non-stale processing claim for the same `campaign_id`.

When CAS detects that another writer changed the campaign document, the claim helper MUST re-read current state and either:

- complete as the claim winner if still eligible, or
- fail closed with `flow_a_execution_already_claimed` when a non-stale peer claim now holds `processing`.

Claim contention losers MUST set `already_claimed=true` semantics and `recovery_classification=manual_intervention_required`, MUST NOT increment a successful peer’s logical ownership into a second active claim, and MUST NOT proceed as if they held the claim.

This requirement hardens the US-033 post-processing surface. It MUST NOT redefine abandoned-claim stale reclaim policy as a new deliverable (US-034). Existing stale detection helpers MAY remain unchanged.

#### Scenario: Racing idle claims produce one processing claim

- **WHEN** two concurrent claim calls both observe `execution_state=idle` for the same queued campaign
- **THEN** exactly one call returns completed with `execution_state=processing` and the other fails with `flow_a_execution_already_claimed`

#### Scenario: CAS loser does not leave split claim metadata

- **WHEN** a claim CAS attempt loses to a peer writer that already set `processing`
- **THEN** on-disk metadata shows a single `execution_attempt_id` for the active claim and the loser does not persist a second attempt as the active owner

### Requirement: Concurrent duplicate post processing remains visible to callers

Callers of `claim_flow_a_execution` (including the editorial calendar Flow A connector and incomplete-campaign recovery resume) MUST receive the stable already-claimed failure outcome when blocked by a non-stale active claim, without secret or content-body leakage.

Connector item results that fail at claim MUST include `flow_a_execution_already_claimed` in `errors` (or equivalent structured error list) so operators can distinguish claim contention from publish/image failures.

#### Scenario: Connector surfaces already-claimed on contention

- **WHEN** the calendar Flow A connector attempts execution for a campaign whose non-stale claim is already held
- **THEN** the item result is failed/blocked with `flow_a_execution_already_claimed` and does not invoke publish or ComfyUI for that attempt

#### Scenario: Recovery resume still blocked by non-stale claim

- **WHEN** incomplete-campaign recovery resume requests execution while `execution_state=processing` and the claim is not stale
- **THEN** resume is rejected with duplicate-claim protection and no second claim is created
