## Context

The `silverman-blog-linkedin` worker is feature-complete for phase-1 draft generation: `GET /health`, `POST /process-ready`, `POST /process-file`, `POST /write-linkedin-draft`, `POST /generate-linkedin-draft`, plus an importable n8n workflow. Local Docker smoke tests against n8n succeeded. The worker application and `docker-compose.example.yml` support local/dev use, but there is no version-controlled deployment path for the production Ubuntu server.

The Ubuntu server (`silverman@192.168.0.194`) already runs a shared `local-ai-stack` compose with n8n, postgres, minio, qdrant, portainer, backup-runner, auto-ingest-runner, and n8n-gateway. Editorial data lives at `/home/silverman/compartido_mac/silverman-blog-linkedin`. n8n must continue calling the worker over HTTP only (ADR-0001); the worker remains the filesystem and DeepSeek boundary.

**Current state:** Worker runs locally; n8n workflow uses `worker_base_url` pointing at local Docker. Server has no isolated worker service on port `8010`.

**Constraints:** Do not modify `local-ai-stack/compose.yaml`, n8n gateway, or any shared-stack containers. Do not commit real secrets. Deploy scripts must not run `docker compose down` against unrelated projects.

## Goals / Non-Goals

**Goals:**

- Isolated Docker Compose project at `/home/silverman/silverman-blog-linkedin-worker` on the server.
- Host port `8010` → container port `8000`; n8n `worker_base_url` = `http://192.168.0.194:8010`.
- Version-controlled artifacts: compose file, env example, deploy script, smoke script, operator docs.
- Server-local `.env` for secrets; committed files use placeholders only.
- Read-write mount of shared editorial root only.
- `restart: unless-stopped` and container healthcheck against `GET /health`.
- Safe deploy script and curl-based smoke script with clear PASS/FAIL output.

**Non-Goals:**

- Touching `local-ai-stack`, shared postgres/minio/qdrant, or n8n-gateway configuration.
- Worker application code changes, new HTTP endpoints, or n8n workflow JSON changes.
- Automated SSH deploy from CI, secret managers, or infrastructure-as-code beyond shell + compose.
- Replacing `docker-compose.example.yml` (remains local/dev reference).

## Decisions

### 1. Separate compose project (not local-ai-stack)

**Decision:** Deploy via `deploy/server/silverman-worker.compose.yaml` in its own directory, not as a service in `local-ai-stack/compose.yaml`.

**Rationale:** Worker deployment is still being stabilized. Adding or restarting services in the shared stack risks interrupting n8n, postgres, and other production-adjacent services. A separate compose project has its own lifecycle (`up`, `down`, `logs`) without affecting unrelated containers.

**Alternatives considered:**

- *Add worker service to local-ai-stack* — rejected; violates isolation requirement and increases blast radius.
- *Run worker bare-metal with systemd* — rejected; inconsistent with existing Docker-based ops and ADR-0003 container model.

### 2. Build context from repository root

**Decision:** Compose `build.context` points to the repository root (or a path documented by `deploy-worker.sh` that includes `Dockerfile`, `pyproject.toml`, and `src/`). The deploy script copies or syncs the full repo (or minimal build tree) into the server deployment directory.

**Rationale:** Reuses existing `Dockerfile` without duplication. Image builds on the server from known source.

**Alternatives considered:**

- *Pre-built image pushed to a registry* — deferred; adds registry auth and CI scope not required for single-server phase-1.

### 3. Port mapping 8010:8000

**Decision:** Map host `8010` to container `8000`. Set `PORT=8000` inside the container.

**Rationale:** Avoids collision with other services that may use `8000` on the host. n8n reaches the worker via LAN IP `http://192.168.0.194:8010` (n8n runs in Docker on the same host but uses host-reachable URL or bridge networking as already proven in local smoke tests).

### 4. Volume mount — editorial root only

**Decision:**

```
/home/silverman/compartido_mac/silverman-blog-linkedin:/data/silverman-blog-linkedin
```

Set `SILVERMAN_BLOG_LINKEDIN_BASE_PATH=/data/silverman-blog-linkedin`.

**Rationale:** Worker needs read-write access to `blog-posts/ready`, `linkedin-posts/review`, and `metadata/runs`. Mounting only the editorial tree limits container filesystem exposure. Matches ADR-0003 and existing `docker-compose.example.yml` container path.

### 5. Secrets via server-local `.env`

**Decision:** Compose uses `env_file: .env` (or equivalent) in the deployment directory. Commit `silverman-worker.env.example` with placeholder values and comments. Operator copies to `.env` manually on the server.

**Required variables:**

