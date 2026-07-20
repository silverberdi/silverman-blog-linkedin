## 1. Inspect and lock scope

- [x] 1.1 Confirm US-086 ACs match this change (publish now for eligible variants; confirmation + enablement fail-closed + once-only; Live + URN on success; plain blocks/failures; no SSH for routine happy path); keep BL-015 closed; preserve US-083/US-084/US-085
- [x] 1.2 Inventory `POST /publish-linkedin-due-variants` / `publish_linkedin_due_variants` (`publish_now`, `auto_queue_pending`, dry-run, enablement, sequence/cadence, URN), EventModal action matrix `publish_now` “not available yet”, and missing typed publish-due client
- [x] 1.3 Confirm targeted `campaign_id` + `variant` paths for queued (`publish_now`) and pending (`auto_queue_pending` + `publish_now`); note deferred-future exclusion and any worker gap that would block console ACs

## 2. Worker: confirm publish-due SoT (narrow fixes only)

- [x] 2.1 Confirm targeted queued publish with `publish_now` true; pending with `auto_queue_pending` + `publish_now`; dry-run default; fail closed when not enabled; sequence/cadence/once-only unchanged
- [x] 2.2 Apply only narrow worker/read-model fixes if a console-blocking gap is found (optional schedule-visibility `linkedin_post_urn` for Live re-open verification; no new publish route; do not redesign publish-due)
- [x] 2.3 Ensure Live / in-flight / cancelled remain non-targets for new send; deferred future pending skipped under existing rules

## 3. Console: deliberate publish now + matrix

- [x] 3.1 Add typed client method + types for `POST /publish-linkedin-due-variants` (targeted body: `campaign_id`, `variant`, `dry_run`, `publish_now`, `auto_queue_pending` when pending)
- [x] 3.2 Add EventModal publish-now panel: Preview vs real, mode banner, explicit confirmation for real; copy states LinkedIn API send now (distinct from postpone/cancel)
- [x] 3.3 Wire Waiting to send via `publish_now` only; wire Scheduled via `auto_queue_pending` + `publish_now`; identity from schedule-visibility without requiring pending-supervision join
- [x] 3.4 Update action matrix: `publish_now` available when eligible + `canMutate`; supersede “not available yet (US-086)”; keep postpone and cancel distinct when eligible
- [x] 3.5 After real success: refresh reads; show Live on LinkedIn + traceable URN; withdraw publish-now for that Live item
- [x] 3.6 Map enablement-off / cadence / sequence / config / platform failures to plain language + usable next step; preview MUST NOT claim Live

## 4. Docs alignment in-repo

- [x] 4.1 Update `docs/CURRENT-STATE.md` for BL-032 / US-086 control-center publish-now capability language; do not claim Story accepted
- [x] 4.2 Do not reopen BL-015; do not mark US-086 / BL-032 Story accepted by code alone

## 5. Tests, assets, and verification

- [x] 5.1 Pytest: confirm targeted publish_now (+ auto_queue_pending for pending); enablement fail-closed; cadence/sequence; once-only URN; add/adjust only if worker/read-model changed
- [x] 5.2 Vitest: publish Waiting to send; publish Scheduled; preview ≠ Live; real Live + URN; matrix; enablement/block reasons; Live non-target; US-083/US-084/US-085 regressions (postpone + cancel still distinct)
- [x] 5.3 Rebuild static console assets into worker static path
- [x] 5.4 Run targeted pytest + Vitest; `git diff --check`; secrets audit on touched files

## 6. Business validation

- [ ] 6.1 After explicit deploy approval (separate from apply): operator walkthrough that US-086 ACs work (eligible publish now, confirmation, Live + URN, plain failures, no SSH for routine happy path)
- [ ] 6.2 Update `docs/product/progress-checklist.md` and US-086 status only for demonstrated criteria; leave BL-015 closed; do not mark Story accepted by code alone
- [x] 6.3 Confirm non-goals held: no second publish pipeline, no ADR-0001 / enablement bypass, no cancel/postpone regression, no BL-015 reopen
