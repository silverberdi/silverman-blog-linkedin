## Why

The deployed worker on `192.168.0.194:8010` still uses the temporary API key `local-test-key`, which was acceptable for initial bring-up but must be replaced before ongoing production use. Rotating `SILVERMAN_BLOG_LINKEDIN_API_KEY` requires coordinated updates to the server-local worker `.env` and the n8n workflow `worker_api_key` without committing secrets or breaking the live draft-generation flow.

## Goals

- Document a safe, repeatable procedure to rotate `SILVERMAN_BLOG_LINKEDIN_API_KEY` on the Ubuntu server.
- Define validation steps proving the old key is rejected, the new key is accepted, and n8n can still generate LinkedIn drafts.
- Define rollback steps if rotation fails mid-flight.
- Keep secrets server-local only; never commit real API keys to the repository.

## Non-Goals

- Changing worker HTTP endpoints, authentication scheme, or publishing behavior.
- Modifying `local-ai-stack` runtime files or n8n gateway configuration.
- Rotating `DEEPSEEK_API_KEY` or other unrelated secrets.
- Automating n8n workflow edits via the repository (operators update the live workflow manually).

## What Changes

- Add a **Worker API key rotation** section to `docs/deployment/ubuntu-server-worker-deployment.md` with ordered steps, validation checks, and rollback.
- Add `deploy/server/verify-worker-api-key-rotation.sh` — a small server-side helper that validates health, rejects the old Bearer token, and accepts the new one without printing, persisting, or committing secrets.
- Extend deployment artifact tests to verify the rotation doc section and helper script exist (structure only; no live server or real keys).
- No application code changes, no new worker endpoints, no n8n workflow JSON changes in git.

## Capabilities

### New Capabilities

_None — operational procedures extend the existing deployment capability._

### Modified Capabilities

- `ubuntu-server-worker-deployment`: Add requirements for documented worker API key rotation, post-rotation validation (health, auth rejection/acceptance, n8n end-to-end), rollback, and an optional safe verification helper script.

## Impact

| Area | Impact |
|------|--------|
| `docs/deployment/ubuntu-server-worker-deployment.md` | New rotation and rollback section |
| `deploy/server/verify-worker-api-key-rotation.sh` | New optional validation helper (server-only) |
| `deploy/server/smoke-worker.sh` | Reused after rotation; no code change required |
| Server `.env` | `/home/silverman/silverman-blog-linkedin-worker/.env` — operator edits `SILVERMAN_BLOG_LINKEDIN_API_KEY` |
| n8n workflow | **Silverman Blog LinkedIn Draft Generation** — operator updates `worker_api_key` in Set Configuration |
| Worker container | Restart required after `.env` change |
| Repository secrets | None committed; placeholders only |
