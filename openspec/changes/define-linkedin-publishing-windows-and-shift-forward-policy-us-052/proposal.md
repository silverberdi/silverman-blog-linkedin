## Why

US-051 ratified LinkedIn cadence spacing and the shared “cadence conflict” meaning, but operators still lack written **preferred publishing windows** and **shift-forward reschedule rules** for when a candidate `scheduled_at_utc` is cadence-infeasible. Without that policy, US-088 (and residual US-087 warning) cannot place or warn consistently, and calendars risk keeping infeasible times as if they will send.

## What Changes

- Publish an operator-facing **publishing windows + shift-forward** policy under `docs/operations/` (sibling to the US-051 cadence spacing policy, with cross-links) that US-088 / residual US-087 consume.
- Introduce capability `linkedin-publishing-windows-and-shift-forward-policy` as documentation/policy contracts (no schedule-time executable code, console warning UI, or worker cadence math in this change).
- Cross-link editorial preferred windows from `content-strategy/silverman-editorial-system.md` `#linkedin-distribution-strategy` (Tue–Thu; 08:00–10:00 or 16:00–18:00 America/Bogota) without changing publish-time 72h math.
- Light update to `linkedin-cadence-spacing-policy` docs/capability so “preferred windows deferred to US-052” becomes a pointer to the new normative policy.
- CURRENT-STATE (and editorial pointers as needed) so operators can open the written rules; leave US-052 / BL-021 Story accepted unchecked until operator review after apply.

### Goals

- Satisfy **BL-021 / US-052** acceptance criteria as documentation/policy (Story accepted still requires operator review after apply).
- Lock preferred LinkedIn publishing windows (local-day / clock guidance) at strategy level for variant placement.
- Lock audience-segment balancing at strategy level (variant packaging remains Flow A).
- Lock shift-forward reschedule rules: cadence-infeasible candidate → next feasible slot (also US-040K max 2/local day + existing distribution strategy constraints); MUST NOT silently keep an infeasible time.
- State residual cadence-conflict edge case still requires the US-087 console warning.
- Define fail-closed bounds for “no feasible slot” at policy level (US-088 enforces).
- Preserve US-020 / BL-007 publish-time cadence guard unchanged; no second cadence engine or disagreeing 72h constant.

### Non-goals

- Console cadence-conflict warning UI (**US-087**).
- Schedule-time shift-forward code in `schedule-linkedin-distribution` / spill paths (**US-088**).
- Replan already-Scheduled conflicts (**US-089**).
- Worker cadence math, env defaults, n8n, LinkedIn publish-due cron, OAuth, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` changes.
- Moving audience packaging ownership out of Flow A.
- Superseding US-040K density or BL-019 gap unless explicitly decided (this change does **not** supersede them).
- Marking US-052 / BL-021 Story accepted or closing BL-021 by this proposal/apply alone.
- Weakening, duplicating, or reimplementing the US-020 / BL-007 publish-time cadence guard.

### Acceptance criteria addressed

| US-052 criterion | How this change addresses it |
|---|---|
| Preferred publishing windows (local-day / clock) at strategy level | Normative ops policy + capability requirements; cross-link editorial `#linkedin-distribution-strategy` |
| Balance audience segments at strategy level; packaging stays Flow A | Policy cites existing audience sequencing in editorial canon; packaging ownership unchanged |
| Shift-forward when cadence-infeasible; respect density + strategy; no silent infeasible keep | Normative reschedule rules + fail-closed bounds for US-088 |
| Residual cadence-conflict still shows US-087 warning | Explicit edge-case requirement in policy/capability |
| Outcome visible to operators | Ops policy + CURRENT-STATE / editorial pointers |
| Failures / blocked states clearly communicated | Policy vocabulary for no-feasible-slot vs cadence conflict vs density-full (distinct) |
| No duplicate / weaken of existing completed work | Docs-only; US-020 guard untouched; US-051 conflict definition reused |

### Intentionally excluded

- Executable placement / shift-forward in worker schedule paths (US-088).
- Console warning UI and projection fields (US-087).
- Replan of existing Scheduled conflicts (US-089).
- Any runtime enforcement beyond documenting bounds US-088 MUST honor later.

## Capabilities

### New Capabilities

- `linkedin-publishing-windows-and-shift-forward-policy`: Operator-visible normative preferred LinkedIn publishing windows, strategy-level audience balancing (packaging remains Flow A), shift-forward reschedule rules when a candidate slot is cadence-infeasible, residual US-087 warning obligation, and fail-closed “no feasible slot” bounds for US-088 — without implementing schedule-time code or changing US-020 publish-time 72h math.

### Modified Capabilities

- `linkedin-cadence-spacing-policy`: Replace “preferred windows deferred to US-052” with a normative pointer to the US-052 publishing-windows / shift-forward policy artifact; do not change US-020 spacing, cadence-conflict definition, density/gap coexistence, or 72h constant.

## Impact

- **Product:** Advances **BL-021 / US-052** only; leaves US-087–US-089 and BL-021 open; does not mark Story accepted by proposal alone.
- **Docs:** New (or extended) ops policy under `docs/operations/`; CURRENT-STATE capability-language pointer; cross-links from US-051 cadence spacing policy and content-strategy preferred windows.
- **OpenSpec:** New capability under `openspec/specs/` after sync; light MODIFIED delta on `linkedin-cadence-spacing-policy`; no delta that rewrites publish-time guard requirements.
- **Worker / n8n / Docker / cron / enablement / console:** No runtime behavior changes in this change.
- **Preserved:** US-020 / BL-007 closed contracts; US-051 cadence conflict meaning; US-040K density; BL-019 gap trigger; ADR-0001; ADR-0002; Flow A packaging ownership.
