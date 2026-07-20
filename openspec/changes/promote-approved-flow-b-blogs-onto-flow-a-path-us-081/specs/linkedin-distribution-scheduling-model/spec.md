## ADDED Requirements

### Requirement: Flow B spill algorithm A scheduling strategy

The worker SHALL support LinkedIn distribution scheduling strategy `flow_b_spill_a` for Flow A campaigns that originated from a promoted Flow B blog (Flow B provenance with usable gap context). When `flow_b_spill_a` applies, per-variant `scheduled_at_utc` placement MUST follow spill algorithm A under US-040K local-day density max 2 (settings `density_max_per_local_day` default 2, never exceeding max 2): (1) target-week gap days (`empty_days[]`) chronological with remaining capacity; (2) other days in the target week with remaining capacity; (3) forward day-by-day after the week with remaining capacity. Occupancy MUST count LinkedIn members in `pending` / `queued` / `published` for density. Scheduling MUST NOT call LinkedIn API publish. If no day can be assigned without exceeding max 2, the operation MUST fail closed with a structured error.

#### Scenario: Spill A strategy places onto gap days first

- **WHEN** `schedule_linkedin_distribution` runs with strategy `flow_b_spill_a` for a `flow_a` campaign that has Flow B `target_week` and non-empty `empty_days[]` with available density capacity
- **THEN** the earliest variants receive `scheduled_at_utc` on those gap days in chronological order
- **AND** no local day receives more than density max 2 LinkedIn members

#### Scenario: Spill A spills within week then forward

- **WHEN** `flow_b_spill_a` scheduling has exhausted gap-day capacity and variants remain
- **THEN** remaining variants are placed on other days in the target week with remaining capacity
- **AND** then on subsequent local days after the week under max 2

#### Scenario: Spill A fails closed when density exhausted

- **WHEN** `flow_b_spill_a` cannot place a remaining variant without exceeding max 2 on candidate days in policy order
- **THEN** the operation fails with a structured scheduling error
- **AND** it does not write a partial schedule that exceeds density max 2

### Requirement: Auto-select spill A for Flow B provenance

When `schedule_linkedin_distribution` is invoked without an explicit alternate strategy (or with default strategy) and the campaign carries Flow B origin provenance with usable `target_week` / `empty_days[]` (from promoted sidecar or equivalent campaign metadata), the worker MUST resolve scheduling to `flow_b_spill_a`. When Flow B gap provenance is absent, the worker MUST continue to use default `flow_a_staggered`. An explicit request for `flow_a_staggered` MUST remain honored even for Flow B–origin campaigns. Unknown strategy names MUST continue to fail with `linkedin_schedule_invalid_strategy`. Campaign `flow` MUST remain `flow_a` for promoted Flow B blogs (Flow B provenance MUST NOT set campaign `flow` to `flow_b`).

#### Scenario: Default strategy selects spill A for Flow B origin with gap context

- **WHEN** `schedule_linkedin_distribution` is called for a `flow_a` campaign with Flow B provenance including `empty_days[]` and no explicit non-default strategy override
- **THEN** scheduling uses `flow_b_spill_a`

#### Scenario: Default strategy keeps stagger without Flow B gap provenance

- **WHEN** `schedule_linkedin_distribution` is called for a `flow_a` campaign without Flow B gap provenance and strategy is default
- **THEN** scheduling uses `flow_a_staggered`

#### Scenario: Explicit stagger override remains available

- **WHEN** `schedule_linkedin_distribution` is called with `strategy` `flow_a_staggered` for a Flow B–origin campaign
- **THEN** staggered scheduling is used
- **AND** spill algorithm A is not required for that request
