# Runtime State

Volatile point-in-time operational snapshot. **Not** architectural authority — see [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Durable status: [CURRENT-STATE.md](CURRENT-STATE.md).

Update after deploys, activation changes, smoke tests, external-integration validation, or confirmed revision changes.

## Snapshot

**`verified_at_utc`:** `2026-07-10T00:00:00Z`
**Evidence source:** Operator smoke on Ubuntu server `192.168.0.194`; worker diagnostic scripts; n8n import verification

| Fact | Value | Evidence |
|------|-------|----------|
| Worker URL | `http://192.168.0.194:8010` | Deploy + health check |
| `BUILD_REVISION` | `88cd5bc` | Container build / deploy metadata |
| Editorial mount | `/data/silverman-blog-linkedin` | `deploy-worker.sh` compose |
| Public blog mount | `/public-blog` → host `/home/silverman/silverberdi.github.io` | Deploy verification |
| n8n Flow A workflow | Imported, **inactive** | `import-flow-a-n8n-workflow.sh`, workflow id `silvermanFlowAPublish01` |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | `false` | Server `.env` (not logged here) |
| ComfyUI image generation | Enabled during Flow A validation smoke | Operator confirmation; exact env names only |
| LinkedIn API real publish | Not validated in production | Guard flag false |
| n8n unattended scheduling | Not active | Workflow `active: false` |

## Unverified / unknown

| Fact | Status |
|------|--------|
| Current `BUILD_REVISION` on server if redeployed after snapshot | `unknown` — re-verify after deploy |
| DeepSeek API quota / rate limits | `unknown` |
| ComfyUI availability right now | `unknown` — check before image-dependent publish |

## Secrets

This file MUST NOT contain API keys, tokens, or credentials. Consult server `.env` on the host for live values.

## When to consult

Use this file when a task depends on **live** flags (publication enabled, n8n active, deployed revision). Do not inject indiscriminately into every OpenSpec proposal.
