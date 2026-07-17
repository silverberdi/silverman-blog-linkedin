# Runtime State

Volatile point-in-time operational snapshot. **Not** architectural authority — see [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Durable status: [CURRENT-STATE.md](CURRENT-STATE.md).

Update after deploys, activation changes, smoke tests, external-integration validation, or confirmed revision changes.

## Snapshot

**`verified_at_utc`:** `2026-07-17T18:00:01Z`
**Evidence source:** Post-US-025 archive deploy of accumulated code (US-022 + US-023 worker surface + US-024/US-025 docs already in git) — rsync + rebuild on Ubuntu `192.168.0.194`; container env `BUILD_REVISION`; `verify-worker-deploy.sh` OVERALL PASS; OpenAPI exposes `/validate-linkedin-article-preview`

| Fact | Value | Evidence |
|------|-------|----------|
| Worker URL | `http://192.168.0.194:8010` | Deploy + health check |
| `BUILD_REVISION` | `d15d85b0c5827cc8d0a4fdb5038b01530a009f87` (HEAD after US-025 archive) | Container env after pin rebuild 2026-07-17; `.build_git_sha` on target |
| Editorial mount | `/data/silverman-blog-linkedin` → host `/home/silverman/compartido_mac/silverman-blog-linkedin` | Deploy compose |
| Public blog mount | `/public-blog` → host `/home/silverman/silverberdi.github.io` | Deploy verification |
| n8n Flow A workflow | **Active** (`silvermanFlowAPublish01`, **35** nodes, Schedule `0 9 * * *` UTC, single-flight, includes `/complete-flow-a-ready-path`); repo export `active: false` | Post-resume export check |
| Set Configuration opt-ins (server) | `git_publication=true`, `live_site_confirmation=true`, `update_calendar=true` | Post-activate export check |
| OpenAPI `/complete-flow-a-ready-path` | Present | Live OpenAPI probe |
| `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED` | `true` | Server `.env` |
| `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED` | `true` | Server `.env` |
| `GIT_SSH_COMMAND` | Set (deploy key + known_hosts paths) | Server `.env`; container env present |
| Git publication US-001 | Validated with real push | [phase3-us001 report](operations/phase3-us001-git-publication-validation-2026-07-11.md); BL-005 commits `6daac7a` / `9a0158b` |
| Live-site confirmation US-002 | Validated with HTTP 200 + slug marker | [phase3-us002 report](operations/phase3-us002-live-site-confirmation-validation-2026-07-11.md); BL-005 both posts confirmed |
| BL-001 smoke artifacts | Removed from public site and editorial mount | Cleanup commits on `silverberdi.github.io` |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | `true` (baseline unchanged during US-019/US-020 validation) | [us-019/us-020 validation](operations/us-019-us-020-linkedin-publication-validation-2026-07-17.md) |
| LinkedIn OAuth token store | Configured; `token_present` during validation | Directory mount `secrets/linkedin-oauth/` |
| LinkedIn API real publish US-003 | Validated — one variant `published` with URN | [phase3-us003 report](operations/phase3-us003-linkedin-publication-validation-2026-07-11.md) |
| ComfyUI image generation | Enabled during Flow A validation smoke | Operator confirmation; exact env names only |
| n8n Flow A schedule activated (US-010) | Server workflow `active: true` with daily 09:00 UTC Schedule Trigger | [us-010 validation](operations/us-010-flow-a-n8n-activation-validation-2026-07-15.md); reconfirmed 2026-07-16 |
| LinkedIn publication guard (US-011) | Validated — fail-closed when disabled; Flow A has no LinkedIn API path; baseline restored `true` | [us-011 validation](operations/us-011-linkedin-publication-guard-validation-2026-07-15.md) |
| Fully unattended Flow A (BL-005) | **Closed** — Manual Post A + Schedule Post B both `flow_a_complete`; no LinkedIn API publish | [bl-005 ops](operations/bl-005-unattended-flow-a-validation-2026-07-15.md) |
| Calendar LinkedIn summaries (BL-003) | Validated — calendar items include BL-005 completed rows with `flow_a_completion` | Reconcile + BL-005 upserts |
| Scheduled LinkedIn publication (BL-007 / US-018–US-020) | **Closed** — US-018 + US-019 evidence + US-020 sequence/cadence validated on `BUILD_REVISION=3c4d9f5`; n8n publish-pending export stays `active: false` | [us-018](operations/us-018-scheduled-linkedin-publication-validation-2026-07-16.md); [us-019/us-020](operations/us-019-us-020-linkedin-publication-validation-2026-07-17.md) |
| Preview input verification US-023 | Validated — real failure detected, live-site OG remediation (`silverberdi.github.io` `e4d10de`), passing real runs with persisted evidence on both 2026-07-15 campaigns | [us-023 validation](operations/us-023-linkedin-preview-input-validation-2026-07-17.md) |
| Preview rendering confirmation US-024 | Demonstrated — post-publish observation `preview_not_rendered_post_format` on `keep-contracts-boring`; Post Inspector outage recorded as `confirmation_blocked` | [blocked](operations/us-024-preview-confirmation-blocked-2026-07-17.md); [post-publish](operations/us-024-preview-confirmation-keep-contracts-boring-2026-07-17.md) |
| Preview fallback decision US-025 | Demonstrated — `fallback_accept_rendering` + `fallback_format_change_deferred`, zero metadata/budget impact | [us-025 decision](operations/us-025-preview-fallback-decision-keep-contracts-boring-2026-07-17.md) |
| Real publishes 2026-07-17 (targeted, operator-approved) | `domain-first :: executive-recruiter` → `urn:li:share:7483952071243898881` (18:33:39Z); `keep-contracts-boring :: executive-recruiter` → `urn:li:share:7483953784612786177` (18:40:27Z); `a-bounded-context :: engineering-leadership` → `urn:li:share:7483974070842241024` (20:01:04Z, attempt #2 after controlled failure); all replay-idempotent | Publish-due responses + stored US-019 evidence |
| Retry/recovery US-021/US-022 | Validated on primary chain — controlled transport failure, uncertain classification, attested re-queue, successful retry, evidence preserved; container hosts injection reverted | [us-021/us-022 validation](operations/us-021-us-022-linkedin-retry-recovery-validation-2026-07-17.md) |
| Public blog OG metadata | `og:image` + description from front matter + `site.url=https://silverman.pro` live since `e4d10de` (2026-07-17) | Live OG tag check post-deploy |

## Unverified / unknown

| Fact | Status |
|------|--------|
| DeepSeek API quota / rate limits | `unknown` |
| ComfyUI availability right now | `unknown` — check before image-dependent publish |

## Operator notes

- Repo export stays `active: false`; server may be `active: true`.
- Ready-path Set Configuration git/live defaults remain `false` in git; server prepared import patched to `true` for BL-005.
- US-018 (`auto_queue_pending`) previously deployed at `c7bce02`; superseded by `3c4d9f5` for US-019/US-020; superseded by `d15d85b` for accumulated US-022/US-023 (+ US-025 archive HEAD). Docs-only RUNTIME-STATE follow-up is `b3eba03` and does not require redeploy.
- After US-019/US-020 validation: `technical-architect` on the 2026-07-06 campaign and `engineering-leadership` on the deferring campaign remain `queued` (cadence-blocked, no URN) until ≥72h after their campaign’s last `published_at`.
- New cadence anchors from 2026-07-17 publishes: `domain-first` next variant eligible ~2026-07-20T18:33Z; `keep-contracts-boring` next variant eligible ~2026-07-20T18:40Z; `a-bounded-context` next variant eligible ~2026-07-20T20:01Z.
- Deployed ≠ operationally validated (BL-008): US-022 primary chain validated 2026-07-17; correction/cancel/exhaustion paths remain unit-test scope.
- Pages live-confirmation can 404 briefly after push; resume after HTTP 200 (documented in BL-005).
- Deployed ≠ operationally validated: US-022 (BL-008) still needs controlled demonstration before story acceptance. BL-009 (US-023/US-024/US-025) demonstrated and accepted 2026-07-17 — backlog item closed.
