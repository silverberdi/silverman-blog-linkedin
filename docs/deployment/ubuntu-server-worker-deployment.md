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
| `docker-compose.example.yml` | Local/dev compose (not for server) |
