## 1. Local date helpers and calendar placement

- [x] 1.1 Replace primary UTC day-bucketing helpers with operator-local day-key / week / month helpers (`localDayKey`, today, week start, month grid, labels) per design D1–D2; keep UTC helpers only for diagnostics
- [x] 1.2 Switch WeekView day columns and MonthCalendarView cells to local-day bucketing of `scheduled_at_utc` / mapped blog due times
- [x] 1.3 Switch Week/Month navigation cursors, Today / This week, and chrome labels to local calendar (remove primary `(UTC)` clock labels)
- [x] 1.4 Pad schedule-visibility `from_utc`/`to_utc` query windows from local week/month cursors so near-edge local days are not dropped (design D4)

## 2. Local-first ScheduleEditor and error copy

- [x] 2.1 Rewrite `datetimeLocalToUtcIso` / `utcIsoToDatetimeLocal` so picker digits are operator-local wall time; emit `*_utc` ISO only at the typed API boundary (design D3)
- [x] 2.2 Update ScheduleEditor labels/help to local-first with timezone cue; remove routine “think in UTC” / “(UTC)” coaching copy
- [x] 2.3 Client future guard: reject only when new absolute time is not strictly after now; allow earlier-than-previous when still future; present copy in local terms
- [x] 2.4 Remap `*_time_invalid` (and related) operator-facing strings in `errors.ts` to plain local language; leave raw UTC in diagnostics only

## 3. EventModal / Week / Month primary displays

- [x] 3.1 Ensure Week chips, Month→EventModal path, and EventModal schedule line use local date/time with visible timezone cue as the primary clock (design D5)
- [x] 3.2 Keep raw `scheduled_at_utc` / UTC day behind expandable diagnostics; do not restore dual primary UTC+local clocks for routine work
- [x] 3.3 Confirm Week default, Month secondary, EventModal + toasts, and no List chrome remain intact (no G/H regression)

## 4. Tests, build, and implementation evidence

- [x] 4.1 Add/update Vitest for local-day bucketing including near-midnight fixtures where UTC day ≠ local day (deterministic TZ in tests)
- [x] 4.2 Add/update Vitest for local-first picker round-trip to `new_scheduled_at_utc` / `new_due_at_utc`
- [x] 4.3 Add/update Vitest for earlier-but-still-future reschedule allowed; past-now rejected; absence of routine UTC coaching copy in ScheduleEditor/error strings
- [x] 4.4 Run Vitest viewport matrix at ~1280px and ~375px covering Visual DoD scenes (component/DOM evidence; not Story accepted)
- [x] 4.5 Ensure prior Week/Month/EventModal/ScheduleEditor/session/`canMutate` suites still pass
- [x] 4.6 Production `npm run build`; rebuild worker static assets under `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/` for `GET /flow-a/console/linkedin-variant-supervision`
- [x] 4.7 Secrets audit on frontend source and built assets; `git diff --check` clean for touched paths
- [x] 4.8 If browser capture unavailable locally, record limitation in CURRENT-STATE / notes; do not mark Visual DoD or Story accepted

## 5. Docs honesty (pre-walkthrough)

- [x] 5.1 Update CURRENT-STATE for US-040I console-layer implementation status only (not Story accepted; BL-015 open; J/K not delivered; G/H Story accepted still gated)
- [x] 5.2 Update user-stories / progress-checklist demonstrated checkboxes only for criteria actually shown; leave Acceptance criteria validated and Story accepted unchecked
- [x] 5.3 Document US-040J and US-040K as follow-ups; do not claim density or cancelled reopen shipped
- [x] 5.4 Preserve qualified language: never bare “Flow A complete”; LinkedIn published ≠ blog handoff; dry-run ≠ real mutation

## 6. Visual DoD + operator walkthrough (post-deploy / agreed preview)

> Leave unchecked until after explicit deploy or agreed preview approval and capture/walkthrough. Vitest alone MUST NOT complete this section.

- [ ] 6.1 Capture Visual DoD — desktop: local times on Week with timezone cue
- [ ] 6.2 Capture Visual DoD — desktop: local times on Month / EventModal with timezone cue
- [ ] 6.3 Capture Visual DoD — desktop: near-midnight day placement (correct local day)
- [ ] 6.4 Capture Visual DoD — desktop: reschedule earlier-but-still-future
- [ ] 6.5 Capture Visual DoD — desktop: proof routine UI does not force UTC thinking
- [ ] 6.6 Capture Visual DoD — mobile: local times on Week with timezone cue
- [ ] 6.7 Capture Visual DoD — mobile: local times on Month / EventModal with timezone cue
- [ ] 6.8 Capture Visual DoD — mobile: near-midnight day placement (correct local day)
- [ ] 6.9 Capture Visual DoD — mobile: reschedule earlier-but-still-future
- [ ] 6.10 Capture Visual DoD — mobile: proof routine UI does not force UTC thinking
- [ ] 6.11 Operator walkthrough on deployed or explicitly agreed preview; operator confirms local-time UX meets intent in their timezone
- [ ] 6.12 Only after 6.1–6.11: mark Acceptance criteria validated and Story accepted in product docs; keep BL-015 open unless full backlog outcome is also operator-validated; do not close US-040G/H Story accepted as a side effect

## 7. Lifecycle gates

- [x] 7.1 Explicit approval of this proposal before `/opsx-apply`
- [x] 7.2 `/opsx-apply` implementation of tasks 1–5 (and 4 evidence)
- [x] 7.3 `/opsx-verify` after implementation (re-run if post-verify edits)
- [x] 7.4 Explicit user approval → implementation commit (change + frontend + static + honest docs)
- [x] 7.5 `/opsx-sync` → separate sync commit
- [x] 7.6 `/opsx-archive` → separate archive commit
- [x] 7.7 Push only with explicit approval
- [ ] 7.8 Deploy only with explicit approval (required before Visual DoD / walkthrough unless an agreed preview is documented)
- [ ] 7.9 Business validation: section 6 walkthrough complete before Story accepted; BL-015 remains open
