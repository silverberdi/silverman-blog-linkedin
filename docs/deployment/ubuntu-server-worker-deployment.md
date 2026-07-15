# Ubuntu server worker deployment

Deploy the `silverman-blog-linkedin` HTTP worker on the Ubuntu server (`silverman@192.168.0.194`) as an **isolated Docker Compose project**. This deployment does **not** modify `local-ai-stack` (n8n, postgres, minio, qdrant, portainer, backup-runner, auto-ingest-runner, n8n-gateway).

**Status and live flags:** [CURRENT-STATE.md](../CURRENT-STATE.md), [RUNTIME-STATE.md](../RUNTIME-STATE.md).
**Build identity:** Image built with `BUILD_REVISION` from git HEAD at deploy time (not `SILVERMAN_BUILD_REVISION`).
**Site published/live:** Worker handoff writes to `/public-blog`; operator must **manually** `git commit` and `git push` the GitHub Pages repo.

For local development on Mac, use `docker-compose.example.yml` instead.

## Strategy

| Aspect | Value |
|--------|-------|
| Compose project | Isolated — `deploy/server/silverman-worker.compose.yaml` only |
| Deployment directory | `/home/silverman/silverman-blog-linkedin-worker` |
| Host port | `8010` → container `8000` |
| Editorial mount (host) | `/home/silverman/compartido_mac/silverman-blog-linkedin` |
| Editorial mount (container) | `/data/silverman-blog-linkedin` |
| Public blog repo mount (host) | `/home/silverman/silverberdi.github.io` (override via `SILVERMAN_PUBLIC_BLOG_REPO_PATH`) |
| Public blog repo mount (container) | `/public-blog` (`SILVERMAN_GITHUB_PAGES_REPO_PATH`) |
| Site URL | `https://silverman.pro` (override via `SILVERMAN_SITE_URL`) |
| n8n `worker_base_url` | `http://192.168.0.194:8010` |

## Prerequisites

- Docker and Docker Compose v2 on the Ubuntu server
- Repository checkout or synced artifacts on the server
- Write access to `/home/silverman/compartido_mac/silverman-blog-linkedin` (for `metadata/runs/` and `linkedin-posts/review/`)
- Editorial folder layout under the shared mount (see README), including `editorial-calendar/` (required for `/health`; `editorial-calendar/calendar.json` optional for `/health`)
- **Flow A publish:** a local clone of the GitHub Pages repo (`silverberdi.github.io`) on the server host with `_posts/` and `assets/images/` (default `/home/silverman/silverberdi.github.io`). The deploy script does **not** clone this repo automatically.

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
- Optional (ComfyUI blog images): `SILVERMAN_COMFYUI_IMAGE_ENABLED` (default `false`), `SILVERMAN_COMFYUI_BASE_URL`, `SILVERMAN_COMFYUI_API_PREFIX`, `SILVERMAN_COMFYUI_API_KEY`, `SILVERMAN_COMFYUI_AUTH_HEADER_NAME`, `SILVERMAN_COMFYUI_EXTRA_DATA_API_KEY_FIELD`, `SILVERMAN_COMFYUI_WORKFLOW_PATH`, `SILVERMAN_COMFYUI_TIMEOUT_SECONDS`, `SILVERMAN_COMFYUI_IMAGE_WIDTH`, `SILVERMAN_COMFYUI_IMAGE_HEIGHT`, `SILVERMAN_COMFYUI_DRY_RUN` — see README ComfyUI section. **Comfy Cloud:** `SILVERMAN_COMFYUI_AUTH_HEADER_NAME=X-API-Key` (raw key, not Bearer), optional `SILVERMAN_COMFYUI_EXTRA_DATA_API_KEY_FIELD=api_key_comfy_org` for Partner Nodes; `Authorization: Bearer` only for hosted APIs that document Bearer auth
- Optional (Flow A publish): `SILVERMAN_PUBLIC_BLOG_REPO_PATH` — host path to the `silverberdi.github.io` checkout (default `/home/silverman/silverberdi.github.io`); used by compose to mount `/public-blog`
- Optional (Git publication): `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED` (default `false`), `SILVERMAN_BLOG_GIT_PUBLICATION_BRANCH` (default `main`), `SILVERMAN_BLOG_GIT_PUBLICATION_REMOTE` (default `origin`), `SILVERMAN_BLOG_GIT_COMMIT_MESSAGE_TEMPLATE` — guarded commit/push after blog handoff when the request includes `git_publication: true`; see [blog-publishing-bridge.md](../workflows/blog-publishing-bridge.md)
- Optional: `SILVERMAN_SITE_URL` — canonical public site URL (default `https://silverman.pro`)

