# Tasks: implement-scheduled-linkedin-publication-execution-us-018

## 1. Pre-implementation review

- [x] 1.1 Re-read canonical `openspec/specs/linkedin-publication-integration/spec.md`, the US-017 supervision mechanics doc, and `docs/product/bl-007-auto-queue-pending-handoff.md`; confirm this change's delta specs do not conflict with US-019/US-020 boundaries
- [x] 1.2 Inventory local WIP state (`git status`, `git stash list`): confirm which WIP artifacts exist in the working tree vs must be recreated (worker `auto_queue_pending` code and tests are not on `main`; `deploy/server/run-publish-pending-linkedin-variants.sh`, `deploy/server/finish-pending-linkedin-publication.sh`, and `n8n/workflows/silverman-blog-linkedin-publish-pending.json` are untracked) — absorb/rewrite each against the approved delta specs, never merge blindly

## 2. Worker implementation (`linkedin_publication_flow.py`)

- [x] 2.1 Add `auto_queue_pending` parameter (default `False`) to `publish_linkedin_due_variants`; default-off path must leave existing behavior byte-for-byte identical
- [x] 2.2 Implement pending-target collection: bounded scan over `metadata/campaigns/*.json` (reuse `_list_campaign_ids`), filtered to `flow_a` + `distribution_scheduled`, honoring `campaign_id`/`variant` filters; unreadable or ineligible campaigns skip without failing the run
- [x] 2.3 Implement due evaluation: `scheduled_at_utc <= now_utc` (UTC-aware parse; missing/unparsable schedule ⇒ skip with stable reason); `publish_now=true` bypasses the schedule gate only
- [x] 2.4 Implement eligibility exclusions per US-017 contract (design D3 normative rule): skip when `publish_state` is not `pending` (including `failed` — no automatic re-queue), when `cancelled`, or when `operator_supervision.auto_queue_eligible` is `false` — except defer runtime re-evaluation: `last_action` `defer` with deferred `scheduled_at_utc <= now_utc` ⇒ eligible without persisted flip; `publish_now` never overrides supervision exclusions nor bypasses a deferred time still in the future
- [x] 2.5 Auto-queue eligible variants by reusing the existing queue service logic (safety delay, `publish_after_utc`, artifact hash and source URL validation, metadata writes); no re-queue of already-`queued` variants
- [x] 2.6 Extend `LinkedInPublishDueResult` (and per-variant results) with auto-queue phase outcomes and stable skip codes `linkedin_publish_auto_queue_skipped_not_due`, `linkedin_publish_auto_queue_skipped_supervision`, `linkedin_publish_auto_queue_skipped_state`; no variant body text or secrets in results
- [x] 2.7 Ensure dry-run combined path performs zero mutation and zero LinkedIn/OAuth calls while reporting planned queue + publish outcomes

## 3. HTTP contract (`main.py`)

- [x] 3.1 Add optional `auto_queue_pending` (default `false`) to the publish-due request model (`extra="forbid"` preserved); reject `variant` without `campaign_id` with HTTP 422
- [x] 3.2 Surface auto-queue phase results and skip reasons in the JSON response; add structured logging for auto-queue counts (queued/published/skipped) without secrets

## 4. Tests (`tests/test_linkedin_publication.py`)

