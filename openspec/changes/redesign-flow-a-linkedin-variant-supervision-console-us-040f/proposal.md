## Why

US-040A–E delivered a capable Flow A LinkedIn variant supervision console (stack, dual views, ScheduleEditor, auth readiness, counts/safety polish), but the operator-facing surface still read too much like a technical status page. A console-layer UX redesign (US-040F) was implemented in the working tree before an OpenSpec change existed, and main specs were updated ahead of a change archive. This change **restores OpenSpec continuity** without rewriting A–E sources of truth.

**Retroactive OpenSpec alignment.** The redesign is already demonstrated in the frontend working tree. This change restores authority hierarchy: proposal → design → delta specs → tasks → verify → implementation commit → sync (parity with main) → archive. It does not invent a parallel product surface.

**Honest UX status:** the first redesign pass improves scanability and app-shell structure, but further UX iteration is expected. This change MUST NOT mark US-040F Story accepted or BL-015 closed.

## Goals

- Restore OpenSpec authority for US-040F (artifacts + archive trail after E).
- Record the delivered redesign contract: modern dark operational shell, interactive metrics, card triage + detail drawer, calendar remaining schedule-first, technical prose secondary.
- Preserve US-040A–E worker HTTP / ScheduleEditor / session / `canMutate` baselines.
- Keep qualified publication language (`pending` / `queued` / `cancelled` / `flow_a_complete` / blog handoff ≠ LinkedIn API published).
- Leave browser screenshot matrix and deeper UX polish as follow-ups when the operator accepts the visual direction.

## Non-Goals

- Public URL hosting / Google OIDC activation.
- BFF/DB/user-management; LinkedIn API publish; enablement bypass; Flow B.
- Closing BL-015 or marking Story accepted from this change alone.
- Rewriting US-040A–E mutation or auth SoT.
- Claiming final UX product-quality acceptance while further redesign discussion continues.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (US-040F) | Remains open |
| **US-040F** | Yes | Modern operational UX redesign; Story not accepted from apply alone |
| **US-040A–E** | Preserve | Stack, views, mutations, auth readiness, E polish |
| **Further UX passes** | Follow-up | Expected after operator review |

## What Changes

- OpenSpec change artifacts authorizing the US-040F redesign already present in the console frontend.
- Metric focus semantics clarified (reset focus flags, then apply target filter).
- List schedule display labels UTC vs local clearly.
- Product docs / CURRENT-STATE remain honest: implemented console-layer redesign; not Story accepted; BL-015 open; UX iteration may continue.
- Main `openspec/specs/linkedin-variant-supervision-console` US-040F requirements treated as parity with this delta (sync confirms, does not invent a second contract).

## Impact

- **Product:** Advances BL-015 / US-040F documentation authority; BL-015 stays open.
- **Frontend:** Existing redesign + small filter/time clarity fixes; Vite optional LAN worker proxy for local preview only.
- **Worker:** No new mutation SoT.
- **Deploy:** Separate explicit approval after UX direction is closer to expectation.
