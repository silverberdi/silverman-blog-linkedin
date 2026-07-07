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

**Important:** Run deploy on the Ubuntu server so files sync to `/home/silverman/silverman-blog-linkedin-worker` and Docker rebuilds the worker on port `8010`. Running `deploy-worker.sh` from a Mac without SSH only syncs to a local path and does **not** update the server worker.

## Execution modes

`deploy-worker.sh` supports two execution layouts. It detects the layout from the script location and nearby files—never by blindly walking up to `/home`.

| Mode | How to run | Source files | Sync behavior |
|------|------------|--------------|---------------|
| **Repo layout** | From a repository checkout: `./deploy/server/deploy-worker.sh` | Repository root (`Dockerfile`, `pyproject.toml`, `README.md`, `src/`) | Rsyncs build tree and deployment artifacts into `DEPLOY_DIR` (default `/home/silverman/silverman-blog-linkedin-worker`) |
| **Target layout** | From the synced server directory: `/home/silverman/silverman-blog-linkedin-worker/deploy-worker.sh` | The target directory itself (must already contain `Dockerfile`, `pyproject.toml`, `README.md`, `src/`) | Skips rsync; validates local files, then builds and recreates the container |

Use **repo layout** after pulling or syncing a full checkout (first deploy or when deployment scripts change). Use **target layout** for routine rebuilds on the server when artifacts are already in place—this avoids the bug where `../..` from the target directory incorrectly resolved sources to `/home`.

**Repo layout** (from checkout on server or Mac):

```bash
./deploy/server/deploy-worker.sh
```

**Target layout** (on server after initial sync):

```bash
/home/silverman/silverman-blog-linkedin-worker/deploy-worker.sh
# or:
cd /home/silverman/silverman-blog-linkedin-worker
./deploy-worker.sh
```

The script:

