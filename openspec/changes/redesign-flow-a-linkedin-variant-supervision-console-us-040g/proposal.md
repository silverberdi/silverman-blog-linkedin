## Why

Operator review after US-040F rejected list-first triage and empty/unexplained list landings as the mental model for Flow A LinkedIn supervision. Operators need to grasp “what publishes this week” in seconds from a calendar product surface. US-040G (BL-015) makes the console **calendar-first**: Week as default home, Month as secondary density view, and List removed from operator chrome — without dropping prior supervision capabilities or closing BL-015 from implementation alone.

## Goals

- Replace list-first UX with Week (default) + Month (secondary) as the only first-class views.
- Remove List from operator chrome (no List tab, no list landing, no empty list as home).
- Preserve prior edit / defer / cancel / schedule capabilities via calendar entry points (temporary detail/ScheduleEditor path until US-040H event modal).
- Deliver intentional empty week/month states and a modern, responsive operational calendar UX.
- Encode Shared UX DoD: Visual DoD evidence + operator walkthrough required before Story accepted; Vitest alone insufficient.
- Preserve React + TypeScript + Vite, same-origin static assets, typed API client, shared model, ScheduleEditor SoT, session/`canMutate`, worker HTTP only (ADR-0001).

## Non-Goals

- **US-040H** full event modal + toast feedback (follow-up). This change MAY keep a minimal interim click path so Week/Month are not capability regressions; it MUST NOT ship H’s modal/toast product.
- **US-040I** operator-local day bucketing overhaul (interim UTC day placement + local time display OK; debt called out).
- **US-040J** cancelled reopen worker path.
- **US-040K** max-2-per-local-day enforcement.
- Public URL hosting / Google OIDC / BFF / DB / user-management.
- LinkedIn API publish from the console; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` bypass; Flow B; n8n Execute Command.
- Push / deploy without explicit approval after apply/verify.
- Marking **US-040G Story accepted**, **Acceptance criteria validated**, or **BL-015 closed** from implementation, Vitest, or OpenSpec task checkboxes alone.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (US-040G only) | Remains open until operator-validated completion outcome |
| **US-040G** | Yes | Calendar-first Week + Month; remove List; Visual DoD + walkthrough gate |
| **US-040A–F** | Preserve architecture | Stack, ScheduleEditor SoT, session/`canMutate`, Month density UX; List-as-first-class **superseded** for future UX |
| **US-040H** | Follow-up | Not in apply scope except minimal interim event click path if required for G usability |
| **US-040I** | Out (debt noted) | Keep interim UTC bucketing + local display |
| **US-040J / US-040K** | Out | Do not implement |

US-040G acceptance criteria addressed by this change (implementation + evidence gates; Story accepted only after walkthrough):

- Remove List from operator chrome; Week default / Month secondary; preserve filters/dry-run/unsaved drafts on switch.
- Readable week layout with day headers, today emphasis, scannable event chips; Month remains density-oriented.
- Prev/next week & month + Today/This-week control; intentional empty states; metrics navigate within Week/Month only.
- Preserve stack/contracts; no public URL/OIDC/BFF/LinkedIn publish/Flow B.
- Visual DoD (desktop + mobile scenes) + operator walkthrough before Story accepted.

Intentionally excluded: H modal/toasts product, I local-day bucketing, J reopen, K density cap, deploy/push, Story accepted from code alone.

## What Changes

- **BREAKING (operator UX):** List is no longer a first-class view. View switcher becomes `Week` | `Month` with Week selected by default on first load / hard refresh.
- Add **Week view** as the default operational calendar surface (day-column layout; see design).
- Keep **Month** as secondary first-class density view; improve empty/dense states to product quality.
- Remove List chrome and list-as-home landing; delete or retire List production components/tests per design (not “hide behind a flag”).
- Retarget metric chips to filter + navigate within Week/Month only (never reopen a list).
- Provide interim event-chip → existing detail drawer / ScheduleEditor path so calendar views are not capability regressions until US-040H.
- Update `linkedin-variant-supervision-console` requirements to supersede list-as-first-class language for this and future UX.
- Tasks include Visual DoD scenes and an operator walkthrough gate left unchecked until after deploy/agreed preview + walkthrough.

## Capabilities

### New Capabilities

_(none — calendar-first redesign extends the existing console capability)_

### Modified Capabilities

- `linkedin-variant-supervision-console`: Supersede dual first-class List + Month with Week (default) + Month (secondary); remove List from operator chrome; add Week UX, empty-state, metric navigation, interim calendar action entry points, Visual DoD / walkthrough gates; preserve worker HTTP reads/mutations, ScheduleEditor SoT, session/`canMutate`, and qualified publication language.

## Impact

- **Product:** Advances BL-015 / US-040G toward calendar-first UX; BL-015 stays open; US-040G Story accepted only after Visual DoD + operator walkthrough.
- **Frontend:** `frontend/linkedin-variant-supervision-console/` — ViewSwitcher, App/AppShell, new Week view, Month empty/nav polish, StatusSummary metric navigation, List removal, tests/static rebuild.
- **Worker:** No new mutation SoT; continue serving same-origin static console at `GET /flow-a/console/linkedin-variant-supervision`. Pending-supervision and schedule-visibility GETs remain; pending-supervision stays available as a read for shared-model detail (not as a List UI).
- **Specs:** Delta under `openspec/changes/.../specs/linkedin-variant-supervision-console/`; sync later updates main.
- **Deploy:** Explicit approval required after verify; Story accepted blocked until walkthrough on deployed or agreed preview.
