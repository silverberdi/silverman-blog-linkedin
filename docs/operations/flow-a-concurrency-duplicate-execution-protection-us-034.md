# Flow A concurrency and duplicate-execution protection (US-034)

Operator-facing outcomes for **BL-013 / US-034** only: concurrent or repeated
triggers must not duplicate **distribution scheduling** or **LinkedIn API
publication**, and abandoned **processing** claims must be recoverable via stale
detect + reclaim. Worker HTTP remains the safety net (ADR-0001); n8n
single-flight is complementary defense-in-depth.

## Status

- **Implemented, automated-tested, and acceptance criteria validated** against fixture evidence (2026-07-18).
- **Not** deployed or operationally validated on the live worker by this document alone.
- US-033 remains accepted (fixture evidence). US-035 and BL-013 remain open.

## In scope (US-034)

| Surface | Protection | Operator-visible outcome |
|---------|------------|--------------------------|
| Distribution scheduling | First-time `derivatives_generated` → `distribution_scheduled` uses campaign-metadata fingerprint CAS (+ flock); matching proof remains idempotent | Completed schedule (winner or matching loser); mismatch: `linkedin_schedule_metadata_mismatch`; no duplicate `state_history` / no `scheduled_at_utc` rewrite on matching rerun |
| LinkedIn API publication | Pre-API evidence re-check; successful URN persist via CAS; already-published short-circuit (including `publish_now`) | `linkedin_publish_already_published` with preserved `linkedin_post_urn` / `published_at`; zero LinkedIn API calls on skip |
| Abandoned claims | Existing stale detect + reclaim vocabulary | Detect completed: `execution_state=stale`, `recovery_classification=retryable`; detect skipped when not yet stale; reclaim: `reclaimed_from_stale=true`, new `execution_attempt_id`; non-stale: `flow_a_execution_already_claimed` + `manual_intervention_required` |

## Out of scope (do not expect from US-034)

| Story / ops | Not delivered here |
|-------------|--------------------|
| **US-033 rework** | Claim CAS / image skip / blog handoff already delivered; left intact |
| **US-035** | Restart validation evidence |
| Ops | Git push, live-site mutation, deploy, production n8n activation |

## How to read outcomes

### Schedule completed vs mismatch

Matching schedule identity on an already-`distribution_scheduled` campaign returns
`status=completed` without rewriting anchors. Conflicting identity fails with
`linkedin_schedule_metadata_mismatch`.

### LinkedIn already published

Variant `publish_state=published` with stored URN → no LinkedIn API call;
warning `linkedin_publish_already_published`. Peer evidence won under contention
is preserved; losers do not clear the winner URN.

### Stale detect

- Completed: abandoned `processing` past
  `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` → `stale` + `retryable` (no file moves).
- Skipped: still active / not yet stale → `status=skipped`, remains `processing`
  with `manual_intervention_required` guidance for duplicate claim.

### Reclaim from stale

`claim_flow_a_execution` on `stale` yields `reclaimed_from_stale=true`, new
attempt id, incremented `attempt_count`. Resume inherits schedule / LinkedIn /
US-033 idempotency so completed evidence is not duplicated.

### Already claimed (non-stale)

`flow_a_execution_already_claimed`, `already_claimed=true`,
`recovery_classification=manual_intervention_required`.

## Non-goals reminder

Do not treat this document as US-035 restart validation, US-034 business
acceptance, BL-013 closure, deploy proof, or production n8n activation.

## Related evidence

- Change proposal: `openspec/changes/add-flow-a-concurrency-duplicate-execution-protection-schedule-linkedin-reclaim-us-034/`
- Tests: `tests/test_flow_a_concurrency_us034.py`
- Prior story: [flow-a-concurrency-duplicate-execution-protection-us-033.md](flow-a-concurrency-duplicate-execution-protection-us-033.md)
