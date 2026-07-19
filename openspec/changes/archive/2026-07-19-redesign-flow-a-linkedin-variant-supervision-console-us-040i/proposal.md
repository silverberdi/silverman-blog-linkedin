## Why

Operators plan publications in local wall time and local calendar days, but the live console still labels Month as UTC and buckets Week/Month events by UTC day — so near-midnight schedules can land on the “wrong” day — while ScheduleEditor treats `datetime-local` digits as a UTC wall clock. US-040I (BL-015) removes that debt now that US-040G calendar-first chrome and US-040H EventModal + toasts are implemented/deployed.

## Goals

- Make **operator-local date/time** the primary clock in Week, Month, and EventModal, with a visible timezone cue (e.g. `CST`).
- Bucket Week/Month day columns/cells by **local calendar date**, not UTC date (no wrong-day placement near midnight).
- Make ScheduleEditor / reschedule controls **local-first**; convert to `*_utc` wire fields only at the typed API client boundary.
- Present “must be in the future” copy and client guards as absolute-time safety explained in local terms; allow moving earlier than the previous schedule when the new time is still after now.
- Ensure empty/error/help copy NEVER tells the operator to “think in UTC” for routine work; UTC MAY remain in expandable diagnostics only.
- Preserve US-040G/H interaction model (Week default, Month secondary, EventModal, toasts); no return of List-as-primary.
- Encode Shared UX DoD: Visual DoD (desktop + mobile) + operator walkthrough required before Story accepted; Vitest alone insufficient.
- Preserve worker `*_utc` contracts unless a paired OpenSpec change explicitly extends them; keep editorial calendar SoT in Postgres (US-041 / BL-031) separate from LinkedIn variant schedules in campaign metadata.
- Leave BL-015 open; leave US-040J (cancelled/reopen) and US-040K (max 2/local day) out of scope unless a hard dependency appears (document as follow-ups).

## Non-Goals

- **US-040J** cancelled event handling / reopen-reschedule worker path.
- **US-040K** max-2-publications-per-local-day density enforcement (local-day helpers MAY be shared later; do not ship K product rules here).
- Closing **US-040H** (or US-040G) Visual DoD / Story accepted — separate operator gate.
- Deploy/rsync editorial-safety hardening; restoring historically wiped calendar/campaign rows beyond current live state.
- Migrating campaign metadata / LinkedIn variant schedules into Postgres.
- Public URL hosting / Google OIDC / BFF / user-management product.
- LinkedIn API publish from the console; bypassing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; Flow B; n8n Execute Command.
- Extending worker schedule wire fields beyond `*_utc` (no local-timezone API fields in this change).
- Push / deploy without explicit approval after apply/verify.
- Marking **US-040I Story accepted**, **Acceptance criteria validated**, or **BL-015 closed** from implementation, Vitest, or OpenSpec task checkboxes alone.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (US-040I only) | Remains open until operator-validated completion outcome |
| **US-040I** | Yes | Operator-local time experience; Visual DoD + walkthrough gate |
| **US-040G / US-040H** | Preserve | Week/Month chrome, EventModal, toasts; do not regress; do not close their Story-accepted gates |
| **US-040J / US-040K** | Out | Follow-ups; document only unless hard dependency |
| **US-041 / BL-031** | Preserve separation | Postgres editorial calendar SoT ≠ LinkedIn variant campaign metadata schedules |

US-040I acceptance criteria addressed by this change (implementation + evidence gates; Story accepted only after walkthrough):

- Primary schedule displays in Week, Month, and EventModal use operator-local date/time with visible timezone cue.
- Week/Month placement uses local-day bucketing; any remaining UTC-only diagnostics are secondary / expandable.
- Schedule editor datetime controls are local-first; conversion to `*_utc` happens at the API boundary.
- Validation copy and client-side guards match “strictly after now” in absolute time, presented as local; earlier-than-previous-schedule moves allowed when still future.
- Empty/error/help states never instruct the operator to “think in UTC” for routine edits.
- Visual DoD evidence (desktop + mobile) for required scenes; Vitest alone insufficient for Story accepted.
- Operator walkthrough on deployed or agreed preview before Story accepted.
- Failures / blocked states clearly communicated (`*_time_invalid` → plain local-language mapping).
- Existing completed work not duplicated or unintentionally changed (worker UTC contracts preserved).

Intentionally excluded: J reopen, K density product rules, H/G Story accepted closure, deploy/push, Story accepted from code alone, Postgres migration of LinkedIn schedules, Google/OIDC.

## What Changes

- **BREAKING (operator UX):** Week/Month day placement and navigation switch from UTC calendar days/months/weeks to **operator-local** calendar days/weeks/months; ScheduleEditor stops treating picker digits as UTC wall clock.
- Replace UTC day-key helpers with **local day-key / local week / local month** helpers for primary calendar chrome (Today emphasis, Previous/Next, labels).
- Show primary times with timezone abbreviation cue; demote raw UTC ISO to diagnostics only.
- Rewrite ScheduleEditor labels, help, and client future-guards to local-first; map worker `*_time_invalid` errors to plain local language (no “think in UTC”).
- Update `linkedin-variant-supervision-console` requirements: supersede UTC day-bucketing as primary placement rule; add US-040I Visual DoD / walkthrough gates; keep `*_utc` wire contracts.
- Vitest coverage for local bucketing (including near-midnight fixtures), local-first picker round-trip to `*_utc`, earlier-but-still-future reschedule, and absence of routine UTC coaching copy; rebuild static assets into worker static path.
- Honest CURRENT-STATE / US-040I product status (implemented ≠ Story accepted; Visual DoD + walkthrough gated; BL-015 open; J/K still not delivered).

## Capabilities

### New Capabilities

_(none — operator-local time experience extends the existing console capability)_

### Modified Capabilities

- `linkedin-variant-supervision-console`: Supersede UTC calendar-day bucketing and UTC-first ScheduleEditor UX with operator-local primary displays, local-day Week/Month placement, local-first schedule editing with `*_utc` conversion only at the API boundary, local-language future validation (allow earlier-than-previous when still after now), and US-040I Visual DoD / walkthrough gates; preserve Week/Month/EventModal/toasts, worker HTTP SoT, session/`canMutate`, and qualified publication language.

## Impact

- **Product:** Advances BL-015 / US-040I toward local-time supervision; BL-015 stays open; US-040I Story accepted only after Visual DoD + operator walkthrough; does not close US-040G/H Story accepted.
- **Frontend:** `frontend/linkedin-variant-supervision-console/` — `dateHelpers`, WeekView, MonthCalendarView, EventModal, ScheduleEditor, error copy maps, tests, static rebuild into `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`.
- **Worker:** No new mutation SoT expected; continue serving same-origin static console. Existing `new_scheduled_at_utc` / `new_due_at_utc` and absolute-time future enforcement remain. Schedule-visibility fetch windows MAY need slight padding so local days near UTC month/week edges remain visible — console-side range construction preferred over new worker contract fields.
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
