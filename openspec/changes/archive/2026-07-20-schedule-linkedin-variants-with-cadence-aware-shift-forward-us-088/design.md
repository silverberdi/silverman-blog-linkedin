## Context

US-051 ratified cadence conflict as the live US-020 gate (same-campaign **72h** between successful `published` evidence). US-052 documented preferred publishing windows (Tue–Thu / 08:00–10:00 or 16:00–18:00 America/Bogota), shift-forward rules, and a fail-closed **28 operator-local-day** horizon. US-087 projects `cadence_conflict` on schedule-visibility and warns in the console (implemented/deployed; residual conflicts must still warn).

Today, `schedule_linkedin_distribution` still places slots via:

- `flow_a_staggered` — fixed day offsets from an anchor (`_compute_staggered_schedules`) with preferred-weekday default anchors but **no** cadence feasibility check against published evidence.
- `flow_b_spill_a` — empty-day / week / forward spill under US-040K density (`flow_b_spill_schedule.py`) but **no** cadence shift-forward.

Operators can therefore schedule times that US-087 already marks as cadence-conflicted (or that will refuse at publish-due). **US-088** implements schedule-time prevention so new placements shift forward to feasible slots.

Stakeholders: content operators; n8n/HTTP callers of `POST /schedule-linkedin-distribution`; implementers of US-089 (must reuse the same placement rules later).

Constraints: ADR-0001; ADR-0002; US-020 publish-time guard remains authoritative at send; reuse `CADENCE_MINIMUM_INTERVAL` / shared helpers (US-087 `project_cadence_conflict_at`); no enablement bypass; no LinkedIn API publish from schedule paths; no US-089 replan in this change.

## Goals / Non-Goals

**Goals:**

- Cadence-aware placement for all paths that set LinkedIn `scheduled_at_utc` through `schedule_linkedin_distribution` (`flow_a_staggered` and `flow_b_spill_a`).
- Shift forward when the preferred/candidate slot is cadence-infeasible under US-051/US-020 meaning at that candidate instant.
- Next slot MUST also respect US-040K max 2/local day and existing strategy constraints.
- Prefer US-052 preferred windows while scanning forward.
- Fail closed within 28 operator-local days with a structured error; no infinite scan; no silent infeasible keep.
- Schedule response / campaign metadata / calendar SoT reflect shifted times.
- Preserve US-087 projection semantics for residual conflicts.
- Pytest covering happy-path shift, density interaction, horizon fail-closed, and no LinkedIn API / no enablement mutation.

**Non-Goals:**

- US-089 replan of already-Scheduled conflicts.
- Story accepted / BL-021 closure.
- Publish-time 72h math changes, n8n, cron, OAuth, enablement.
- Redefining cadence conflict to include density / sequence / OAuth / enablement-off.
- Console warning redesign.
- New public HTTP routes (prefer extending existing schedule entry point).

## Decisions

1. **Extend existing schedule entry point — no new route**  
   Implement inside `schedule_linkedin_distribution` / strategy helpers so n8n and Flow B promote/spill keep using `POST /schedule-linkedin-distribution`.  
   - Alternative: new `/shift-forward-schedule` endpoint → rejected; duplicates orchestration and bypasses existing idempotency/CAS.

2. **Reuse US-020 / US-087 cadence semantics — no second engine**  
   Feasibility “not cadence-conflicted” MUST use the same interval and published-evidence collection as publish-time / US-087 (`CADENCE_MINIMUM_INTERVAL`, `project_cadence_conflict_at` or equivalent shared helper). Cadence checks **published** same-campaign evidence at the candidate `scheduled_at_utc` — not density-full, not sequence-alone, not OAuth, not enablement-off.  
   - Alternative: invent schedule-vs-schedule 72h between unpublished siblings → rejected for this story; would invent a second meaning. Sibling separation remains strategy stagger / spill rules; publish-time US-020 remains authoritative once siblings publish.

3. **Placement pipeline: preferred candidate → feasibility gate → shift-forward scan**  
   For each variant in strategy order:
   1. Compute the strategy’s **preferred candidate** (stagger offset from anchor, or next spill-A day/slot).
   2. If feasible (cadence + density + strategy invariants), accept it.
   3. Else scan **forward** for the next feasible slot within the horizon.
   - Never write the infeasible preferred time as `scheduled_at_utc`.

4. **Preferred-window micro-order while shifting (US-052 guidance)**  
   When scanning forward on a local day (and when choosing clock times on preferred days), prefer:
   1. Preferred window on preferred day (morning 08:00–10:00, then afternoon 16:00–18:00 America/Bogota) at a deterministic representative instant (e.g. window start or existing default clock mapped into the window).
   2. If preferred days are exhausted within remaining horizon constraints for that step, continue forward day-by-day still preferring those windows when the day is Tue–Thu; on non-preferred days use a single deterministic default clock consistent with today’s `DEFAULT_PUBLISH_HOUR_UTC` / spill day clock so behavior stays testable.
   - Exact representative minutes MAY match existing code’s default publish clock when already inside a preferred window; do not invent a second timezone SoT — operator TZ for local-day horizon and density remains America/Bogota (gap settings / US-040K helpers as already used).

