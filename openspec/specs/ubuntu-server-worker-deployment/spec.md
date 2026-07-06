# ubuntu-server-worker-deployment

## Purpose

Version-controlled, isolated Docker Compose deployment for the `silverman-blog-linkedin` HTTP worker on Ubuntu server `192.168.0.194`. The worker runs in its own compose project on host port `8010`, mounts the shared editorial tree at `/home/silverman/compartido_mac/silverman-blog-linkedin`, loads secrets from a server-local `.env`, and is operated via deploy and smoke scripts—without modifying `local-ai-stack` or shared-stack services. n8n continues to call the worker over HTTP only (ADR-0001).

## Requirements

### Requirement: Isolated server compose project

The repository SHALL provide an isolated Docker Compose file at `deploy/server/silverman-worker.compose.yaml` for deploying the worker on the Ubuntu server without modifying the existing `local-ai-stack` compose or shared-stack services.

#### Scenario: Compose is self-contained

- **WHEN** an operator inspects `deploy/server/silverman-worker.compose.yaml`
- **THEN** it defines a worker service that builds from the repository Dockerfile, uses `restart: unless-stopped`, and does not reference or depend on `local-ai-stack` services

#### Scenario: Deploy does not affect shared stack

- **WHEN** an operator runs `docker compose` using only `silverman-worker.compose.yaml` in the worker deployment directory
- **THEN** existing n8n, postgres, minio, qdrant, portainer, backup-runner, auto-ingest-runner, and n8n-gateway containers are not stopped or modified by that command

### Requirement: Server port and container networking

The isolated compose deployment SHALL publish the worker HTTP service on host port `8010` mapped to container port `8000`, with `PORT=8000` set inside the container.

#### Scenario: Host port mapping

- **WHEN** the worker container is running via `silverman-worker.compose.yaml`
- **THEN** `GET http://localhost:8010/health` on the server host reaches the worker health endpoint

#### Scenario: n8n worker base URL

- **WHEN** n8n on the server is configured with `worker_base_url` set to `http://192.168.0.194:8010`
- **THEN** HTTP Request nodes can reach the deployed worker without using n8n Execute Command or direct filesystem access

### Requirement: Editorial volume mount

The isolated compose deployment SHALL mount only the shared editorial directory on the server host into the container at `/data/silverman-blog-linkedin` and set `SILVERMAN_BLOG_LINKEDIN_BASE_PATH=/data/silverman-blog-linkedin`.

#### Scenario: Host editorial path

- **WHEN** the compose file is used on the target Ubuntu server
- **THEN** it mounts `/home/silverman/compartido_mac/silverman-blog-linkedin` to `/data/silverman-blog-linkedin` inside the container

#### Scenario: Write access for processing

- **WHEN** the worker runs with the documented volume mount
- **THEN** the container can write to `metadata/runs/` and `linkedin-posts/review/` under the mounted editorial root when host permissions allow

### Requirement: Server-local secrets configuration

The repository SHALL provide `deploy/server/silverman-worker.env.example` documenting required and optional environment variables for server deployment. Real secret values MUST NOT appear in committed repository files.

#### Scenario: Example documents worker API key

- **WHEN** an operator reads `silverman-worker.env.example`
- **THEN** it documents `SILVERMAN_BLOG_LINKEDIN_API_KEY` with a placeholder value and explains it must match n8n workflow configuration

#### Scenario: Example documents DeepSeek settings

