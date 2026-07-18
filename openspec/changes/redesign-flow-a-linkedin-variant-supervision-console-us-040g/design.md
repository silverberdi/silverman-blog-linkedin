## Context

US-040A–F delivered a React + TypeScript + Vite Flow A LinkedIn variant supervision console with dual first-class **List** + **Month**, shared ScheduleEditor, session/`canMutate`, and a first UX redesign pass. Operator feedback (2026-07-18) rejected list-first triage and empty/unexplained list landings. Product authority (US-040G, BL-015, shared UX DoD) requires a **calendar-first** console: Week default, Month secondary, List removed from operator chrome.

**Current evidence:** List is default (`ConsoleView = "list" | "calendar"`); ViewSwitcher exposes List | Month calendar; Month uses UTC day-bucketing with local display; metric chips only set filters (implicitly favoring List triage). US-040G–K not started per CURRENT-STATE.

**Constraints:** ADR-0001 browser → worker HTTP only; preserve ScheduleEditor mutation SoT (US-017 defer + editorial-calendar schedule-update); no public URL/OIDC/BFF; no J reopen / K density in this change; Story accepted gated by Visual DoD + operator walkthrough.

## Goals / Non-Goals

**Goals:**

- Week as default first-class home; Month as secondary first-class density view.
- Remove List from operator chrome and list-as-home landing.
- Intentional empty week/month product states; thumb-friendly week/month navigation + Today/This-week.
- Metric chips navigate/focus within Week/Month only.
- Interim event action path so G is not a capability regression before H.
- Freeze design decisions below; encode Visual DoD + walkthrough gates in tasks.
- Preserve stack, shared model, typed client, session/`canMutate`, qualified publication language.

**Non-Goals:**

- US-040H event modal + toast product (interim detail/ScheduleEditor only).
- US-040I local-day bucketing overhaul.
- US-040J cancelled reopen worker path; US-040K max-2/day enforcement.
- Push/deploy without explicit approval; Story accepted / BL-015 closed from implementation alone.

## Decisions

### D1 — Week layout: day columns (not hour time-grid)

**Choice:** Week is a **seven day-column** layout (desktop) with events as **stacked chips** inside each day column. Not an hour-by-hour time grid.

**Rationale:** Editorial publication density is sparse (often zero–few items per day; US-040K will later cap at two per local day). An hour grid wastes vertical space and implies continuous scheduling this product does not have. Day columns match “what publishes which day this week” in under three seconds.

**Mobile:** Thumb-friendly prev/next week controls; readable day sections (stacked vertical day blocks or equivalent) with scannable chips — not a horizontally scrolled dense table as the only layout.

**Today:** Emphasize today’s column/section. Event chips show title/campaign label, channel, local time, concise state — not raw ids as the primary label.

### D2 — List components and tests: delete from production path

**Choice:** **Delete** List from the operator production path (remove from `App` routing, ViewSwitcher, default view, shell copy). Delete `ListView` production component usage and List-chrome-specific tests that assert List as a first-class surface. Migrate capability coverage (edit/defer/cancel/schedule, shared model identity) to Week/Month + interim detail/ScheduleEditor entry points.

**Not chosen:** Hide-behind-flag (leaves dead chrome and false dual-view contracts). Archive-in-tree unused modules (drift risk).

**Historical note:** US-040A–F List-preserving language remains valid for those stories’ demonstrated scope; it MUST NOT block G from removing List.

### D3 — Interim action entry points until US-040H (honest UX)

**Choice:** Clicking an **event chip** (Week or Month) opens the **existing** detail drawer / ScheduleEditor surfaces already used from Month/agenda (ItemDetail + ScheduleEditor + confirmation). This is an **interim** affordance so Week/Month are not dead and prior capabilities remain reachable.

**Honesty rules:**

- Primary interaction is the **event chip**, not a day-dump agenda as the main action surface (light day selection/focus MAY exist for Month parity; it MUST NOT restore list-like triage chrome).
- Do **not** ship US-040H modal chrome or toast system in this change.
- UI copy or short secondary hint MAY state that a focused event modal is a follow-up — MUST NOT claim the interim drawer *is* the H modal product.
- Full edit/defer/cancel/schedule continue through existing worker HTTP + ScheduleEditor SoT with dry-run default and cancel confirmation.

### D4 — Metric chips without List

**Choice:** Metric chip click **resets focus flags then applies the target filter** (preserve US-040F D4 filter table) **and** navigates the active calendar cursor so the operator sees matching work inside Week or Month:

