## Context

US-051 ratified cadence conflict as the live US-020 gate (same-campaign **72h** against successful `published` evidence). US-052 documented preferred windows, shift-forward, and a fail-closed **28 operator-local-day** horizon. US-087 projects `cadence_conflict` on schedule-visibility and warns in Silverman Authority Manager. US-088 implements schedule-time prevention in `schedule_linkedin_distribution` via shared `linkedin_schedule_feasibility` (`CADENCE_MINIMUM_INTERVAL` / `project_cadence_conflict_at` / `find_feasible_slot_forward`).

**Gap:** already-Scheduled (`pending`) and Waiting to send (`queued`) items that are cadence-infeasible at their current `scheduled_at_utc` remain on the calendar. Operators can manually postpone via `POST /defer-linkedin-variant` (US-084), but there is no bulk/operator-safe **replan** that selects only cadence conflicts and applies the same US-088 shift-forward engine. US-087 EventModal still says “postpone / wait for later replan” without a shipped replan path.

Stakeholders: content operators; ops curl callers; implementers reusing US-088 helpers.

Constraints: ADR-0001; ADR-0002; US-020 publish-time guard remains authoritative at send; reuse US-088 feasibility module — no second 72h engine; no LinkedIn API publish; no enablement bypass; dry-run default; do not mark Story accepted by code alone.

## Goals / Non-Goals

**Goals:**

- Authenticated worker HTTP replan for cadence-infeasible not-yet-Live LinkedIn variants (`pending` and `queued` when still cadence-tied to `scheduled_at_utc` / publish timing).
- Reuse US-088 shift-forward + density + preferred windows + 28-day horizon via `linkedin_schedule_feasibility`.
- After successful real replan: campaign metadata + calendar/schedule-visibility agree; US-087 warnings clear when the new slot is feasible.
- Dry-run / preview default; real requires explicit confirmation (preview ≠ Live).
- Documented one-shot ops path against the same HTTP endpoint.
- Only conflicted items move; non-conflicting Scheduled items stay put.
- Fail closed with structured errors when no feasible slot; no silent infeasible keep.
- Pytest + optional thin console affordance calling the same endpoint.

**Non-Goals:**

- Story accepted / BL-021 closure.
- Publish-time 72h math, n8n, cron, OAuth, enablement defaults.
- US-087 warning chrome redesign beyond clear-after-success / next-step honesty.
- BL-022 metrics.
- Treating density/sequence/OAuth/enablement as cadence conflict.
- Re-implementing US-088 schedule-time placement for **new** schedules.

## Decisions

1. **New authenticated HTTP endpoint as replan SoT (not extend defer alone)**  
   Add `POST /replan-linkedin-cadence-conflicts` (exact path locked here) with API-key auth, structured JSON body/result, `dry_run` default **true**.  
   Rationale: defer is operator-chosen target time; replan is “select cadence conflicts → compute next feasible via US-088 engine → apply.” Extending defer with auto-target would overload US-084 semantics and risk silent target invention inside postpone UX.  
   - Alternative: only document a Python one-shot script → rejected; ADR-0001 prefers HTTP; US-089 prefers worker HTTP.  
   - Alternative: auto-invoke on schedule-visibility GET → rejected; mutating reads are unsafe.

2. **Selection = US-087 cadence conflict at current `scheduled_at_utc` only**  
   Eligible targets: LinkedIn variants with `publish_state` in `{pending, queued}`, non-null parseable `scheduled_at_utc`, and `project_cadence_conflict_at` / schedule-visibility equivalent **true** at that instant (same meaning as US-087 / US-051).  
   Exclude: `published`, `cancelled`, `failed`, in-flight `publishing`, items without schedule, items that are cadence-feasible.  
   Density-full alone, sequence-alone, OAuth, enablement-off MUST NOT select a variant for replan.  
   Scope filters (request body): optional `campaign_id` and/or explicit `targets[]` of `{campaign_id, variant_id}`; when omitted, scan editorial campaigns for eligible conflicts in a documented deterministic order (campaign id ascending, then variant order as stored).  
   - Alternative: replan all Scheduled items “just in case” → rejected (needlessly moves non-conflicts).

3. **Placement = call US-088 `find_feasible_slot_forward` (no fork)**  
   For each selected target, treat current `scheduled_at_utc` as the preferred/origin candidate. Compute next feasible via `linkedin_schedule_feasibility.find_feasible_slot_forward` (cadence + US-040K density + optional stagger when replan is campaign-scoped with sibling awareness). Prefer US-052 windows while scanning; horizon = 28 operator-local days from the **current** slot’s local day as day 0 (same counting as US-088 / US-052).  
   If the current slot is somehow already feasible at apply time (race), leave it unchanged and report `unchanged` / skipped-not-conflicted — do not invent a later move.  
   If no feasible slot within horizon → fail that target with `linkedin_schedule_no_feasible_slot` (or replan-scoped alias that maps to the same operator meaning); MUST NOT write the infeasible time as “success.”  
   - Alternative: invent schedule-vs-schedule 72h between unpublished siblings → rejected (second meaning; US-088 already rejected this). Sibling separation remains existing stagger/defer rules where enforced; published-evidence cadence remains the conflict gate.

