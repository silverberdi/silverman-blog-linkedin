# n8n Server Worker Integration — 2026-07-06

> **Historical operations record** (2026-07-06) — Point-in-time server integration notes. **Current status:** [CURRENT-STATE.md](../CURRENT-STATE.md) and [RUNTIME-STATE.md](../RUNTIME-STATE.md). Authority: [CONTEXT-AUTHORITY.md](../CONTEXT-AUTHORITY.md).

## Purpose

Record the operational changes applied on the Ubuntu server to make the real n8n instance call the deployed `silverman-blog-linkedin` worker.

## Final runtime endpoints

- n8n editor: `http://192.168.0.194:5678`
- worker API: `http://192.168.0.194:8010`
- worker container: `silverman-blog-linkedin-worker`
- n8n container: `local-ai-stack-n8n-1`
- n8n gateway container: `local-ai-stack-n8n-gateway-1`

## Files changed manually on the server

These files are part of `/home/silverman/local-ai-stack`, not the `silverman-blog-linkedin` repository:

- `/home/silverman/local-ai-stack/compose.yaml`
- `/home/silverman/local-ai-stack/infra/n8n-gateway/default.conf.template`

## Reverse proxy fixes

The n8n gateway nginx template was updated to:

- preserve the browser host and port using `$http_host`
- support WebSocket upgrade headers for `/rest/push`

This fixed:

- `Invalid origin`
- `Lost connection to the server`
- failed n8n push/WebSocket connection

## n8n environment fixes

The n8n service was updated with explicit reverse-proxy/public URL settings:

- `N8N_PROXY_HOPS="1"`
- `N8N_HOST="192.168.0.194"`
- `N8N_PORT="5678"`
- `N8N_PROTOCOL="http"`
- `N8N_EDITOR_BASE_URL="http://192.168.0.194:5678"`
- `WEBHOOK_URL="http://192.168.0.194:5678/"`

This fixed the `X-Forwarded-For` / `trust proxy` validation error.

## Workflow configuration

The workflow `Silverman Blog LinkedIn Draft Generation` must use:

- `worker_base_url = http://192.168.0.194:8010`

The worker API key must match the server-local worker `.env` value at:

- `/home/silverman/silverman-blog-linkedin-worker/.env`

Do not commit real API keys.

## Manual validation completed

The real n8n server workflow successfully called the deployed worker and generated a LinkedIn draft.

Evidence:

- new metadata: `metadata/runs/run-20260706T160926Z-c2bd.json`
- new draft: `linkedin-posts/review/20260706T160934Z-01-why-i-did-not-start-with-the-database-executive-recruiter.md`
- metadata status: `completed`
- `draft_written`: `true`
- `errors`: `[]`
- worker base path: `/data/silverman-blog-linkedin`

## Follow-up

Rotate the temporary `local-test-key` worker API key and update the n8n workflow configuration to match the new value.
