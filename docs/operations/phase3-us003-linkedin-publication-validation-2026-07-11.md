# Phase 3 Report: US-003 / US-004 / US-005 LinkedIn publication validation

**Date:** 2026-07-11  
**Server:** silverman@192.168.0.194  
**Change:** validate-first-real-linkedin-publication  
**Script:** `deploy/server/run-us003-linkedin-publication-validation-smoke.sh`

## OAuth bootstrap (tasks §0)

| Check | Result |
|-------|--------|
| Host `linkedin-oauth/` directory with token + state files (`chmod 600`) | **PASS** — migrated from legacy flat file binds |
| Cloudflare Tunnel `api.silverman.pro` → worker | **PASS** — browser authorization completed |
| OAuth env vars in server `.env` | **PASS** — names present; values not recorded here |
| Browser authorization | **PASS** — operator completed 2026-07-11 |
| `GET /linkedin/oauth/status` — `token_present`, `member_urn`, expiry | **PASS** — `token_present: true`, scopes `openid,profile,w_member_social` |

## Validation window

| Item | Value |
|------|-------|
| Worker service version (`GET /health`) | `0.1.0` |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` during window | `true` (restored `false` after) |
| Campaign id | `flow-a-2026-07-10-a-bounded-context-is-not-a-folder` |
| Variant id | `executive-recruiter` |
| Operator approved real publish | **yes** — editorial post *A Bounded Context Is Not a Folder* |

## Smoke outcome

| Check | Result |
|-------|--------|
| OAuth preflight | **PASS** |
| `POST /queue-linkedin-publication` `dry_run: false` → `queued` | **PASS** |
| `POST /publish-linkedin-due-variants` `dry_run: false`, `publish_now: true` → `published` | **PASS** |
| `linkedin_post_urn` in HTTP response and campaign metadata | **PASS** — `urn:li:share:7481629806233628672` |
| Idempotent repeat publish-due | **PASS** — `linkedin_publish_already_published`; URN unchanged |
| Script `OVERALL` line | **FAIL** — false negative: post-restore `/linkedin/oauth/status` polled before worker ready after container recreate |
| Safeguards after window (manual verify ~5s later) | **PASS** — `.env` and worker `publication_enabled: false` |

### Publish state transitions (`executive-recruiter`)

| Step | `publish_state` | `linkedin_post_urn` | Notes |
|------|-----------------|---------------------|-------|
| Before queue | `pending` | — | |
| After queue | `queued` | — | `publish_after_utc: 2026-07-11T10:45:46Z` |
| After publish | `published` | `urn:li:share:7481629806233628672` | `published_at: 2026-07-11T08:45:48Z` |
| After idempotent rerun | `published` | unchanged | warning `linkedin_publish_already_published` |

## US-004 visibility confirmation (manual)

| Check | Result |
|-------|--------|
| Post visible on operator LinkedIn profile feed/activity | **PASS** — operator confirmed 2026-07-11 |
| `linkedin_post_urn` recorded | **PASS** — see table above |
| `published_at` UTC recorded | **PASS** — `2026-07-11T08:45:48Z` |
| Article link preview with hero image | **Not validated** — post visible as text; no image card preview observed. Expected for v1 text-only API publish; follow-up **BL-009** |

## US-005 safeguard restoration

| Check | Result |
|-------|--------|
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` in `.env` | **PASS** |
| Container recreated after restoration | **PASS** |
| Worker `publication_enabled: false` | **PASS** — verified after health settle |
| Restoration during validation window | `2026-07-11` (same session as publish) |

## Operational fixes discovered during validation

1. **OAuth state write:** Docker file bind-mounts reject atomic rename (`EBUSY`); compose uses writable directory mount `secrets/linkedin-oauth:/secrets/linkedin-oauth` and `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH=/secrets/linkedin-oauth/linkedin-oauth-tokens.json`.
2. **Campaign eligibility:** Production campaign at `flow_a_complete` with `pending` variants; worker extended to allow `distribution_scheduled`, `distribution_complete`, and `flow_a_complete` for publication endpoints.
3. **Smoke script:** Safeguard restore order fixed (`restore` before `SKIP_RESTORE`); post-restore health wait recommended (script may report `OVERALL: FAIL` on timing only).

## User story mapping

| Story | Acceptance criteria demonstrated | Pass |
|-------|----------------------------------|------|
| **US-003** | OAuth/member validation; approved variant; `pending`→`queued`→`published`; clear outcomes | **Pass** |
| **US-004** | URN stored; LinkedIn visibility confirmed; no duplicate external post | **Pass** (preview image deferred to BL-009) |
| **US-005** | Publication safeguards restored after controlled test | **Pass** |

## BL-002

**BL-002 closed** when US-003, US-004, and US-005 are all **Pass** above (2026-07-11).

## Notes

- No API keys, tokens, client secrets, or authorization codes in this report.
- Real LinkedIn post remains on operator profile until manually removed in LinkedIn (out of scope for automation).
- Other variants on the same campaign remain `pending`; only `executive-recruiter` was published.
