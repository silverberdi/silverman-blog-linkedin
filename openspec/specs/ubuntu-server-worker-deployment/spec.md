# ubuntu-server-worker-deployment

## Purpose

Version-controlled, isolated Docker Compose deployment for the `silverman-blog-linkedin` HTTP worker on Ubuntu server `192.168.0.194`. The worker runs in its own compose project on host port `8010`, mounts the shared editorial tree at `/home/silverman/compartido_mac/silverman-blog-linkedin`, loads secrets from a server-local `.env`, and is operated via deploy and smoke scripts—without modifying `local-ai-stack` or shared-stack services. The worker compose may join the external `local-ai-stack_backend` network for n8n webhook DNS used by operational alerts. n8n continues to call the worker over HTTP only (ADR-0001).

## Requirements

### Requirement: Isolated server compose project

The repository SHALL provide an isolated Docker Compose file at `deploy/server/silverman-worker.compose.yaml` for deploying the worker on the Ubuntu server without modifying the existing `local-ai-stack` compose or shared-stack services.

Isolation means the worker runs as its own compose project and deploy commands MUST NOT stop or recreate shared-stack containers. The worker compose MAY attach to the Docker network `local-ai-stack_backend` marked `external: true` so the container can resolve the n8n service DNS name for operational-alert webhook emission. The worker compose MUST NOT define or depend_on local-ai-stack application services (n8n, postgres, minio, qdrant, portainer, backup-runner, auto-ingest-runner, n8n-gateway).

#### Scenario: Compose is self-contained for lifecycle

- **WHEN** an operator inspects `deploy/server/silverman-worker.compose.yaml`
- **THEN** it defines a worker service that builds from the repository Dockerfile, uses `restart: unless-stopped`, and does not define or `depends_on` local-ai-stack application services

#### Scenario: Optional external n8n network for alerts

- **WHEN** operational alert emission targets the internal n8n webhook DNS name
- **THEN** the worker compose MAY list `local-ai-stack_backend` under `networks` with `external: true` and MUST NOT embed that network’s services into the worker project

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

### Requirement: Worker API key rotation documentation

The repository SHALL document a safe procedure for rotating `SILVERMAN_BLOG_LINKEDIN_API_KEY` on the deployed Ubuntu server in `docs/deployment/ubuntu-server-worker-deployment.md`. The procedure MUST NOT instruct operators to commit real API keys to the repository.

#### Scenario: Rotation steps documented

- **WHEN** an operator reads the worker API key rotation section in `docs/deployment/ubuntu-server-worker-deployment.md`
- **THEN** it describes generating a new key, backing up the current worker `.env` value and n8n `worker_api_key`, updating `/home/silverman/silverman-blog-linkedin-worker/.env`, restarting the worker container, updating n8n workflow **Silverman Blog LinkedIn Draft Generation** `worker_api_key` to match, and keeping `worker_base_url` as `http://192.168.0.194:8010`

#### Scenario: Post-rotation validation documented

- **WHEN** an operator follows the rotation validation steps in the deployment guide
- **THEN** the guide requires confirming `GET /health` still returns HTTP 200, authenticated endpoints reject the previous Bearer token, authenticated endpoints accept the new Bearer token, and a manual n8n workflow run produces a new draft under `linkedin-posts/review/` without moving the source post out of `blog-posts/ready/`

#### Scenario: Rotation rollback documented

- **WHEN** an operator needs to roll back a failed rotation
- **THEN** the deployment guide describes restoring the previous `SILVERMAN_BLOG_LINKEDIN_API_KEY` in the server-local `.env`, restarting the worker, running `smoke-worker.sh`, restoring the previous n8n `worker_api_key` if changed, and re-running the n8n workflow

### Requirement: Worker API key rotation verification helper

The repository SHALL provide `deploy/server/verify-worker-api-key-rotation.sh` to validate worker API key rotation on the server using HTTP checks with clear PASS/FAIL output.

#### Scenario: Health check during rotation verification

- **WHEN** `verify-worker-api-key-rotation.sh` runs against a healthy deployed worker
- **THEN** it performs `GET http://localhost:8010/health`, expects HTTP 200, and prints PASS or FAIL without printing secret values

#### Scenario: Old key rejection check

