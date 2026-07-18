## 1. Model and shell foundations

- [x] 1.1 Change `ConsoleView` to `"week" | "month"`; default store view to `"week"`; update `requestViewChange` / draft-warn paths
- [x] 1.2 Replace ViewSwitcher labels/controls with `Week` | `Month` only (remove List tab and list test ids from chrome)
- [x] 1.3 Wire `App` / `AppShell` to render Week by default and Month as secondary; remove List from operator chrome and first paint
- [x] 1.4 Add week cursor helpers (week start/end, shift week, today/this-week) alongside existing month helpers; document interim UTC day-bucketing debt for US-040I

## 2. Week view and Month empty/nav polish

- [x] 2.1 Implement Week day-column layout (design D1): day headers, today emphasis, stacked event chips (title/label, channel, local time, state)
- [x] 2.2 Add prev/next week navigation and a thumb-friendly Today / This week control (desktop + mobile)
- [x] 2.3 Implement intentional empty week state (short copy + clear-filters path when filters hid everything)
- [x] 2.4 Ensure Month remains density-oriented with intentional empty month state; keep today/selected/overflow behavior without diagnostic cell walls
- [x] 2.5 Responsive mobile Week: readable day sections/chips without horizontal table-only scrolling

## 3. Interim actions, metrics, List removal

- [x] 3.1 Wire event-chip click on Week/Month to interim ItemDetail / ScheduleEditor path (design D3); keep dry-run default, cancel confirmation, `canMutate` gating
- [x] 3.2 Add honest interim UX copy/hint that full event modal is a follow-up (do not claim US-040H shipped)
- [x] 3.3 Retarget StatusSummary metric chips: reset-then-apply filters (US-040F D4) + navigate Week/Month cursor to next match; never open List (design D4)
- [x] 3.4 Delete List production component usage and List-chrome-specific tests; migrate capability coverage to Week/Month + interim entry points
- [x] 3.5 Confirm day click does not restore list-like multi-item diagnostic dump as the primary action surface

## 4. Tests, build, and implementation evidence

- [x] 4.1 Add/update Vitest coverage for Week default, Week|Month switcher, empty week/month, dense week/month fixtures, Today/This-week, metric calendar navigation, List chrome absence, interim event actions
- [x] 4.2 Run Vitest viewport matrix at ~1280px and ~375px covering Visual DoD scenes (component/DOM evidence; not Story accepted)
- [x] 4.3 Ensure prior ScheduleEditor / session / `canMutate` / error-mapping suites still pass after List removal
- [x] 4.4 Production `npm run build`; rebuild worker static assets for `GET /flow-a/console/linkedin-variant-supervision`
- [x] 4.5 Secrets audit on frontend source and built assets; `git diff --check` clean for touched paths
- [x] 4.6 If browser capture unavailable locally, record limitation in CURRENT-STATE / notes (design D8); do not mark Visual DoD or Story accepted

## 5. Docs honesty (pre-walkthrough)

- [x] 5.1 Update CURRENT-STATE for US-040G console-layer implementation status only (not Story accepted; BL-015 open; I debt; H/J/K not delivered)
- [x] 5.2 Update user-stories / progress-checklist demonstrated checkboxes only for criteria actually shown; leave Acceptance criteria validated and Story accepted unchecked
- [x] 5.3 Do not mark BL-015 closed; do not claim US-040H modal/toasts, US-040I local bucketing, US-040J reopen, or US-040K density shipped

## 6. Visual DoD + operator walkthrough (post-deploy / agreed preview)

> Leave unchecked until after explicit deploy or agreed preview approval and capture/walkthrough. Vitest alone MUST NOT complete this section.

- [ ] 6.1 Capture Visual DoD — desktop: Week first paint
- [ ] 6.2 Capture Visual DoD — desktop: empty week
- [ ] 6.3 Capture Visual DoD — desktop: dense week
- [ ] 6.4 Capture Visual DoD — desktop: Month switch
- [ ] 6.5 Capture Visual DoD — desktop: empty month
- [ ] 6.6 Capture Visual DoD — desktop: dense month
- [ ] 6.7 Capture Visual DoD — desktop: Today / This-week control
- [ ] 6.8 Capture Visual DoD — desktop: proof List chrome is gone
- [ ] 6.9 Capture Visual DoD — mobile: Week first paint
- [ ] 6.10 Capture Visual DoD — mobile: empty week
- [ ] 6.11 Capture Visual DoD — mobile: dense week
- [ ] 6.12 Capture Visual DoD — mobile: Month switch
- [ ] 6.13 Capture Visual DoD — mobile: empty month
- [ ] 6.14 Capture Visual DoD — mobile: dense month
- [ ] 6.15 Capture Visual DoD — mobile: Today / This-week control
- [ ] 6.16 Capture Visual DoD — mobile: proof List chrome is gone
- [ ] 6.17 Operator walkthrough on deployed or explicitly agreed preview; operator confirms Week-default calendar UX meets intent
- [ ] 6.18 Only after 6.1–6.17: mark Acceptance criteria validated and Story accepted in product docs; keep BL-015 open unless full backlog outcome is also operator-validated

## 7. Lifecycle gates

- [x] 7.1 `/opsx-verify` after implementation (re-run if post-verify edits)
- [x] 7.2 Explicit user approval → implementation commit (change + frontend + static + honest docs)
- [x] 7.3 `/opsx-sync` → separate sync commit
- [x] 7.4 `/opsx-archive` → separate archive commit
- [x] 7.5 Push only with explicit approval
- [ ] 7.6 Deploy only with explicit approval (required before Visual DoD / walkthrough unless an agreed preview is documented)
