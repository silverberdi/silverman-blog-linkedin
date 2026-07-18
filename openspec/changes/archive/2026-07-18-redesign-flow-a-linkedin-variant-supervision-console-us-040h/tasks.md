## 1. Toast system and banner demotion

- [x] 1.1 Add toast store API (`pushToast` / dismiss / auto-dismiss ~4–6s / stacking) and a fixed overlay toast host (top-right or equivalent; MUST NOT permanently push calendar layout)
- [x] 1.2 Migrate happy-path mutation success feedback from persistent `actionBanner` / full-width green success banners to toasts; keep dry-run vs real copy visually obvious
- [x] 1.3 Demote LinkedIn publish-guard from full-width green enablement banner to compact app-bar chip / quiet status (session strip may remain quiet)
- [x] 1.4 Ensure error/blocked feedback uses error toasts and/or in-modal errors (not silent); keep structural non-green warn banners only where already required (not happy-path success)

## 2. Event modal shell and day-click rules

- [x] 2.1 Implement EventModal shell: desktop centered/anchored modal; mobile full/near-full sheet; operator fields first; expandable diagnostics (design D1, D7)
- [x] 2.2 Wire Week/Month event-chip activation to open EventModal (replace interim detail as primary surface)
- [x] 2.3 Remove multi-item day-agenda dump (`month-day-focus` chip list / equivalent); empty day click = light hover/focus only (design D2)
- [x] 2.4 Implement focus trap, Escape/backdrop/close dismiss, draft-loss warning when unsaved edits/schedule drafts exist, visible focus rings (design D6)

## 3. Wire mutations into modal; retire interim panel

- [x] 3.1 Embed ScheduleEditor / reschedule-defer inside EventModal; reuse US-017 + schedule-update semantics, dry-run default, `canMutate`, idempotency (design D3)
- [x] 3.2 Migrate edit content and cancel flows into EventModal; keep destructive cancel behind explicit confirmation dialog (not toast-only)
- [x] 3.3 On real success: toast + refresh + close or return to view mode; on dry-run success: toast with dry-run copy and keep modal usable
- [x] 3.4 Remove `InterimEventPanel` from production operator path; migrate/update tests that depended on interim chrome
- [x] 3.5 Confirm List chrome remains unrestored and no new worker mutation routes were added without design amendment (design D8)

## 4. Tests, build, and implementation evidence

- [x] 4.1 Add/update Vitest coverage: modal open/close, draft-warn on Escape/close, toast dismiss + stack, cancel confirmation, no day-agenda dump, no List restoration
- [x] 4.2 Run Vitest viewport matrix at ~1280px and ~375px covering Visual DoD scenes (component/DOM evidence; not Story accepted)
- [x] 4.3 Ensure prior ScheduleEditor / session / `canMutate` / calendar Week-Month suites still pass after interim retirement
- [x] 4.4 Production `npm run build`; rebuild worker static assets under `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/` for `GET /flow-a/console/linkedin-variant-supervision`
- [x] 4.5 Secrets audit on frontend source and built assets; `git diff --check` clean for touched paths
- [x] 4.6 If browser capture unavailable locally, record limitation in CURRENT-STATE / notes (design D9); do not mark Visual DoD or Story accepted

## 5. Docs honesty (pre-walkthrough)

- [x] 5.1 Update CURRENT-STATE for US-040H console-layer implementation status only (not Story accepted; BL-015 open; I/J/K not delivered)
- [x] 5.2 Update user-stories / progress-checklist demonstrated checkboxes only for criteria actually shown; leave Acceptance criteria validated and Story accepted unchecked
- [x] 5.3 Do not mark BL-015 closed; do not claim US-040I local bucketing, US-040J reopen, or US-040K density shipped

## 6. Visual DoD + operator walkthrough (post-deploy / agreed preview)

> Leave unchecked until after explicit deploy or agreed preview approval and capture/walkthrough. Vitest alone MUST NOT complete this section.

- [ ] 6.1 Capture Visual DoD — desktop: event open
- [ ] 6.2 Capture Visual DoD — desktop: modal hierarchy (operator fields before diagnostics)
- [ ] 6.3 Capture Visual DoD — desktop: edit/reschedule in modal
- [ ] 6.4 Capture Visual DoD — desktop: toast success + auto-dismiss
- [ ] 6.5 Capture Visual DoD — desktop: toast stack
- [ ] 6.6 Capture Visual DoD — desktop: cancel confirmation
- [ ] 6.7 Capture Visual DoD — desktop: proof of no day-agenda dump
- [ ] 6.8 Capture Visual DoD — desktop: proof of no persistent green success banner on happy path
- [ ] 6.9 Capture Visual DoD — mobile: event open / sheet
- [ ] 6.10 Capture Visual DoD — mobile: modal hierarchy
- [ ] 6.11 Capture Visual DoD — mobile: edit/reschedule in modal
- [ ] 6.12 Capture Visual DoD — mobile: toast success + auto-dismiss
- [ ] 6.13 Capture Visual DoD — mobile: toast stack
- [ ] 6.14 Capture Visual DoD — mobile: cancel confirmation
- [ ] 6.15 Capture Visual DoD — mobile: proof of no day-agenda dump
- [ ] 6.16 Capture Visual DoD — mobile: proof of no persistent green success banner on happy path
- [ ] 6.17 Operator walkthrough on deployed or explicitly agreed preview; operator confirms modal + toast UX meets intent
- [ ] 6.18 Only after 6.1–6.17: mark Acceptance criteria validated and Story accepted in product docs; keep BL-015 open unless full backlog outcome is also operator-validated

## 7. Lifecycle gates

- [x] 7.1 Explicit approval of this proposal before `/opsx-apply`
- [x] 7.2 `/opsx-apply` implementation of tasks 1–5 (and 4 evidence)
- [x] 7.3 `/opsx-verify` after implementation (re-run if post-verify edits)
- [x] 7.4 Explicit user approval → implementation commit (change + frontend + static + honest docs)
- [x] 7.5 `/opsx-sync` → separate sync commit
- [x] 7.6 `/opsx-archive` → separate archive commit
- [x] 7.7 Push only with explicit approval
- [x] 7.8 Deploy only with explicit approval (required before Visual DoD / walkthrough unless an agreed preview is documented)
- [ ] 7.9 Business validation: section 6 walkthrough complete before Story accepted; BL-015 remains open