- **WHEN** `verify-worker-api-key-rotation.sh` runs with `OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY` set to the previous key and the worker `.env` contains the new key
- **THEN** it performs `POST /process-ready` with `Authorization: Bearer <old key>`, expects HTTP 401, and prints PASS or FAIL without printing the old or new key values

#### Scenario: New key acceptance check

- **WHEN** `verify-worker-api-key-rotation.sh` runs with a valid new `SILVERMAN_BLOG_LINKEDIN_API_KEY` in the server-local `.env`
- **THEN** it performs `POST /process-ready` with `Authorization: Bearer <new key from .env>`, expects HTTP 200, and prints PASS or FAIL without printing the key value

#### Scenario: Helper does not persist secrets

- **WHEN** an operator inspects `verify-worker-api-key-rotation.sh` and its documented usage
- **THEN** the script does not write API keys to files, does not accept the new key as a command-line argument, and does not echo key material to stdout or stderr

#### Scenario: Overall result on verification failure

- **WHEN** a required rotation verification check fails
- **THEN** `verify-worker-api-key-rotation.sh` prints FAIL for the failed check and exits with a non-zero status

### Requirement: Container healthcheck

The isolated compose deployment SHALL include a healthcheck that probes `GET /health` inside the container on port `8000`.

#### Scenario: Compose healthcheck defined

- **WHEN** an operator inspects `silverman-worker.compose.yaml`
- **THEN** it defines a healthcheck consistent with the worker `GET /health` endpoint on the container listen port

### Requirement: Deployment documentation

The repository SHALL include `docs/deployment/ubuntu-server-worker-deployment.md` describing Ubuntu server deployment prerequisites, directory layout, environment setup, deploy and smoke procedures, n8n `worker_base_url` configuration, worker API key rotation, rollback, and troubleshooting.

#### Scenario: Operator follows deployment guide

- **WHEN** an operator follows `docs/deployment/ubuntu-server-worker-deployment.md` on the target server
- **THEN** they can deploy the worker to port `8010`, run smoke tests, rotate the worker API key safely, and point n8n at `http://192.168.0.194:8010` without modifying `local-ai-stack`

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

#### Scenario: Rotation artifacts structure

- **WHEN** deployment artifact tests run
- **THEN** they verify `deploy/server/verify-worker-api-key-rotation.sh` exists, is executable or documents execution via `bash`, and `docs/deployment/ubuntu-server-worker-deployment.md` includes a worker API key rotation section

### Requirement: Server compose can run the separated operator UI service

The isolated Ubuntu server deployment SHALL provide a compose service (in `deploy/server/silverman-worker.compose.yaml` or an adjacent documented compose file in `deploy/server/`) that runs the separated operator UI artifact alongside the existing worker service. The UI service MUST publish a LAN host port distinct from the worker’s `8010` mapping (default recommendation `8011` unless the operator documents a different free port).

The UI service MUST NOT mount the editorial data tree as a browser source of truth and MUST NOT replace n8n→worker HTTP orchestration. Deploy commands for the UI MUST NOT require modifying `local-ai-stack` application services.

#### Scenario: UI service is defined for LAN publish

- **WHEN** an operator inspects the US-093 server compose artifacts
- **THEN** a separated operator UI service is defined with a host port distinct from `8010` and builds from the UI Dockerfile (or equivalent documented build context)

#### Scenario: UI compose does not absorb shared-stack services

- **WHEN** an operator starts the operator UI service via the documented compose file
- **THEN** local-ai-stack application services (n8n, postgres, minio, qdrant, portainer, backup-runner, auto-ingest-runner, n8n-gateway) are not defined as dependencies that the UI project owns or recreates

### Requirement: Server env example documents UI API base URL and CORS allowlist

The repository SHALL document server-local environment variables for the separated UI API base URL and the worker UI-origin allowlist in `deploy/server/` env examples (worker and/or UI). Examples MUST use non-secret placeholders only and MUST NOT embed real API keys.

#### Scenario: Env example names UI API base URL

- **WHEN** an operator reads the US-093-updated server env example files
- **THEN** `SILVERMAN_OPERATOR_UI_API_BASE_URL` (or the documented equivalent) appears with a non-secret placeholder such as `http://192.168.0.194:8010`

#### Scenario: Env example names UI origin allowlist

- **WHEN** an operator reads the US-093-updated server env example files
- **THEN** `SILVERMAN_OPERATOR_UI_ORIGINS` (or the documented equivalent) appears with a non-secret placeholder origin for the UI LAN URL

