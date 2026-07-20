## 1. Inspect and lock scope

- [x] 1.1 Confirm US-083 acceptance criteria in `docs/product/user-stories.md` match this change; leave US-084/US-085/US-086 and BL-015 closed
- [x] 1.2 Inventory current LinkedIn label surfaces (`publicationStateLabel`, calendar chips, filters, EventModal status pill, toasts) and existing action gating (`actions`, `scheduleEditable`, `reopenEligible`, `canMutate`)
- [x] 1.3 Decide whether any schedule-visibility / pending-supervision read fields are required for truthful availability; default to console-only if existing fields suffice

## 2. Operator-language status labels

- [x] 2.1 Map LinkedIn display states to primary labels: pending→Scheduled, queued/(publishing)→Waiting to send, published/`linkedinApiPublished`→Live on LinkedIn, failed→Failed, cancelled→Cancelled
- [x] 2.2 Keep blog `completed` → Published on blog; ensure colors/filters remain distinct from Live on LinkedIn
- [x] 2.3 Add short helper copy where needed so Waiting to send / queued is unmistakably not LinkedIn API published
- [x] 2.4 Demote technical `publish_state` / `publication_state` to diagnostics (or secondary text) without removing operator access to them

## 3. Action availability matrix

- [x] 3.1 Add EventModal (LinkedIn) “What you can do now” matrix listing available vs unavailable controls with plain-language reasons
- [x] 3.2 Wire available controls to existing eligibility only (edit/cancel-pending/reschedule-defer/reopen + `canMutate`)
- [x] 3.3 Show cancel-queued and publish now as unavailable / not available yet (US-085 / US-086) — do not implement those mutations
- [x] 3.4 Ensure blocked states (no mutate session, schedule block reason, reopen ineligible, failed/critical) are clearly communicated

## 4. Dry-run vs real clarity

- [x] 4.1 Strengthen preview vs real labeling before submit for edit, cancel-pending, reopen, and ScheduleEditor defer/reschedule
- [x] 4.2 Ensure success toasts/outcomes for dry-run cannot be read as saved schedule, real cancel, or live on LinkedIn
- [x] 4.3 Ensure real success outcomes state committed/saved without false LinkedIn live claims

## 5. Worker read-model (only if required)

- [x] 5.1 If 1.3 requires it: add minimal additive honesty fields to schedule-visibility and/or pending-supervision (no new mutation routes)
- [x] 5.2 If worker touched: update pytest for read mapping / non-mutation; otherwise skip

## 6. Tests, assets, and docs

- [x] 6.1 Add/adjust Vitest for label map, queued≠live, blog≠LinkedIn live, action matrix availability/unavailability, and dry-run vs real outcome copy (~1280/~375 as applicable)
- [x] 6.2 Rebuild static console assets into worker static path
- [x] 6.3 Update `docs/CURRENT-STATE.md` if console product-role language changes (control-center foundation / honest status); do not claim Story accepted
- [x] 6.4 Run targeted Vitest (+ pytest if worker changed); `git diff --check`; secrets audit on touched files

## 7. Business validation

- [ ] 7.1 After explicit deploy approval (separate from apply): operator walkthrough that US-083 AC are visible on the live console
- [x] 7.2 Update `docs/product/progress-checklist.md` and US-083 status only for demonstrated criteria; leave US-084–US-086 and BL-015 untouched
- [x] 7.3 Confirm non-goals held: no publish-now path, no cancel-queued mutation, no US-084 reschedule redesign, no ADR-0001 / enablement bypass

> Deployed 2026-07-20 on `192.168.0.194:8010` (live assets `index-C4S9vr3i.js` / `index-BEnefPLS.css`; deploy verify OVERALL PASS). 7.1 remains open until the operator walkthrough closes Story accepted.