- [x] 4.1 `auto_queue_pending` default false: `pending` variants untouched; existing publish-due tests still pass unchanged
- [x] 4.2 Happy path: due eligible `pending` variant is queued and published once with mocked LinkedIn client (`publish_now=true`, `dry_run=false`, enablement on)
- [x] 4.3 Eligibility exclusions: not-due schedule skip, `cancelled` skip, deferred-not-yet-due skip (persisted `auto_queue_eligible=false` from defer), `failed` not auto-requeued — each with the documented stable skip code and no state mutation
- [x] 4.4 Deferred variant becomes eligible at runtime when new `scheduled_at_utc` is due, without a persisted `auto_queue_eligible` flip (`last_action=defer`, `auto_queue_eligible=false` in fixture)
- [x] 4.5 `publish_now=true` bypasses the schedule gate for strategy-default variants but never queues cancelled variants nor deferred variants whose new schedule is still in the future
- [x] 4.6 Once-only: repeat combined real run makes no second LinkedIn API call, preserves `linkedin_post_urn`/`published_at`, and does not rewrite queue metadata of already-`queued` variants
- [x] 4.7 Fail-closed: real combined run with enablement off returns `linkedin_publish_not_enabled`, no API call, no variant marked `failed`; dry-run combined run performs no mutation and no LinkedIn/OAuth calls
- [x] 4.8 HTTP: `auto_queue_pending` accepted and defaults false; unknown fields 422; `variant` without `campaign_id` 422; auth still required
- [x] 4.9 Safety-delay two-gate behavior: auto-queued variant with future `publish_after_utc` and `publish_now=false` ends the call `queued` with a visible not-yet-due outcome
- [x] 4.10 Workflow guard test: publish-pending n8n export has `"active": false`, default configuration `dry_run: true`, and no Execute Command nodes; no other n8n workflow JSON modified by this change

## 5. Operator tooling and n8n export (absorb WIP)

- [x] 5.1 Finalize `deploy/server/run-publish-pending-linkedin-variants.sh` against the approved contract: dry-run default, `--real` preflights `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`, `--respect-schedule` ⇒ `publish_now=false`, `--variant` requires `--campaign-id`, never prints secrets, reports per-variant outcome and overall pass/fail
- [x] 5.2 Finalize `deploy/server/finish-pending-linkedin-publication.sh` (Mac-side scp + run helper; HTTP-only, no worker bypass)
- [x] 5.3 Finalize `n8n/workflows/silverman-blog-linkedin-publish-pending.json`: manual trigger, health check, publish-due HTTP call with `auto_queue_pending: true`, `"active": false`, default configuration `dry_run: true` (fix current WIP default `false`), no Execute Command, no real credentials in export

## 6. Documentation

- [x] 6.1 Update LinkedIn publication operator docs: combined `auto_queue_pending` path, due semantics vs safety delay, supervision exclusions, script usage, and explicit statement that canonical two-step remains available and workflow import ≠ unattended automation
- [x] 6.2 Update `docs/CURRENT-STATE.md`: US-018 auto-queue implemented (not operationally validated); replace BL-007 "construction WIP" note with formalized status; keep BL-007 open and US-019/US-020 deferred
- [x] 6.3 Update `docs/product/bl-007-auto-queue-pending-handoff.md` to record the WIP was absorbed under this approved change

## 7. Verification and commit gates (approval-gated)

- [x] 7.1 Run targeted tests (`pytest tests/test_linkedin_publication.py`) then full `pytest`; zero new warnings; `git diff --check` clean; secrets audit on new/modified files
- [x] 7.2 Run `/opsx-verify`; fix findings and re-run if any post-verify edits
- [ ] 7.3 Implementation commit with explicit user approval (stage explicit paths only; exclude unrelated files); then `/opsx-sync` and `/opsx-archive` as separate approved commits

## 8. Operational validation (separate gated step — not implied by implementation commit)

- [ ] 8.1 With explicit user approval: push, deploy to `192.168.0.194`, confirm `BUILD_REVISION` via `/health` matches the implementation commit
- [ ] 8.2 Dry-run smoke on server via `run-publish-pending-linkedin-variants.sh` (no flags): verify identify/queue/publish plan, skip reasons, and zero mutation evidence
- [ ] 8.3 With explicit user approval, controlled real window: verify once-only publish (URN evidence, repeat-run idempotency), supervision exclusions respected, then restore `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` per policy and record evidence in `docs/operations/`
- [ ] 8.4 Business validation: demonstrate each US-018 acceptance criterion against evidence; update `docs/product/user-stories.md` US-018 checkboxes and `docs/product/progress-checklist.md` only for demonstrated criteria; keep BL-007 open (US-019/US-020 pending)
