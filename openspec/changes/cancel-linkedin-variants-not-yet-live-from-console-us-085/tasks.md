## 1. Inspect and lock scope

- [x] 1.1 Confirm US-085 ACs match this change (cancel Scheduled/`pending` and Waiting to send/`queued`; confirmation + preview honesty; post-real Cancelled + no publish actions; reopen restore; plain failures); leave US-086 out; keep BL-015 closed; preserve US-083/US-084
- [x] 1.2 Inventory existing `POST /cancel-linkedin-publication` / `cancel_linkedin_publication` (pending + queued + failed), EventModal cancel panel (supervision-join gated today), action matrix `cancel_queued` “not available yet”, client `cancelVariant`, and reopen path
- [x] 1.3 Confirm cancel does not call LinkedIn API and is not blocked solely by `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; note any worker gap that would block console ACs

## 2. Worker: confirm cancel SoT (narrow fixes only)

- [x] 2.1 Confirm `pending` → `cancelled` (`pre_queue`) and `queued` → `cancelled` (`post_queue`) with dry-run default, idempotency, `auto_queue_eligible` false, reject `published`
- [x] 2.2 Apply only narrow worker fixes if a console-blocking gap is found (do not redesign cancel state machine; no new cancel route)
- [x] 2.3 Ensure in-flight `publishing` / Live remain non-cancellable with stable codes suitable for console plain-language mapping

## 3. Console: deliberate cancel for pending + queued

- [x] 3.1 Redesign EventModal cancel as a deliberate control for Scheduled and Waiting-to-send (phase-aware copy; distinct from postpone)
- [x] 3.2 Wire queued cancel via schedule-visibility `campaignId`/`variantId` without requiring pending-supervision join; keep pending cancel via existing supervision path
- [x] 3.3 Persist only through `POST /cancel-linkedin-publication`; reuse US-083 dry-run default, mode banner, and explicit confirmation for real cancel
- [x] 3.4 Update action matrix: `cancel_pending` and `cancel_queued` available when eligible + `canMutate`; `publish_now` remains unavailable (US-086)
- [x] 3.5 After real cancel: refresh reads; show Cancelled; withdraw publish/cancel-pending/cancel-queued affordances; keep reopen when eligible (US-040J)
- [x] 3.6 Map cancel failures/blocks to plain language + usable next step (cancel-not-allowed, auth, validation, session, in-flight)

## 4. Docs alignment in-repo

- [x] 4.1 Update `docs/CURRENT-STATE.md` for BL-032 / US-085 control-center cancel capability language; do not claim Story accepted
- [x] 4.2 Do not reopen BL-015; do not mark US-086 done

## 5. Tests, assets, and verification

- [x] 5.1 Pytest: confirm pending + queued cancel (and reject Live); add/adjust only if worker behavior changed; dry-run/idempotency preserved
- [x] 5.2 Vitest: cancel Scheduled; cancel Waiting to send; preview ≠ real; post-real Cancelled + matrix; confirmation required; Live/session blocked; US-083/US-084 regressions (~1280/~375 as applicable)
- [x] 5.3 Rebuild static console assets into worker static path
- [x] 5.4 Run targeted pytest + Vitest; `git diff --check`; secrets audit on touched files

## 6. Business validation

- [ ] 6.1 After explicit deploy approval (separate from apply): operator walkthrough that US-085 ACs work for Scheduled and Waiting to send, confirmation/preview honesty holds, post-cancel Cancelled + reopen path clear
- [ ] 6.2 Update `docs/product/progress-checklist.md` and US-085 status only for demonstrated criteria; leave US-086 and BL-015 closed/untouched; do not mark Story accepted by code alone
- [x] 6.3 Confirm non-goals held: no publish-now / LinkedIn API path, no ADR-0001 / enablement bypass for publication, no second cancel pipeline, no BL-015 reopen
