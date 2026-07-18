## Context

US-040A–G delivered a React + TypeScript + Vite Flow A LinkedIn variant supervision console that is **calendar-first** (Week default, Month secondary, List removed). Event work still uses an **interim** path: event chip → `InterimEventPanel` / `ItemDetail` / `ScheduleEditor`, with mutation success written to persistent full-width `action-banner` / `status-banner` / green `enablement-banner` in `AppShell`. Month still renders a `month-day-focus` multi-item chip list when a day is selected — a day-agenda dump that competes with item detail.

Product authority (US-040H, BL-015, shared UX DoD) requires a focused **event modal** as the single view/edit/reschedule/cancel surface, ephemeral **toasts** for happy-path feedback, and no persistent full-width green success banners on the primary scan path.

**Current evidence (post-G / empty-grid fix):** Week/Month deployed; interim panel honest-but-not-H; `setActionBanner({ kind: "ok", ... })` after edit/defer/cancel/schedule; enablement shown as full-width `.banner.ok` when publish guard is on.

**Constraints:** ADR-0001 browser → worker HTTP only; reuse ScheduleEditor + US-017 mutation SoT; no new routes unless strictly justified; no I/J/K products; Story accepted gated by Visual DoD + operator walkthrough; BL-015 stays open.

## Goals / Non-Goals

**Goals:**

- Event-chip → focused event modal (single surface for view + edit + reschedule/defer + cancel where supported).
- Empty day click → light hover/focus only; **remove** multi-item day-agenda dump (`month-day-focus` chip list pattern).
- Operator-facing hierarchy first; diagnostics expandable.
- Ephemeral toast system for success / dry-run / non-blocking info (and error toasts or in-modal errors for failures).
- Demote publish-guard / session context to compact app-bar chip or quiet status — not full-width green banner.
- Keyboard/a11y: focus trap, Escape/backdrop/close with draft-loss warning, visible focus rings, no hover-only critical actions.
- Mobile sheet / desktop modal layouts; Vitest coverage; static rebuild; honest docs.
- Freeze design decisions below; encode Visual DoD + walkthrough gates in tasks.

**Non-Goals:**

- US-040I local-day bucketing overhaul; US-040J cancelled reopen; US-040K density cap.
- Filters dock removal; public URL / OIDC / BFF / LinkedIn publish / Flow B / n8n Execute Command.
- New worker mutation SoT by default; Story accepted / BL-015 closed from implementation alone.

## Decisions

### D1 — Event modal replaces InterimEventPanel as primary surface

**Choice:** Introduce an `EventModal` (name flexible) as the **only** primary event surface opened from Week/Month event chips. Retire `InterimEventPanel` from the production operator path (delete or reduce to a thin adapter that mounts the modal — prefer delete + migrate tests).

**Modal contents (hierarchy):**

1. Title / campaign label
2. Channel / audience
3. Local datetime (existing local display helpers; do not claim US-040I)
4. Publication state (qualified language)
5. Risk / blocked / deferred cues when applicable
6. Actions: Edit content, Reschedule/Defer (ScheduleEditor), Cancel (where supported)
7. Expandable **Diagnostics** (raw ids, endpoint names, worker codes, technical notes)

**Not chosen:** Keep interim panel and restyle it lightly (fails “single focused modal” product intent). Build a parallel second detail path (capability split / drift).

### D2 — Day click: light focus only; remove day-agenda dump

**Choice:** Clicking empty day space (or day header/cell without activating a chip) MAY set a light selected/hover visual on that day cell. It MUST NOT open or reveal a multi-item agenda list below/beside the calendar that competes with the event modal (`month-day-focus` + `month-day-chip-list` production pattern MUST be removed or reduced to non-actionable visual focus only — no chip dump).

Overflow “+N more” on Month cells remains a density cue only; activating a specific event still requires a chip (or an overflow chip that opens the modal for that item — not a day dump panel).

**Not chosen:** Keep day-focus chip list as “helpful overflow” (explicitly forbidden by US-040H). Open modal with multi-select day contents (agenda dump in modal clothing).

### D3 — Embed ScheduleEditor and existing mutation flows inside the modal

**Choice:** Reuse `ScheduleEditor` and existing typed client methods (`correctVariant`, `deferVariant`, `cancelPublication`, editorial-calendar schedule-update) inside the modal shell. Preserve dry-run default, `confirmRealMutation` for real writes, cancel confirmation dialog, `canMutate` gating, and idempotency keys.

**UX:** ScheduleEditor opens as a panel/section **within** the event modal (or a nested step of the same modal), not as a separate page/list return. After successful real commit, close modal (or return to view mode) and toast; dry-run keeps modal open with toast confirming validation-only.

**Not chosen:** New worker endpoints for “modal open” or “toast ack”. Rewrite mutation contracts.

### D4 — Toast system for ephemeral feedback

**Choice:** Add a lightweight in-app toast host (React portal or fixed region), typically **top-right**, overlaying the viewport without changing document flow of the calendar.

| Feedback | Surface |
|----------|---------|
| Success (real write) | Toast `ok` — copy MUST say real/persisted |
| Dry-run success | Toast `info` or distinct dry-run variant — copy MUST say dry-run / no mutation |
| Non-blocking info | Toast |
| Mutation / auth errors | Error toast **and/or** in-modal error region (not silent) |
| Destructive cancel confirm | **Dialog** (existing confirmation), then success toast after confirmed action |
| Session expired / forbidden | Keep quiet session strip / chip; errors may toast |

