## ADDED Requirements

### Requirement: Replan already-scheduled cadence-infeasible LinkedIn variants (US-089)

The worker SHALL expose an authenticated replan service and HTTP entry point `POST /replan-linkedin-cadence-conflicts` that selects already-scheduled LinkedIn variants that are **cadence-infeasible** at their current `scheduled_at_utc` and shifts them forward to the next **feasible** slot.

Eligible targets MUST be not-yet-Live variants with `publish_state` **`pending`** or **`queued`**, a usable `scheduled_at_utc`, and cadence conflict under the US-051 / US-020 meaning at that instant (same gate as live `linkedin_publish_blocked_cadence` / related cadence skip / US-087 `cadence_conflict` projection). Density-full alone, sequence-alone, OAuth missing, and publication enablement off MUST NOT select a variant for replan.

The request MAY filter by optional `campaign_id` and/or explicit `targets[]` of `{campaign_id, variant_id}`. When filters are omitted, the worker MUST scan for eligible conflicts in a documented deterministic order. Variants that are cadence-feasible at their current slot MUST NOT be needlessly moved.

Replan placement MUST reuse the US-088 shared feasibility module (`linkedin_schedule_feasibility` / `find_feasible_slot_forward` or equivalent) with `CADENCE_MINIMUM_INTERVAL` / `project_cadence_conflict_at` — the worker MUST NOT invent a second cadence engine or disagreeing 72h constant. Feasible slots MUST also respect US-040K density max **2** / operator-local day and applicable strategy constraints. Preferred-window scanning and the **28** operator-local-day horizon MUST match US-052 / US-088 (current slot’s operator-local day = day 0).

On successful **real** apply for a target: update campaign schedule metadata consistently (`scheduled_at_utc`; for `queued`, keep `queued` and align `publish_after_utc` with the new schedule as US-084 defer does). Calendar / schedule-visibility SoT MUST reflect the new times after refresh. Silent keep of a known cadence-infeasible time as a successful replan outcome is forbidden.

#### Scenario: Cadence-conflicted pending variant is shifted forward

- **WHEN** an authenticated replan runs (real mode) against a `pending` LinkedIn variant whose current `scheduled_at_utc` is cadence-infeasible under US-051/US-020
- **THEN** the worker assigns a later feasible `scheduled_at_utc` using shared US-088 shift-forward helpers
- **AND** campaign metadata records the new time
- **AND** `publish_state` remains `pending`

#### Scenario: Cadence-conflicted queued variant keeps queued and updates publish timing

- **WHEN** an authenticated replan runs (real mode) against a `queued` LinkedIn variant whose current `scheduled_at_utc` is cadence-infeasible
- **THEN** the worker updates `scheduled_at_utc` to a feasible later slot
- **AND** `publish_state` remains `queued`
- **AND** `publish_after_utc` is aligned with the new schedule

#### Scenario: Cadence-feasible Scheduled items are not needlessly moved

- **WHEN** replan runs against a set that includes cadence-feasible not-yet-Live LinkedIn variants
- **THEN** those feasible variants keep their existing `scheduled_at_utc`
- **AND** only cadence-infeasible eligible targets are proposed/applied for move

#### Scenario: Selection matches US-087 cadence meaning

- **WHEN** replan evaluates whether a variant is a replan target
- **THEN** selection uses the same 72h published-evidence cadence gate as US-087 / publish-time helpers
- **AND** density-full alone, sequence-alone, OAuth, and enablement-off do not select the variant

#### Scenario: HTTP endpoint requires auth

- **WHEN** `POST /replan-linkedin-cadence-conflicts` is called without valid API authentication
- **THEN** the request is rejected and no schedule metadata is mutated

### Requirement: Replan dry-run preview and explicit real confirmation (US-089)

`POST /replan-linkedin-cadence-conflicts` and the replan service entry point MUST support `dry_run` and MUST default `dry_run` to **true**. Dry-run / preview MUST compute and return the proposed moves (previous and proposed `scheduled_at_utc` per target, plus per-target errors when applicable) without mutating campaign metadata or calendar SoT.

Real replan (`dry_run` false) MUST require explicit confirmation semantics consistent with console patterns (preview ≠ Live on LinkedIn; preview ≠ LinkedIn API published). Real mode MUST NOT apply a partial plan that leaves some selected targets successfully moved and others silently unchanged when the computed plan was not fully feasible — fail closed for the request when any selected target cannot be placed (after returning/allowing preview of per-target errors). CAS / concurrent-write conflicts MUST fail closed with a structured error and MUST NOT invent silent retries that publish.

#### Scenario: Dry-run default does not mutate

- **WHEN** replan is invoked without overriding dry-run (or with `dry_run` true)
- **THEN** the response includes proposed moves for eligible cadence conflicts
- **AND** no campaign schedule metadata is written

#### Scenario: Real replan requires explicit dry_run false

- **WHEN** replan is invoked with `dry_run` false after operator confirmation
- **THEN** eligible feasible moves are persisted to campaign metadata
- **AND** the response does not claim LinkedIn API published

#### Scenario: No feasible slot for a selected target fails closed

- **WHEN** shift-forward cannot find a feasible slot within the US-052 28 operator-local-day horizon for a selected cadence-conflicted target
- **THEN** replan fails closed with structured error `linkedin_schedule_no_feasible_slot` (or an equivalent replan-scoped code that preserves the same operator meaning)
- **AND** the worker does not write a successful outcome that leaves that target at a known cadence-infeasible time

### Requirement: Replan does not publish or bypass enablement (US-089)

Cadence replan MUST NOT call LinkedIn API publish endpoints and MUST NOT bypass or force-enable `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. US-020 publish-time cadence evaluation remains authoritative at send. After a successful real replan to a feasible slot, schedule-visibility MUST be able to project `cadence_conflict` **false** for that item at the new `scheduled_at_utc` (US-087 warning clears on refresh). Residual true conflicts (race with new published evidence) MUST still be projectable under existing US-087 rules.

#### Scenario: Successful replan does not publish

- **WHEN** real cadence replan succeeds
- **THEN** no LinkedIn API publish is attempted
- **AND** affected variants remain not Live solely because of replan

#### Scenario: Enablement is not bypassed by replan

- **WHEN** replan runs while publication enablement is off
- **THEN** replan still only mutates schedule metadata (when real) and does not force-enable publication

#### Scenario: US-087 warning clears when new slot is feasible

- **WHEN** real replan moves a previously cadence-conflicted item to a feasible `scheduled_at_utc` and schedule-visibility is refreshed
- **THEN** that item’s `cadence_conflict` is false
- **AND** the console cadence-conflict warning MUST NOT remain active solely due to the old slot
