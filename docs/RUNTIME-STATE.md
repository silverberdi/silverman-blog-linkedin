# Runtime State

Volatile point-in-time operational snapshot. **Not** architectural authority — see [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Durable status: [CURRENT-STATE.md](CURRENT-STATE.md).

Update after deploys, activation changes, smoke tests, external-integration validation, or confirmed revision changes.

## Snapshot

**`verified_at_utc`:** `2026-07-11T07:45:00Z`
**Evidence source:** US-001/US-002 Phase 3 validation reports; deploy verification on Ubuntu server `192.168.0.194`

| Fact | Value | Evidence |
|------|-------|----------|
| Worker URL | `http://192.168.0.194:8010` | Deploy + health check |
| `BUILD_REVISION` | `1783752289` (timestamp fallback; server target layout has no `.git`) | Deploy output 2026-07-11 |
| Editorial mount | `/data/silverman-blog-linkedin` | `deploy-worker.sh` compose |
| Public blog mount | `/public-blog` → host `/home/silverman/silverberdi.github.io` | Deploy verification |
| n8n Flow A workflow | Imported, **inactive** | `import-flow-a-n8n-workflow.sh`, workflow id `silvermanFlowAPublish01` |
| `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED` | `true` | Server `.env` during validation window |
| `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED` | `true` | Server `.env` during US-002 validation window |
| `GIT_SSH_COMMAND` | Set (deploy key + known_hosts paths) | Server `.env`; container env present |
| Git publication US-001 | Validated with real push | [phase3-us001 report](operations/phase3-us001-git-publication-validation-2026-07-11.md) |
| Live-site confirmation US-002 | Validated with HTTP 200 + slug marker | [phase3-us002 report](operations/phase3-us002-live-site-confirmation-validation-2026-07-11.md) |
| BL-001 smoke artifacts | Removed from public site and editorial mount | Cleanup commits `558c1c3`, `b128c57` on `silverberdi.github.io` |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | `false` | Server `.env` (not logged here) |
| ComfyUI image generation | Enabled during Flow A validation smoke | Operator confirmation; exact env names only |
| LinkedIn API real publish | Not validated in production | Guard flag false |
| n8n unattended scheduling | Not active | Workflow `active: false` |

## Unverified / unknown

| Fact | Status |
|------|--------|
| Current `BUILD_REVISION` if redeployed from git checkout on Mac | `unknown` — server uses timestamp fallback |
| DeepSeek API quota / rate limits | `unknown` |
| ComfyUI availability right now | `unknown` — check before image-dependent publish |
| Remote divergence / duplicate-artifact Git guards under real collision | `unknown` — code + unit tests only; not exercised in smoke |

## Secrets

This file MUST NOT contain API keys, tokens, or credentials. Consult server `.env` on the host for live values.

## When to consult

Use this file when a task depends on **live** flags (publication enabled, n8n active, deployed revision). Do not inject indiscriminately into every OpenSpec proposal.
