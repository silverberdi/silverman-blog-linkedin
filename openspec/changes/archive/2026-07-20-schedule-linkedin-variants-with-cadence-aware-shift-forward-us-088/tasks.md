## 1. Shared cadence feasibility for schedule-time

- [x] 1.1 Confirm reuse of `CADENCE_MINIMUM_INTERVAL` / `project_cadence_conflict_at` (or extract a thin shared helper) so schedule-time cadence checks match US-020 / US-087 published-evidence semantics — no second 72h engine
- [x] 1.2 Add a schedule-facing feasibility helper that combines cadence projection + US-040K density capacity (including in-batch accepted slots) + strategy invariants for a candidate `scheduled_at_utc`
- [x] 1.3 Define structured error `linkedin_schedule_no_feasible_slot` and map it through the existing schedule HTTP/result error path (distinct from `linkedin_schedule_spill_density_exhausted`)

## 2. Shift-forward scan (US-052 horizon + preferred windows)

- [x] 2.1 Implement finite forward scan with 28 operator-local-day horizon (candidate local day = day 0; search days 0…28 inclusive per ops policy)
- [x] 2.2 Prefer US-052 windows while scanning (Tue–Thu; 08:00–10:00 then 16:00–18:00 America/Bogota) with deterministic clock choice; never write a known cadence-infeasible preferred slot
- [x] 2.3 Wire shift-forward into `flow_a_staggered` placement so audience order and ≥3 calendar-day consecutive spacing hold after shifts
- [x] 2.4 Wire cadence feasibility + shift-forward into `flow_b_spill_a` without inverting spill day priority (empty days → other week days → forward)

## 3. Integration and non-mutation guards

- [x] 3.1 Ensure `schedule_linkedin_distribution` / `POST /schedule-linkedin-distribution` use cadence-aware placement for both strategies; schedule results and campaign metadata expose shifted `scheduled_at_utc`
- [x] 3.2 Verify scheduling never calls LinkedIn API publish and never bypasses / force-enables `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
- [x] 3.3 Confirm US-087 `cadence_conflict` projection helpers/fields are not weakened (residual conflicts still projectable)

## 4. Tests

- [x] 4.1 Pytest: shift-forward happy path — preferred cadence-infeasible slot moves to later feasible time; metadata/result reflect shift
- [x] 4.2 Pytest: density interaction — shift-forward skips density-full local days (max 2) while searching
- [x] 4.3 Pytest: fail-closed horizon — no feasible slot within 28 local days → `linkedin_schedule_no_feasible_slot`; no silent infeasible keep
- [x] 4.4 Pytest: non-mutation — no LinkedIn publish client calls; enablement env behavior unchanged; cadence meaning aligned with shared helpers
- [x] 4.5 Pytest: spill-A path covers cadence shift without breaking empty-day priority (targeted fixture)
- [x] 4.6 Run `git diff --check` on touched files; fix any new warnings attributable to this change

## 5. Docs and business progress

- [x] 5.1 Update `docs/CURRENT-STATE.md` for US-088 schedule-time cadence-aware shift-forward (implemented vs Story accepted); keep US-089 / BL-021 open
- [x] 5.2 Light ops policy pointer in `docs/operations/linkedin-publishing-windows-and-shift-forward-policy.md` that US-088 enforces the scan (do not change window/horizon numbers)
- [x] 5.3 Update `docs/product/progress-checklist.md` and `docs/product/user-stories.md` only for US-088 criteria actually demonstrated; do not mark Story accepted or close BL-021 without operator review
- [x] 5.4 Business validation: confirm acceptance criteria map (cadence evaluate, shift-forward, fail-closed, no publish/enablement bypass, residual US-087 warning intact, visible shifted times, clear blocked states, no duplicate cadence engine)
