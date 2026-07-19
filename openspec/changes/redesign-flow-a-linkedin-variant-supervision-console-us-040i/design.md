## Context

US-040G delivered calendar-first Week + Month; US-040H delivered EventModal + toasts. Live console still:

- Buckets Week columns and Month cells with `utcDayKey` / UTC week and month cursors (`dateHelpers.ts`).
- Labels Month/Week chrome with `(UTC)` while chips already show local wall time via `formatLocalTime` / `formatLocalDisplay`.
- Treats ScheduleEditor `datetime-local` digits as a **UTC wall clock** (`datetimeLocalToUtcIso` appends `Z`; `utcIsoToDatetimeLocal` uses `getUTC*` components) and coaches the operator with “New scheduled time (UTC)” / “think in UTC” style copy.
- Maps `*_time_invalid` errors with explicit “(UTC)” wording.

Product authority (US-040I, BL-015, shared UX DoD) requires **operator-local** primary clock and **local calendar-day** bucketing, with UTC retained as storage/wire only.

**SoT separation (preserve):** Editorial calendar rows live in Postgres (`silverman_linkedin_db`, US-041 / BL-031). LinkedIn variant schedules live in campaign metadata. Console continues to read both through worker HTTP (`pending-supervision` + `schedule-visibility`) and MUST NOT merge those stores.

**Constraints:** ADR-0001 browser → worker HTTP only; preserve `*_utc` mutation fields; no J/K products; Story accepted gated by Visual DoD + operator walkthrough; BL-015 stays open; do not close US-040G/H Story accepted.

## Goals / Non-Goals

**Goals:**

- Primary displays (Week, Month, EventModal) use operator-local date/time with visible timezone cue.
- Week/Month day placement and navigation use **local** calendar days / weeks / months.
- ScheduleEditor is local-first; convert to `new_scheduled_at_utc` / `new_due_at_utc` only at the typed API client boundary.
- Future validation: absolute “strictly after now”; copy in local terms; allow earlier-than-previous when still future.
- Strip routine “think in UTC” coaching from empty/error/help copy; UTC only in expandable diagnostics.
- Preserve Week default, Month secondary, EventModal, toasts; no List restoration.
- Vitest + static rebuild; honest docs; Visual DoD / walkthrough gates encoded in tasks.

**Non-Goals:**

- US-040J cancelled reopen; US-040K max-2-per-local-day product enforcement.
- Closing US-040G/H Visual DoD / Story accepted.
- Worker wire-field rename or local-timezone API fields.
- Campaign metadata → Postgres migration; wipe restore; Google/OIDC; LinkedIn publish from console; Flow B; n8n Execute Command.
- Story accepted / BL-015 closed from implementation alone.

## Decisions

### D1 — Browser timezone is the operator clock (no TZ picker in US-040I)

**Choice:** Use the browser’s resolved timezone (`Intl` / `Date` local getters) as the operator’s clock. Show a short timezone name cue (`timeZoneName: "short"`, e.g. `CST`) on primary schedule displays and ScheduleEditor labels. Do **not** ship a timezone dropdown or persist a preferred IANA zone in this change.

**Rationale:** US-040I acceptance is “my local timezone”; browser TZ matches single-operator local use. A picker is a product expansion (multi-machine / travel) with no AC demand.

**Not chosen:** Hard-code America/Chicago; force UTC display with a conversion calculator; add operator TZ preference storage.

### D2 — Local day-key helpers replace UTC day-keys for primary chrome

**Choice:** Introduce `localDayKey(iso)`, `todayLocalDayKey()`, local week start (keep **Sunday-start** week shape for continuity with US-040G unless a hard conflict appears), `buildLocalWeekDayKeys`, `currentLocalMonth`, `buildLocalMonthGrid`, and local labels **without** `(UTC)`. WeekView / MonthCalendarView / store cursors / Today affordances switch to these helpers.

Rename or deprecate `utcDayKey` for primary placement. Keep a thin UTC helper **only** for expandable diagnostics (e.g. EventModal diagnostics “UTC day” / raw ISO).

**Placement rule:** An item with `scheduled_at_utc` (LinkedIn) or mapped `due_at_utc` (blog) lands on the local calendar date of that instant in the operator’s timezone.

**Near-midnight fixture:** e.g. `2026-07-20T05:00:00Z` in America/Chicago (CDT, UTC−5) is local `2026-07-20 00:00` → local day `2026-07-20`; the same instant MUST NOT be forced onto UTC day `2026-07-20` when the operator’s local day differs (use fixtures where UTC day ≠ local day to prove the bug is gone).

**Not chosen:** Keep UTC bucketing and only change labels (fails AC). Dual-bucket both UTC and local days in the grid (cognitive load).

### D3 — Local-first ScheduleEditor; `*_utc` only at API boundary

**Choice:** Rewrite conversion helpers:

