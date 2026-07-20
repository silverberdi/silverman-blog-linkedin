## Why

Calendar, scheduler, and console operators do not yet share one written meaning of LinkedIn cadence spacing that matches the worker’s already-enforced US-020 publish-time guard. BL-021 / US-051 must ratify that meaning now so US-087–US-089 (warning, shift-forward, replan) consume one definition of “cadence conflict” instead of inventing a second cadence engine or weakening the live 72h guard.

## What Changes

- Publish an operator-facing LinkedIn cadence spacing / frequency policy under `docs/operations/` that ratifies US-020 as the normative same-campaign 72h rule and defines “cadence conflict” for later BL-021 stories.
- Introduce capability `linkedin-cadence-spacing-policy` as documentation/policy contracts (no worker cadence math, routes, cron, or console UI in this change).
- Cross-link CURRENT-STATE (and prerequisites/glossary as needed) so operators can open the shared meaning; leave US-051 / BL-021 Story accepted unchecked until operator review after apply.

### Goals

- Satisfy **BL-021 / US-051** acceptance criteria as documentation/policy (Story accepted still requires operator review after apply).
- Lock one shared meaning of LinkedIn campaign spacing, frequency planning, blog frequency (strategy-level), density/gap coexistence, and “cadence conflict” for US-087 → US-088 → US-089.
- Preserve US-020 / BL-007 publish-time cadence behavior unchanged.

### Non-goals

- Console cadence-conflict warning UI (**US-087**).
- Schedule-time shift-forward mechanics (**US-088**) or replan of already-Scheduled conflicts (**US-089**).
- Full **US-052** publishing windows / rescheduling policy (may sketch only if needed for US-051 clarity).
- Worker cadence math, env defaults, n8n, LinkedIn publish-due cron, OAuth, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` changes.
- Weakening, bypassing, or reimplementing a second cadence constant that disagrees with the worker.
- BL-020 editorial backlog, BL-022 metrics, Flow B runtime changes.
- BL-032 control-center work except as future consumers of the conflict definition.
- Marking US-051 / BL-021 Story accepted or closing BL-021 by this proposal/apply alone.
- Sequence-conflict UX (sequence remains **distinct** from cadence conflict unless a later story expands).

### Acceptance criteria addressed

| US-051 criterion | How this change addresses it |
|---|---|
| Ratify US-020 72h same-campaign spacing; cross-campaign independence | Normative ops policy + capability requirements cite publish-time `published` + evidence rule; no second engine |
| LinkedIn frequency planning ≈ ~2/local day | Reaffirm US-040K density as the default fill assumption (not superseded) |
| Blog frequency at strategy level | Document strategy expectations; no blog cadence automation |
| US-040K density + BL-019 gap as interim coexisting controls | Explicit density ≠ cadence 72h; gap trigger does not bypass cadence |
| Define “cadence conflict” for console/scheduler stories | Same gate as live `linkedin_publish_blocked_cadence` / related auto-queue cadence skip at `scheduled_at_utc` (or proposed slot) |
| Outcome visible to operators | Ops policy + CURRENT-STATE pointer |
| Failures/blocked states clearly communicated | Policy language for cadence vs density vs enablement vs OAuth vs sequence |
| No duplicate/weaken of US-020 / BL-007 | Docs-only; no `src/` cadence changes |

### Intentionally excluded

- US-052 executable windows / shift-forward policy (follow-on).
- US-087 / US-088 / US-089 implementation.
- Any runtime enforcement beyond what US-020 already does at publish/auto-queue time.

## Capabilities

### New Capabilities

- `linkedin-cadence-spacing-policy`: Operator-visible ratification of LinkedIn campaign spacing (US-020 72h), frequency planning assumptions, blog frequency strategy expectations, interim coexistence with US-040K density and BL-019 gap trigger, and the normative “cadence conflict” definition consumed by later BL-021 stories — without changing publish-time guard behavior.

### Modified Capabilities

- (none — documentation/policy capability; existing `linkedin-publication-integration` US-020 requirements remain authoritative and unchanged)

## Impact

- **Product:** Advances **BL-021 / US-051** only; leaves US-052, US-087–US-089, and BL-021 open.
- **Docs:** New ops policy under `docs/operations/`; CURRENT-STATE capability-language pointer; light cross-links from prerequisites / glossary / product trio as needed after apply.
- **OpenSpec:** New capability under `openspec/specs/` after sync; no delta to publish-time guard specs.
- **Worker / n8n / Docker / cron / enablement:** No runtime behavior changes in this change.
- **Preserved:** US-020 / BL-007 closed contracts; US-040K density; BL-019 gap trigger; ADR-0001; sequence vs cadence distinction.