**Behavior:** Auto-dismiss ~4–6s; manual dismiss control; stack newest-on-top or oldest-on-top consistently (prefer newest on top); max visible stack small (e.g. 3) with overflow dropping oldest.

**Store:** Replace happy-path `setActionBanner({ kind: "ok", ... })` usage with `pushToast(...)`. Persistent `action-banner` / full-width green success banners MUST leave the primary scan path.

**Not chosen:** Toast-only cancel (unsafe). Keep green action banners and add toasts too (double noise). Library-heavy toast framework unless already in tree (prefer minimal custom matching console CSS).

### D5 — App-bar quiet context; remove happy-path green banners

**Choice:**

- **LinkedIn publish-guard:** Move from full-width `.banner.ok` to a compact chip or quiet status in the app bar / session strip (warn state MAY stay slightly more visible than “ok”).
- **Session:** Keep compact session strip (already quieter than green success banners).
- **Status / action banners:** Remove from primary scan path for happy-path success; blocking warnings that are not “everything is fine” (e.g. filter-hidden critical, calendar issues) MAY remain as non-green warn banners where they already exist — do not convert every warn into toast if it is structural context for the current view. Happy-path **ok** success MUST be toast-only.

**Not chosen:** Delete all banners including session and warn/error structural cues. Keep enablement as full-width green “ok”.

### D6 — Keyboard, focus, and draft-loss

**Choice:**

- Modal: focus trap while open; initial focus on close control or first actionable field.
- Escape, backdrop click, and explicit close: if unsaved edit/schedule draft exists, show draft-loss warning (confirm discard) before close; otherwise dismiss immediately.
- Visible `:focus-visible` rings on modal controls and chips; critical actions are buttons (not hover-only).
- Nested cancel confirmation and draft-warn dialogs stack above the event modal; closing them MUST NOT silently lose the parent modal unless confirmed.

### D7 — Responsive layout

**Choice:**

- **Desktop (≥ ~768 or existing console breakpoint):** Centered or lightly anchored modal over dimmed backdrop; hierarchy title → state → schedule → actions.
- **Mobile (~375):** Full-screen or near-full sheet with large touch targets; sticky action region preferred near bottom or top for thumb reach.

Preserve existing dark operational theme tokens; do not introduce a new marketing visual system.

### D8 — No new worker HTTP unless forced

**Choice:** Prefer zero new routes. Reads remain `GET /flow-a/schedule-visibility` + `GET /flow-a/linkedin-variants/pending-supervision`. Mutations remain existing US-017 / schedule-update POSTs.

If implementation discovers a hard blocker requiring a new endpoint, **pause** and amend this design via a scoped artifact update before coding it — do not invent routes silently.

### D9 — Evidence plan (shared DoD with G–K)

**Choice (layered):**

1. **Required for Story accepted:** Visual DoD scenes (desktop + mobile) via screenshots or equivalent browser-driven capture on **deployed or explicitly agreed preview**, plus operator walkthrough confirming modal + toast UX feels focused and modern.
2. **Required for implementation commit / “business outcome demonstrated”:** Vitest covering modal open/close, draft-warn, toast dismiss/stack, cancel confirmation, no day-agenda dump, no List restoration; production build; secrets audit.
3. **If local apply environment lacks browser capture:** record limitation in CURRENT-STATE; leave Visual DoD / Story-accepted tasks unchecked.

Vitest alone MUST NEVER flip Story accepted or Acceptance criteria validated.

### D10 — Honest status language

**Choice:** After apply, CURRENT-STATE / user-stories / progress-checklist record US-040H as **implemented in console layer** (or equivalent) with **Not Story accepted; BL-015 open**; Visual DoD + walkthrough gated. Do not claim I/J/K done. Do not close BL-015.

## Risks / Trade-offs

- [Risk] Moving ScheduleEditor into modal creates nested focus/draft complexity → Mitigation: D3 + D6; single draft flag in store; tests for Escape draft-warn.
- [Risk] Removing month-day-focus feels like lost overflow access → Mitigation: D2; chips in cell + “+N more” cue; chip click opens modal; Visual DoD proves no dump.
- [Risk] Operators miss success feedback without green banners → Mitigation: D4 toasts with clear dry-run vs real copy; walkthrough gate.
- [Risk] Enablement chip too quiet to notice publish-guard → Mitigation: D5 quiet but present; warn state when off stays visible; qualified copy preserved.
- [Risk] Accidental new worker routes → Mitigation: D8 pause-and-amend.
- [Risk] Vitest mistaken for Story accepted → Mitigation: D9; tasks section 6 unchecked until walkthrough.
- [Risk] Scope creep into I (local bucketing) while showing local times → Mitigation: Non-goals; document I debt remains.

## Migration Plan

1. Add toast host + store API; migrate happy-path `actionBanner` ok paths to toasts.
2. Build EventModal shell; wire chip → open modal; migrate edit/defer/cancel/ScheduleEditor into modal.
3. Remove InterimEventPanel production path; remove month-day-focus multi-item dump; demote enablement banner to app-bar chip.
4. Vitest matrix; production build; rebuild static assets; honest docs.
5. Lifecycle: verify → commit → sync → archive → push → deploy (each approval-gated) → Visual DoD + walkthrough → Story accepted only then.

No data migration. No worker API version bump expected.

## Open Questions

_None blocking proposal._ At apply time only: confirm toast placement (top-right vs top-center) if Visual DoD feedback prefers otherwise — default top-right per product intent.
