# Runtime State

Volatile point-in-time operational snapshot. **Not** architectural authority — see [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Durable status: [CURRENT-STATE.md](CURRENT-STATE.md).

Update after deploys, activation changes, smoke tests, external-integration validation, or confirmed revision changes.

## Snapshot

**`verified_at_utc`:** `2026-07-15T21:43:03Z`
**Evidence source:** US-011 LinkedIn publication-guard validation; US-010 Flow A n8n activation; US-009 identity; BL-003 calendar LinkedIn summary; prior US-001/US-002/US-003 Phase 3 reports; deploy on Ubuntu server `192.168.0.194`

| Fact | Value | Evidence |
|------|-------|----------|
| Worker URL | `http://192.168.0.194:8010` | Deploy + health check |
| `BUILD_REVISION` | `1784088086` (timestamp fallback; server target layout has no `.git`) | Deploy output 2026-07-15; BL-003 smoke |
| Editorial mount | `/data/silverman-blog-linkedin` | `deploy-worker.sh` compose |
| Public blog mount | `/public-blog` → host `/home/silverman/silverberdi.github.io` | Deploy verification |
| n8n Flow A workflow | **Active** on server (`silvermanFlowAPublish01`, 31 nodes, Schedule `0 9 * * *` UTC, single-flight); repo export `active: false` | [us-010 validation](operations/us-010-flow-a-n8n-activation-validation-2026-07-15.md) |
| `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED` | `true` | Server `.env` |
| `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED` | `true` | Server `.env` |
| `GIT_SSH_COMMAND` | Set (deploy key + known_hosts paths) | Server `.env`; container env present |
| Git publication US-001 | Validated with real push | [phase3-us001 report](operations/phase3-us001-git-publication-validation-2026-07-11.md) |
| Live-site confirmation US-002 | Validated with HTTP 200 + slug marker | [phase3-us002 report](operations/phase3-us002-live-site-confirmation-validation-2026-07-11.md) |
| BL-001 smoke artifacts | Removed from public site and editorial mount | Cleanup commits on `silverberdi.github.io` |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | `true` (US-011 window: baseline `true` → temporary `false` → restored `true`) | [us-011 validation](operations/us-011-linkedin-publication-guard-validation-2026-07-15.md); prior [us-009 §5.5](operations/us-009-canonical-flow-a-n8n-identity-validation-2026-07-15.md) |
| LinkedIn OAuth token store | Configured; `token_present` during validation | Directory mount `secrets/linkedin-oauth/`; [phase3-us003 report](operations/phase3-us003-linkedin-publication-validation-2026-07-11.md) |
| LinkedIn API real publish US-003 | Validated — one variant `published` with URN | [phase3-us003 report](operations/phase3-us003-linkedin-publication-validation-2026-07-11.md) |
| ComfyUI image generation | Enabled during Flow A validation smoke | Operator confirmation; exact env names only |
| n8n Flow A schedule activated (US-010) | Server workflow `active: true` with daily 09:00 UTC Schedule Trigger | [us-010 validation](operations/us-010-flow-a-n8n-activation-validation-2026-07-15.md) |
| LinkedIn publication guard (US-011) | Validated — fail-closed when disabled; Flow A has no LinkedIn API path; baseline restored `true` | [us-011 validation](operations/us-011-linkedin-publication-guard-validation-2026-07-15.md) |
| Fully unattended Flow A (BL-005) | Not achieved | Activation ≠ unattended E2E; empty-ready evidence only |
| Calendar LinkedIn summaries (BL-003) | Validated — all 3 calendar items have non-null `linkedin_package_status` / `linkedin_distribution_status` | Reconcile-close smoke + legacy operator patch 2026-07-15 |

## Unverified / unknown

| Fact | Status |
|------|--------|
| Current `BUILD_REVISION` if redeployed from git checkout on Mac | Known for last server deploy (`1784088086`); drifts on next rebuild |
| DeepSeek API quota / rate limits | `unknown` |
| ComfyUI availability right now | `unknown` — check before image-dependent publish |
| Remote divergence / duplicate-artifact Git guards under real collision | `unknown` — code + unit tests only; not exercised in smoke |
| LinkedIn article preview image on published posts (BL-009) | `not validated` — text post visible; no hero image card observed |

## Secrets

This file MUST NOT contain API keys, tokens, or credentials. Consult server `.env` on the host for live values.

## When to consult

Use this file when a task depends on **live** flags (publication enabled, n8n active, deployed revision). Do not inject indiscriminately into every OpenSpec proposal.
