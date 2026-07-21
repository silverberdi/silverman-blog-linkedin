## Why

US-052 documents preferred windows and shift-forward rules, and US-087 warns when a Scheduled slot would already hit the live US-020 cadence gate — but `schedule-linkedin-distribution` (and Flow B spill-A placement) still write preferred/`start_at_utc`/stagger/spill candidates without evaluating same-campaign 72h cadence. New schedules can land on times the automatic publisher will refuse for cadence, leaving the calendar as a lie until operators notice the US-087 warning or wait for US-089 replan.

## What Changes

- Make schedule-time placement **cadence-aware**: when choosing LinkedIn `scheduled_at_utc`, evaluate same-campaign 72h cadence under the US-051 / US-020 meaning (same gate as `linkedin_publish_blocked_cadence` / related cadence skip at that candidate instant).
- When a preferred/candidate slot is **cadence-infeasible**, **shift forward** to the next **feasible** slot that also respects US-040K density max **2**/operator-local day and existing strategy constraints (`flow_a_staggered` stagger; `flow_b_spill_a` empty-day / week / forward spill order as applicable). Prefer US-052 preferred windows (Tue–Thu / 08:00–10:00 or 16:00–18:00 America/Bogota) while scanning forward.
- **Fail closed** with a structured, operator-visible error if no feasible slot exists within the documented **28 operator-local-day** horizon (US-052 default). No infinite scan; no silent infeasible placement.
- Cover **Flow A** `schedule-linkedin-distribution` and **Flow B spill-A** paths that write LinkedIn `scheduled_at_utc`.
- Scheduling MUST **NOT** call LinkedIn API publish and MUST **NOT** bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Do **not** weaken US-087 `cadence_conflict` projection: residual post-placement conflicts (rare) MUST still warn.
- Reuse `CADENCE_MINIMUM_INTERVAL` / shared cadence helpers (US-020 / US-087); no second cadence engine; ADR-0001 (n8n → worker HTTP only).

## Goals

- Satisfy **BL-021 / US-088** acceptance criteria in `docs/product/user-stories.md`.
- Make new schedule results / calendar times reflect shifted feasible slots.
- Communicate fail-closed / blocked states clearly (distinct from density-full alone, sequence-alone, OAuth, enablement-off).
- Leave US-020 publish-time cadence guard authoritative at send.
- Prefer after US-087 so residual edge conflicts stay visible.

## Non-goals

- **US-089** replan of already-Scheduled cadence conflicts.
- Marking **US-052** / **US-087** / **US-088** / **BL-021** Story accepted or closing BL-021 by this change alone.
- Changing publish-time 72h evaluation, n8n, LinkedIn publish-due cron, OAuth, or enablement.
- Treating density-full, sequence-alone, OAuth, or enablement-off as “cadence conflict.”
- A second cadence engine or disagreeing 72h constant.
- Console warning UI redesign (US-087 already shipped; preserve behavior).
- Browser filesystem SoT or n8n Execute Command (ADR-0001).

## Acceptance criteria addressed

| US-088 criterion | How this change addresses it |
|---|---|
| Evaluate same-campaign 72h cadence when choosing slots | Schedule / spill placement paths check US-051/US-020 cadence at candidate `scheduled_at_utc` |
| Shift forward to next feasible slot (density + strategy) | Forward scan with US-040K max 2 + stagger/spill constraints; prefer US-052 windows |
| Fail closed within documented bounds | Structured error when no slot within 28 operator-local days |
| No LinkedIn API publish; no enablement bypass | Explicit non-mutation of publish path / enablement |
| Residual conflict still shows US-087 warning | Do not weaken cadence_conflict projection |
| Outcome visible (schedule results / calendar times) | Written `scheduled_at_utc` / schedule response reflect shifted slots |
| Failures clearly communicated | Distinct structured error for no-feasible-slot vs existing density/spill errors |
| No duplicate / weaken completed work | Reuse shared cadence helpers; US-020 remains authoritative at send |

## Intentionally excluded

- Replan of existing Scheduled conflicts (US-089).
- Story accepted / BL-021 closure.
- Publish-time guard, n8n, cron, OAuth, enablement changes.
- Redefining cadence conflict to include density/sequence/OAuth/enablement.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `linkedin-distribution-scheduling-model`: require cadence-aware placement and shift-forward for `flow_a_staggered` and `flow_b_spill_a` (and any related path that sets LinkedIn `scheduled_at_utc` via `schedule_linkedin_distribution`); fail closed within the US-052 28 operator-local-day horizon with a structured error; preserve no LinkedIn API publish / no enablement bypass; reuse shared US-020 cadence semantics.
- `linkedin-publishing-windows-and-shift-forward-policy`: light MODIFIED pointer that executable schedule-time shift-forward is owned by this change (US-088), without rewriting preferred-window or horizon policy numbers.

## Impact

- **Worker:** `linkedin_distribution_schedule.py`, `flow_b_spill_schedule.py`, shared reuse of cadence projection helpers / `CADENCE_MINIMUM_INTERVAL` from publication flow (or extracted shared module if needed without forking meaning); density helpers already used by spill/defer paths; pytest for shift-forward happy path, density interaction, fail-closed horizon, and non-mutation of enablement / no LinkedIn API.
- **HTTP:** existing `POST /schedule-linkedin-distribution` response/errors gain fail-closed no-feasible-slot semantics; no new public route required unless design proves otherwise.
- **Console:** no required UI feature work; US-087 warning MUST remain accurate for residual conflicts.
- **Docs after implementation:** CURRENT-STATE capability language; ops policy pointer that US-088 enforces the US-052 scan; product checklist/story progress only when criteria are demonstrated.
- **Preserved:** US-020 / BL-007 publish-time guard; US-051 cadence conflict meaning; US-052 windows + 28-day horizon; US-087 projection; US-040K density; ADR-0001; ADR-0002.

## Related backlog / stories

- **BL-021** — Define Editorial Calendar and Publishing Cadence
- **US-088** — Schedule LinkedIn Variants With Cadence-Aware Shift Forward (this change)
- Prerequisites: **US-051** (policy), **US-052** (windows + shift-forward policy), **US-087** (console warning — implemented/deployed; residual conflicts must still warn)
- Apply order: US-051 → US-087 → **US-088** → US-089