1. Detects **repo layout** vs **target layout** (see [Ubuntu server deployment](docs/deployment/ubuntu-server-worker-deployment.md#execution-modes))
2. Creates `/home/silverman/silverman-blog-linkedin-worker` if needed (repo layout)
3. Syncs `Dockerfile`, `pyproject.toml`, `README.md`, `src/`, and deployment artifacts (repo layout only; target layout validates files in place)
3. Verifies Flow A source modules exist in the target directory (with sha256 digests)
4. Exits with instructions if `.env` is missing
5. Builds the worker image with `BUILD_REVISION` from git HEAD (busts stale Docker cache)
6. Runs `docker compose up -d --force-recreate` in the worker directory
7. Prints container id, image id, and start time
8. Runs `verify-worker-deploy.sh`, which retries `GET /health` and `GET /openapi.json` until the worker is ready after container recreate, then confirms Flow A endpoints are exposed

The script never runs `docker compose down` and never touches `local-ai-stack`.

If deploy completes but verification fails (health OK, OpenAPI still missing Flow A paths), force a no-cache rebuild on the server:

```bash
cd /home/silverman/silverman-blog-linkedin-worker
DEPLOY_FORCE_REBUILD=1 ./deploy-worker.sh
```

### 3. Smoke test

```bash
/home/silverman/silverman-blog-linkedin-worker/smoke-worker.sh
```

Required checks:

- `GET http://localhost:8010/health` — HTTP 200
- `POST http://localhost:8010/process-ready` — Bearer auth, HTTP 200

Optional generation smoke runs when `DEEPSEEK_API_KEY` is set and a `.md` file exists in `blog-posts/ready/`. It is not required for overall PASS.

### 3a. Post-deploy Flow A verification (required before n8n smoke)

`smoke-worker.sh` does not inspect OpenAPI. After every deploy, confirm the running worker exposes Flow A endpoints:

```bash
/home/silverman/silverman-blog-linkedin-worker/verify-worker-deploy.sh
```

This checks:

- Target directory contains current Flow A modules (`main.py`, `blog_publish_flow.py`, etc.)
- Container `silverman-blog-linkedin-worker` is running on port `8010`
- `GET /health` and `GET /openapi.json` return HTTP 200 (retries for up to ~60s after recreate; override with `VERIFY_MAX_ATTEMPTS` / `VERIFY_RETRY_INTERVAL_SECONDS`)
- `GET /openapi.json` includes `/publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`

`deploy-worker.sh` runs this verification automatically. It waits for worker readiness after `--force-recreate` before checking OpenAPI paths, and fails if endpoints are still missing after retries.

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

**Phase 2:** n8n reachability; workflow import reported as `pending_import` when import cannot be confirmed over HTTP alone. A successful `deploy/server/import-flow-a-n8n-workflow.sh` run on the Ubuntu server satisfies manual import verification evidence.

**Phase 3–4:** manual operator steps only (manual n8n trigger; idempotent rerun verification). No cron/webhook activation. No LinkedIn API calls.

If Phase 0 fails with a stale-worker message while git checks pass, rebuild/restart the worker on the **Ubuntu server** (not only from Mac):

```bash
./deploy/server/deploy-worker.sh
# or on server:
DEPLOY_FORCE_REBUILD=1 /home/silverman/silverman-blog-linkedin-worker/deploy-worker.sh
/home/silverman/silverman-blog-linkedin-worker/verify-worker-deploy.sh
```

Confirm `/openapi.json` exposes Flow A endpoints before n8n smoke. The readiness script does **not** run deploy or restart automatically.

Relationship to `smoke-worker.sh`: smoke-worker is minimal post-deploy; `flow_a_readiness.py` is the Flow A pre-smoke gate with OpenAPI and git checks.

### 4. Configure n8n (draft generation workflow)

In the **Set Configuration** node of workflow `Silverman Blog LinkedIn Draft Generation`:

| Field | Value |
|-------|-------|
| `worker_base_url` | `http://192.168.0.194:8010` |
| `worker_api_key` | Same value as `SILVERMAN_BLOG_LINKEDIN_API_KEY` in server `.env` |

Do not modify n8n gateway or `local-ai-stack` compose.

Run the workflow manually and verify a draft appears under `linkedin-posts/review/` while the source post remains in `blog-posts/ready/`.

### 5. Import Flow A n8n workflow

The `local-ai-stack` deployment exposes n8n through an **nginx gateway** container (for example `local-ai-stack-n8n-gateway-1`). The gateway is **not** the n8n application — do not run `n8n import:workflow` against it. Select the real n8n container by image (`docker.n8n.io/n8nio/n8n` or `n8nio/n8n`), for example `local-ai-stack-n8n-1`.

**Why a stable workflow id:** n8n imports into Postgres via `workflow_entity.id`. Exports without a top-level `id` (or with null `createdAt` / `updatedAt` / `versionId`) can fail with `null value in column "id"`. The import script sets stable id `silvermanFlowAPublish01` before import.

1. Copy the workflow export to the server import path:

   ```bash
   mkdir -p /home/silverman/n8n-imports
   cp /path/to/repo/n8n/workflows/silverman-blog-linkedin-flow-a-publish.json \
      /home/silverman/n8n-imports/silverman-blog-linkedin-flow-a-publish.source.json
   ```

2. Run the import script on the Ubuntu server:

   ```bash
   /home/silverman/silverman-blog-linkedin-worker/import-flow-a-n8n-workflow.sh
   # or from repo checkout:
   ./deploy/server/import-flow-a-n8n-workflow.sh
   ```

   Defaults: source `/home/silverman/n8n-imports/silverman-blog-linkedin-flow-a-publish.source.json`, prepared output alongside with `.prepared.json` suffix, worker env `/home/silverman/silverman-blog-linkedin-worker/.env`, `worker_base_url` `http://192.168.0.194:8010`, workflow name **Silverman Blog LinkedIn Flow A Publish**, id `silvermanFlowAPublish01`.

3. Confirm safe output only (`worker_api_key: configured` — never the key) and `OVERALL: PASS` with 26 nodes and `active=false`.

The script reads `SILVERMAN_BLOG_LINKEDIN_API_KEY` from the worker `.env`, updates **Set Configuration** `worker_base_url` and `worker_api_key`, imports via `docker exec <n8n-container> n8n import:workflow`, and verifies with `export:workflow`. It does **not** activate the workflow, add cron/webhook triggers, call the LinkedIn API, or modify the worker or nginx gateway.

**Workflow must remain inactive** until a future operational change explicitly enables scheduling. Manual smoke uses the n8n editor Manual Trigger only.

Phase 0 `n8n_workflow_import` may remain **pending** when the readiness script cannot verify import over HTTP alone; a successful import script run satisfies manual import verification evidence.

## Updates

Re-run the deploy script on the **Ubuntu server** after pulling or syncing new code:

```bash
./deploy/server/deploy-worker.sh
/home/silverman/silverman-blog-linkedin-worker/smoke-worker.sh
/home/silverman/silverman-blog-linkedin-worker/verify-worker-deploy.sh
```

The deploy builds with `BUILD_REVISION`, recreates the container (`--force-recreate`), and verifies OpenAPI Flow A paths. Use `DEPLOY_FORCE_REBUILD=1` for a `--no-cache` image rebuild when the worker remains stale.

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

### Stale container image / Flow A OpenAPI missing after deploy

Symptom: `GET /health` returns HTTP 200 but `GET /openapi.json` is missing `/publish-blog-post`, `/generate-linkedin-package`, or `/schedule-linkedin-distribution`.

Common causes:

1. **Deploy ran on Mac, not the server** — `deploy-worker.sh` syncs to `TARGET_DIR` on the machine where it runs. Run it on the Ubuntu server (SSH) or ensure `DEPLOY_DIR` points at the server deployment directory.
2. **Docker reused a cached image** — the worker runs code installed at image build time (`pip install .`), not from a live source mount. Force rebuild:

```bash
cd /home/silverman/silverman-blog-linkedin-worker
DEPLOY_FORCE_REBUILD=1 ./deploy-worker.sh
```

3. **Old container still bound to port 8010** — deploy now uses `--force-recreate`; verify with:

```bash
/home/silverman/silverman-blog-linkedin-worker/verify-worker-deploy.sh
```

Manual no-cache rebuild:

```bash
cd /home/silverman/silverman-blog-linkedin-worker
BUILD_REVISION=$(date +%s) docker compose -f silverman-worker.compose.yaml build --no-cache
docker compose -f silverman-worker.compose.yaml up -d --force-recreate
/home/silverman/silverman-blog-linkedin-worker/verify-worker-deploy.sh
```

### Secrets in git

Real `SILVERMAN_BLOG_LINKEDIN_API_KEY` and `DEEPSEEK_API_KEY` values must exist only in server-local `.env`. Committed files use `CHANGE_ME_*` placeholders.

## Related files

| File | Purpose |
|------|---------|
| `deploy/server/silverman-worker.compose.yaml` | Isolated compose definition |
| `deploy/server/silverman-worker.env.example` | Documented env placeholders |
| `deploy/server/deploy-worker.sh` | Deploy script (sync, build, recreate, verify) |
| `deploy/server/verify-worker-deploy.sh` | Post-deploy worker readiness wait + Flow A OpenAPI verification |
| `deploy/server/smoke-worker.sh` | HTTP smoke tests |
| `deploy/server/verify-worker-api-key-rotation.sh` | Post-rotation auth verification |
| `docker-compose.example.yml` | Local/dev compose (not for server) |
