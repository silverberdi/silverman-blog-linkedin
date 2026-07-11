## 0. OAuth operator prerequisites (blocking — before validation window)

- [x] 0.1 Create host token store files if absent: `linkedin-oauth-tokens.json` and `linkedin-oauth-state.json` under worker secrets dir with `chmod 600` (Docker file bind-mounts require existing host files — see `phase2-git-publication-validation-2026-07-11.md`) — **done** via `secrets/linkedin-oauth/` directory mount
- [x] 0.2 Confirm Cloudflare Tunnel routes `https://api.silverman.pro` → worker `localhost:8010` for OAuth callback
- [x] 0.3 Confirm OAuth env vars in server `.env` (`SILVERMAN_LINKEDIN_CLIENT_ID`, `SILVERMAN_LINKEDIN_CLIENT_SECRET`, `SILVERMAN_LINKEDIN_REDIRECT_URI`, `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH`) — no secrets in versioned files
- [x] 0.4 Complete browser authorization: `GET /linkedin/oauth/authorize` → consent → successful callback
- [x] 0.5 Verify `GET /linkedin/oauth/status` reports `token_present`, `member_urn`, and actionable expiry metadata (no token cleartext) — must pass before enabling real publish

## 1. Preflight and gap analysis (verify only — minimal code expected)

- [x] 1.1 Verify `GET /linkedin/oauth/status` exists and returns member URN, expiry metadata, and publication-enabled flag without token cleartext
- [x] 1.2 Verify publish-due idempotency for already `published` variants (`linkedin_publish_already_published`, no second API call per `test_idempotent_published_rerun`); implement minimal fix only if verification fails
- [x] 1.3 Confirm selected validation campaign is Flow A `distribution_scheduled` with target variant in `publish_state` `pending` and valid artifact — **used** `flow_a_complete` campaign with `pending` variant (worker eligibility extended during validation)

## 2. US-003 validation smoke script

- [x] 2.1 Create `deploy/server/run-us003-linkedin-publication-validation-smoke.sh` with explicit `--campaign-id` and `--variant` (no auto-detect for real publish); reject Flow B campaigns and non-`pending` variants unless documented operator override
- [x] 2.2 Implement OAuth preflight via `GET /linkedin/oauth/status` with fail-closed abort before real steps
- [x] 2.3 Implement validation window enablement for `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` with container recreate (mirror US-001 pattern) and mandatory restoration to `false` in trap/finally
- [x] 2.4 Implement real queue step (`POST /queue-linkedin-publication`, `dry_run: false`) with variant state snapshots before/after
- [x] 2.5 Implement real publish step (`POST /publish-linkedin-due-variants`, `dry_run: false`, `publish_now: true`) and assert `published` + `linkedin_post_urn`
- [x] 2.6 Implement idempotency rerun (second real publish-due) and assert `linkedin_publish_already_published` (or equivalent) with no duplicate external publication
- [x] 2.7 Ensure script never prints API keys, tokens, or secrets; emit `OVERALL: PASS` / `OVERALL: FAIL`

## 3. Extend shared smoke tooling (optional — skip if US-003 script is self-contained)

- [x] 3.1 Extend `deploy/server/run-linkedin-publication-smoke.sh` with optional `--publish-now` and `--idempotency-rerun` only if US-003 script composes this script instead of inline curl calls — **skipped** (US-003 script is self-contained)
- [x] 3.2 Extend `deploy/server/collect-flow-a-smoke-evidence.sh` to report `linkedin_post_urn` presence for `published` variants (no body text, no tokens)

## 4. Worker code fixes (only if preflight verification in §1 fails)

- [x] 4.1 If idempotency verification in 1.2 fails (unexpected), implement `already_published` publish-due outcome preserving existing URN and metadata — **N/A** (verification passed)
- [x] 4.2 If oauth status diagnostic gaps block preflight, implement minimal fix aligned with `linkedin-oauth-token-lifecycle` spec — **done** — OAuth directory mount + `_atomic_write_json` EBUSY fallback; compose/env path updates
- [x] 4.3 Add or extend unit tests for any worker changes; run targeted pytest for touched modules — **done** — `test_flow_a_complete_campaign_can_queue`; OAuth lifecycle tests pass

## 5. Documentation and operator runbook

- [x] 5.1 Document US-003 controlled validation procedure in deployment/LinkedIn operator docs (OAuth bootstrap §0, enablement window, irreversibility vs US-001/002, visibility checklist, safeguard restoration, HTTP 426 remediation)
- [x] 5.2 Add Phase 3 evidence template under `docs/operations/` for US-003/US-004/US-005 mapping
- [x] 5.3 Reference US-003 script in `docs/deployment/ubuntu-server-worker-deployment.md` alongside US-001/US-002 scripts
- [x] 5.4 Update `docs/CURRENT-STATE.md` — distinguish implemented vs operationally validated LinkedIn publication (do not mark validated until live evidence)
- [x] 5.5 Update `docs/RUNTIME-STATE.md` only after live validation window (enablement flag transitions)

## 6. Business validation (US-003, US-004, US-005)

- [x] 6.1 Confirm tasks §0 OAuth bootstrap complete and `GET /linkedin/oauth/status` green on `192.168.0.194` immediately before validation window
- [x] 6.2 Operator approves one LinkedIn variant for real publication (document campaign id and variant id in Phase 3 report)
- [x] 6.3 Run `run-us003-linkedin-publication-validation-smoke.sh` during approved window; capture queue → queued → published state transitions
- [x] 6.4 Confirm `linkedin_post_urn` in HTTP response and campaign metadata; complete manual LinkedIn visibility checklist (US-004)
- [x] 6.5 Verify idempotent repeat publish-due does not create duplicate LinkedIn post (US-004)
- [x] 6.6 Confirm `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` restored and worker reflects disabled state (US-005)
- [x] 6.7 Write dated Phase 3 report `docs/operations/phase3-us003-linkedin-publication-validation-YYYY-MM-DD.md` with evidence (no secrets)
- [x] 6.8 Update `docs/product/progress-checklist.md` and user-story checkboxes for US-003, US-004, US-005 only when acceptance criteria demonstrated; mark BL-002 complete only when all three stories pass

## 7. Verification gate

- [x] 7.1 Run `/opsx-verify` for this change before commit approval
- [x] 7.2 Run `git diff --check` and secrets audit on modified files
