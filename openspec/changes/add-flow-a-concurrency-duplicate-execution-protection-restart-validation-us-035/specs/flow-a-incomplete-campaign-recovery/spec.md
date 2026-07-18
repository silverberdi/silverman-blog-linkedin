## ADDED Requirements

### Requirement: Restart validation exercises incomplete-campaign recovery without changing contracts

Incomplete-campaign recovery MUST remain available as an operator path after mid-flight worker/process interruption, and US-035 restart validation MUST exercise existing inspect / resume / repair contracts without changing them.

In particular, after restart-related interruption:

- Inspect MUST continue to derive `last_valid_stage` from persisted evidence only and MUST NOT invent milestones.
- Resume MUST continue to reject non-stale `execution_state=processing` claims with `recovery_classification=manual_intervention_required` (stable reason such as `flow_a_recovery_active_non_stale_claim`).
- Stale claims MUST continue to be reclaimed using existing stale/reclaim rules before resume continues.
- Resume MUST continue to short-circuit stages whose durable evidence already satisfies the corresponding milestone and MUST NOT duplicate blog publish, package, or schedule side effects.
- Repair MUST continue to allow only the existing allowlisted actions (including `clear_stale_execution_claim` when stale rules allow) and MUST fail closed on ambiguity.
- Default resume MUST NOT enable Git publication, live-site confirmation, or LinkedIn API publication.
- LinkedIn API publication recovery remains owned by `linkedin-retry-recovery-classification` (BL-008).

US-035 MUST NOT add new recovery endpoints, new recovery-action taxonomy values, or new repair actions solely for restart handling.

#### Scenario: Post-interruption resume blocked by non-stale claim

- **WHEN** incomplete-campaign resume is requested after mid-flight interruption while `execution_state=processing` and the claim is not stale
- **THEN** resume returns blocked with `manual_intervention_required` / active non-stale claim reason and performs zero stage side effects

#### Scenario: Post-interruption resume after stale reclaim preserves completed stages

- **WHEN** an interrupted campaign is stale-reclaimed and incomplete-campaign resume runs with durable blog and/or schedule evidence already present
- **THEN** resume short-circuits completed stages without republishing matching blog identity or creating duplicate schedule slots

#### Scenario: Restart validation does not expand repair allowlist

- **WHEN** repair is requested after a restart-related interruption
- **THEN** only existing allowlisted repair actions are accepted and inventing publish/schedule/LinkedIn success remains rejected
