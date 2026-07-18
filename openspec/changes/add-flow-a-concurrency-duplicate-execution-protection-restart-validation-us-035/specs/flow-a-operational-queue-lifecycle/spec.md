## ADDED Requirements

### Requirement: Post-restart stuck processing claims reuse stale detect and reclaim vocabulary

After a worker or process interruption mid-Flow A, a campaign left with `execution_state=processing` MUST continue to use the existing operational-queue vocabulary:

- Non-stale `processing` claims remain blocked for duplicate claim (`flow_a_execution_already_claimed`, `recovery_classification=manual_intervention_required`).
- Stale detection continues to use `last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` and transitions eligible claims to `execution_state=stale` with `recovery_classification=retryable` without moving files.
- Reclaim continues via `claim_flow_a_execution` from `stale` with a new `execution_attempt_id` and `reclaimed_from_stale` (or equivalent) operator-visible semantics.
- Allowlisted incomplete-campaign repair `clear_stale_execution_claim` remains the explicit operator path to release an eligible stale claim to `idle` without erasing durable stage evidence.

Worker process start / restart MUST NOT invent a parallel reclaim mechanism, new execution states, or automatic clearance of non-stale `processing` claims.

This requirement distinguishes restart/crash-recovery **validation** (US-035) from abandoned-claim reclaim as a US-034 deliverable while reusing the same stale/reclaim path for recovery after interruption.

#### Scenario: Mid-flight interruption leaves processing claim intact across process boundary

- **WHEN** Flow A execution is interrupted after a successful claim and the worker process later restarts before the stale threshold
- **THEN** campaign metadata still shows `execution_state=processing` with the prior attempt identity and duplicate claim remains rejected as already-claimed / manual intervention required

#### Scenario: Interrupted processing becomes reclaimable only after stale rules

- **WHEN** an interrupted `processing` claim ages past `last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`
- **THEN** stale detection marks `execution_state=stale` and `recovery_classification=retryable`, and a subsequent claim reclaim yields a new `execution_attempt_id` with `reclaimed_from_stale` true (or equivalent)

#### Scenario: No startup auto-clear of non-stale claims

- **WHEN** the worker starts or restarts while campaigns have non-stale `execution_state=processing`
- **THEN** those claims are not cleared or reclaimed solely as a side effect of process start
