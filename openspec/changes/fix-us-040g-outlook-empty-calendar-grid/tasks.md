## 1. Empty Week / Month grid persistence

- [x] 1.1 Change `WeekView` so zero-item weeks still render `week-columns` day structure; empty cue (banner/overlay) + clear-filters when filters hid everything; navigation remains usable
- [x] 1.2 Change `MonthCalendarView` so zero-item months still render `calendar-grid` day cells; empty cue + clear-filters when filters hid everything; navigation remains usable
- [x] 1.3 Adjust CSS so empty cue does not displace or hide the calendar chrome (Outlook-like blank days)

## 2. Tests, build, docs honesty

- [x] 2.1 Update Vitest empty week/month cases to assert calendar structure testids remain mounted alongside empty-state cues (and filter-zero clear path)
- [x] 2.2 Update metric zero-match coverage if needed so calendar grid stays present
- [x] 2.3 Run frontend Vitest suite and `npm run build`; refresh worker static assets under `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`
- [x] 2.4 Secrets audit on touched frontend/static paths; `git diff --check` clean
- [x] 2.5 Update `docs/CURRENT-STATE.md` and US-040G product status honestly (empty-grid fix applied; Story accepted / Visual DoD still gated until redeploy + walkthrough); do not close BL-015; do not claim Filters dock removal or Cancelled chip

## 3. Visual DoD + operator walkthrough (post-deploy)

> Leave unchecked until explicit deploy approval and capture/walkthrough.

- [ ] 3.1 Capture Visual DoD — desktop: empty week with day columns visible
- [ ] 3.2 Capture Visual DoD — desktop: empty month with day grid visible
- [ ] 3.3 Capture Visual DoD — mobile: empty week with day columns visible
- [ ] 3.4 Capture Visual DoD — mobile: empty month with day grid visible
- [ ] 3.5 Operator walkthrough confirms Outlook-like empty calendar UX; only then update US-040G empty-state acceptance / Story accepted gates as warranted; keep BL-015 open unless full backlog outcome is also validated
- [ ] 3.6 Update `docs/product/progress-checklist.md` for demonstrated outcomes only

## 4. Lifecycle gates

- [x] 4.1 `/opsx-verify` after implementation (re-run if post-verify edits)
- [x] 4.2 Explicit user approval → implementation commit
- [ ] 4.3 `/opsx-sync` → separate sync commit
- [ ] 4.4 `/opsx-archive` → separate archive commit
- [ ] 4.5 Push only with explicit approval
- [ ] 4.6 Deploy only with explicit approval (required before Visual DoD / walkthrough unless an agreed preview is documented)
