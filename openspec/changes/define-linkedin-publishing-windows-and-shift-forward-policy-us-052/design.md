## Context

US-051 delivered the normative LinkedIn cadence spacing policy and the shared **cadence conflict** definition (US-020 publish-time gate at `scheduled_at_utc` / proposed slot — not density-full alone, not OAuth, not enablement-off; sequence remains distinct). Editorial canon already lists preferred days/windows and audience sequencing under `#linkedin-distribution-strategy`, but BL-021 / **US-052** still lacks an operator-facing **ops policy** that binds those windows to **shift-forward** when a candidate slot is cadence-infeasible, plus fail-closed bounds for “no feasible slot.”

US-088 will implement executable shift-forward in `schedule-linkedin-distribution` / spill paths; US-087 will warn on residual conflicts; US-089 will replan already-Scheduled conflicts. This change is **documentation/policy only** so those stories consume one written rule set.

Stakeholders: editorial manager / content operator; implementers of US-088 (primary consumer), US-087 (residual warning), US-089 (reuse same placement rules).

Constraints: ADR-0001; ADR-0002 (blog canonical; LinkedIn variants are distribution assets); US-020 / BL-007 stay closed and authoritative at send; US-051 cadence conflict meaning unchanged; no application code, console UI, cron, n8n, OAuth, or enablement changes in this change.

## Goals / Non-Goals

**Goals:**

- Normative ops policy for preferred LinkedIn publishing windows (local-day / clock guidance) at strategy level.
- Strategy-level audience balancing (existing editorial sequencing); packaging ownership remains Flow A.
- Normative shift-forward rules: cadence-infeasible candidate → next feasible slot (also US-040K max 2/local day + existing distribution strategy constraints); MUST NOT silently keep an infeasible time.
- Residual cadence-conflict after placement still requires US-087 warning.
- Fail-closed bounds for “no feasible slot” documented for US-088.
- Capability contracts + CURRENT-STATE / editorial pointers; US-052 Story accepted remains an operator gate.

**Non-Goals:**

- US-087 warning UI, US-088 schedule-time code, US-089 replan.
- Worker cadence math, env defaults, n8n, cron, OAuth, enablement.
- Second cadence engine or disagreeing 72h constant.
- Supersession of US-040K density or BL-019 gap.
- New HTTP endpoints.

## Decisions

1. **Docs-only / policy-first for US-052** — Match US-051 pattern: written rules now; executable placement is US-088.
   - Alternative: ship US-052 + US-088 together → rejected for this proposal (user scope locks US-052 only; progress-checklist apply order still US-051 → US-087 → US-088 → US-089 with US-052 policy as US-088 prerequisite).

2. **Sibling ops policy** — Canonical path: `docs/operations/linkedin-publishing-windows-and-shift-forward-policy.md`. Keep US-051 spacing/conflict doc focused; cross-link both ways.
   - Alternative: only extend `linkedin-cadence-spacing-policy.md` → workable but mixes spacing ratification with windows/reschedule; sibling keeps BL-021 story boundaries clear.
   - Apply MAY add a short section pointer inside the US-051 doc replacing “deferred to US-052.”

3. **Single new capability `linkedin-publishing-windows-and-shift-forward-policy`** — Documentation contracts (scenarios verify policy presence and normative statements, not HTTP). Light **MODIFIED** delta on `linkedin-cadence-spacing-policy` so frequency language no longer leaves windows permanently deferred.
   - Alternative: only expand spacing capability → rejected; US-052 is a distinct story and consumer surface for US-088.

4. **Preferred windows source** — Normative ops policy **adopts** editorial canon guidance without inventing a new clock math engine:
   - Preferred local days: **Tuesday, Wednesday, Thursday**
   - Preferred local clock windows: **08:00–10:00** or **16:00–18:00**
   - Operator timezone: **America/Bogota**
   - Cross-link `content-strategy/silverman-editorial-system.md` `#linkedin-distribution-strategy`.
   - Schedule-intent stagger (≥3 calendar days) remains planning guidance; publish-time **72h** / US-020 remains authoritative at send (US-051).

