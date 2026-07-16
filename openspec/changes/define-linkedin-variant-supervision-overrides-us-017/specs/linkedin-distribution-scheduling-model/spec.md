## ADDED Requirements

### Requirement: Supervised defer of scheduled_at_utc while pending

The worker MUST allow operator defer (US-017) to update per-variant `scheduled_at_utc` while `publish_state` is `pending`.

Supervised defer MUST NOT rewrite schedule idempotency proof keys from the original Flow A schedule operation unless a new OpenSpec change explicitly defines reschedule idempotency semantics.

Supervised defer MUST append deferral history under `operator_supervision.deferral_history` on the variant entry.

Supervised defer MUST preserve stagger ordering intent: `new_scheduled_at_utc` for one variant MUST NOT require automatic sibling rescheduling in US-017 (sibling spacing adjustments are operator responsibility or future work).

Supervised defer MUST NOT transition campaign `state` away from `distribution_scheduled`.

#### Scenario: Defer updates only target variant schedule

- **WHEN** defer succeeds for one variant in a multi-variant campaign
- **THEN** only that variant's `scheduled_at_utc` changes and sibling variant schedules are unchanged

#### Scenario: Defer does not reset original schedule idempotency

- **WHEN** defer succeeds for a variant on an idempotent-completed schedule campaign
- **THEN** the original schedule idempotency proof remains intact and a repeat `POST /schedule-linkedin-distribution` with the same key still returns `completed` without rewriting original stagger proof

### Requirement: Supervised reschedule validation

Defer MUST reject `new_scheduled_at_utc` that is not strictly in the future relative to worker UTC now.

Defer MUST reject variants not in `publish_state` `pending`.

Defer MUST store all schedule timestamps in UTC ISO8601.

#### Scenario: Future-only defer times

- **WHEN** defer is requested with `new_scheduled_at_utc` equal to or before current UTC time
- **THEN** the operation fails with `linkedin_supervision_defer_time_invalid`

#### Scenario: Defer requires pending publish state

- **WHEN** defer is requested for a variant with `publish_state` `queued`
- **THEN** the operation fails with `linkedin_supervision_variant_not_pending`
