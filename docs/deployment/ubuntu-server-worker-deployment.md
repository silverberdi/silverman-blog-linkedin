# Ubuntu server worker deployment

Deploy the `silverman-blog-linkedin` HTTP worker on the Ubuntu server (`silverman@192.168.0.194`) as an **isolated Docker Compose project**. This deployment does **not** modify `local-ai-stack` (n8n, postgres, minio, qdrant, portainer, backup-runner, auto-ingest-runner, n8n-gateway).

For local development on Mac, use `docker-compose.example.yml` instead.

## Strategy

| Aspect | Value |
|--------|-------|
| Compose project | Isolated — `deploy/server/silverman-worker.compose.yaml` only |
| Deployment directory | `/home/silverman/silverman-blog-linkedin-worker` |
| Host port | `8010` → container `8000` |
| Editorial mount (host) | `/home/silverman/compartido_mac/silverman-blog-linkedin` |
| Editorial mount (container) | `/data/silverman-blog-linkedin` |
| n8n `worker_base_url` | `http://192.168.0.194:8010` |

## Prerequisites

- Docker and Docker Compose v2 on the Ubuntu server
- Repository checkout or synced artifacts on the server
- Write access to `/home/silverman/compartido_mac/silverman-blog-linkedin` (for `metadata/runs/` and `linkedin-posts/review/`)
- Editorial folder layout under the shared mount (see README)

## First-time setup

### 1. Create server-local `.env`

**Warning:** Never commit `.env` or real API keys to git. Use placeholders only in version-controlled files.

```bash
cd /home/silverman/silverman-blog-linkedin-worker
cp silverman-worker.env.example .env
```

Edit `.env` on the server and set:

- `SILVERMAN_BLOG_LINKEDIN_API_KEY` — must match `worker_api_key` in the n8n workflow
- `DEEPSEEK_API_KEY` — required for `POST /generate-linkedin-draft`
- Optional: `DEEPSEEK_MODEL`, `DEEPSEEK_TIMEOUT_SECONDS`, `DEEPSEEK_MAX_OUTPUT_TOKENS`

### 2. Deploy

From a repository checkout on the server (or after syncing the repo):

```bash
./deploy/server/deploy-worker.sh
```

The script:

1. Creates `/home/silverman/silverman-blog-linkedin-worker` if needed
2. Syncs `Dockerfile`, `pyproject.toml`, `README.md`, `src/`, and deployment artifacts
3. Exits with instructions if `.env` is missing
4. Runs `docker compose -f silverman-worker.compose.yaml up -d --build` **only** in the worker directory

The script never runs `docker compose down` and never touches `local-ai-stack`.

### 3. Smoke test

```bash
/home/silverman/silverman-blog-linkedin-worker/smoke-worker.sh
```

Required checks:

- `GET http://localhost:8010/health` — HTTP 200
- `POST http://localhost:8010/process-ready` — Bearer auth, HTTP 200

Optional generation smoke runs when `DEEPSEEK_API_KEY` is set and a `.md` file exists in `blog-posts/ready/`. It is not required for overall PASS.

### 3b. Flow A deployment readiness (before Flow A n8n smoke)

`smoke-worker.sh` confirms basic worker HTTP health. Before Flow A orchestration smoke, run the Flow A readiness gate so repository state and running worker OpenAPI surface are aligned.

```bash
# From repository checkout on server or Mac
python3 scripts/flow_a_readiness.py \
  --repo-path . \
  --worker-base-url http://localhost:8010 \
  --n8n-base-url http://192.168.0.194:5678 \
  --env-file /home/silverman/silverman-blog-linkedin-worker/.env \
  --phase all
```

**Phase 0 (required gate):** git HEAD / `origin/main`, expected commits (`79f5345`, `962ba2f`, `53708eb` by default), required Flow A files, worker `GET /health` and `GET /openapi.json` with paths `/health`, `/process-ready`, `/publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`, Flow A workflow export `"active": false`.

**Phase 1:** non-destructive `POST /process-ready` when API key is configured (never prints the key).

**Phase 2:** n8n reachability; workflow import reported as `pending_import` when import cannot be confirmed.

**Phase 3–4:** manual operator steps only (manual n8n trigger; idempotent rerun verification). No cron/webhook activation. No LinkedIn API calls.

If Phase 0 fails with a stale-worker message while git checks pass, rebuild/restart the worker manually:

```bash
./deploy/server/deploy-worker.sh
```

The readiness script does **not** run deploy or restart automatically.

Relationship to `smoke-worker.sh`: smoke-worker is minimal post-deploy; `flow_a_readiness.py` is the Flow A pre-smoke gate with OpenAPI and git checks.

### 4. Configure n8n

In the **Set Configuration** node of workflow `Silverman Blog LinkedIn Draft Generation`:

| Field | Value |
|-------|-------|
| `worker_base_url` | `http://192.168.0.194:8010` |
| `worker_api_key` | Same value as `SILVERMAN_BLOG_LINKEDIN_API_KEY` in server `.env` |

Do not modify n8n gateway or `local-ai-stack` compose.

Run the workflow manually and verify a draft appears under `linkedin-posts/review/` while the source post remains in `blog-posts/ready/`.

## Updates

Re-run the deploy script after pulling or syncing new code:

```bash
./deploy/server/deploy-worker.sh
/home/silverman/silverman-blog-linkedin-worker/smoke-worker.sh
```

The deploy uses `--build` to refresh the image.

## Worker API key rotation

Rotate `SILVERMAN_BLOG_LINKEDIN_API_KEY` when replacing a temporary or compromised key. Real keys must exist **only** in the server-local `.env` and n8n workflow configuration—never in git.