4. **Apply semantics mirror defer schedule fields (pending vs queued)**  
   On successful **real** apply for a target:  
   - Update `scheduled_at_utc` to the new feasible UTC.  
   - If `queued`: keep `publish_state` `queued`; align `publish_after_utc` with the new schedule (same as US-084 defer).  
   - If `pending`: keep `pending`; preserve existing auto-queue / supervision field conventions (set `last_action` to a replan-specific value e.g. `replan_cadence` and append a short history entry — may reuse deferral_history shape or a sibling `replan_history` list; prefer one audit list with `action` discriminant to avoid dual SoTs).  
   - MUST NOT call LinkedIn API; MUST NOT change enablement.  
   - Atomic per-campaign metadata write (reuse existing campaign CAS / write helpers used by defer/schedule).  
   Dry-run: compute proposed moves; return preview payload; **zero** metadata mutation.

5. **Batch order and density occupancy**  
   Process selected targets in deterministic order (earliest current `scheduled_at_utc`, then campaign_id, then variant_id). Each accepted real (or preview-accepted) new slot occupies density `planned_counts` for later targets in the same request — matching US-088 multi-variant batch behavior. Cadence checks remain against **published** evidence only (plus density/strategy).  
   Partial success policy: **fail closed for the request when any selected target cannot be placed** after computing the full plan — prefer all-or-nothing apply for real mode once the plan is validated (preview always returns the full plan including per-target errors). Rationale: avoids leaving a half-fixed calendar that looks “done.” If CAS conflict mid-apply, abort remaining and report structured partial/conflict error; do not invent silent retries that publish.  
   - Alternative: best-effort partial apply → rejected for v1 (harder operator mental model; silent partial keep risk).

6. **Console: thin optional affordance; warning clear via refresh**  
   Minimum product path: authenticated HTTP + documented curl/ops.  
   Console SHOULD expose a deliberate **Replan cadence conflicts** control (EventModal when `cadence_conflict` true, and/or a bulk ops entry) that calls the new endpoint with Preview vs Make real (US-083 honesty). After successful real replan, refresh schedule-visibility; Week/Month indicators clear when `cadence_conflict` is false at the new slot. Update EventModal next-step copy so it no longer implies replan is only “later / not shipped.”  
   MUST NOT redesign the red warning chrome itself.  
   - Alternative: console-only filesystem patch → rejected (ADR-0001 / no browser SoT).

7. **No publish / no enablement mutation**  
   Replan paths MUST NOT call LinkedIn publish adapters and MUST NOT force-on `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. Tests assert no publish client calls and enablement env unchanged.

8. **Ops documentation**  
   After apply: short ops pointer (CURRENT-STATE + ops policy note) with curl example for dry-run then real (`dry_run=false` + explicit confirm header or body flag consistent with existing worker patterns). No n8n Execute Command.

9. **Docs touch**  
   CURRENT-STATE notes US-089 replan implemented; light ops policy pointer that US-089 owns executable replan; product checklist Work started / criteria only when demonstrated — no Story accepted by code alone.

## Risks / Trade-offs

- [Risk] All-or-nothing frustrates when one of many conflicts cannot place → Mitigation: preview lists per-target errors first; operator can narrow `targets[]` / wait for evidence aging / manual defer.
- [Risk] Concurrent defer/publish races mid-replan → Mitigation: CAS on campaign metadata; re-check cadence eligibility at apply; structured conflict error; no silent overwrite without CAS.
- [Risk] Implementers fork 72h math → Mitigation: mandatory import from `linkedin_schedule_feasibility` / publication helpers; pytest parity with US-087 projection.
- [Risk] Queued replan accidentally returns to pending → Mitigation: specs lock queued keep; mirror defer apply fields.
- [Risk] Scope creep into metrics / Story accepted → Mitigation: non-goals; tasks forbid checklist Story accepted.
- [Risk] Silent keep of infeasible current time marked success → Mitigation: forbidden; fail closed or shift — never claim success while still cadence-conflicted at written slot unless race documented as unchanged-not-conflicted.

## Migration Plan

1. Implement + pytest on Mac after explicit `/opsx-apply` approval.
2. Optional console static rebuild if thin affordance ships.
3. Deploy worker (+ static if needed) to `192.168.0.194` only with explicit deploy approval.
4. Operator dry-run against live conflict set (or fixture), then confirmed real replan.
5. Rollback: revert implementation commit; existing schedules unchanged; no data migration required. After rollback, US-087 continues to warn; manual defer remains available.

## Open Questions

- None blocking proposal. Optional later (out of scope): unattended cron replan; gap-settings-tunable horizon for replan only.