- **WHEN** an operator reads `silverman-worker.env.example`
- **THEN** it documents `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `DEEPSEEK_TIMEOUT_SECONDS`, and `DEEPSEEK_MAX_OUTPUT_TOKENS` with placeholder or default values and no real API keys

#### Scenario: Compose reads server-local env file

- **WHEN** the worker is deployed on the server with a manually created `.env` file derived from the example
- **THEN** the compose deployment loads secret and configuration values from that server-local `.env` file and does not require secrets in the compose YAML itself

### Requirement: Deploy script

The repository SHALL provide `deploy/server/deploy-worker.sh` that safely deploys the isolated worker to `/home/silverman/silverman-blog-linkedin-worker` on the target server.

#### Scenario: Creates deployment directory

- **WHEN** an operator runs `deploy-worker.sh` and the target deployment directory does not exist
- **THEN** the script creates `/home/silverman/silverman-blog-linkedin-worker` (or a documented override) before running compose

#### Scenario: Syncs deployment artifacts

- **WHEN** an operator runs `deploy-worker.sh` from a repository checkout
- **THEN** the script copies or syncs required deployment and build artifacts into the target deployment directory

#### Scenario: Instructs manual env setup

- **WHEN** a server-local `.env` file is missing or incomplete
- **THEN** the script explains that the operator must create `.env` manually from `silverman-worker.env.example` and does not write real secrets into the repository

#### Scenario: Starts worker via isolated compose only

- **WHEN** `deploy-worker.sh` completes successfully
- **THEN** it has run `docker compose` using `silverman-worker.compose.yaml` in the worker deployment directory with build and detached start, and has not run `docker compose down` against unrelated projects

### Requirement: Smoke test script

The repository SHALL provide `deploy/server/smoke-worker.sh` that validates a deployed worker on the server using HTTP checks with clear PASS/FAIL output.

#### Scenario: Health check passes

- **WHEN** `smoke-worker.sh` runs against a healthy deployed worker
- **THEN** it performs `GET http://localhost:8010/health`, expects HTTP 200, and prints PASS for the health check

#### Scenario: Authenticated process-ready check

- **WHEN** `smoke-worker.sh` runs with a valid `SILVERMAN_BLOG_LINKEDIN_API_KEY` available from the server-local `.env`
- **THEN** it performs `POST /process-ready` with Bearer authentication and prints PASS or FAIL based on the HTTP response

#### Scenario: Optional generation smoke

- **WHEN** `DEEPSEEK_API_KEY` is configured and at least one ready Markdown file exists under the editorial mount
- **THEN** `smoke-worker.sh` MUST support an optional deeper generation smoke and report PASS or FAIL without requiring that check for basic deployment validation

#### Scenario: Overall result on failure

- **WHEN** a required smoke check fails
- **THEN** `smoke-worker.sh` prints FAIL for the failed check and exits with a non-zero status

### Requirement: Container healthcheck

The isolated compose deployment SHALL include a healthcheck that probes `GET /health` inside the container on port `8000`.

#### Scenario: Compose healthcheck defined

- **WHEN** an operator inspects `silverman-worker.compose.yaml`
- **THEN** it defines a healthcheck consistent with the worker `GET /health` endpoint on the container listen port

### Requirement: Deployment documentation

The repository SHALL include `docs/deployment/ubuntu-server-worker-deployment.md` describing Ubuntu server deployment prerequisites, directory layout, environment setup, deploy and smoke procedures, n8n `worker_base_url` configuration, rollback, and troubleshooting.

#### Scenario: Operator follows deployment guide

- **WHEN** an operator follows `docs/deployment/ubuntu-server-worker-deployment.md` on the target server
- **THEN** they can deploy the worker to port `8010`, run smoke tests, and point n8n at `http://192.168.0.194:8010` without modifying `local-ai-stack`

### Requirement: README deployment link

The repository README SHALL link to `docs/deployment/ubuntu-server-worker-deployment.md` for Ubuntu server deployment instructions.

#### Scenario: README points to server guide

- **WHEN** a developer reads the README Docker or deployment section
- **THEN** they find a link to the Ubuntu server worker deployment documentation distinct from the local `docker-compose.example.yml` workflow

### Requirement: Deployment artifact validation tests

The repository SHALL include lightweight automated tests that verify presence and basic structure of server deployment artifacts without requiring a live server connection.

#### Scenario: Compose artifact structure

- **WHEN** deployment artifact tests run in CI or locally
- **THEN** they verify `deploy/server/silverman-worker.compose.yaml` exists and declares the expected host port `8010`, container port `8000`, and editorial volume mount path

#### Scenario: Env example structure

- **WHEN** deployment artifact tests run
- **THEN** they verify `silverman-worker.env.example` documents required variable names and contains no patterns matching committed real secrets (placeholder values only)