| Direction | Behavior |
|-----------|----------|
| Display → picker | `utcIsoToDatetimeLocal` uses **local** `getFullYear/Month/Date/Hours/...` components for `datetime-local` |
| Picker → API | `datetimeLocalToUtcIso` interprets digits as **local** wall time and emits ISO `...Z` (or offset-normalized UTC) for `new_scheduled_at_utc` / `new_due_at_utc` |

Labels: “New scheduled time” + timezone cue (e.g. `CST`), **not** “(UTC)”. Help text: stored/transported as UTC at the worker boundary; operator does not enter UTC digits.

**Client future guard:** Compare parsed absolute instant to `Date.now()` (or equivalent). Reject only when `new <= now`. Do **not** require `new > previous_scheduled_at`. Copy: “must be after now in your local time” (or equivalent). Worker remains authoritative for `linkedin_supervision_defer_time_invalid` / `calendar_schedule_time_invalid`.

**Error map (`errors.ts`):** Remove routine “(UTC)” coaching from operator-facing strings; map codes to plain local language. Raw UTC ISO MAY remain in expandable diagnostics.

**Not chosen:** Send local offset fields on the wire (needs paired worker contract). Keep picker-as-UTC (current debt). Client-only validation without worker absolute check (unsafe).

### D4 — Schedule-visibility fetch windows: pad in console, keep worker `from_utc`/`to_utc`

**Choice:** Keep worker schedule-visibility contract (`from_utc` / `to_utc`). When the console navigates a **local** week or month, compute a UTC query window that covers the full local period, with **±1 day padding** (or equivalent) so items near local midnight at month/week edges are not dropped. Prefer console-side range construction over new worker query params.

**Not chosen:** New worker `timezone=` parameter in this change. Fetch unbounded ranges.

### D5 — Preserve G/H interaction model; UTC is diagnostic-only

**Choice:** No List chrome. Event chip → EventModal. Toasts remain. Primary modal schedule line uses local display + TZ cue; diagnostics may show raw `scheduled_at_utc` / UTC day key.

**Not chosen:** Restore dual “UTC + local” as equal primary clocks (superseded by US-040I mental model).

### D6 — Follow-ups J/K; shared helpers only if cheap

**Choice:** Document US-040J and US-040K as follow-ups. Local day-key helpers MAY be reused by US-040K later; do **not** implement density caps, cancelled reopen, or Cancelled metric chip in this change.

**Hard dependency check:** None identified — density and reopen do not block local-time UX.

### D7 — Honest status and acceptance gates

**Choice:** After apply: update CURRENT-STATE / user-stories / progress-checklist to “implemented in console layer” / business outcome demonstrated only when Vitest + rebuild evidence exists; leave Acceptance criteria validated and Story accepted open until Visual DoD + walkthrough. Do not mark BL-015 closed. Do not mark US-040G/H Story accepted as a side effect.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| DST transitions shift local day boundaries | Use `Date`/`Intl` local APIs; add fixtures spanning a DST change where practical; document that browser TZ rules apply |
| Vitest environment TZ differs from operator TZ | Pin or mock timezone in unit tests (e.g. `process.env.TZ` or explicit IANA in helpers under test) so bucketing assertions are deterministic |
| Padded fetch windows miss items if padding too small | Use ≥1 local day pad; add regression test for month-edge near-midnight item |
| Operators confuse diagnostics UTC with primary clock | Keep diagnostics collapsed by default; never put “enter UTC” in primary help |
| Accidental List / interim-panel regression | Preserve G/H tests; assert Week default + EventModal path |
| Over-claiming Story accepted | Tasks explicitly gate Visual DoD + walkthrough; status language forbids code-only acceptance |

## Migration Plan

1. Implement local helpers + view/editor/copy changes behind normal Vite build.
2. Rebuild static assets into worker static path (same as prior console changes).
3. `/opsx-verify` → implementation commit (approval-gated) → sync → archive (separate commits).
4. Explicit push → explicit deploy to `192.168.0.194:8010`.
5. Capture Visual DoD (desktop + mobile) for required US-040I scenes; operator walkthrough in the operator’s timezone.
6. Only then mark Story accepted / Acceptance criteria validated; BL-015 remains open.

**Rollback:** Redeploy prior static build + frontend commit; worker mutation contracts unchanged, so rollback is console-asset reversible.

## Open Questions

- None blocking propose. If during apply a hard dependency on US-040K density appears (unexpected), pause and amend design rather than silently shipping K.
- Optional later: operator TZ preference / IANA picker — out of scope unless product reopens AC.

## HTTP / security / deployment notes

- No new worker mutation routes; no secret embedding in static assets.
- Auth remains injectable API-key / session/`canMutate`; dry-run default and confirm-for-real unchanged.
- Deploy remains separate from implementation; no live mutation assumed by Vitest.
