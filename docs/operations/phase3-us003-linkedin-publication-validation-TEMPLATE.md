# Phase 3 Report: US-003 / US-004 / US-005 LinkedIn publication validation

**Date:** YYYY-MM-DD  
**Server:** silverman@192.168.0.194  
**Change:** validate-first-real-linkedin-publication  
**Script:** `deploy/server/run-us003-linkedin-publication-validation-smoke.sh`

## OAuth bootstrap (tasks §0)

| Check | Result |
|-------|--------|
| Host `linkedin-oauth-tokens.json` + `linkedin-oauth-state.json` (chmod 600) | |
| Cloudflare Tunnel `api.silverman.pro` → `localhost:8010` | |
| OAuth env vars in server `.env` (no secrets in repo) | |
| Browser authorization completed | |
| `GET /linkedin/oauth/status` — `token_present`, `member_urn`, expiry metadata | |

## Validation window

| Item | Value |
|------|-------|
| Worker service version (`GET /health`) | |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` during window | `true` |
| Campaign id | |
| Variant id | |
| Operator approved variant for real publish | yes / no |

## Smoke outcome

| Check | Result |
|-------|--------|
| OAuth preflight (`GET /linkedin/oauth/status`) | |
| `POST /queue-linkedin-publication` `dry_run: false` → `queued` | |
| `POST /publish-linkedin-due-variants` `dry_run: false`, `publish_now: true` → `published` | |
| `linkedin_post_urn` in HTTP response and campaign metadata | |
| Idempotent repeat publish-due (`linkedin_publish_already_published`, no duplicate post) | |
| Script `OVERALL` | PASS / FAIL |

### Publish state transitions

| Step | `publish_state` | `linkedin_post_urn` | Notes |
|------|-----------------|---------------------|-------|
| Before queue | | | |
| After queue | | | |
| After publish | | | |
| After idempotent rerun | | | unchanged |

## US-004 visibility confirmation (manual)

| Check | Result |
|-------|--------|
| Post visible on operator LinkedIn profile feed/activity | |
| `linkedin_post_urn` recorded | |
| `published_at` UTC recorded | |
| Optional public post URL | |

## US-005 safeguard restoration

| Check | Result |
|-------|--------|
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` restored | |
| Container recreated after restoration | |
| `GET /linkedin/oauth/status` `publication_enabled: false` | |
| Restoration timestamp (UTC) | |

## User story mapping

| Story | Acceptance criteria demonstrated | Pass |
|-------|----------------------------------|------|
| **US-003** | OAuth/member validation; one approved variant; state transitions; clear outcomes | |
| **US-004** | URN stored; LinkedIn visibility confirmed; no duplicate external post | |
| **US-005** | Publication safeguards restored after controlled test | |

## BL-002

Mark **BL-002** complete only when US-003, US-004, and US-005 are all **Pass** above.

## Notes

- No API keys, tokens, client secrets, or authorization codes in this report.
- Real LinkedIn post may remain visible until operator deletes manually in LinkedIn (out of scope for automation).