### 1a. Prepare public GitHub Pages repo checkout (Flow A publish)

Before Flow A publish smoke, clone or sync the public blog repo on the Ubuntu server:

```bash
git clone git@github.com:silverberdi/silverberdi.github.io.git /home/silverman/silverberdi.github.io
# Or rsync from another machine that already has the checkout
```

The checkout must contain `_posts/` and `assets/images/`. `deploy-worker.sh` verifies this before `docker compose up` and fails with remediation if missing. Set `SKIP_PUBLIC_BLOG_REPO_CHECK=1` only when deploying without Flow A publishing.

The worker container receives `SILVERMAN_GITHUB_PAGES_REPO_PATH=/public-blog` from compose. Without this mount, `POST /publish-blog-post` fails with `blog_publish_public_repo_not_configured` even when n8n validation passes — that error indicates a worker deployment/configuration issue, not an n8n failure.

### Git publication prerequisites (optional)

Automatic Git publication is **disabled by default**. When enabling `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true`:

1. The worker Docker image includes the `git` binary (`git --version` must succeed in the built container).
2. Configure a repository-scoped GitHub deploy key for `silverberdi.github.io` with push access to the target branch.
3. Mount the private key read-only from the worker secrets directory into the container (never commit key material to git).
4. Configure Git/SSH in the container to use the mounted key (for example via `GIT_SSH_COMMAND`).
5. Run controlled validation with `git_publication: true` on `POST /publish-blog-post` or calendar execution before relying on automation.

Do not store keys, tokens, or credential file contents in HTTP responses, campaign metadata, logs, or versioned documentation examples.

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
- Container env `SILVERMAN_GITHUB_PAGES_REPO_PATH=/public-blog` and paths `/public-blog/_posts`, `/public-blog/assets/images` exist inside the worker container

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

**Phase 0 (required gate):** git HEAD / `origin/main`, expected commits by default (`88cd5bc` Flow A calendar completion, `96519c3` guarded Git publication, `9dba064` live-site confirmation — override with repeatable `--expected-commit`), required Flow A files, worker `GET /health` and `GET /openapi.json` with paths `/health`, `/process-ready`, `/publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`, Flow A workflow export `"active": false`.

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

#### Canonical Flow A workflow identity (US-009 / US-010)

| Attribute | Value |
|-----------|-------|
| Repository export | `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` |
| Workflow display name | `Silverman Blog LinkedIn Flow A Publish` |
| Stable n8n workflow id | `silvermanFlowAPublish01` |
| Expected node count | `31` |
| Export `active` (git) | `false` |
| Server `active` after US-010 activation | `true` (RUNTIME-STATE authority; separate from import) |
| Schedule | Daily `0 9 * * *` UTC via Schedule Trigger |
| Single-flight | `Single-Flight Guard` (TTL 2h; `skipped_already_running`) |
| Default import source on server | `/home/silverman/n8n-imports/silverman-blog-linkedin-flow-a-publish.source.json` |
| Import script | `deploy/server/import-flow-a-n8n-workflow.sh` (or target layout `/home/silverman/silverman-blog-linkedin-worker/import-flow-a-n8n-workflow.sh`) |
| Default `worker_base_url` | `http://192.168.0.194:8010` |

**Not the canonical Flow A workflow:** `silverman-blog-linkedin-draft-generation.json` (Flow B drafts) and any LinkedIn `publish-pending` helper workflow (BL-007 handoff).

