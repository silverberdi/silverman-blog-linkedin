## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Deployment documentation

The repository SHALL include `docs/deployment/ubuntu-server-worker-deployment.md` describing Ubuntu server deployment prerequisites, directory layout, environment setup, deploy and smoke procedures, n8n `worker_base_url` configuration, worker API key rotation, rollback, and troubleshooting.

#### Scenario: Operator follows deployment guide

- **WHEN** an operator follows `docs/deployment/ubuntu-server-worker-deployment.md` on the target server
- **THEN** they can deploy the worker to port `8010`, run smoke tests, rotate the worker API key safely, and point n8n at `http://192.168.0.194:8010` without modifying `local-ai-stack`

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