### Requirement: Server env examples document UAT and prod UI↔API pairing defaults

The repository SHALL document non-secret UAT and prod pairing defaults in `deploy/server/` env examples or clearly separated overlays such that each profile sets matching `SILVERMAN_DEPLOYMENT_ENVIRONMENT` and `SILVERMAN_OPERATOR_UI_ENV_LABEL`, and points `SILVERMAN_OPERATOR_UI_API_BASE_URL` at that profile’s worker origin placeholder (UAT UI → UAT API placeholder; prod UI → prod API placeholder).

Examples MUST NOT embed real API keys or bearer tokens. Documenting these defaults MUST NOT claim that a live second UAT stack or full BL-029 CI/UAT stand-up is complete.

#### Scenario: UAT overlay pairs UI label and API base to UAT

- **WHEN** an operator reads the UAT pairing env example
- **THEN** worker and UI environment tokens are `uat` and the UI API base URL placeholder is the UAT worker origin (not the prod placeholder)

#### Scenario: Prod overlay pairs UI label and API base to prod

- **WHEN** an operator reads the prod pairing env example
- **THEN** worker and UI environment tokens are `prod` and the UI API base URL placeholder is the prod worker origin (not the UAT placeholder)

### Requirement: Deploy docs describe dual-service topology and US-094 pairing

Operator deploy documentation for the Ubuntu worker SHALL briefly describe the dual-service topology (worker API on `8010`, operator UI on the chosen UI port), state that browsers use the separated UI while n8n continues to call the worker HTTP API only, and SHALL describe US-094 UAT/prod UI↔API pairing (env var names, closed `uat`/`prod` vocabulary, and default overlays).

After US-096, documentation MUST state that the supported operator console path is exclusively the separated UI service and MUST NOT present worker-embedded `GET /flow-a/console/linkedin-variant-supervision` (or equivalent) as a supported or compatibility production path. Documentation MUST note that former worker console URLs fail closed with a clear operator-visible outcome.

When US-099 is active, documentation MUST describe Cloudflare Tunnel (or equivalent) front-only public UI exposure, private worker API, and private UI→API hop at a topology level without embedding secrets or tunnel tokens. Documentation MUST NOT claim full BL-029 CI/UAT stand-up is complete merely because pairing defaults, validation, or public UI topology exist. Documentation MUST NOT claim Story accepted solely from docs updates.

#### Scenario: Deploy guide mentions both services and pairing

- **WHEN** an operator reads the updated ubuntu-server worker deployment guide after US-096
- **THEN** the guide identifies how to reach the separated operator UI and the worker API as distinct LAN endpoints, reiterates ADR-0001 (n8n → worker HTTP only), documents UAT/prod pairing configuration by env var name, and does not present the embedded worker console as a supported or compatibility production path

#### Scenario: Deploy guide notes decommissioned worker console URLs

- **WHEN** an operator reads the updated ubuntu-server worker deployment guide after US-096
- **THEN** the guide states that former worker console URLs fail closed and that operators should use the separated UI port (default `8011`)

#### Scenario: Deploy guide describes US-099 front-only topology when in scope

- **WHEN** an operator reads the ubuntu-server worker deployment guide after US-099 docs updates
- **THEN** the guide describes UI-only public ingress via Cloudflare Tunnel (or equivalent), private API, and private UI→API hop without printing secrets or claiming the worker API is internet-public

### Requirement: Worker image build does not embed the operator console SPA

The isolated Ubuntu server worker image build MUST NOT require a frontend production embed step (`build:embedded`, copying console assets into the worker package static tree, or equivalent) for a successful API image build after US-096.

Compose comments and deploy scripts MUST treat `silverman-operator-ui` as the exclusive supported console service and MUST NOT instruct operators to embed the SPA into the worker for production.

#### Scenario: Worker Dockerfile does not require build embedded

- **WHEN** an operator follows the documented worker image build after US-096
- **THEN** the instructions do not require `npm run build:embedded` (or equivalent) before building the worker API image

#### Scenario: Compose treats separated UI as exclusive console

- **WHEN** an operator inspects server compose comments or UI service docs after US-096
- **THEN** the separated operator UI service is described as the supported console path and the worker is not described as hosting a compatibility console SPA
