## 1. Worker reopen contract

- [x] 1.1 Implement reopen/reschedule-from-cancelled service (`cancelled` → `pending` + `new_scheduled_at_utc`) per design D2–D4 (eligibility, audit history, `auto_queue_eligible` true, no LinkedIn API call, dry-run default)
- [x] 1.2 Expose authenticated `POST /reopen-linkedin-variant` (or equivalent kebab-case fixed at apply) with API key auth, structured JSON success/error, idempotency replay, optional `actor`/`source`/`reason`
- [x] 1.3 Fail closed for ineligible states (published/pending/queued/failed; failed→cancelled recovery path; past `new_scheduled_at_utc`) with stable codes (`linkedin_reopen_not_allowed`, time-invalid family)
- [x] 1.4 Apply interim defer-like duplicate-slot / saturation checks to reopen’s new schedule when applicable; do **not** implement US-040K max-2/local-day product rules
- [x] 1.5 Confirm cancel remains irreversible except via reopen; defer/correct MUST NOT restore cancelled → pending

## 2. Schedule-visibility cancellation context

- [x] 2.1 Add additive nullable fields on LinkedIn schedule-visibility items: `cancelled_at_utc`, `cancellation_phase`, `cancellation_reason`, `reopen_eligible` (design D5)
- [x] 2.2 Compute `reopen_eligible` from the same eligibility rules as the reopen service; keep fields secret-safe
- [x] 2.3 Preserve existing cancelled inclusion in Week/Month range queries; do not hide cancelled items

## 3. Console cancelled UX + reopen path

- [x] 3.1 Strengthen calm cancelled chip styling/label on Week and Month (distinct from failed/blocked; not LinkedIn API published)
- [x] 3.2 Implement cancelled EventModal what / why / what-next copy using schedule-visibility cancellation fields; raw codes only in diagnostics
- [x] 3.3 Wire reopen & reschedule for eligible + `canMutate` sessions: confirm → local-first schedule pick (US-040I) → dry-run default → real confirm → reopen POST → success toast → refresh schedule-visibility (+ pending-supervision)
- [x] 3.4 Map reopen failure codes to plain-language failure toasts; block anonymous/read-only reopen
- [x] 3.5 Keep active pending cancel destructive, confirmed, via existing `POST /cancel-linkedin-publication`; outcome refreshes to calm cancelled chip
- [x] 3.6 If reopen is temporarily blocked mid-apply, ship explicit read-only cancelled modal (no fake Edit) and record the deferral in CURRENT-STATE — prefer completing 3.3

## 4. Tests, build, and implementation evidence

- [x] 4.1 Pytest: real reopen restores pending + schedule + eligibility; dry-run no mutation; idempotent replay; pre_queue and post_queue→pending; failed-cancellation refused; past time refused; auth 401; no LinkedIn call
- [x] 4.2 Pytest: schedule-visibility exposes cancellation context + `reopen_eligible` for cancelled items
- [x] 4.3 Vitest: cancelled chip Week/Month calm styling; cancelled modal what/why/what-next; reopen happy path (or explicit read-only copy); failure toast; `canMutate` gating
- [x] 4.4 Vitest viewport matrix at ~1280px and ~375px covering Visual DoD scenes (component/DOM evidence; not Story accepted)
- [x] 4.5 Ensure prior Week/Month/EventModal/ScheduleEditor/session/`canMutate`/local-time suites still pass
- [x] 4.6 Production `npm run build`; rebuild worker static assets under `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`
- [x] 4.7 Secrets audit on touched worker/frontend/static paths; `git diff --check` clean
- [x] 4.8 If browser capture unavailable locally, record limitation in CURRENT-STATE / notes; do not mark Visual DoD or Story accepted

## 5. Docs honesty (pre-walkthrough)

- [x] 5.1 Update CURRENT-STATE for US-040J implementation status only (not Story accepted; BL-015 open; G/H/I Story accepted still gated; K not delivered)
- [x] 5.2 Update [linkedin-variant-supervision-mechanics.md](../../../docs/operations/linkedin-variant-supervision-mechanics.md) (and conflicting irreversibility notes where needed) for the approved reopen path
- [x] 5.3 Update user-stories / progress-checklist demonstrated checkboxes only for criteria actually shown; leave Acceptance criteria validated and Story accepted unchecked
- [x] 5.4 Document US-040K as follow-up; do not claim density product shipped
- [x] 5.5 Preserve qualified language: never bare “Flow A complete”; cancelled ≠ LinkedIn API published; dry-run ≠ real mutation

## 6. Visual DoD + operator walkthrough (post-deploy / agreed preview)

> Leave unchecked until after explicit deploy or agreed preview approval and capture/walkthrough. Vitest alone MUST NOT complete this section.

- [ ] 6.1 Capture Visual DoD — desktop: cancelled chip on Week
- [ ] 6.2 Capture Visual DoD — desktop: cancelled chip on Month
- [ ] 6.3 Capture Visual DoD — desktop: cancelled modal what / why / what next
- [ ] 6.4 Capture Visual DoD — desktop: reopen/reschedule happy path (or explicit interim read-only copy)
- [ ] 6.5 Capture Visual DoD — desktop: failure toast
- [ ] 6.6 Capture Visual DoD — mobile: cancelled chip on Week/Month
- [ ] 6.7 Capture Visual DoD — mobile: cancelled modal
- [ ] 6.8 Capture Visual DoD — mobile: reopen happy path or explicit read-only copy
- [ ] 6.9 Capture Visual DoD — mobile: failure toast (or equivalent failure communication)
- [ ] 6.10 Operator walkthrough on deployed or explicitly agreed preview; operator confirms cancelled-event UX meets intent
- [ ] 6.11 Only after 6.1–6.10: mark Acceptance criteria validated and Story accepted in product docs; keep BL-015 open; do not close US-040G/H/I Story accepted as a side effect

## 7. Lifecycle gates

- [x] 7.1 Explicit approval of this proposal before `/opsx-apply`
- [x] 7.2 `/opsx-apply` implementation of tasks 1–5 (and 4 evidence)
- [x] 7.3 `/opsx-verify` after implementation (re-run if post-verify edits)
- [ ] 7.4 Explicit user approval → implementation commit (change + worker + frontend + static + honest docs)
- [ ] 7.5 `/opsx-sync` → separate sync commit
- [ ] 7.6 `/opsx-archive` → separate archive commit
- [ ] 7.7 Push only with explicit approval
- [ ] 7.8 Deploy only with explicit approval (required before Visual DoD / walkthrough unless an agreed preview is documented)
- [ ] 7.9 Business validation: section 6 walkthrough complete before Story accepted; BL-015 remains open
