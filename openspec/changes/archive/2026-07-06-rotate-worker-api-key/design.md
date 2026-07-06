## Context

The `silverman-blog-linkedin` worker is deployed on Ubuntu server `192.168.0.194` at `http://192.168.0.194:8010` via an isolated Docker Compose project in `/home/silverman/silverman-blog-linkedin-worker`. Secrets live only in the server-local `.env` file. The n8n workflow **Silverman Blog LinkedIn Draft Generation** (`http://192.168.0.194:5678`) calls the worker over HTTP with `Authorization: Bearer <worker_api_key>` (ADR-0001).

Current state:

| Setting | Location | Current value |
|---------|----------|---------------|
| `SILVERMAN_BLOG_LINKEDIN_API_KEY` | `/home/silverman/silverman-blog-linkedin-worker/.env` | `local-test-key` (temporary) |
| `worker_api_key` | n8n Set Configuration node | Must match worker `.env` |
| `worker_base_url` | n8n Set Configuration node | `http://192.168.0.194:8010` (unchanged) |

Authenticated endpoints (`POST /process-ready`, `POST /process-file`, `POST /write-linkedin-draft`, `POST /generate-linkedin-draft`) reject missing or invalid Bearer tokens with HTTP 401. `GET /health` is unauthenticated.

Existing `deploy/server/smoke-worker.sh` validates health and authenticated `POST /process-ready` using the current `.env` key but does not verify that a **previous** key is rejected.

## Goals / Non-Goals

**Goals:**

- Provide a documented, low-risk rotation sequence with explicit validation and rollback.
- Add a small verification helper that confirms old-key rejection and new-key acceptance without exposing secrets.
- Reuse existing smoke tooling where possible.

**Non-Goals:**

- New worker endpoints or auth mechanisms.
- Committing real keys, n8n credentials, or `.env` files.
- Changing `local-ai-stack`, n8n gateway, or editorial/publishing behavior.
- Automated n8n API updates from the repository.

## Decisions

### 1. Documentation-first rotation procedure

**Decision:** Add a dedicated **Worker API key rotation** section to `docs/deployment/ubuntu-server-worker-deployment.md` rather than a separate doc file.

**Rationale:** Operators already use this guide for deploy, smoke, and n8n configuration. Keeping rotation alongside deployment reduces drift.

**Alternatives considered:**

- Standalone `docs/operations/rotate-worker-api-key.md` — rejected as unnecessary fragmentation for a single operational task.

### 2. Rotation order: worker first, then n8n

**Decision:** Update server `.env`, restart the worker, validate with the new key, then update n8n `worker_api_key`.

**Rationale:**

1. Worker restart picks up the new key immediately.
2. Brief window where n8n still sends the old key produces 401s (visible, safe) rather than the worker accepting a stale n8n key after worker-only rollback.
3. `smoke-worker.sh` and the verification helper can run on the server before touching n8n.

**Alternatives considered:**

- n8n first — rejected because the worker would reject the new n8n key until `.env` is updated, causing confusing failures during the overlap.

### 3. Verification helper script

**Decision:** Add `deploy/server/verify-worker-api-key-rotation.sh` that:

- Reads the **new** key from the server-local `.env` (same `load_env_var` pattern as `smoke-worker.sh`).
- Accepts the **old** key only via environment variable `OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY` (never as a script argument, to avoid `ps` exposure).
- Runs three checks: `GET /health` (200), `POST /process-ready` with old Bearer (401), `POST /process-ready` with new Bearer (200).
- Prints PASS/FAIL per check; never echoes key values.
- Exits non-zero on any required failure.

**Rationale:** Manual `curl` steps are error-prone; a focused script standardizes validation after rotation and is reusable for future rotations. Reusing `.env` for the new key avoids prompting for secrets.

**Alternatives considered:**

- Extend `smoke-worker.sh` with an `--old-key` flag — rejected to keep smoke simple and avoid mixing deploy smoke with rotation-specific logic.
- No script, documentation only — rejected because the user asked for a helper when it adds clear value; old-key rejection is not covered by existing smoke.

### 4. n8n end-to-end validation is manual

**Decision:** Document manual execution of workflow **Silverman Blog LinkedIn Draft Generation** and verification of a new draft under `linkedin-posts/review/`.

**Rationale:** n8n workflow state lives outside the repository; HTTP-only integration (ADR-0001) means the repo cannot safely automate live workflow edits.

### 5. Rollback strategy

**Decision:** Document symmetric rollback:

1. Restore previous `SILVERMAN_BLOG_LINKEDIN_API_KEY` in server `.env`.
2. `docker compose ... up -d` (or restart) in `/home/silverman/silverman-blog-linkedin-worker`.
3. Run `smoke-worker.sh`.
4. Restore previous `worker_api_key` in n8n if it was already changed.
5. Re-run n8n workflow to confirm.

**Rationale:** Matches existing deployment rollback patterns; no new infrastructure.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operator commits real key to git | Doc emphasizes server-only `.env`; helper never writes keys; tests check placeholders only |
| Brief n8n outage during rotation | Expected 401s until n8n updated; document order and keep rollback steps |
| Old key in shell history | Use `.env` for new key; pass old key via env var in same session, not CLI args |
| Worker not restarted after `.env` edit | Doc and tasks require compose restart before validation |
| Rotation doc drifts from scripts | Spec ties doc section to helper script behavior |

## Migration Plan

1. **Prepare:** Generate a strong replacement key offline (e.g. `openssl rand -hex 32`); store only in password manager until applied.
2. **Backup:** Note current `.env` value and n8n `worker_api_key` (secure notes, not git).
3. **Rotate worker:** Edit `/home/silverman/silverman-blog-linkedin-worker/.env`; restart worker container.
4. **Validate worker:** Run `verify-worker-api-key-rotation.sh` with `OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY=local-test-key` (or prior key); run `smoke-worker.sh`.
5. **Update n8n:** Set `worker_api_key` in Set Configuration to match new `.env` value.
6. **Validate n8n:** Execute workflow manually; confirm draft in `linkedin-posts/review/` and source post unchanged in `blog-posts/ready/`.
7. **Rollback (if needed):** Reverse steps 3–5 using backed-up values.

## Open Questions

_None — scope is intentionally narrow and operational._
