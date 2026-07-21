## ADDED Requirements

### Requirement: Cadence-aware schedule-time placement and shift-forward (US-088)

When `schedule_linkedin_distribution` (including HTTP `POST /schedule-linkedin-distribution`) computes LinkedIn variant `scheduled_at_utc` values for strategies `flow_a_staggered` and `flow_b_spill_a`, the worker MUST evaluate same-campaign cadence feasibility at each candidate slot under the US-051 / US-020 meaning: the same gate as live `linkedin_publish_blocked_cadence` / related cadence skip at that candidate instant (minimum real interval of **72 hours** against same-campaign successful `published` evidence), using the same interval constant / shared helpers as the publish-time guard and US-087 projection (`CADENCE_MINIMUM_INTERVAL` / equivalent). The worker MUST NOT invent a second cadence engine or disagreeing 72h constant.

When the strategy’s preferred/candidate slot is **cadence-infeasible**, the worker MUST **shift forward** to the next **feasible** slot. A feasible slot MUST satisfy all of:

1. Not cadence-conflicted under the meaning above at that `scheduled_at_utc`
2. Remaining capacity under interim US-040K max **2** LinkedIn density members per operator-local day (including already-accepted slots in the current schedule batch)
3. Existing distribution strategy constraints for the path in use (`flow_a_staggered` audience order and minimum 3 calendar days between consecutive accepted variants; `flow_b_spill_a` empty-day → other week days → forward order)

While scanning forward, the worker MUST prefer US-052 preferred publishing windows as placement guidance (preferred local days Tuesday–Thursday; preferred local clocks 08:00–10:00 or 16:00–18:00; operator timezone America/Bogota) without treating those windows as a second publish-time cadence engine.

The worker MUST NOT silently keep a known cadence-infeasible preferred/candidate time as `scheduled_at_utc`. Successful schedule results and campaign metadata MUST record the shifted feasible `scheduled_at_utc` values so calendar / schedule-visibility times reflect the placement.

Cadence-infeasible MUST NOT be redefined to mean density-full alone, sequence-alone, OAuth missing, or publication enablement off.

#### Scenario: Preferred slot shifts forward when cadence-infeasible

- **WHEN** `schedule_linkedin_distribution` computes a preferred candidate `scheduled_at_utc` that would hit same-campaign US-020 cadence refuse/skip against existing `published` evidence
- **THEN** the worker does not write that infeasible preferred time
- **AND** it assigns a later feasible `scheduled_at_utc` that clears cadence and respects density max 2 and the active strategy constraints
- **AND** the schedule result / campaign metadata expose the shifted time

#### Scenario: Feasible preferred slot is kept

- **WHEN** the preferred candidate slot is cadence-feasible and satisfies density max 2 and strategy constraints
- **THEN** the worker schedules that slot without unnecessary forward shift

#### Scenario: Density is respected during shift-forward

- **WHEN** shift-forward considers a candidate local day that already has 2 density members (excluding capacity freed only by rules already defined for density evaluation)
- **THEN** that day is not accepted as a feasible slot
- **AND** scanning continues forward within bounds

#### Scenario: Stagger strategy preserves sequence and day spacing after shift

- **WHEN** `flow_a_staggered` shifts a later variant forward for cadence
- **THEN** audience sequencing order is preserved
- **AND** consecutive accepted variants remain at least 3 calendar days apart

#### Scenario: Spill A order remains authoritative for day priority

- **WHEN** `flow_b_spill_a` placement encounters a spill-ordered candidate day that is cadence-infeasible
- **THEN** the worker advances to a later feasible slot without inverting spill priority (empty days before other week days before post-week forward days)
- **AND** density max 2 remains enforced

#### Scenario: Cadence meaning matches publish-time / US-087 helpers

- **WHEN** schedule-time cadence feasibility is evaluated for a candidate slot
- **THEN** evaluation uses the same 72h interval and published-evidence semantics as the publish-time guard / US-087 projection helpers
- **AND** density-full alone, sequence-alone, OAuth, and enablement-off are not labeled as cadence conflict

### Requirement: Fail-closed when no feasible slot within US-052 horizon (US-088)

Forward search for a feasible `scheduled_at_utc` MUST be finite. The default horizon MUST be **28 operator-local days** measured from the original preferred/candidate slot’s operator-local calendar day as **day 0**, searching day 0 (at/after the candidate clock under window/strategy rules) and local days **1…28** inclusive, per `docs/operations/linkedin-publishing-windows-and-shift-forward-policy.md`. Infinite scan is forbidden.

If no feasible slot exists within that horizon for a required variant, scheduling MUST **fail closed** with structured error code `linkedin_schedule_no_feasible_slot` (operator-visible via schedule result / HTTP error mapping consistent with existing LinkedIn schedule errors). The worker MUST NOT write a partial schedule that leaves a known cadence-infeasible preferred time in place for the failing variant.

This failure mode MUST remain distinct from `linkedin_schedule_spill_density_exhausted` when the failure is specifically inability to find any cadence+density+strategy-feasible slot within the horizon (implementations MAY still return density-exhausted when spill density is exhausted under existing spill-only rules without a cadence horizon search applying).

#### Scenario: No feasible slot within 28 local days fails closed

- **WHEN** cadence-aware shift-forward cannot find a feasible slot within 28 operator-local days from the original candidate local day
- **THEN** scheduling fails with `linkedin_schedule_no_feasible_slot`
- **AND** it does not silently persist an infeasible preferred `scheduled_at_utc` for the affected placement

#### Scenario: Infinite scan is forbidden

- **WHEN** schedule-time shift-forward runs
- **THEN** candidate search does not continue past the documented 28 operator-local-day horizon

### Requirement: Schedule-time shift-forward does not publish or bypass enablement (US-088)

Cadence-aware placement and shift-forward MUST NOT call LinkedIn API publish endpoints and MUST NOT bypass or force-enable `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. Scheduled variants MUST remain `publish_state` `pending` on first-time schedule success (unchanged from existing scheduling contracts). US-020 publish-time cadence evaluation remains authoritative at send. US-087 schedule-visibility `cadence_conflict` projection MUST NOT be weakened by this change; residual post-placement cadence conflicts (rare) MUST still be projectable/warnable.

#### Scenario: Successful cadence-aware schedule does not publish

- **WHEN** cadence-aware `schedule_linkedin_distribution` succeeds (with or without shifting)
- **THEN** no LinkedIn API publish is attempted
- **AND** scheduled variants have `publish_state` `pending`

#### Scenario: Enablement is not bypassed by scheduling

- **WHEN** cadence-aware scheduling runs while publication enablement is off
- **THEN** scheduling still does not call LinkedIn API publish and does not force enablement on

#### Scenario: Residual cadence conflict projection remains available

- **WHEN** after placement a not-yet-Live LinkedIn item remains cadence-infeasible at its written `scheduled_at_utc` (edge case)
- **THEN** schedule-visibility MAY still project `cadence_conflict` true under existing US-087 rules
- **AND** this change does not remove or redefine that projection to ignore true cadence conflicts
