## Context

US-040A–D delivered the Flow A LinkedIn variant supervision console as React + TypeScript + Vite under `frontend/linkedin-variant-supervision-console/`, served same-origin at `GET /flow-a/console/linkedin-variant-supervision`. Baseline includes:

- Dual first-class List + Month calendar views; shared `ScheduleEditor`; CSS-grid month + mobile agenda
- Typed `SupervisionApiClient` + injectable `AuthProvider` with session states (anonymous / authenticated / expired / forbidden / service-unavailable) and `canRead` / `canMutate` gating (US-040D)
- Shared normalized model (`SupervisionItem` / `ScheduleItem` / filters including blocked + due-soon 48h); status color tokens; filters with discoverable hidden critical failures
- Worker reads: `GET /flow-a/linkedin-variants/pending-supervision`, `GET /flow-a/schedule-visibility`; mutations: US-017 POSTs + `POST /editorial-calendar/update-item-schedule`
- `StatusSummary` today is sparse technical metadata (`observedAtUtc`, `status`, `read_only`, pending count, integration_failures)—not operator at-a-glance attention counts
- Qualified language: `pending` / `queued` / `cancelled` / `flow_a_complete` / blog handoff ≠ LinkedIn API published
- Public URL hosting and Google/OIDC IdP **not activated** (separate security change)

US-040E (BL-015 final polish) must make attention, risk, and next actions obvious across List and Month without rewriting A–D SoT, without new mutation endpoints unless strictly required, and without claiming public/Google activation or closing BL-015 from propose alone.

**Constraints:** ADR-0001 browser → worker HTTP only; no n8n Execute Command; no browser filesystem writes; no hardcoded secrets; preserve US-040A–D; leave BL-015 open until E demonstrated; prefer frontend UX on existing APIs.

## Goals / Non-Goals

**Goals:**

- At-a-glance counts: upcoming, pending, due soon, deferred, blocked, failed, recently published.
- Visual priority for blocked/failed without overwhelming normal scheduled content.
- Concise operator-facing labels; diagnostic codes in expandable details.
- Clear affordances for view switch, filter, inspect, reschedule/defer/cancel (where supported), refresh, dry-run/commit.
- List = scanning/triage; Month = schedule comprehension.
- Destructive actions confirmed and separated from routine navigation.
- Keyboard (laptop) + touch (mobile) accessibility.
- Desktop + mobile visual validation for the US-040E scenario matrix.
- Dark theme consistency across loading / empty / error / detail / confirmation / success.
- First screen = operational console (no marketing landing).

**Non-Goals:**

- Public URL / internet exposure; live Google OAuth/OIDC IdP.
- BFF/DB/user-management; LinkedIn API publish; enablement bypass; Flow B.
- Closing BL-015 / BL-021; Story accepted from propose alone.
- Rewriting US-040A–D stack, dual views, ScheduleEditor mutation SoT, or auth-readiness.
- New worker mutation SoT; new read endpoints unless count semantics cannot be derived client-side.

## Decisions

### D1 — Derive at-a-glance counts client-side from the shared model

**Choice:** Compute operational counts in the frontend from the shared normalized model fed by existing pending-supervision + schedule-visibility reads. Upgrade `StatusSummary` into a compact count strip (chips or equivalent) visible in AppShell for both List and Month.

| Count | Primary source | Definition (normative for this slice) |
|-------|----------------|----------------------------------------|
| Upcoming | Schedule snapshot items (visible month / loaded schedule window) with future `scheduledAtUtc` and not cancelled | Future scheduled blog + LinkedIn items |
| Pending | Items with display state `pending` (list pending window + schedule where present) | Supervision-window / not-yet-queued |
| Due soon | Shared `isDueSoon` / `DUE_SOON_HOURS` (48h) already in model | Within next 48 hours from reference now |
| Deferred | Display state `deferred` or pending rows with deferred/`auto_queue_eligible` false context | Operator-deferred / not auto-queue eligible |
| Blocked | `blocked === true` and/or display state `blocked` | Actionable blocked |
| Failed | Display state `failed` and/or `integrationFailures` / critical failed siblings | Actionable failure attention |
| Recently published | Display state `published` **or** `linkedinApiPublished === true` with schedule in the last **7 days** UTC from reference now | Recent success visibility—NOT a claim that `pending`/`queued`/`flow_a_complete`/blog handoff is LinkedIn API published |

Counts MUST respect that filters may hide items: show counts for the **current filter scope** as the primary strip, and when filters hide critical failures keep the existing discoverable critical-failure affordance (US-040B). Do not invent a second divergent count cache per view.

