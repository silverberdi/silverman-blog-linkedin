## 1. Worker local-day density evaluator

- [x] 1.1 Implement shared `evaluate_local_day_density` (or equivalent) per design D1–D3: operator-local day keys, density inclusion set (pending/queued/deferred-pending + published-on-calendar + blog; exclude cancelled/failed), exclude moving item, window expanded for TZ edges
- [x] 1.2 Accept IANA `operator_timezone` on density-gated mutations; validate zoneinfo; env fallback `SILVERMAN_OPERATOR_TIMEZONE`; fail closed with stable timezone-required/invalid code when neither is valid (do not silently use UTC day for K)
- [x] 1.3 Define stable codes distinct from interim saturation/duplicate-slot: e.g. `linkedin_supervision_local_day_density`, `calendar_schedule_local_day_density`, timezone codes (exact names fixed at apply)
- [x] 1.4 Keep interim LinkedIn duplicate-slot + UTC-day/72h saturation and interim blog max-1/UTC-day **additive** (D4); document BL-021 MAY later supersede K
- [x] 1.5 Density evaluation MUST NOT call LinkedIn / DeepSeek / ComfyUI / Git

## 2. Wire density into mutations

- [x] 2.1 Enforce max-2 local-day density on `POST /defer-linkedin-variant` (dry-run validates; real fails closed; accept `operator_timezone`)
- [x] 2.2 Enforce max-2 local-day density on `POST /reopen-linkedin-variant` (dry-run validates; real fails closed; accept `operator_timezone`)
- [x] 2.3 Enforce shared max-2 local-day density on editorial-calendar blog schedule-update (additive to interim blog 1/UTC-day)
- [x] 2.4 Allow self-move same local day when others_on_day ≤ 1 after exclusion; allow moves that reduce occupancy from 3+ days; refuse placements that would yield > 2
- [x] 2.5 Update OpenAPI / request models for optional `operator_timezone` on affected endpoints

## 3. Console density UX

- [x] 3.1 Week/Month calm full cue at 2 density members; distinct over-capacity cue at 3+; do not hide chips (D6)
- [x] 3.2 Client-side density helpers aligned with D1 using schedule-visibility snapshot + `localDayKey` (US-040I)
- [x] 3.3 ScheduleEditor / defer reschedule: prefer prevent/warn saturated local days before commit; send `operator_timezone` on mutations
- [x] 3.4 Reopen schedule pick: same client-side cap + `operator_timezone`; plain-language block for 3rd placement
- [x] 3.5 Map density + timezone error codes in `explainErrorCodes` / toasts to plain language (“This day already has 2 publications”); keep raw codes in diagnostics only
- [x] 3.6 Preserve EventModal fix path for grandfathered 3+ days (move via reschedule/defer); no silent delete/auto-redistribute
- [x] 3.7 Preserve Week default + Month secondary, EventModal + toasts, local-time, cancelled reopen, session/`canMutate`, dry-run/confirm, ADR-0001, `*_utc` wire fields

## 4. Tests, build, and implementation evidence

- [x] 4.1 Pytest: defer refuses 3rd density member; self-move same day allowed; cancelled excluded; published counts; missing TZ fails closed; dry-run no mutation; no LinkedIn call
- [x] 4.2 Pytest: reopen refuses full local day; reopen succeeds onto under-capacity day; local-midnight boundary with fixed TZ (e.g. America/Chicago)
- [x] 4.3 Pytest: blog schedule-update refuses day with 2 LinkedIn density members; additive coexistence with interim blog 1/UTC-day
- [x] 4.4 Pytest: moving one item off a 3+ day onto an empty day succeeds (grandfather reduce path)
- [x] 4.5 Vitest: full cue at 2; over-full 3+ still visible; picker/modal plain-language block for 3rd; Month density cue; local-midnight occupancy matches Week/Month
- [x] 4.6 Vitest viewport matrix at ~1280px and ~375px covering Visual DoD scenes (component/DOM evidence; not Story accepted)
- [x] 4.7 Ensure prior Week/Month/EventModal/ScheduleEditor/session/`canMutate`/local-time/reopen suites still pass
- [x] 4.8 Production `npm run build`; rebuild worker static assets under `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`
- [x] 4.9 Secrets audit on touched worker/frontend/static paths; `git diff --check` clean
- [x] 4.10 If browser capture unavailable locally, record limitation in CURRENT-STATE / notes; do not mark Visual DoD or Story accepted

## 5. Docs honesty (pre-walkthrough)

- [x] 5.1 Update CURRENT-STATE for US-040K implementation status only (not Story accepted; BL-015 open; G/H/I/J Story accepted still gated; note interim vs BL-021)
- [x] 5.2 Update ops docs if density codes / operator_timezone are operator-facing (e.g. supervision mechanics) without claiming Story accepted
- [x] 5.3 Update user-stories / progress-checklist demonstrated checkboxes only for criteria actually shown; leave Acceptance criteria validated and Story accepted unchecked
- [x] 5.4 Do not mark US-040G/H/I/J Story accepted or BL-015 closed as a side effect
- [x] 5.5 Preserve qualified language: never bare “Flow A complete”; density ≠ LinkedIn API published; dry-run ≠ real mutation; K interim MAY be superseded by BL-021

## 6. Visual DoD + operator walkthrough (post-deploy / agreed preview)

> Leave unchecked until after explicit deploy or agreed preview approval and capture/walkthrough. Vitest alone MUST NOT complete this section.

- [ ] 6.1 Capture Visual DoD — desktop: local day at 2 publications (full cue) on Week
- [ ] 6.2 Capture Visual DoD — desktop: Month density cue at 2
- [ ] 6.3 Capture Visual DoD — desktop: attempt to place a 3rd (plain-language block)
- [ ] 6.4 Capture Visual DoD — desktop: existing 3+ day still visible with fix path (EventModal move)
- [ ] 6.5 Capture Visual DoD — desktop: local-midnight boundary occupancy
- [ ] 6.6 Capture Visual DoD — mobile: full cue at 2 (Week and/or Month)
- [ ] 6.7 Capture Visual DoD — mobile: attempt to place a 3rd (plain-language block)
- [ ] 6.8 Capture Visual DoD — mobile: 3+ day visible with fix path
- [ ] 6.9 Capture Visual DoD — mobile: local-midnight boundary (or equivalent boundary communication)
- [ ] 6.10 Operator walkthrough on deployed or explicitly agreed preview; operator confirms max-2 density UX is obvious and prevents a spammy plan
- [ ] 6.11 Only after 6.1–6.10: mark Acceptance criteria validated and Story accepted in product docs; keep BL-015 open; do not close US-040G/H/I/J Story accepted as a side effect

## 7. Lifecycle gates

- [x] 7.1 Explicit approval of this proposal before `/opsx-apply`
- [x] 7.2 `/opsx-apply` implementation of tasks 1–5 (and 4 evidence)
- [x] 7.3 `/opsx-verify` after implementation (re-run if post-verify edits)
- [x] 7.4 Explicit user approval → implementation commit (change + worker + frontend + static + honest docs)
- [x] 7.5 `/opsx-sync` → separate sync commit
- [x] 7.6 `/opsx-archive` → separate archive commit
- [x] 7.7 Push only with explicit approval
- [x] 7.8 Deploy only with explicit approval (required before Visual DoD / walkthrough unless an agreed preview is documented)
- [ ] 7.9 Business validation: section 6 walkthrough complete before Story accepted; BL-015 remains open
