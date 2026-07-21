## 1. Replan service core (selection + US-088 reuse)

- [x] 1.1 Add replan service module (or extend supervision/schedule module) that selects not-yet-Live `pending`/`queued` LinkedIn variants with cadence conflict at current `scheduled_at_utc` using shared `CADENCE_MINIMUM_INTERVAL` / `project_cadence_conflict_at` — density/sequence/OAuth/enablement alone MUST NOT select
- [x] 1.2 For each selected target, call `linkedin_schedule_feasibility.find_feasible_slot_forward` (or equivalent shared API) with current slot as origin; prefer US-052 windows; 28 operator-local-day horizon; occupy density `planned_counts` across the batch — no second 72h engine
- [x] 1.3 Implement apply semantics: update `scheduled_at_utc`; keep `pending`/`queued` as applicable; for `queued` align `publish_after_utc`; append audit history (`replan_cadence` or equivalent); CAS/atomic campaign write; never silently keep infeasible time as success
- [x] 1.4 Enforce all-or-nothing real apply after a fully feasible plan; return structured `linkedin_schedule_no_feasible_slot` (or equivalent meaning) when any selected target cannot place; leave non-conflicted variants unchanged

## 2. Authenticated HTTP + dry-run

- [x] 2.1 Expose authenticated `POST /replan-linkedin-cadence-conflicts` with `dry_run` default **true**; optional `campaign_id` / `targets[]` filters; structured preview of previous→proposed times and per-target errors
- [x] 2.2 Wire auth rejection (no mutation), stable error mapping, and secret-safe responses consistent with existing worker HTTP patterns
- [x] 2.3 Document one-shot ops/curl path (dry-run then real) against the same endpoint — no n8n Execute Command (ADR-0001)

## 3. Console thin affordance (optional but preferred)

- [x] 3.1 Typed client method for replan endpoint; EventModal (and/or bulk ops) Preview vs Make real confirmation (US-083 honesty)
- [x] 3.2 After successful real replan, refresh schedule-visibility so Week/Month slots move and US-087 cadence-conflict indicators clear when the new slot is feasible
- [x] 3.3 Update EventModal cadence next-step copy so it does not claim operators must only “wait for later replan” when US-089 is available; do not redesign warning chrome beyond clear-after-success / next-step honesty

## 4. Tests

- [x] 4.1 Pytest: cadence-conflicted pending shifts forward; metadata reflects new `scheduled_at_utc`; feasible siblings in the same set are not needlessly moved
- [x] 4.2 Pytest: cadence-conflicted queued keeps `queued`, updates `scheduled_at_utc` + `publish_after_utc`
- [x] 4.3 Pytest: dry-run default proposes moves with zero metadata mutation; real apply persists
- [x] 4.4 Pytest: horizon fail-closed → `linkedin_schedule_no_feasible_slot` (or equivalent); no silent infeasible keep
- [x] 4.5 Pytest: selection/parity with shared cadence helpers; density respected during batch; no LinkedIn publish client calls; enablement env unchanged
- [x] 4.6 Vitest (if console affordance ships): preview vs real honesty; post-replan refresh clears conflict indicator when feasible
- [x] 4.7 Run `git diff --check` on touched files; fix any new warnings attributable to this change

## 5. Docs and business progress

- [x] 5.1 Update `docs/CURRENT-STATE.md` for US-089 replan (implemented vs Story accepted); keep US-087/US-088/US-051/US-052/BL-021 open unless operator-accepted separately
- [x] 5.2 Light ops policy pointer in `docs/operations/linkedin-publishing-windows-and-shift-forward-policy.md` that US-089 owns executable replan (do not change window/horizon numbers)
- [x] 5.3 Update `docs/product/progress-checklist.md` and `docs/product/user-stories.md` only for US-089 criteria actually demonstrated (Work started / demonstrated); do **not** mark Story accepted or close BL-021 without operator review; do not mark US-088/US-087 accepted by this change
- [x] 5.4 Business validation: map AC (authenticated replan path, US-088 reuse, warnings clear, dry-run/confirm, no publish/enablement bypass, conflicted-only moves, visible outcomes, clear failures, no duplicated cadence engine); demonstrate on live conflict set or equivalent fixture