**Execution frequency (materialized in export):** daily at **09:00 UTC** via Schedule Trigger. Repository export remains `"active": false`. Server activation (`active: true`) is an explicit post-import operator step. Ready-folder HTTP path is retained (`POST /process-ready` → publish → package → schedule); this is **not** a rewrite to `POST /editorial-calendar/execute-flow-a-due`. Empty ready folder → clean no-op. Prefer empty-ready evidence; do not call LinkedIn publication APIs for US-010 checks.

**Flow A vs LinkedIn enablement:** Activated/scheduled Flow A ≠ `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`. Campaign `distribution_scheduled` ≠ LinkedIn API published. Real LinkedIn API publish remains fail-closed via `linkedin_publish_not_enabled` until separately approved. **US-011 is not permanent LinkedIn-off** — controlled evidence may set the flag `false`, prove fail-closed, then restore the recorded baseline (see [us-011 validation](../operations/us-011-linkedin-publication-guard-validation-2026-07-15.md)). US-011 **validated 2026-07-15**; BL-005 remains open. Out of scope for US-011: BL-005, BL-007 / `auto_queue_pending` / publish-pending WIP, Flow B, calendar `execute-flow-a-due` rewrite, new LinkedIn routes.

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

3. Confirm safe output only (`worker_api_key: configured` — never the key) and `OVERALL: PASS` with 31 nodes, Schedule Trigger `0 9 * * *` UTC, single-flight guard present, and `active=false` immediately after import.

4. **Activate separately (US-010, approval-gated):** enable `silvermanFlowAPublish01` in n8n UI (or scripted activate). Verify with:

   ```bash
   ./deploy/server/collect-flow-a-smoke-evidence.sh --expect-server-active
   ```

   Prefer empty `blog-posts/ready/` for concurrency/restart evidence (Manual no-op). Do not flip `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` for US-010. Record evidence under `docs/operations/us-010-flow-a-n8n-activation-validation-YYYY-MM-DD.md`.

The script reads `SILVERMAN_BLOG_LINKEDIN_API_KEY` from the worker `.env`, updates **Set Configuration** `worker_base_url` and `worker_api_key`, imports via `docker exec <n8n-container> n8n import:workflow`, and verifies with `export:workflow`. It does **not** activate the workflow by default, call the LinkedIn API, or modify the worker or nginx gateway.

**Import → verify → activate:** import prepares/verifies inactive; activation is a separate operator step. Repository export must stay `"active": false`. n8n active ≠ BL-005 unattended; blog handoff ≠ site live.

Phase 0 `n8n_workflow_import` may remain **pending** when the readiness script cannot verify import over HTTP alone; a successful import script run satisfies manual import verification evidence.

### 5a. Collect Flow A post-smoke evidence

After a manual Flow A n8n execution (Phase 3), collect read-only evidence with the server-side script. **Do not** use ad-hoc SSH heredocs with nested `docker inspect --format` quoting — manual evidence commands failed in practice due to shell quoting and because the server `.env` may not define `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` (only `SILVERMAN_BLOG_LINKEDIN_API_KEY`).

```bash
# Target layout (on Ubuntu server)
/home/silverman/silverman-blog-linkedin-worker/collect-flow-a-smoke-evidence.sh

# Repo layout
./deploy/server/collect-flow-a-smoke-evidence.sh
```

**Defaults:** `WORKER_BASE_URL=http://localhost:8010`, `WORKER_CONTAINER=silverman-blog-linkedin-worker`, workflow id `silvermanFlowAPublish01`, slug fragment `why-i-did-not-start-with-the-database`.

**Modes:** default pre-activation expects `active=false`; `--expect-server-active` expects `active=true` after intentional activate. Both modes require Schedule Trigger `0 9 * * *` UTC, single-flight guard, and expected node count `31`.

**Base path resolution (in order):** `BASE_PATH` override if set and directory exists; worker container env `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`; Docker mount mapped to host source containing `/data/silverman-blog-linkedin`; `GET /health` `base_path`; known host candidates (`/home/silverman/compartido_mac/silverman-blog-linkedin`, etc.). The script prints how the path was resolved.

