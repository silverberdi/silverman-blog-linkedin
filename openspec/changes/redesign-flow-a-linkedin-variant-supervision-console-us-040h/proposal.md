## Why

US-040G delivered calendar-first Week + Month, but event work still uses an interim detail panel (`InterimEventPanel` / ItemDetail / ScheduleEditor) and happy-path feedback still lands in persistent full-width banners that push the calendar and compete with the scan surface. Operators need a focused **event modal** as the single view/edit/reschedule/cancel surface, with success and dry-run feedback as ephemeral **toasts** — without a day-agenda dump or large green “everything is fine” banners on the primary path. US-040H (BL-015) closes that interaction gap now that G (including Outlook-like empty-grid persistence) is implemented and deployed.

## Goals

- Make **event-chip click** the primary interaction; empty day space MUST NOT open a multi-item day-agenda dump.
- Replace the interim detail path with a focused **event modal** as the single surface for view + edit + reschedule/defer + cancel (where already supported).
- Present **operator-facing fields first**; bury raw ids, endpoint names, and worker codes in expandable diagnostics.
- Route success / dry-run / non-blocking info to **ephemeral toasts** (top-right or equivalent), auto-dismiss ~4–6s, manually dismissible, sensible stacking — MUST NOT permanently push the calendar down.
- Remove persistent full-width green success/status banners from the primary scan path; LinkedIn publish-guard / session MAY remain as a compact app-bar chip or quiet status.
- Keep destructive cancel behind explicit confirmation (not toast-only); keep dry-run vs real visually obvious in modal and toast copy.
- Meet keyboard/a11y: focus trap, Escape/backdrop/close with draft-loss warning when unsaved, visible focus rings, no hover-only critical actions; mobile full/near-full sheet; desktop centered/anchored modal with clear hierarchy.
- Encode Shared UX DoD: Visual DoD evidence + operator walkthrough required before Story accepted; Vitest alone insufficient.
- Preserve React + TypeScript + Vite, same-origin static assets, typed API client, shared model, ScheduleEditor / US-017 mutation semantics, session/`canMutate`, worker HTTP only (ADR-0001).

## Non-Goals

- **US-040I** operator-local day bucketing / timezone overhaul (local time on chips MAY remain if already present; do not claim I done).
- **US-040J** Cancelled metric chip / reopen UX.
- **US-040K** max-2-per-local-day density enforcement.
- Filters dock removal.
- Public URL hosting / Google OIDC / BFF / DB / user-management.
- LinkedIn API publish from the console; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` bypass; Flow B; n8n Execute Command.
- New worker mutation SoT or new HTTP routes unless strictly required and justified in design (prefer reuse of existing US-017 / schedule-update contracts).
- Push / deploy without explicit approval after apply/verify.
- Marking **US-040H Story accepted**, **Acceptance criteria validated**, or **BL-015 closed** from implementation, Vitest, or OpenSpec task checkboxes alone.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (US-040H only) | Remains open until operator-validated completion outcome |
| **US-040H** | Yes | Event modal + toast feedback; Visual DoD + walkthrough gate |
| **US-040A–G** | Preserve | Stack, Week/Month calendar-first, ScheduleEditor SoT, session/`canMutate`; interim panel **superseded** as primary event surface |
| **US-040I / J / K** | Out | Do not implement; do not claim done |

US-040H acceptance criteria addressed by this change (implementation + evidence gates; Story accepted only after walkthrough):

- Event click → modal with view/edit affordances; empty day click MUST NOT open multi-item agenda dump.
- Operator-facing fields first; diagnostics expandable.
- Edit / reschedule / defer / cancel reachable from modal without List.
- Ephemeral toasts replace persistent green success banners on happy path; auto-dismiss + manual dismiss.
- Publish-guard/session MAY stay quiet in app bar (not full-width green banner).
- Dry-run vs real obvious in modal + toast copy; cancel confirmation separate from toast success.
- Keyboard/accessibility requirements above.
- Visual DoD scenes (desktop + mobile) + operator walkthrough before Story accepted.
- Failures via error toasts or in-modal errors (not silent).
- Reuse ScheduleEditor / US-017 semantics; no unintentional baseline churn.

Intentionally excluded: I local-day bucketing, J reopen, K density, filters dock removal, deploy/push, Story accepted from code alone.

## What Changes

- **BREAKING (operator UX):** Interim event panel (`InterimEventPanel` as primary event surface) is replaced by a focused event modal; happy-path mutation success MUST NOT appear as persistent full-width green banners that permanently push the calendar.
- Add **event modal shell** (desktop centered/anchored; mobile full or near-full sheet) opened from event-chip activation only.
- Wire existing **ScheduleEditor** / edit / defer / cancel flows into the modal (reuse US-017 and schedule-update semantics; dry-run default; cancel confirmation dialog).
- Add **toast system** for success / dry-run / non-blocking info (and optionally error toasts); auto-dismiss ~4–6s; manual dismiss; stacking; MUST NOT permanently push calendar layout.
- Demote LinkedIn publish-guard and similar quiet context to compact app-bar chip / quiet status; remove full-width green “everything is fine” banners from the primary scan path.
- Enforce: empty day click → light hover/focus only; **no** multi-item day-agenda dump competing with item detail.
- Update `linkedin-variant-supervision-console` requirements: supersede interim-panel-as-primary and persistent happy-path success-banner language; add modal + toast + Visual DoD / walkthrough gates.
- Vitest coverage for modal open/close, draft-warn, toast dismiss, cancel confirmation, no day-agenda dump, no List restoration; rebuild static assets into worker static path.
- Honest CURRENT-STATE / US-040H product status (implemented ≠ Story accepted; Visual DoD + walkthrough gated; BL-015 open).

## Capabilities

### New Capabilities

_(none — event modal + toast feedback extends the existing console capability)_

### Modified Capabilities

- `linkedin-variant-supervision-console`: Replace interim event detail as primary surface with focused event modal; add ephemeral toast feedback; remove persistent full-width green success banners from primary scan path; allow quiet app-bar publish-guard/session context; require Visual DoD / walkthrough gates for Story accepted; preserve worker HTTP reads/mutations, ScheduleEditor / US-017 SoT, session/`canMutate`, Week/Month calendar-first UX, and qualified publication language.

## Impact

- **Product:** Advances BL-015 / US-040H toward focused event interaction; BL-015 stays open; US-040H Story accepted only after Visual DoD + operator walkthrough.
- **Frontend:** `frontend/linkedin-variant-supervision-console/` — event modal, toast host, AppShell banner demotion, InterimEventPanel retirement/replacement, ScheduleEditor embedding, store feedback wiring, tests, static rebuild into `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`.
- **Worker:** No new mutation SoT expected; continue serving same-origin static console at `GET /flow-a/console/linkedin-variant-supervision`. Existing US-017 and schedule-visibility / pending-supervision contracts remain.
- **Specs:** Delta under `openspec/changes/.../specs/linkedin-variant-supervision-console/`; sync later updates main.
- **Lifecycle (approval-gated):** apply → verify → implementation commit → sync → archive → explicit push → explicit deploy → Visual DoD / operator walkthrough → only then Story accepted. No apply until explicit approval of this proposal.

## Lifecycle gates (normative for this change)

```text
explicit approval of this proposal
→ /opsx-apply
→ /opsx-verify
→ explicit implementation commit approval
→ /opsx-sync (separate commit)
→ /opsx-archive (separate commit)
→ explicit push approval
→ explicit deploy approval
→ Visual DoD capture + operator walkthrough
→ Story accepted only after walkthrough (BL-015 remains open)
```