5. **Horizon counting — honor US-052 ops policy**  
   Original candidate’s operator-local calendar day = **day 0**. Search may use day 0 (at/after candidate clock within window rules) and local days **1…28** inclusive. Do not search past day 28.  
   Structured error code (new): `linkedin_schedule_no_feasible_slot` (distinct from `linkedin_schedule_spill_density_exhausted`).  
   - Alternative: shorter horizon → rejected; user/design prefer US-052 default unless justified otherwise (not justified here).

6. **Density interaction**  
   A slot is infeasible if accepting it would exceed US-040K max 2 for that operator-local day (counting pending/queued/published density members + already-accepted slots in the current schedule batch). Density-full alone is **not** labeled cadence conflict; shift-forward still skips full days. Spill paths that already fail with density exhausted keep that code when the failure mode is purely density with no cadence involvement; when the scan exhausts the **cadence+density+strategy** horizon, use `linkedin_schedule_no_feasible_slot`.

7. **Strategy constraints preserved**  
   - `flow_a_staggered`: preserve audience sequence order; keep minimum **3 calendar days** between consecutive scheduled variants in the campaign after shift (measure between accepted local calendar days / UTC dates consistently with existing stagger intent). If shifting variant *n* forward would violate stagger vs variant *n−1*, continue scanning until stagger + cadence + density hold or horizon fails.  
   - `flow_b_spill_a`: preserve spill order (empty_days → other week days → forward). Cadence shift-forward runs as an additional feasibility filter on candidate days/slots produced by that order (and may advance further forward within horizon when a spill candidate day is cadence-infeasible). Do not invert spill priority.

8. **Multi-variant batch**  
   Place variants sequentially. Each accepted `scheduled_at_utc` occupies density for later siblings in the same request. Cadence evaluation against **published** evidence is recomputed per candidate (evidence does not include unpublished siblings — matches US-020/US-087).

9. **Idempotency / CAS**  
   Keep existing schedule idempotency keys and CAS write path. Shifted times become part of the computed schedule; idempotent re-run with the same inputs must remain stable (deterministic scan). If inputs unchanged and metadata already matches, return idempotent success without rewriting.

10. **No publish / no enablement mutation**  
    Schedule paths MUST NOT call LinkedIn publish adapters and MUST NOT read/write `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` to force-on. Tests assert no publish client calls and enablement env unchanged.

11. **US-087 non-regression**  
    Do not change `project_cadence_conflict_at` meaning or weaken schedule-visibility fields. After successful US-088 placement, residual `cadence_conflict=true` should be rare (race with new publish evidence); when present, warning MUST still apply.

12. **Docs touch**  
    After apply: CURRENT-STATE notes schedule-time shift-forward implemented; light ops policy pointer that US-088 enforces the US-052 scan (without changing window/horizon numbers). Product checklist: Work started / criteria only when demonstrated — no Story accepted by code alone.

## Risks / Trade-offs

- [Risk] Stagger + cadence + density make some campaigns fail closed within 28 days → Mitigation: structured error with clear vocabulary; operators can adjust anchor / wait for US-089 / publish evidence aging; horizon is documented.
- [Risk] Spill-A day order vs preferred-window micro-order ambiguity → Mitigation: spill day order wins for day selection; window micro-order applies to clock choice on an accepted day and when advancing past cadence-blocked days.
- [Risk] Implementers treat unpublished sibling schedules as cadence peers → Mitigation: design + specs lock published-evidence-only meaning; stagger remains the sibling separator.
- [Risk] Duplicate cadence math drifts from publish-time → Mitigation: mandatory reuse of shared helpers / constant; pytest parity with US-087 projection.
- [Risk] Scope creep into US-089 replan → Mitigation: non-goals; tasks forbid replan endpoints/UI.
- [Risk] Silent keep of infeasible preferred time “for later warning” → Mitigation: forbidden; fail closed or shift — never write known cadence-infeasible preferred slot.

## Migration Plan

1. Implement + pytest on Mac after explicit `/opsx-apply` approval.
2. Deploy worker (and any static rebuild only if console touched — not expected) to `192.168.0.194` only with explicit deploy approval.
3. Rollback: revert implementation commit; existing schedules unchanged; no data migration required. New schedules after rollback lose shift-forward until redeployed.
4. Already-Scheduled cadence conflicts remain for **US-089** (US-087 continues to warn).

## Open Questions

- None blocking proposal. Optional later (out of scope): expose horizon via gap operator settings; US-089 replan UX.
