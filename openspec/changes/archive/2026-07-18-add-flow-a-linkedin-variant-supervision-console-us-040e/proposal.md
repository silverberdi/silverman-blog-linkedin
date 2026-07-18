## Why

US-040A–D delivered a maintainable React console with dual List/Month views, shared ScheduleEditor mutations over worker HTTP, and auth-session readiness—but operator attention, risk, and next actions are still harder to scan than an operational control surface requires. Status summary is sparse technical metadata; actionable blocked/failed states compete visually with routine scheduled content; labels and affordances are uneven for laptop keyboard and mobile touch use. US-040E is the final BL-015 polish slice: make attention, risk, and next actions obvious in both views so operators can supervise confidently from anywhere—without activating public URL hosting, live Google/OIDC, or rewriting A–D sources of truth.

## Goals

- Provide at-a-glance counts for upcoming, pending, due soon, deferred, blocked, failed, and recently published items.
- Prioritize actionable states visually so blocked/failed are noticeable without overwhelming normal scheduled content.
- Use concise operator-facing labels for technical states; keep detailed diagnostic codes in expandable details when needed.
- Provide clear affordances for view switch, filtering, inspecting, rescheduling, deferring, cancelling (where supported), refreshing, and dry-run/commit mode.
- Keep List optimized for scanning/triage and Month calendar optimized for schedule comprehension—do not force one view to carry both jobs poorly.
- Keep destructive/irreversible actions behind confirmation; do not place them next to routine navigation.
- Preserve keyboard accessibility (laptop) and touch accessibility (mobile).
- Validate visual behavior with desktop + mobile screenshots or equivalent UI checks covering dense/empty lists, dense/empty months, blocked items, long titles, view switching, and schedule editing.
- Keep the dark theme consistent across loading, empty, error, detail, confirmation, and success states.
- First screen MUST be the usable operational console experience—no marketing-style landing page.
- Clear failure/blocked communication; understandable outcomes; qualified GLOSSARY language (`pending` / `queued` / `cancelled` / `flow_a_complete` / blog handoff ≠ LinkedIn API published).
- Preserve US-040A–D stack, dual views, ScheduleEditor mutation SoT, and auth-readiness (session states + `canMutate` gating).

## Non-Goals

