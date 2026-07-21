## 1. Inspect and lock scope

- [x] 1.1 Confirm US-087 acceptance criteria in `docs/product/user-stories.md` match this change; leave US-088 / US-089 / US-052 Story accepted / BL-021 closure out of scope
- [x] 1.2 Inventory Week/Month chip rendering, EventModal status surfaces, schedule-visibility DTO/`ScheduleVisibilityItem`, and US-020 cadence helper (`CADENCE_MINIMUM_INTERVAL` / publish guard) for reuse
- [x] 1.3 Confirm US-051 cadence-conflict vocabulary (≠ density, ≠ sequence, ≠ OAuth, ≠ enablement) and US-052 residual warning obligation (docs only; no shift-forward code)

## 2. Worker cadence-conflict projection

- [x] 2.1 Add shared read-only cadence projection helper that reuses US-020 72h semantics (no second constant; no publish-due behavior change)
- [x] 2.2 Extend `ScheduleVisibilityItem` (+ `to_dict`) with `cadence_conflict`, `cadence_conflict_code`, `cadence_earliest_feasible_at_utc` per design D1–D3
- [x] 2.3 Populate fields for eligible not-yet-Live LinkedIn items; force false/null for Live, Cancelled, Failed, blog, density-only, sequence-only, evidence-invalid-alone
- [x] 2.4 Ensure schedule-visibility remains read-only (no metadata mutation, no LinkedIn API, enablement untouched)

## 3. Console warning UX

- [x] 3.1 Extend typed client / shared model with cadence-conflict fields from schedule-visibility
- [x] 3.2 Week view: red (or equivalent) cadence-conflict indicator on conflicted LinkedIn chips without replacing US-083 primary status
- [x] 3.3 Month view: same indicator for conflicted LinkedIn items (readable under density)
- [x] 3.4 EventModal: plain-language cadence conflict + usable next step (earliest feasible local time and/or postpone / wait for replan — do not claim US-089 is shipped)
- [x] 3.5 Ensure feasible items show no cadence warning; distinctness from Failed / Cancelled / Waiting to send / density-full cues; no Live implication

## 4. Tests, assets, and docs

- [x] 4.1 Pytest: conflict true/false fixtures; earliest-feasible when computable; Live/cancelled/failed/blog/density-only negatives; non-mutation
- [x] 4.2 Vitest: Week + Month indicator; EventModal copy/next step; feasible negative; distinctness regressions vs Failed/density
- [x] 4.3 Rebuild static console assets into worker static path
- [x] 4.4 Update `docs/CURRENT-STATE.md` that US-087 is implemented (not Story accepted); do not claim BL-021 closed
- [x] 4.5 Run targeted pytest + Vitest; `git diff --check`; secrets audit on touched files

## 5. Visual DoD and business validation

- [x] 5.1 Capture or schedule Visual DoD evidence (desktop + mobile): Week conflicted chip; Month conflicted item; EventModal explanation + next step; feasible without warning; distinct from Failed/density; mobile EventModal — unless operator waives formal pack
  - Scheduled in `visual-dod-plan.md` (not captured in apply environment; Story accepted still gated).
- [ ] 5.2 After explicit deploy approval (separate from apply): operator walkthrough that US-087 AC are visible on the live console
- [x] 5.3 Update `docs/product/progress-checklist.md` and US-087 status only for demonstrated criteria; leave US-088 / US-089 / BL-021 closure untouched
- [x] 5.4 Confirm non-goals held: no US-088 shift-forward, no US-089 replan, no second publish pipeline, no ADR-0001 / enablement / US-020 math changes
