## Why

The worker and n8n orchestration flow are proven locally, but the Ubuntu server still has no version-controlled, isolated deployment path for the worker. Operators cannot run the worker against the shared editorial tree on `192.168.0.194` without risking changes to the existing `local-ai-stack` compose (n8n, postgres, minio, qdrant, and related services). This change delivers a separate Docker Compose deployment on host port `8010` so n8n can call `http://192.168.0.194:8010` while shared stack services remain untouched.

## Goals

- Version-controlled server deployment artifacts under `deploy/server/` (compose, env example, deploy script, smoke script).
- Isolated deployment directory on the server: `/home/silverman/silverman-blog-linkedin-worker`.
- Worker container on port `8000`, exposed on host port `8010`, with `restart: unless-stopped`.
- Mount only the shared editorial root: `/home/silverman/compartido_mac/silverman-blog-linkedin` → `/data/silverman-blog-linkedin`.
- Server-local `.env` for secrets (never committed); example file documents required variables.
- Operator documentation for deployment, smoke testing, and n8n `worker_base_url` configuration.
- Optional lightweight tests validating deployment artifact structure—no over-engineering.

## Non-Goals

- Modifying `/home/silverman/local-ai-stack/compose.yaml` or any existing shared-stack service (n8n, postgres, minio, qdrant, portainer, backup-runner, auto-ingest-runner, n8n-gateway).
- Changing worker application code or HTTP endpoint behavior.
- Automatic secret provisioning, CI/CD pipelines, or remote SSH automation from the repository.
- LinkedIn publishing, GitHub publishing, or moving blog posts out of `blog-posts/ready/`.
- Replacing or merging with `docker-compose.example.yml` (that file remains the local/dev example).
- Dairector content.

## What Changes

- Add OpenSpec capability `ubuntu-server-worker-deployment` defining requirements for isolated Ubuntu server deployment.
- Add `deploy/server/silverman-worker.compose.yaml` — isolated compose with build context, port `8010:8000`, editorial volume mount, env from server-local `.env`, healthcheck, `unless-stopped` restart.
- Add `deploy/server/silverman-worker.env.example` — documented placeholders for `SILVERMAN_BLOG_LINKEDIN_API_KEY`, `DEEPSEEK_API_KEY`, and optional DeepSeek tuning vars (no real secrets).
- Add `deploy/server/deploy-worker.sh` — safe, explicit deploy script: create target dir, sync artifacts, instruct manual `.env` creation, run compose for this project only.
- Add `deploy/server/smoke-worker.sh` — `GET /health` and authenticated `POST /process-ready` checks; optional deeper generation smoke when DeepSeek key and ready `.md` exist.
- Add `docs/deployment/ubuntu-server-worker-deployment.md` — full operator guide (paths, ports, rollback, n8n URL).
- Update `README.md` with a link to the deployment guide.
- Add optional lightweight pytest checks for deployment artifact presence and basic compose/env structure.

## Why a Dedicated HTTP Worker (Not n8n Execute Command)

The worker already owns filesystem boundaries, path validation, metadata writes, and DeepSeek calls (ADR-0001). Server deployment must preserve that model: n8n continues to call the worker over HTTP only. This change deploys the worker container in isolation—it does not grant n8n host filesystem or shell access.

## Capabilities

### New Capabilities

- `ubuntu-server-worker-deployment`: Version-controlled, isolated Docker Compose deployment for the worker on Ubuntu server `192.168.0.194`, host port `8010`, editorial mount at `/home/silverman/compartido_mac/silverman-blog-linkedin`, server-local secrets via `.env`, deploy and smoke scripts, and operator documentation—without modifying `local-ai-stack` or shared services.

### Modified Capabilities

- _(none — worker runtime requirements are unchanged; this change adds deployment artifacts and ops documentation only)_

## Impact

- **Repository**: New `deploy/server/` directory, `docs/deployment/` guide, README link, optional deployment artifact tests.
- **Worker application**: No behavioral changes expected; existing Dockerfile and env var contract reused.
- **Ubuntu server**: New isolated directory `/home/silverman/silverman-blog-linkedin-worker`; worker listens on `8010`; editorial data read/write via existing shared mount path.
- **n8n**: After deploy, operators set workflow `worker_base_url` to `http://192.168.0.194:8010`; no gateway or stack compose changes.
- **Security**: Real API keys remain server-local only; committed files use placeholders and examples.
- **Operations**: Rollback is `docker compose down` in the worker project directory only; `local-ai-stack` is never stopped or modified by deploy scripts.