- Activating public URL hosting / internet exposure.
- Live Google OAuth / OIDC IdP integration (US-040D readiness already done; activation needs a separate security change).
- BFF, database, or user-management product.
- LinkedIn API publish; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` bypass; Flow B.
- Closing BL-015 or BL-021 from propose or apply alone; marking Story accepted from propose alone.
- Rewriting US-040A–D visibility, schedule-mutation, or auth-readiness sources of truth.
- New worker mutation SoT unless strictly required for polish affordances (prefer frontend UX on existing APIs).
- Replacing React + TypeScript + Vite, CSS-grid calendar, or shared ScheduleEditor.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (US-040E only) | Leave backlog open until E demonstrated; do not close from propose alone |
| **US-040E** | Yes | All acceptance criteria in `docs/product/user-stories.md` |
| **US-040A / US-040B / US-040C / US-040D / US-038–US-040** | Preserve | Stack, dual views, schedule visibility, mutations, auth readiness |
| **Public URL / Google activation** | Out | Separate security change; CURRENT-STATE must not claim activated |
| **Flow B / BL-016+** | Out | Explicitly excluded |
| **BL-021** | Out | Do not close; cadence rules remain interim as already delivered by US-040C |

**US-040E acceptance criteria addressed:** at-a-glance counts; visual priority for actionable states; concise labels + expandable diagnostics; clear affordances (view/filter/inspect/reschedule/defer/cancel/refresh/dry-run); List vs Month job separation; destructive actions confirmed and separated from routine nav; keyboard + touch accessibility; desktop/mobile visual validation scenarios; dark theme consistency across console states; no marketing landing—first screen is operational console; understandable outcomes and clear failure/blocked communication; no unintentional duplication of A–D / Flow B.

**Intentionally excluded:** public URL hosting; live Google/OIDC; Story accepted / BL-015 closed checkboxes from propose; BFF/DB/user-mgmt; LinkedIn API publish; Flow B; rewriting A–D SoT; new mutation endpoints unless strictly required.

## Frontend stack decision (preserve)

**Keep React + TypeScript + Vite** under `frontend/linkedin-variant-supervision-console/`. Keep CSS-grid calendar and shared `ScheduleEditor`. Browser → worker HTTP only (ADR-0001); no n8n Execute Command; no browser filesystem writes.

## What Changes

- Upgrade `StatusSummary` (and related shell chrome) to at-a-glance operational counts derived from the shared normalized model / existing read payloads—no new mutation SoT.
- Strengthen visual hierarchy and status tokens so blocked/failed/critical items are noticeable without drowning routine scheduled content; keep List triage-dense and Month schedule-comprehensible.
- Map technical `publication_state` / worker codes to concise operator-facing labels; put raw diagnostic codes in expandable details.
- Clarify and group operator affordances (view switcher, filters, inspect/detail, schedule/defer/cancel where supported, refresh, dry-run/commit) with consistent placement and labeling; keep cancel and other irreversible actions behind confirmation and away from routine navigation.
- Improve keyboard focus order / shortcuts where practical and touch targets for mobile without regressing US-040B–D viewport contracts.
- Harden dark-theme consistency for loading, empty, error, detail, confirmation, and success surfaces; ensure AppShell first paint is the operational console (no marketing landing).
- Add desktop + mobile visual validation evidence (screenshots or equivalent UI checks) for the US-040E scenario matrix.
- Rebuild static console assets into the existing worker-served path; update CURRENT-STATE / progress / user-stories only when US-040E outcomes are demonstrated (preserve A–D; do not claim public URL/Google activated; do not close BL-015; do not mark Story accepted from propose).

## Capabilities

### New Capabilities

_None — US-040E extends the existing supervision console operational UX contract rather than inventing a parallel product surface._

### Modified Capabilities

- `linkedin-variant-supervision-console`: Require at-a-glance operational counts, actionable-state visual priority, concise labels with expandable diagnostics, clear affordance grouping, List vs Month job separation, destructive-action safety, keyboard/touch accessibility, dark-theme state consistency, operational first screen (no marketing landing), and desktop/mobile visual validation for the US-040E scenario matrix; preserve US-040A–D baselines; leave public URL / Google activation deferred.

## Impact

- **Product:** Advances BL-015 / US-040E (final polish slice); BL-015 remains open until E demonstrated and accepted; A–D preserved; public URL / Google not activated.
- **Frontend:** StatusSummary counts; label/token hierarchy; affordance/layout polish; accessibility; dark-theme state coverage; visual regression / viewport evidence; prefer existing shared model + APIs.
- **Worker:** Prefer **no** new mutation SoT and **no** new read endpoints unless count semantics cannot be derived client-side from existing pending-supervision + schedule-visibility payloads; if a thin additive field is required, it MUST be read-only and non-mutating.
- **APIs:** Browser → worker HTTP only (ADR-0001); no n8n Execute Command; no browser filesystem writes; no LinkedIn publish; no enablement bypass.
- **Deploy:** Same Vite build → worker static assets; no separate frontend server; **no** internet exposure activation in this change.
- **Docs:** CURRENT-STATE / progress-checklist / user-stories only when demonstrated at apply time; do not mark Story accepted or BL-015 closed from propose; do not claim public URL/Google activated.
- **Tests:** Frontend Vitest for counts, labels, affordances, a11y smoke, dark-theme states; viewport/visual checks for the scenario matrix; pytest console route + secrets audit as needed; no real LinkedIn/DeepSeek/ComfyUI/Google IdP.