**Collected evidence:** worker `GET /health` and `GET /openapi.json` (Flow A paths); public blog repo readiness (`SILVERMAN_GITHUB_PAGES_REPO_PATH`, `/public-blog/_posts`, `/public-blog/assets/images`, host mount when available); **editorial artifacts** under the resolved editorial base path (`metadata/runs/*.json`, `metadata/campaigns/*.json`, `linkedin-posts/generated/`); **public blog artifacts** — published `_posts` and `assets/images` matching the slug fragment under the public GitHub Pages repo host mount (`${PUBLIC_BLOG_HOST_MOUNT}`, default `/home/silverman/silverberdi.github.io`) or inside the container at `/public-blog` when the host mount cannot be resolved; n8n workflow export confirming mode-aware `active`, Schedule Trigger, single-flight guard, and 31 nodes.

Published blog files are informational for diagnosis (e.g. publish succeeded but LinkedIn generation failed later). They do not affect `OVERALL: PASS`.

**Overall status:** `PASS` when worker, public blog repo, and n8n checks pass and latest campaign evidence shows `distribution_scheduled` (or later) or `linkedin_distribution` exists; `PENDING` when worker, public blog repo, and n8n are OK but the campaign has not reached distribution (e.g. `validated`, `blog_published`, `derivatives_generated` without package/distribution); `FAIL` when base path is unresolved, Flow A OpenAPI paths are missing, public blog repo is not mounted or incomplete, active-state expectation for the selected mode is violated, n8n is missing, or campaign state is `error`. Plain campaign metadata existence alone does not produce `PASS`. Generated LinkedIn files count toward evidence only when campaign state is at least `derivatives_generated` or `distribution_scheduled`. If worker and n8n are OK but the public repo is missing, the script reports `FAIL` with remediation (not `PENDING`) — publish would fail with `blog_publish_public_repo_not_configured`. For `published` variants, reports whether `linkedin_post_urn` is present (no post body, no tokens).

The collect-flow-a script is read-only: no secrets printed, no n8n activation, no LinkedIn API calls, no deploy/restart. Optional `--json` for machine-readable summary.

### 5c. US-003 LinkedIn publication validation (BL-002)

Controlled first-real-publish validation. **Publishes one real LinkedIn post** when `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` during the validation window. Prerequisites: [linkedin-publication-prerequisites.md](linkedin-publication-prerequisites.md) OAuth bootstrap.

```bash
/home/silverman/silverman-blog-linkedin-worker/run-us003-linkedin-publication-validation-smoke.sh \
  --campaign-id <flow-a-campaign-id> \
  --variant <approved-variant-id>
```

Requires explicit `--campaign-id` and `--variant`. Restores `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` after the run. Record evidence in `docs/operations/phase3-us003-linkedin-publication-validation-YYYY-MM-DD.md` (see [template](../operations/phase3-us003-linkedin-publication-validation-TEMPLATE.md)). Unlike US-001/US-002 smoke, the LinkedIn post is not automatically removed. Does not print secrets.

### 5b. Deterministic Flow A worker smoke (before n8n)

**Manual n8n execution is not the diagnostic source of truth.** Run the worker smoke script first to exercise publish → package → schedule directly against the deployed worker.

```bash
# Target layout (on Ubuntu server)
/home/silverman/silverman-blog-linkedin-worker/run-flow-a-worker-smoke.sh

# Repo layout
./deploy/server/run-flow-a-worker-smoke.sh
```

**Defaults:** `WORKER_BASE_URL=http://localhost:8010`, `.env` at `/home/silverman/silverman-blog-linkedin-worker/.env`, ready post `blog-posts/ready/01-why-i-did-not-start-with-the-database.md`, public blog host `/home/silverman/silverberdi.github.io`, `SITE_URL=https://silverman.pro`.