| Metric | Filter (unchanged semantics) | Calendar navigation |
|--------|------------------------------|---------------------|
| Upcoming | Clear focus flags | Stay on current view; prefer Week if useful to show nearest upcoming week |
| Pending / Due soon / Deferred / Blocked / Failed / Recently published | Same as US-040F D4 | Jump Week cursor to the week containing the next matching item (by schedule); if on Month, jump month cursor to that item’s month. If no match, keep cursor and show intentional empty filtered state |

**MUST NOT** switch to or reopen a List view. Channel/campaign filters preserved across metric clicks.

### D5 — View switcher and default

**Choice:** Segmented control labels **`Week` | `Month`**. `ConsoleView` becomes `"week" | "month"` (rename away from `"list" | "calendar"`). Default on first load and hard refresh: **`week`**. Switching MUST preserve filters, dry-run/commit mode, and warn before discarding unsaved schedule drafts (existing store behavior).

### D6 — Empty states

**Choice:** Empty week and empty month MUST render deliberate product empty states (short copy such as “No publications this week” / “No publications this month”, path to clear filters when filters hid everything). Never an unexplained blank content void. Dark theme consistent with shell.

### D7 — Time / day bucketing interim debt (US-040I)

**Choice:** Keep **UTC day-bucketing** for Week/Month placement (existing helpers) and continue showing **local** wall time on chips. Document UTC vs operator-local day mismatch as known debt for **US-040I**. Do not expand G apply scope into local-day bucketing overhaul.

### D8 — Evidence plan when browser capture may be limited

**Choice (layered):**

1. **Required for Story accepted:** Visual DoD scenes (desktop + mobile) via screenshots or equivalent browser-driven capture on **deployed or explicitly agreed preview**, plus operator walkthrough confirmation.
2. **Required for implementation commit / “business outcome demonstrated”:** Vitest viewport/component matrix covering the Visual DoD scenes at desktop (~1280) and mobile (~375) widths; production build; secrets audit.
3. **If local apply environment lacks browser capture** (no Playwright/Puppeteer/Chromium/in-app browser): record the limitation in CURRENT-STATE / implementation notes; keep Vitest matrix; leave Visual DoD and Story-accepted task checkboxes **unchecked** until capture + walkthrough after deploy/preview.

Vitest alone MUST NEVER flip Story accepted or Acceptance criteria validated.

### D9 — Follow-ups H/I do not expand apply scope

**Choice:** US-040H (modal + toasts) and US-040I (local-day experience) are noted as follow-ups. Apply scope stays G-only except D3 interim click path required for usability. J/K remain out.

### D10 — Data reads unchanged

**Choice:** Continue `GET /flow-a/schedule-visibility` for Week/Month placement and `GET /flow-a/linkedin-variants/pending-supervision` for pending detail/draft fields in the shared model. No new worker mutation SoT. Pending-supervision remains a **data** source, not a List UI.

## Risks / Trade-offs

- [Risk] Removing List before H modal feels like capability loss → Mitigation: D3 interim drawer/ScheduleEditor; explicit honesty that H follows.
- [Risk] Day-column Week feels sparse vs time-grid expectations → Mitigation: D1 product density rationale; Visual DoD + walkthrough may request polish without reopening List.
- [Risk] UTC bucketing vs local “today” confusion → Mitigation: D7 debt callout; chip local times; I owns bucketing.
- [Risk] Metric “jump to next match” is ambiguous with zero matches → Mitigation: D4 empty filtered state; no List fallback.
- [Risk] Browser capture unavailable during apply → Mitigation: D8; gates stay open; no Story accepted from Vitest.
- [Risk] Spec drift vs historical List-first requirements → Mitigation: delta REMOVED/MODIFIED with migration notes; A–F remain historical for their demonstrated scope.

## Migration Plan

1. Implement Week view + switcher default; wire App to Week/Month only.
2. Retarget metrics (D4); empty states (D6); interim event actions (D3).
3. Delete List production path and List-chrome tests; migrate capability tests.
4. Rebuild static assets; Vitest matrix; update CURRENT-STATE / product docs honestly (not Story accepted).
5. After explicit deploy/preview approval: capture Visual DoD; operator walkthrough; only then Story accepted.

No data migration. No worker API version bump required.

## Open Questions

_None blocking proposal._ Confirm at apply time only if operator rejects day-column Week in walkthrough (then follow-up change — do not restore List as home).
