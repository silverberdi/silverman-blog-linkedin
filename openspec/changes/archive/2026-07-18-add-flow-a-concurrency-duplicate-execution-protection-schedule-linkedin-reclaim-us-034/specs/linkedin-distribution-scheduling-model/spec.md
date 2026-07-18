## ADDED Requirements

### Requirement: Concurrent first-time distribution scheduling uses atomic metadata compare-and-swap

First-time distribution scheduling that persists the transition from `derivatives_generated` to `distribution_scheduled` and writes `linkedin_distribution` / per-variant schedule fields MUST use an atomic compare-and-swap (or equivalent) against the on-disk campaign metadata document so that two overlapping schedule attempts cannot both successfully write a first-time schedule for the same `campaign_id`.

When CAS detects that another writer changed the campaign document, the schedule service MUST re-read current state and either:

- return `status` `completed` when the campaign is already `distribution_scheduled` with matching schedule idempotency proof, without appending duplicate `state_history` or rewriting `scheduled_at_utc`, or
- fail closed with `linkedin_schedule_metadata_mismatch` when stored scheduling metadata does not match the expected proof.

This requirement hardens the US-034 duplicate-scheduling surface. It MUST NOT change eligibility rules, staggered strategy semantics, or the schedule-level idempotency key composition already defined by this capability.

#### Scenario: Racing first-time schedules produce one durable schedule write

- **WHEN** two concurrent `schedule_linkedin_distribution` calls both observe `derivatives_generated` for the same eligible campaign
- **THEN** at most one call persists a successful first-time `distribution_scheduled` write and the other ends as completed idempotent or fail-closed without a second distinct schedule set

#### Scenario: CAS loser observing matching peer schedule is idempotent completed

- **WHEN** a schedule CAS attempt loses to a peer that already wrote matching `distribution_scheduled` proof
- **THEN** the loser returns `status` `completed` without duplicate `state_history` and without changing peer `scheduled_at_utc` values

#### Scenario: CAS loser observing mismatched peer schedule fails closed

- **WHEN** a schedule CAS attempt loses to a peer whose stored schedule proof does not match this request’s expected key or anchors
- **THEN** the loser fails with `linkedin_schedule_metadata_mismatch` and does not overwrite peer schedule metadata
