## 1. Filters modal chrome

- [x] 1.1 Add header **Filters** control to `AppShell` app-bar (near view switch / refresh); label prefer Filters per design D1
- [x] 1.2 Implement `FiltersModal` (or equivalent) hosting existing `Filters` controls: Channel, Campaign/label, Blocked only, Due soon (48h), publication states (including `completed` / Published on blog when present), Reset, hidden-critical banner
- [x] 1.3 Remove always-visible `filter-dock` / FOCUS/Filters strip from primary chrome so Week/Month are not permanently preceded by a full filter panel
- [x] 1.4 Modal a11y: `role="dialog"`, Escape + backdrop dismiss, keyboard focus trap, visible focus rings; usable at ~375px (D4)
- [x] 1.5 Closing the modal MUST NOT clear shared filter state

## 2. Active-filter cue and chip coherence

- [x] 2.1 Add helper comparing `FilterState` to `defaultFilters()` (D3); expose calm badge/count (or equivalent) on header Filters when any non-default filter is active
- [x] 2.2 Cue clears when filters return to defaults via Reset or empty-state Clear filters
- [x] 2.3 Metric chips remain one-click focus shortcuts on shared filter state without requiring the modal
- [x] 2.4 Opening Filters modal after a chip focus MUST reflect the resulting filter controls
- [x] 2.5 Preserve Week/Month empty-state Clear filters paths (`resetFilters`) without requiring the modal

## 3. Preserve baselines (no regressions)

- [x] 3.1 Preserve Week default + Month secondary; do not restore List as primary chrome
- [x] 3.2 Preserve EventModal + toasts, local-time (US-040I), cancelled reopen (US-040J), density cues (US-040K), session/`canMutate`, dry-run/confirm, ADR-0001, `*_utc` wire fields
- [x] 3.3 Do not change US-040M completed-blog mapping; keep `completed` checkbox when present
- [x] 3.4 No new worker endpoints; no LinkedIn API publish from console; no public URL / Google OIDC / BFF / user-management; no n8n Execute Command; no browser mount writes

## 4. Tests, build, and implementation evidence

- [x] 4.1 Vitest: permanent filter-dock absent; header Filters opens modal with full control set
- [x] 4.2 Vitest: active cue when filtered; cue clears on reset; modal state survives dismiss
- [x] 4.3 Vitest: metric chip focus applies without modal; modal reflects chip state when opened
- [x] 4.4 Vitest: Week/Month empty Clear filters still resets shared state
- [x] 4.5 Vitest viewport matrix at ~1280px and ~375px covering Visual DoD scenes (component/DOM evidence; not Story accepted)
- [x] 4.6 Ensure prior Week/Month/EventModal/ScheduleEditor/session/`canMutate`/local-time/reopen/density suites still pass
- [x] 4.7 Production `npm run build`; rebuild worker static assets under `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`
- [x] 4.8 Secrets audit on touched frontend/static paths; `git diff --check` clean
- [x] 4.9 If browser capture unavailable locally, record limitation in CURRENT-STATE / notes; do not mark Visual DoD or Story accepted
- [x] 4.10 Full pytest not required unless worker/Python touched; if static-only, note skip rationale in verify notes

## 5. Docs honesty (pre-walkthrough)

- [x] 5.1 Update CURRENT-STATE for US-040L implementation status only (not Story accepted; BL-015 open; do not unset US-038–US-040K/M Story accepted)
- [x] 5.2 Update user-stories / progress-checklist demonstrated checkboxes only for criteria actually shown; leave Acceptance criteria validated and Story accepted unchecked
- [x] 5.3 Do not mark BL-015 closed; do not change US-040M mapping docs as part of L
- [x] 5.4 Preserve qualified language: never bare “Flow A complete”; filters modal ≠ LinkedIn API published; dry-run ≠ real mutation

## 6. Visual DoD + operator walkthrough (post-deploy / agreed preview)

> Leave unchecked until after explicit deploy or agreed preview approval and capture/walkthrough. Vitest alone MUST NOT complete this section.

- [ ] 6.1 Capture Visual DoD — desktop: header Filters control visible
- [ ] 6.2 Capture Visual DoD — desktop: modal opens with full filter set
- [ ] 6.3 Capture Visual DoD — desktop: active-filter badge when filtered
- [ ] 6.4 Capture Visual DoD — desktop: Week/Month uncluttered without permanent dock
- [ ] 6.5 Capture Visual DoD — desktop: metric chip focus still works; modal reflects state
- [ ] 6.6 Capture Visual DoD — desktop: Reset / clear paths remain obvious
- [ ] 6.7 Capture Visual DoD — mobile: header Filters + modal usable (~375)
- [ ] 6.8 Capture Visual DoD — mobile: active-filter badge when filtered
- [ ] 6.9 Capture Visual DoD — mobile: Week/Month uncluttered; chip focus + clear paths
- [ ] 6.10 Operator walkthrough on deployed or explicitly agreed preview; operator confirms calendar feels cleaner and filters remain discoverable
- [ ] 6.11 Only after 6.1–6.10: mark Acceptance criteria validated and Story accepted in product docs; keep BL-015 open; do not unset US-038–US-040K/M Story accepted as a side effect

## 7. Lifecycle gates

- [x] 7.1 Explicit approval of this proposal before `/opsx-apply`
- [x] 7.2 `/opsx-apply` implementation of tasks 1–5 (and 4 evidence)
- [x] 7.3 `/opsx-verify` after implementation (re-run if post-verify edits)
- [x] 7.4 Explicit user approval → implementation commit (change + frontend + static + honest docs)
- [x] 7.5 `/opsx-sync` → separate sync commit
- [ ] 7.6 `/opsx-archive` → separate archive commit
- [ ] 7.7 Push only with explicit approval
- [ ] 7.8 Deploy only with explicit approval (required before Visual DoD / walkthrough unless an agreed preview is documented)
- [ ] 7.9 Business validation: section 6 walkthrough complete before Story accepted; BL-015 remains open
