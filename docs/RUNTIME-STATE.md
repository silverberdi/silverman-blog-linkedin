# Runtime State

Volatile point-in-time operational snapshot. **Not** architectural authority — see [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Durable status: [CURRENT-STATE.md](CURRENT-STATE.md).

Update after deploys, activation changes, smoke tests, external-integration validation, or confirmed revision changes.

## Snapshot

**`verified_at_utc`:** `2026-07-16T14:26:47Z`
**Evidence source:** BL-005 dual Manual+Schedule closure — Post A/B both `flow_a_complete`; Schedule fire `2026-07-16T09:01Z` + post-lag resume `14:26Z`; Ubuntu server `192.168.0.194`

| Fact | Value | Evidence |
|------|-------|----------|
| Worker URL | `http://192.168.0.194:8010` | Deploy + health check |
| `BUILD_REVISION` | `1784157627` (timestamp fallback; target layout has no `.git`; content from clean HEAD `da21e99`) | Deploy 2026-07-15; still serving BL-005 window |
| Editorial mount | `/data/silverman-blog-linkedin` | `deploy-worker.sh` compose |
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
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | `true` (US-011 window: baseline `true` → temporary `false` → restored `true`) | [us-011 validation](operations/us-011-linkedin-publication-guard-validation-2026-07-15.md) |
| LinkedIn OAuth token store | Configured; `token_present` during validation | Directory mount `secrets/linkedin-oauth/` |
| LinkedIn API real publish US-003 | Validated — one variant `published` with URN | [phase3-us003 report](operations/phase3-us003-linkedin-publication-validation-2026-07-11.md) |
| ComfyUI image generation | Enabled during Flow A validation smoke | Operator confirmation; exact env names only |
| n8n Flow A schedule activated (US-010) | Server workflow `active: true` with daily 09:00 UTC Schedule Trigger | [us-010 validation](operations/us-010-flow-a-n8n-activation-validation-2026-07-15.md); reconfirmed 2026-07-16 |
| LinkedIn publication guard (US-011) | Validated — fail-closed when disabled; Flow A has no LinkedIn API path; baseline restored `true` | [us-011 validation](operations/us-011-linkedin-publication-guard-validation-2026-07-15.md) |
| Fully unattended Flow A (BL-005) | **Closed** — Manual Post A + Schedule Post B both `flow_a_complete`; no LinkedIn API publish | [bl-005 ops](operations/bl-005-unattended-flow-a-validation-2026-07-15.md) |
| Calendar LinkedIn summaries (BL-003) | Validated — calendar items include BL-005 completed rows with `flow_a_completion` | Reconcile + BL-005 upserts |

## Unverified / unknown

| Fact | Status |
|------|--------|
| DeepSeek API quota / rate limits | `unknown` |
| ComfyUI availability right now | `unknown` — check before image-dependent publish |

## Operator notes

- Repo export stays `active: false`; server may be `active: true`.
- Ready-path Set Configuration git/live defaults remain `false` in git; server prepared import patched to `true` for BL-005.
- Do not mix BL-007 WIP into deploy trees; last deploy used `git archive` clean HEAD.
- Pages live-confirmation can 404 briefly after push; resume after HTTP 200 (documented in BL-005).
