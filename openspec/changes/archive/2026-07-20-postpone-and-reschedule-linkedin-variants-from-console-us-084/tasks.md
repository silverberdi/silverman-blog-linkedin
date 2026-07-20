## 1. Inspect and lock scope

- [x] 1.1 Confirm US-084 ACs (including AC1 for not-Live = pending **and** queued) match this corrected change; leave US-085/US-086 out; keep BL-015 closed
- [x] 1.2 Inventory defer service, schedule-visibility `schedule_editable`, EventModal/ScheduleEditor, action matrix, article-preview delay policy language forbidding queued defer
- [x] 1.3 Confirm due/publish-due gates use `scheduled_at_utc` (and any companion fields) so queued postpone to a future time is skipped as not due

## 2. Worker: extend defer for queued

- [x] 2.1 Extend `defer_linkedin_variant` / `POST /defer-linkedin-variant` to accept `queued` as well as `pending` (reject published/cancelled/failed/publishing)
- [x] 2.2 Implement queued semantics: keep `publish_state` `queued`; update `scheduled_at_utc`; append deferral history; dry-run default; idempotency unchanged; no LinkedIn API call
- [x] 2.3 Preserve pending defer semantics (`pending` stays pending; `auto_queue_eligible` false / pre-queue fields as today)
- [x] 2.4 Keep US-040K density + interim cadence checks on the new schedule for both states
- [x] 2.5 Set schedule-visibility `schedule_editable` true for LinkedIn `pending` and `queued`; false for live/cancelled/failed/publishing with block reasons

## 3. Console: deliberate postpone control + matrix

- [x] 3.1 Redesign EventModal postpone/reschedule as deliberate primary control for schedule-editable Scheduled **and** Waiting-to-send items
- [x] 3.2 Wire both through shared ScheduleEditor → `POST /defer-linkedin-variant`; reuse US-083 preview vs real honesty
- [x] 3.3 Update action matrix: postpone available for pending and queued when editable + `canMutate`; cancel-queued and publish-now remain unavailable (US-085/US-086)
- [x] 3.4 Plain-language blocks for live/failed/publishing/cancelled/session/density with usable next steps

## 4. Calendar ↔ authoritative schedule agreement

- [x] 4.1 After successful **real** defer (pending or queued): refresh schedule-visibility (+ pending-supervision as applicable) into the shared model
- [x] 4.2 Ensure Week/Month place the variant on the new operator-local day/time; old slot is not operator truth
- [x] 4.3 Ensure preview/dry-run does not move calendar placement; demote stale secondary calendar-join

## 5. Policy / docs alignment in-repo

- [x] 5.1 Align article-preview fallback delay policy text/tests with queued defer allowed (keep queued; no un-queue-to-pending)
- [x] 5.2 Update `docs/CURRENT-STATE.md` if control-center postpone capability language changes; do not claim Story accepted

## 6. Tests, assets, and verification

- [x] 6.1 Pytest: defer pending unchanged; defer queued keeps queued + new schedule; reject live; density/cadence; schedule-visibility editable for queued; dry-run/idempotency
- [x] 6.2 Vitest: deliberate control; pending + queued real reschedule calendar agreement; preview no move; matrix; refusal next steps; US-083 regressions (~1280/~375 as applicable)
- [x] 6.3 Rebuild static console assets into worker static path
- [x] 6.4 Run targeted pytest + Vitest; `git diff --check`; secrets audit on touched files

## 7. Business validation

- [ ] 7.1 After explicit deploy approval (separate from apply): operator walkthrough that US-084 AC1 works for Scheduled **and** Waiting to send, calendar agrees after real change, refusals understandable
  - Note (2026-07-20): **Deployed** (`8184d2d`, assets `index-DzxHvZB-.js` / `index-BEnefPLS.css`; verify OVERALL PASS). Operator walkthrough / Story accepted still open.
- [x] 7.2 Update `docs/product/progress-checklist.md` and US-084 status only for demonstrated criteria; leave US-085/US-086 and BL-015 closed/untouched
  - Note (2026-07-20): Status set to implemented+deployed; AC checkboxes / Story accepted remain open pending walkthrough.
- [x] 7.3 Confirm non-goals held: no cancel-queued mutation, no publish-now / LinkedIn API path, no ADR-0001 / enablement bypass, no BL-015 reopen