**Why:** AC requires at-a-glance counts; existing payloads already carry publication states, blocked/critical, due-soon helpers, and integration failures. Avoids new worker SoT.

**Alternatives considered:** New worker aggregation endpoint — deferred unless apply proves client derivation insufficient; prefer frontend first. Hardcode counts only from List pending rows — rejected (Month schedule items would be invisible to “upcoming/published”).

### D2 — Actionable visual priority without alarm fatigue

**Choice:** Keep existing `STATUS_COLOR` tokens; strengthen hierarchy:

- Blocked / failed / critical: stronger border, badge weight, or row/day accent—still dark-theme friendly and readable
- Routine planned/pending/queued: calmer chrome so the calendar month does not read as all-alert
- List: denser triage cues (status pill + optional critical stripe) optimized for scanning
- Month: keep day cells schedule-comprehensible; use compact badges / overflow counts rather than full diagnostic walls in cells; put full diagnostics in ItemDetail / expandable details

Do **not** flash, autoplay motion, or use emoji as the primary risk signal.

**Why:** AC: noticeable blocked/failed without overwhelming normal scheduled content; List vs Month job separation.

**Alternatives considered:** Same dense diagnostic dump in every calendar cell — rejected (forces Month to do List’s job poorly). Only color text with no structure — rejected (weak for color-vision / scan).

### D3 — Operator-facing labels + expandable diagnostics

**Choice:** Introduce a small shared label map (e.g. `publicationStateLabel`) for display states:

| State | Operator label (example) |
|-------|--------------------------|
| planned | Planned |
| pending | Pending review |
| queued | Queued |
| published | Published (API evidence) / Published when `linkedinApiPublished` |
| deferred | Deferred |
| cancelled | Cancelled |
| blocked | Blocked |
| failed | Failed |

Raw worker codes (`linkedin_supervision_*`, `calendar_*`, HTTP status names) and issue messages remain available under an expandable “Details” / diagnostics region on ItemDetail, banners that already show codes, and confirmation failure panels. Primary chrome MUST prefer the concise label; MUST NOT remove code visibility for operators who need it.

Qualified language remains mandatory: never label `pending` / `queued` / `cancelled` / `flow_a_complete` / blog handoff as LinkedIn API published.

**Why:** AC concise labels + expandable diagnostics.

**Alternatives considered:** Hide all codes — rejected (ops debugging). Show only codes — rejected (AC wants concise labels).

### D4 — Affordance grouping and destructive-action separation

**Choice:** Organize AppShell / view chrome into clear groups:

1. **Navigation / mode:** ViewSwitcher (List | Month), Refresh, dry-run/commit default toggle
2. **Filter / triage:** existing Filters
3. **Inspect / mutate:** open detail, ScheduleEditor, edit/defer from List; cancel only via ConfirmationFlow
4. **Session:** Sign in / Clear credential (US-040D)—visually secondary to operational controls

Cancel and other irreversible commits MUST:

- Remain behind `ConfirmationFlow` (or equivalent) for real (`dry_run` false) cancel
- NOT sit adjacent to ViewSwitcher or Refresh as peer primary buttons in the same tight cluster
- Remain gated by `canMutate`

Schedule reschedule/defer continue through shared ScheduleEditor with existing dry-run + confirm for real commits (US-040C).

**Why:** AC clear affordances + destructive safety.

**Alternatives considered:** Flatten all actions into one toolbar row — rejected (AC: don’t place destructive next to routine nav).

### D5 — List vs Month job separation (preserve dual first-class views)

**Choice:** Explicit UX contract:

- **List:** scanning and bulk operational triage for pending LinkedIn supervision (Stories 1–3 detail + actions). Prefer density, status/risk cues, filter responsiveness.
- **Month:** schedule comprehension (what lands which day). Prefer day placement, time, compact status, agenda on mobile—not full edit forms in cells.

Do not merge both into a single overloaded surface. Shared model + switcher remain; polish MUST NOT degrade either view’s primary job.

**Why:** Explicit US-040E AC.

### D6 — Accessibility: keyboard + touch

**Choice:**

- Keyboard: logical focus order through shell → filters → active view → detail/editor; visible focus rings on interactive controls; Enter/Space activate buttons; Escape closes confirmation/detail/editor where those overlays exist (without discarding unsaved schedule drafts silently—warn if needed, preserving US-040B/D draft rules)
- Touch: maintain ≥44px-class touch targets for primary controls on mobile; stacked list cards and agenda already required by US-040B—polish MUST not shrink them below usable size
- Do not rely on hover-only for critical actions