**Endpoint sequence:** `GET /health` → `POST /publish-blog-post` → `POST /generate-linkedin-package` → `POST /schedule-linkedin-distribution`. After each POST, the script prints campaign metadata snapshot (`state`, `source_public_url`, published paths, `linkedin_package`, `linkedin_distribution`, `errors`); on publish failure it prints the snapshot when `campaign_id` is available. Exits `OVERALL: PASS` only when final campaign state is `distribution_scheduled` with `linkedin_distribution` metadata present.

**Failure isolation:**

| Layer | Typical signal |
|-------|----------------|
| Worker deployment | `blog_publish_public_repo_not_configured`, health/OpenAPI failures |
| Worker publish idempotency | `validated` campaign + public files exist but publish fails (`blog_publish_target_exists`) — worker reconciliation |
| Worker error-state recovery | Campaign `error` from prior failed publish + public files match source — worker reconciles to `blog_published` when safe |
| Reconciliation ordering | `blog_publish_target_exists` with `source_public_url: null` while campaign has URL — check `blog_publish.reconciliation_skip_reason`; redeploy worker with ordering fix |
| Canonical publish-output comparison | `blog_publish_target_exists` with `reconciliation_skip_reason` content mismatch while public files exist — inspect `blog_publish` expected/actual SHA-256 diagnostics; redeploy worker |
| Public image drift (manual correction) | Public post matches canonical output, public image exists but differs from ready PNG — worker adopts existing public image; never overwrite public asset from ready folder |
| n8n orchestration | Worker smoke `PASS`, n8n fails at same HTTP node — re-import workflow JSON |
| Provider config | `deepseek_config_invalid` during package generation |
| Schedule mapping | Package `PASS`, schedule fails with `linkedin_schedule_*` errors |

Flags: `--dry-run`, `--worker-base-url`, `--relative-path`, `--site-url`, `--editorial-root`, `--public-blog-root`. No secrets printed, no n8n activation, no LinkedIn API, no git push, no destructive cleanup.

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

`GET /health` may return HTTP 200 with `status: degraded` when editorial folders are missing. Ensure the full folder layout exists under `/home/silverman/compartido_mac/silverman-blog-linkedin`, including:

```bash
mkdir -p /home/silverman/compartido_mac/silverman-blog-linkedin/editorial-calendar
```

Container path: `/data/silverman-blog-linkedin/editorial-calendar/`. The folder is required for `/health`; `calendar.json` inside it is optional for `/health` and may be added later for planning endpoints.

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

### Flow A publish fails with `blog_publish_public_repo_not_configured`

Symptom: Flow A n8n execution reaches **Publish Blog Post**, validation passes, campaign metadata reaches `validated`, but publishing fails with `blog_publish_public_repo_not_configured`.

This is a **worker deployment/configuration** issue, not an n8n failure. The worker container is missing `SILVERMAN_GITHUB_PAGES_REPO_PATH` or the `/public-blog` mount.

Remediation:

1. Clone or sync `silverberdi.github.io` to the server (default `/home/silverman/silverberdi.github.io`).
2. Ensure `_posts/` and `assets/images/` exist in that checkout.
3. Set `SILVERMAN_PUBLIC_BLOG_REPO_PATH` in `.env` if using a non-default host path.
4. Redeploy on the Ubuntu server (see deploy-worker.sh in the worker deployment directory).
5. Confirm with `verify-worker-deploy.sh` or `collect-flow-a-smoke-evidence.sh` — public blog repo section should pass.

The deploy script does not clone the GitHub Pages repo automatically.

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
| `deploy/server/collect-flow-a-smoke-evidence.sh` | Read-only Flow A post-smoke evidence collection |
| `deploy/server/run-flow-a-worker-smoke.sh` | Deterministic Flow A worker smoke (publish/package/schedule without n8n) |
| `deploy/server/run-us003-linkedin-publication-validation-smoke.sh` | US-003 controlled first-real LinkedIn publication validation (BL-002) |
| `deploy/server/run-linkedin-publication-smoke.sh` | Generic LinkedIn publication dry-run/real smoke |
| `deploy/server/verify-worker-api-key-rotation.sh` | Post-rotation auth verification |
| `docker-compose.example.yml` | Local/dev compose (not for server) |
