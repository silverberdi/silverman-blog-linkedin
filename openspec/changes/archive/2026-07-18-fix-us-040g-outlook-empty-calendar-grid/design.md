## Context

US-040G delivered Week (default) + Month, removed List chrome, and is deployed on `192.168.0.194:8010` for operator walkthrough. Operator feedback (2026-07-18): when a week or month has nothing scheduled, the console currently **replaces** the day grid with a standalone empty panel. Operators expect Outlook-like behavior — blank days stay visible so the surface still reads as a calendar while paging prev/next.

**Current implementation defect:** `WeekView` and `MonthCalendarView` branch on `weekItemCount === 0` / `monthItemCount === 0` and render only `calendar-empty-state`, omitting `week-columns` / `calendar-grid`.

**Constraints:** Console-layer only; worker HTTP unchanged; no List restoration; Filters dock and Cancelled chip explicitly out of this change (operator-requested follow-ups tracked separately / US-040J).

## Goals / Non-Goals

**Goals:**

- Persist Week day columns and Month day cells for empty and filter-zero periods.
- Keep calm empty messaging + clear-filters when filters hid everything.
- Update Vitest and Visual DoD empty scenes to require grid presence.
- Keep US-040G / BL-015 acceptance honesty (Story accepted only after redeploy + walkthrough).

**Non-Goals:**

- Filters dock removal; Cancelled metric chip; US-040H/I/J/K products.
- Worker endpoints, mutation SoT, n8n, public hosting, LinkedIn API publish.

## Decisions

### D1 — Empty cue overlays persistent grid (not grid replacement)

**Choice:** Always render the Week/Month calendar structure for the active cursor. When zero items are visible after filters, show a calm empty banner (or equivalent non-destructive cue) **above or over** the grid; day columns/cells remain blank.

**Alternatives considered:**

- Keep replace-with-panel empty state → Rejected; fails Outlook mental model and walkthrough.
- Fake placeholder events → Rejected; dishonest.

### D2 — Navigation remains first-class when empty

**Choice:** Prev/next week|month and Today/This-week stay available on empty periods so operators can move to weeks/months that still look like calendars.

### D3 — Filter-zero path unchanged in product intent

**Choice:** When filters hide all items, keep clear/reset filters affordance; do not collapse the grid. Do **not** remove the Filters dock in this change.

### D4 — Test contract

**Choice:** Vitest MUST assert `week-columns` / `calendar-grid` (or equivalent testids) remain mounted when empty-state testids are present. Update US-040G empty Visual DoD scenes to require grid-visible screenshots after deploy.

### D5 — HTTP / security boundary

**Choice:** No new routes or mounts. Browser continues worker HTTP only (ADR-0001). Same-origin static rebuild only.

## Risks / Trade-offs

- [Risk] Empty banner + full grid feels redundant on dense mobile → Mitigation: compact banner; blank cells stay quiet; no fake events.
- [Risk] Existing Vitest expects grid absent on empty → Mitigation: invert assertions in same change; rebuild static assets.
- [Risk] Operators also want Filters removed / Cancelled chip → Mitigation: documented non-goals; separate propose for chrome polish; Cancelled → US-040J.

## Migration Plan

1. Approve this change → `/opsx-apply`.
2. Frontend empty-grid fix + tests + `npm run build` into worker static.
3. `/opsx-verify` → commit → sync → archive (approval-gated).
4. Explicit deploy approval → operator empty week/month walkthrough + Visual DoD.
5. Only then consider US-040G Story accepted for empty-state AC; BL-015 stays open.

Rollback: redeploy prior static revision; no metadata/API migration.

## Open Questions

- None blocking apply. Banner placement (above grid vs subtle overlay) is an implementation detail within D1 as long as the grid remains visible and scannable.
