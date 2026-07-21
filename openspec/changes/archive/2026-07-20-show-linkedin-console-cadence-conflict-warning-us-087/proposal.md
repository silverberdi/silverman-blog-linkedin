## Why

Operators can see LinkedIn items as **Scheduled** (or Waiting to send) on Silverman Authority Manager even when that slot would hit the live US-020 cadence gate (`linkedin_publish_blocked_cadence` / related cadence skip). Without a clear visual cue, “Scheduled” is easily mistaken for “will send at that time.” US-051 already defines cadence conflict; US-087 is the console warning so residual infeasible slots stay honest before US-088 shift-forward and US-089 replan.

## What Changes

- Week and Month views show a **red (or equivalent) cadence-conflict warning indicator** on LinkedIn-channel items whose current `scheduled_at_utc` is cadence-infeasible under the US-051 / US-020 meaning (same gate as live cadence refuse/skip at that slot).
- EventModal (or equivalent detail) explains the conflict in **plain language** with a **usable next step** (e.g. earliest feasible time from same-campaign `published_at + 72h`, and/or postpone / wait for replan).
- Warning remains **distinct** from Failed / Cancelled / Waiting to send / Live on LinkedIn, and MUST NOT mean density-full alone, OAuth, enablement-off, or sequence-alone.
- Cadence-feasible items MUST NOT show the cadence-conflict warning.
- If the console needs truth for the indicator, expose **additive authenticated schedule-visibility fields** via worker HTTP (no browser filesystem SoT; ADR-0001). Reuse US-020 cadence semantics — do not invent a second 72h engine or weaken publish-time evaluation.
- Capture **Visual DoD** evidence expectations (desktop + mobile) for conflict chips + EventModal explanation.

## Goals

- Satisfy **US-087** acceptance criteria in `docs/product/user-stories.md`.
- Keep BL-032 control-center labels (US-083–US-086) intact; no second publish pipeline; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` untouched.
- Leave US-020 publish-time cadence guard authoritative at send.
- Prefer shipping US-087 before / with US-088 so residual edge conflicts stay visible after schedule-time shift-forward (US-052 residual obligation — docs already written; do not implement US-088 here).

## Non-goals

- **US-052** Story accepted / **BL-021** closure.
- **US-088** schedule-time shift-forward implementation.
- **US-089** replan of already-Scheduled conflicts.
- Changing publish-time 72h cadence evaluation, n8n, cron, OAuth, or enablement.
- Treating density-full, sequence-alone, OAuth, or enablement-off as cadence conflict.
- Browser filesystem SoT or n8n Execute Command (ADR-0001).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `linkedin-variant-supervision-console`: add Week/Month cadence-conflict visual warning and EventModal plain-language explanation + next step for not-yet-Live LinkedIn items; extend authenticated `GET /flow-a/schedule-visibility` (and shared model / typed client) with additive cadence-conflict projection fields when needed; preserve BL-032 status vocabulary and distinctness from density / Failed / Cancelled / Waiting to send / Live.

## Impact

- Worker: `flow_a_schedule_visibility` (+ shared reuse of US-020 cadence interval semantics from publication guard code); pytest for projection accuracy and non-mutation.
- Frontend: Week/Month chips, EventModal copy, shared model / DTO types, Vitest; static console rebuild.
- Specs: delta under `openspec/specs/linkedin-variant-supervision-console/`.
- Docs after implementation (not proposal-only): `docs/CURRENT-STATE.md` when capability lands; product checklist/story progress only when criteria are demonstrated.
- **No** LinkedIn API publish from this change; **no** enablement bypass; **no** US-088/US-089 placement or replan routes.

## Related backlog / stories

- **BL-021** — Define Editorial Calendar and Publishing Cadence
- **US-087** — Show Cadence Conflicts Visually in the LinkedIn Console (this change only)
- Prerequisites: **US-051** cadence-conflict definition (policy defined)
- Apply order: US-051 → **US-087** → US-088 → US-089
- Addresses all US-087 acceptance criteria listed in `docs/product/user-stories.md`
- Intentionally excluded: US-052 Story accepted, US-088, US-089, BL-021 closure, publish-time guard changes