No new heavy a11y library required unless apply finds a small justified dependency; prefer CSS + semantic HTML / ARIA already partially present.

**Why:** AC keyboard + touch accessibility.

### D7 — Dark theme state coverage + operational first screen

**Choice:** Audit and align `console.css` (and component chrome) so loading, empty, error, detail, confirmation, and success surfaces share the same dark tokens, spacing, and banner patterns. App entry (`App` / `AppShell`) MUST render the operational console shell as the first screen—no marketing hero, promo landing, or brand splash that delays the usable console.

Anonymous/auth banners from US-040D remain part of the operational shell, not a separate marketing page.

**Why:** AC dark theme consistency + no marketing landing.

### D8 — Visual validation evidence matrix

**Choice:** Provide desktop + mobile evidence via screenshots **or** equivalent UI checks (Vitest viewport + component assertions, optionally Playwright/manual capture documented in change notes). Required coverage:

| Scenario | Desktop | Mobile |
|----------|---------|--------|
| Dense list | ✓ | ✓ |
| Empty list | ✓ | ✓ |
| Dense month | ✓ | ✓ |
| Empty month | ✓ | ✓ |
| Blocked items visible | ✓ | ✓ |
| Long titles truncated/wrapped understandably | ✓ | ✓ |
| View switching preserves filters/dry-run | ✓ | ✓ |
| Schedule editing (ScheduleEditor open) | ✓ | ✓ |

Store evidence under an agreed path (e.g. `frontend/.../visual-evidence/` or document equivalent Vitest IDs in tasks) without embedding secrets.

**Why:** Explicit US-040E AC for visual validation.

### D9 — Prefer no new worker APIs; preserve A–D SoT

**Choice:** Default apply path is frontend-only polish on existing reads/mutations. If a count cannot be derived honestly, pause and propose a thin additive **read-only** field via the same OpenSpec change’s apply discussion—MUST NOT add mutation SoT, MUST NOT bypass enablement, MUST NOT write mounts from the browser.

Preserve: React+Vite stack, CSS-grid calendar, ScheduleEditor, session/`canMutate`, US-017 + calendar schedule-update endpoints.

**Why:** Proposal non-goals + ADR-0001.

### D10 — Testing and status language

**Choice:**

- Vitest: count derivation; label map; blocked/failed visual classes or roles; affordance placement smoke; ConfirmationFlow still required for real cancel; keyboard focus smoke where practical; dark-theme state class presence; viewport scenarios from D8
- Rebuild static assets; secrets audit source + built assets
- Pytest: console route + secrets as needed
- At apply: CURRENT-STATE records US-040E polish implemented when demonstrated; preserve A–D; **do not** claim public URL/Google activated; **do not** mark Story accepted or BL-015 closed from apply alone—only update checkboxes for criteria actually demonstrated

**Why:** Product rules + CURRENT-STATE discipline.

## Risks / Trade-offs

- [Risk] Count definitions disagree with operator mental model → Mitigation: D1 table is normative; document in StatusSummary tooltips/help text; reuse due-soon 48h and published-with-evidence rules.
- [Risk] Strong blocked styling overwhelms Month → Mitigation: D2 compact badges in cells; full emphasis in List/detail.
- [Risk] Scope creep into public hosting / IdP → Mitigation: explicit non-goals; no CORS widen; no IdP tasks.
- [Risk] Accidental new mutation SoT → Mitigation: D9 frontend-first; tasks forbid new POSTs unless approved mid-apply.
- [Risk] Visual evidence becomes flaky screenshot CI → Mitigation: allow equivalent UI checks; screenshots optional artifacts, not necessarily gating CI flakes.
- [Risk] Over-claiming BL-015 closed → Mitigation: D10 + tasks require open backlog until acceptance validated.

## Migration Plan

1. Implement counts, labels, visual hierarchy, affordance grouping, a11y, and dark-theme polish in the existing Vite app.
2. Add tests + visual validation evidence for the D8 matrix.
3. Rebuild static assets into worker static path; verify same-origin console route and secrets audit.
4. Update CURRENT-STATE / progress-checklist / user-stories only for demonstrated US-040E criteria; leave BL-015 open; leave public URL/Google deferred.
5. Rollback: revert frontend source + rebuild; worker mutation SoT unchanged so rollback is console-layer only.

## Open Questions

_None blocking propose._ If apply finds “recently published” cannot be derived without a worker `published_at` field, either (a) count only items with `linkedinApiPublished` / display `published` inside the loaded schedule window, or (b) add a thin read-only timestamp field via the same change’s apply review—do not invent LinkedIn API published from `flow_a_complete`.
