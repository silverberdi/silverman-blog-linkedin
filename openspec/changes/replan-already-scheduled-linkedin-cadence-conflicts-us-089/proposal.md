## Why

US-087 already warns when not-yet-Live LinkedIn items are cadence-infeasible at their current `scheduled_at_utc`, and US-088 prevents **new** placements from landing on those times — but existing Scheduled (`pending`) and Waiting to send (`queued`) items that already conflict still sit on the calendar as send times the automatic publisher will refuse. Operators need a safe, authenticated replan path that moves only those conflicts forward with the same shift-forward engine, so this week’s calendar matches what can actually send.

## What Changes

- Add an operator-safe, **authenticated worker HTTP** replan entry point (primary SoT) that selects already-scheduled LinkedIn variants that are **cadence-infeasible** at their current slot (`pending`, and `queued` when still cadence-tied to `scheduled_at_utc` / publish timing) and shifts them forward to the next **feasible** slot.
- Replan MUST **reuse** US-088 placement rules via `linkedin_schedule_feasibility` / `CADENCE_MINIMUM_INTERVAL` / `project_cadence_conflict_at` (and the same density + strategy + preferred-window + 28 operator-local-day horizon behavior). MUST **NOT** invent a second 72h cadence engine.
- After successful real replan: campaign schedule metadata and calendar / schedule-visibility SoT update consistently; **US-087** `cadence_conflict` warnings **clear** when the new slot is feasible.
- **Dry-run / preview** MUST be available and SHOULD default on; real replan requires explicit confirmation semantics consistent with console patterns (preview ≠ Live / ≠ LinkedIn API published).
- Document a one-shot ops/curl path against the same HTTP endpoint (ADR-0001; no n8n Execute Command).
- Optional thin console affordance MAY call the same endpoint (EventModal / ops action); MUST NOT redesign US-087 warning UI beyond clearing after successful replan and updating “wait for replan” next-step copy when replan exists.
- Replan MUST **NOT** call LinkedIn API publish and MUST **NOT** bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Non-conflicting Scheduled items MUST **NOT** be needlessly moved; failures / no-feasible-slot MUST fail closed with clear structured communication (no silent infeasible keep).

## Goals

- Satisfy **BL-021 / US-089** acceptance criteria in `docs/product/user-stories.md`.
- Make already-Scheduled cadence conflicts operator-fixable without inventing a second cadence meaning.
- Keep US-020 publish-time cadence authoritative at send; keep US-087 projection authoritative for residual conflicts.
- Demonstrate on live conflict set or equivalent fixture: conflicted items shift; non-conflicted stay put.

## Non-goals

- Marking **US-089** / **US-088** / **US-087** / **US-051** / **US-052** / **BL-021** Story accepted or closing BL-021 by this change alone.
- Changing publish-time US-020 cadence math, n8n, LinkedIn publish-due cron, OAuth, or enablement defaults.
- Redesigning US-087 warning UI beyond clear-after-success / next-step honesty.
- Expanding into **BL-022** metrics.
- Treating density-full, sequence-alone, OAuth, or enablement-off as “cadence conflict.”
- A second cadence engine or disagreeing 72h constant.
- Browser filesystem SoT or n8n Execute Command (ADR-0001).

## Acceptance criteria addressed

| US-089 criterion | How this change addresses it |
|---|---|
| Operator-safe authenticated replan for cadence-infeasible pending/queued | Authenticated worker HTTP (+ documented ops path); updates campaign schedule metadata + calendar SoT |
| Same shift-forward + density rules as US-088; no second engine | Reuse `linkedin_schedule_feasibility` / shared cadence helpers |
| After success, slots move; US-087 warnings clear when feasible | Metadata + schedule-visibility refresh; projection false at new slot |
| Dry-run / preview available (or default); real needs confirmation | `dry_run` default true; console/ops confirmation for real |
| No LinkedIn API publish; no enablement bypass | Explicit non-mutation of publish path / enablement |
| Conflicted items shift; non-conflicting not needlessly moved | Select only cadence-conflicted targets; leave others unchanged |
| Outcome visible; failures clear | Structured result + error codes; no silent infeasible keep |
| No duplicate / weaken completed work | Do not reopen US-020/US-087/US-088 semantics |

## Intentionally excluded

- Story accepted / BL-021 closure.
- Publish-time guard, n8n, cron, OAuth, enablement changes.
- BL-022 metrics.
- Broad US-087 UI redesign.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `linkedin-distribution-scheduling-model`: add authenticated replan of already-scheduled cadence-infeasible LinkedIn variants (pending/queued), reusing US-088 shift-forward feasibility; dry-run default; fail-closed horizon; no LinkedIn API publish / no enablement bypass; only conflicted items move.
- `linkedin-publishing-windows-and-shift-forward-policy`: light MODIFIED pointer that executable **replan** of already-Scheduled conflicts is owned by this change (US-089), without rewriting preferred-window or horizon policy numbers.
- `linkedin-variant-supervision-console`: after successful replan, calendar/US-087 warnings clear when feasible; dry-run vs real honesty if a console affordance is included; MUST NOT redesign warning chrome beyond clear-after-success / next-step honesty.

## Impact

- **Worker:** new replan service (likely beside supervision/schedule modules) calling `linkedin_schedule_feasibility.find_feasible_slot_forward` (or equivalent shared API); campaign metadata CAS/write for `scheduled_at_utc` / related publish-timing fields (`publish_after_utc` for queued as today defer does); authenticated HTTP route; pytest for select-only-conflicts, shift reuse, dry-run non-mutation, horizon fail-closed, no publish/enablement mutation.
- **HTTP:** new authenticated replan endpoint (name finalized in design); dry_run default true.
- **Console (optional thin):** typed client + EventModal/ops control calling the same endpoint; Week/Month refresh clears cadence indicators when feasible.
- **Docs after implementation:** CURRENT-STATE capability language; ops policy pointer that US-089 enforces replan; product checklist/story progress only when criteria are demonstrated.
- **Preserved:** US-020 / BL-007 publish-time guard; US-051 cadence conflict meaning; US-052 windows + 28-day horizon; US-087 projection; US-088 schedule-time shift-forward; US-040K density; ADR-0001; ADR-0002.

## Related backlog / stories

- **BL-021** — Define Editorial Calendar and Publishing Cadence
- **US-089** — Replan Already-Scheduled LinkedIn Variants That Conflict With Cadence (this change)
- Prerequisites (already shipped; do not re-implement): **US-051**, **US-052**, **US-087**, **US-088**
- Apply order: US-051 → US-087 → US-088 → **US-089**