**Warning:** Do not commit `.env`, paste keys into the repository, or store them in workflow JSON checked into git.

### Preparation

1. Generate a strong replacement key on the server or a trusted machine (example):

   ```bash
   openssl rand -hex 32
   ```

2. Record the **current** values in a secure location (password manager or encrypted notes—not git):
   - `SILVERMAN_BLOG_LINKEDIN_API_KEY` from `/home/silverman/silverman-blog-linkedin-worker/.env`
   - `worker_api_key` from the n8n **Set Configuration** node in workflow **Silverman Blog LinkedIn Draft Generation**

3. Back up the server-local `.env`:

   ```bash
   cp /home/silverman/silverman-blog-linkedin-worker/.env \
      /home/silverman/silverman-blog-linkedin-worker/.env.bak.$(date +%Y%m%d%H%M%S)
   ```

### Rotation order (worker first, then n8n)

Update the worker before n8n so validation can run on the server. n8n may return HTTP 401 briefly until `worker_api_key` is updated.

1. **Update worker `.env`** on the server:

   ```bash
   cd /home/silverman/silverman-blog-linkedin-worker
   # Edit .env and set SILVERMAN_BLOG_LINKEDIN_API_KEY to the new value
   ```

2. **Restart the worker container** (isolated compose only):

   ```bash
   cd /home/silverman/silverman-blog-linkedin-worker
   docker compose -f silverman-worker.compose.yaml up -d
   ```

3. **Validate worker auth** (replace the env value with your **previous** key):

   ```bash
   cd /home/silverman/silverman-blog-linkedin-worker
   OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY='<previous-key>' ./verify-worker-api-key-rotation.sh
   ./smoke-worker.sh
   ```

   `verify-worker-api-key-rotation.sh` checks:
   - `GET /health` → HTTP 200
   - `POST /process-ready` with previous Bearer → HTTP 401
   - `POST /process-ready` with current Bearer (from `.env`) → HTTP 200

   The script never prints key values. Pass the old key only via `OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY` (not as a script argument).

4. **Update n8n** at `http://192.168.0.194:5678`:
   - Open workflow **Silverman Blog LinkedIn Draft Generation**
   - In **Set Configuration**, set `worker_api_key` to the same value as the new `SILVERMAN_BLOG_LINKEDIN_API_KEY`
   - Leave `worker_base_url` as `http://192.168.0.194:8010`

5. **Manual n8n workflow smoke:**
   - Run the workflow manually
   - Confirm a new draft appears under `linkedin-posts/review/`
   - Confirm the source post remains in `blog-posts/ready/`

### Rollback (API key rotation)

If rotation fails after changing the worker or n8n:

1. Restore the previous `SILVERMAN_BLOG_LINKEDIN_API_KEY` in `/home/silverman/silverman-blog-linkedin-worker/.env` (from backup or secure notes).

2. Restart the worker:

   ```bash
   cd /home/silverman/silverman-blog-linkedin-worker
   docker compose -f silverman-worker.compose.yaml up -d
   ```

3. Run smoke test:

   ```bash
   /home/silverman/silverman-blog-linkedin-worker/smoke-worker.sh
   ```

4. If n8n was already updated, restore the previous `worker_api_key` in **Set Configuration**.

5. Re-run the n8n workflow and confirm draft generation works.

## Rollback

Stop the worker **only** from the isolated deployment directory:

```bash
cd /home/silverman/silverman-blog-linkedin-worker
docker compose -f silverman-worker.compose.yaml down
```

This does not stop or modify `local-ai-stack` services.

## Troubleshooting

### `.env` missing on deploy

`deploy-worker.sh` exits before compose with instructions to copy `silverman-worker.env.example` to `.env`. Create `.env` manually on the server; never commit it.

### Port 8010 already in use

```bash
ss -tlnp | grep 8010
```

Stop the conflicting process or change the host port mapping in `silverman-worker.compose.yaml` (and update n8n `worker_base_url` accordingly).

### Health check returns `degraded`

`GET /health` may return HTTP 200 with `status: degraded` when editorial folders are missing. Ensure the full folder layout exists under `/home/silverman/compartido_mac/silverman-blog-linkedin`.

### `folders_ready: false` or write failures

Confirm the container user can write to `metadata/runs/` and `linkedin-posts/review/` on the host mount.

### n8n cannot reach the worker

1. Confirm `smoke-worker.sh` passes on the server (`localhost:8010`)
2. Confirm `worker_base_url` is `http://192.168.0.194:8010` (not `localhost` from n8n's perspective if that differs)
3. Check host firewall rules for port `8010`

### Stale container image

Force a rebuild:

```bash
cd /home/silverman/silverman-blog-linkedin-worker
docker compose -f silverman-worker.compose.yaml build --no-cache
docker compose -f silverman-worker.compose.yaml up -d
```

### Secrets in git

Real `SILVERMAN_BLOG_LINKEDIN_API_KEY` and `DEEPSEEK_API_KEY` values must exist only in server-local `.env`. Committed files use `CHANGE_ME_*` placeholders.

## Related files

| File | Purpose |
|------|---------|
| `deploy/server/silverman-worker.compose.yaml` | Isolated compose definition |
| `deploy/server/silverman-worker.env.example` | Documented env placeholders |
| `deploy/server/deploy-worker.sh` | Deploy script |
| `deploy/server/smoke-worker.sh` | HTTP smoke tests |
| `deploy/server/verify-worker-api-key-rotation.sh` | Post-rotation auth verification |
| `docker-compose.example.yml` | Local/dev compose (not for server) |
