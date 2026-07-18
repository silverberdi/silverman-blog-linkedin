## 1. OpenSpec continuity (retroactive)

- [x] 1.1 Create change artifacts (proposal, design, delta specs, tasks) stating retroactive alignment of the US-040F console-layer redesign
- [x] 1.2 Record design decisions for shell, cards/drawer, metric→filter semantics, time labeling, and “UX still iterating”
- [x] 1.3 Keep delta specs aligned with main US-040F requirements (parity sync target)

## 2. Implementation demonstrated + clarity fixes

- [x] 2.1 App shell: app-bar, session strip, metrics, filter dock, content workspace; endpoint-heavy footer removed from primary chrome
- [x] 2.2 List card triage + selected detail drawer; edit/cancel/schedule drawers
- [x] 2.3 Month calendar remains first-class with compact cells + agenda
- [x] 2.4 Metric chips apply focus filters with reset-then-apply semantics (design D4)
- [x] 2.5 List schedule line clarifies local time display (Month remains UTC day placement)
- [x] 2.6 Vitest US-040F redesign coverage + prior A–E suites still pass; production static assets rebuilt

## 3. Docs and gates

- [x] 3.1 CURRENT-STATE / user-stories / progress-checklist updated for demonstrated US-040F console-layer redesign only
- [x] 3.2 Do not mark Story accepted or BL-015 closed; note further UX iteration expected
- [x] 3.3 Browser screenshot matrix remains incomplete / deferred with explicit note
- [ ] 3.4 Push + deploy only after explicit operator approval (UX direction still open)

## 4. Verify / lifecycle

- [x] 4.1 `/opsx-verify` gates for this change (validate, tasks, tests)
- [ ] 4.2 Implementation commit (change + frontend + static + docs)
- [ ] 4.3 Sync parity commit if needed
- [ ] 4.4 Archive commit
- [ ] 4.5 Push / deploy (hold until UX follow-up decision)
