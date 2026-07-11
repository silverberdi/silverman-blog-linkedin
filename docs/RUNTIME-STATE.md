# Runtime State

Volatile point-in-time operational snapshot. **Not** architectural authority — see [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Durable status: [CURRENT-STATE.md](CURRENT-STATE.md).

Update after deploys, activation changes, smoke tests, external-integration validation, or confirmed revision changes.

## Snapshot

**`verified_at_utc`:** `2026-07-11T06:22:00Z`
**Evidence source:** US-001 Git publication smoke (`run-us001-git-publication-smoke.sh`); deploy verification on Ubuntu server `192.168.0.194`

| Fact | Value | Evidence |
|------|-------|----------|
| Worker URL | `http://192.168.0.194:8010` | Deploy + health check |
| `BUILD_REVISION` | `unknown` (target-layout deploy used timestamp fallback) | Re-verify after git-based deploy from Mac |
| Editorial mount | `/data/silverman-blog-linkedin` | `deploy-worker.sh` compose |
| Public blog mount | `/public-blog` → host `/home/silverman/silverberdi.github.io` | Deploy verification |
| n8n Flow A workflow | Imported, **inactive** | `import-flow-a-n8n-workflow.sh`, workflow id `silvermanFlowAPublish01` |
| `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED` | `true` | Server `.env` during US-001 validation window |
| `GIT_SSH_COMMAND` | Set (deploy key + known_hosts paths) | Server `.env`; container env present |
| Git publication US-001 | Validated with real push | Remote `origin/main` `53d0a26…`; smoke `OVERALL: PASS` |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | `false` | Server `.env` (not logged here) |
| ComfyUI image generation | Enabled during Flow A validation smoke | Operator confirmation; exact env names only |
| LinkedIn API real publish | Not validated in production | Guard flag false |
| n8n unattended scheduling | Not active | Workflow `active: false` |

## Unverified / unknown

| Fact | Status |
|------|--------|
| Current `BUILD_REVISION` on server if redeployed from git checkout | `unknown` — re-verify after deploy |
| DeepSeek API quota / rate limits | `unknown` |
| ComfyUI availability right now | `unknown` — check before image-dependent publish |
| US-002 live-site reachability after Git push | `deferred` |

## Secrets

This file MUST NOT contain API keys, tokens, or credentials. Consult server `.env` on the host for live values.

## When to consult

Use this file when a task depends on **live** flags (publication enabled, n8n active, deployed revision). Do not inject indiscriminately into every OpenSpec proposal.