| Variable | Purpose |
|----------|---------|
| `SILVERMAN_BLOG_LINKEDIN_API_KEY` | Worker Bearer auth |
| `DEEPSEEK_API_KEY` | Generation endpoint |
| `DEEPSEEK_MODEL` | Optional override |
| `DEEPSEEK_TIMEOUT_SECONDS` | Optional override |
| `DEEPSEEK_MAX_OUTPUT_TOKENS` | Optional override |

**Rationale:** Keeps secrets out of git. Matches existing worker env contract. Example file documents what operators must set.

### 6. Deploy script behavior

**Decision:** `deploy-worker.sh` is idempotent and explicit:

1. Resolve target directory (`/home/silverman/silverman-blog-linkedin-worker` or `$DEPLOY_DIR` override).
2. Create directory if missing.
3. Copy/sync `deploy/server/*` and required build files (Dockerfile, pyproject.toml, src/, etc.) — method documented in script (rsync or cp from repo clone).
4. Print reminder: create `.env` from `silverman-worker.env.example` if not present; do not auto-generate secrets.
5. Run `docker compose -f silverman-worker.compose.yaml up -d --build` **only** in the worker deploy directory.
6. Never invoke compose against `local-ai-stack`.

**Rationale:** Safe operator workflow; clear separation from shared stack.

### 7. Smoke script behavior

**Decision:** `smoke-worker.sh` runs on the server (or against `localhost:8010`):

| Check | Required | Notes |
|-------|----------|-------|
| `GET http://localhost:8010/health` | Yes | Expect HTTP 200, JSON with `status` |
| `POST /process-ready` with Bearer | Yes | Read `SILVERMAN_BLOG_LINKEDIN_API_KEY` from `.env` |
| `POST /generate-linkedin-draft` | Optional | Only if `DEEPSEEK_API_KEY` set and a `.md` exists in ready |

Print `PASS`/`FAIL` per check and overall result. Exit non-zero on required-check failure.

**Rationale:** Validates deployment without requiring DeepSeek spend on every deploy. Deeper smoke available when keys and content exist.

### 8. Documentation layout

**Decision:** Primary guide at `docs/deployment/ubuntu-server-worker-deployment.md`; README links to it. Covers prerequisites, first-time `.env` setup, deploy, smoke, n8n URL update, rollback, and troubleshooting.

**Rationale:** Keeps README focused; deployment ops get a dedicated runbook.

### 9. Lightweight deployment tests

**Decision:** Optional pytest module asserts committed artifacts exist, compose declares expected port/volume/env keys, env example has required variable names, scripts are executable in repo (or document `chmod +x`). No integration test against live server.

**Rationale:** Catches regressions in artifact structure without over-engineering.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Deploy script accidentally targets wrong compose project | Use explicit `-f silverman-worker.compose.yaml` and fixed project directory; never `cd` into `local-ai-stack` |
| `.env` missing on first deploy causes compose failure | Script checks for `.env`, prints clear instructions from example file, exits early with message |
| Port 8010 already in use | Document `ss -tlnp \| grep 8010` in troubleshooting; operator picks alternate host port only with explicit compose edit |
| Editorial mount permissions prevent writes | Document required write access to `metadata/runs` and `linkedin-posts/review`; health shows `folders_ready` |
| Stale image after code update | Deploy script always uses `--build`; document `docker compose ... build --no-cache` for hard refresh |
| Secrets committed by mistake | Example file uses placeholders; review checklist in docs; no real keys in repo |
| n8n cannot reach worker on 8010 | Document firewall and Docker port publish; smoke from server localhost first, then from n8n host network |

## Migration Plan

### First-time deploy

1. Clone or sync repository on server (or copy artifacts via `deploy-worker.sh` from dev machine).
2. Create `/home/silverman/silverman-blog-linkedin-worker`.
3. Copy `silverman-worker.env.example` → `.env`; fill real keys on server only.
4. Run `deploy-worker.sh`.
5. Run `smoke-worker.sh`; confirm PASS.
6. In n8n workflow **Set Configuration**, set `worker_base_url` to `http://192.168.0.194:8010` and matching API key.
7. Manual workflow run; verify draft under `linkedin-posts/review/`.

### Updates

1. Sync new code/artifacts to deploy directory.
2. Re-run `deploy-worker.sh` (`up -d --build`).
3. Re-run smoke script.

### Rollback

1. In worker deploy directory only: `docker compose -f silverman-worker.compose.yaml down`.
2. Optionally check out previous image tag/commit and redeploy.
3. `local-ai-stack` remains running throughout.

## Open Questions

- **None blocking implementation.** Host firewall rules for port `8010` from n8n container network are assumed working if localhost smoke passes and n8n uses `192.168.0.194:8010` (same pattern as local smoke test).