5. **Feasible slot definition (for shift-forward consumers)** — A candidate slot is **feasible** only when **all** hold:
   - **Not cadence-conflicted** under the US-051/US-020 meaning at that `scheduled_at_utc` (or proposed slot).
   - **Density capacity** remains under interim US-040K max **2** publications per operator-local day.
   - **Existing distribution strategy constraints** for the path in use remain satisfied (e.g. `flow_a_staggered` stagger / empty-day rules; Flow B `flow_b_spill_a` spill order as applicable).
   - Prefer placing inside preferred days/windows when scanning forward; US-088 MAY document a ordered preference (preferred window on preferred day → other clock on preferred day → next preferred day, etc.) as long as it does not contradict this policy.

6. **Shift-forward direction** — When the preferred/candidate slot is cadence-infeasible, the system MUST move **forward in time** to the next feasible slot. MUST NOT keep the infeasible `scheduled_at_utc` as if it will send. MUST NOT invent a second 72h constant or reimplement publish-time guard logic as a competing engine — reuse US-051/US-020 conflict semantics for feasibility checks at schedule time (US-088).

7. **Fail-closed search bounds (policy default for US-088)** — Finite forward search; no infinite scan; no silent infeasible placement.
   - **Default horizon:** **28 operator-local days** measured from the original candidate local day (inclusive of that day as day 0 for counting subsequent days, or equivalent documented inclusive/exclusive rule stated in the ops policy so US-088 is unambiguous).
   - If no feasible slot exists within the horizon: scheduling MUST **fail closed** with a structured, operator-visible error (exact code/shape owned by US-088).
   - A later approved OpenSpec change MAY adjust the numeric horizon; until then, **28 local days** is the documented default bound.
   - Density-full alone is **not** cadence conflict (US-051); shift-forward still MUST respect density when choosing the next slot.

8. **Residual conflict + US-087** — If after placement an item remains cadence-conflicted (edge case: race with newly published evidence, partial placement, operator override outside automation, etc.), the console MUST still show the US-087 warning. This change does not implement the warning; it binds the obligation for US-087/US-088 consumers.

9. **Audience balancing** — Strategy-level only: cite existing audience sequencing / lens rules in editorial canon (`#audience-map`, `#linkedin-distribution-strategy`). Variant **packaging** remains Flow A (`generate-linkedin-package` / derivative package generation). MUST NOT move packaging ownership to Flow B or invent a P4 audience balancer.

10. **No new endpoints** — Docs-only; ADR-0001 unchanged. US-088/US-087/US-089 open their own approved changes for HTTP/UI.

## Risks / Trade-offs

- [Risk] Implementers treat preferred windows as a second publish-time cadence engine → Mitigation: policy restates US-020/US-051 authority at send; windows are placement guidance only.
- [Risk] 28-day horizon is too short/long for some campaigns → Mitigation: documented default; later approved change MAY adjust; fail-closed is required either way.
- [Risk] Shift-forward vs spill-A day order ambiguity → Mitigation: policy requires respecting existing strategy constraints; US-088 design decides algorithm detail within those bounds.
- [Risk] Operators confuse density-full fail-closed with cadence conflict → Mitigation: blocked-state vocabulary distinguishes density vs cadence vs no-feasible-slot.
- [Risk] Proposal treated as Story accepted → Mitigation: progress checklist Work started only after docs exist; Story accepted / BL-021 unchecked pending operator review.
- [Risk] Scope creep into US-088 code → Mitigation: tasks forbid `src/` schedule/cadence edits; non-goals explicit.

## Migration Plan

1. Apply doc + capability artifacts on Mac branch after explicit approval + `/opsx-apply`.
2. No deploy required for capability; optional doc sync on server is operator preference.
3. Rollback: revert change commit; no data migration; no runtime flag changes.

## Open Questions

- None blocking this docs slice. Exact US-088 structured error codes, scan micro-order inside a local day, and whether operator settings later expose the horizon remain for US-088 (must honor this policy’s defaults until a later approved change supersedes them).
