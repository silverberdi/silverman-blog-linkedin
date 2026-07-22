# worker-foundation

## Purpose

HTTP worker service foundation for the `silverman-blog-linkedin` project: environment-based configuration, editorial folder validation, health endpoint, Docker packaging, and foundational tests.

## Requirements

### Requirement: Worker service foundation

The system SHALL provide an HTTP worker service for the `silverman-blog-linkedin` project, implemented in Python with FastAPI, suitable for local development on Mac and deployment as a Docker container on the Linux server.

#### Scenario: Service starts locally

- **WHEN** the worker is started with valid environment configuration on a development machine
- **THEN** the HTTP server listens on the configured `PORT` and accepts HTTP requests

#### Scenario: Service starts in container

- **WHEN** the worker container is started with `SILVERMAN_BLOG_LINKEDIN_BASE_PATH=/data/silverman-blog-linkedin` and a volume mount for editorial data
- **THEN** the HTTP server listens on the configured `PORT` inside the container

### Requirement: Environment-based configuration

The worker SHALL load configuration from environment variables. The following variables MUST be supported:

| Variable | Required | Purpose |
|----------|----------|---------|
| `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` | Yes (default allowed for local dev) | Root path for editorial data |
| `SILVERMAN_BLOG_LINKEDIN_API_KEY` | Yes | Shared secret for future authenticated endpoints |
| `PORT` | No | HTTP listen port |

#### Scenario: Local development defaults

- **WHEN** `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` is not set and the worker starts in local development mode
- **THEN** the worker uses `./data/silverman-blog-linkedin` as the default base path

#### Scenario: Container base path

- **WHEN** the worker runs in a container with `SILVERMAN_BLOG_LINKEDIN_BASE_PATH=/data/silverman-blog-linkedin`
- **THEN** the worker uses `/data/silverman-blog-linkedin` as the editorial root

#### Scenario: Missing API key

- **WHEN** `SILVERMAN_BLOG_LINKEDIN_API_KEY` is unset or empty at startup
- **THEN** the worker fails to start with a clear configuration error that does not expose secret values

#### Scenario: Default port

- **WHEN** `PORT` is not set
- **THEN** the worker listens on port `8000`

### Requirement: Editorial folder validation

The worker SHALL validate the expected editorial folder layout under the configured base path. The following relative paths MUST be checked:

- `blog-posts/ready`
- `blog-posts/processed`
- `blog-posts/error`
- `linkedin-posts/review`
- `linkedin-posts/approved`
- `linkedin-posts/published`
- `metadata/runs`
- `metadata/campaigns`
- `metadata/backups`
- `prompts`

Validation MUST be read-only: it MUST NOT create, delete, move, or modify files or directories.

#### Scenario: All folders present

- **WHEN** the configured base path exists and every expected relative path exists as a directory
- **THEN** folder validation reports all folders as ready

#### Scenario: Missing folder

- **WHEN** one or more expected relative paths do not exist or are not directories
- **THEN** folder validation reports which paths failed and sets aggregate readiness to not ready

#### Scenario: Missing base path

- **WHEN** the configured base path does not exist
- **THEN** folder validation reports the base path as missing and aggregate readiness as not ready

### Requirement: metadata/backups is the editorial backup package root

The expected editorial folder `metadata/backups` under the configured base path MUST be treated as the designated root for editorial-state backup packages and manifests defined by `editorial-backup-scope-retention-integrity`.

Folder validation and `GET /health` MUST continue to treat `metadata/backups` as a required directory for aggregate folder readiness. Health and folder validation MUST remain read-only and MUST NOT create backup packages, verify backup integrity, prune retention, or restore editorial state.

#### Scenario: Backups folder remains part of readiness

- **WHEN** folder validation runs and `metadata/backups` exists as a directory
- **THEN** that path is reported ready as part of the existing expected-folder set

#### Scenario: Health does not perform backup operations

- **WHEN** a client calls `GET /health`
- **THEN** the worker does not create, verify, prune, or restore editorial backup packages as part of that request

### Requirement: Health endpoint

The worker SHALL expose `GET /health` returning structured JSON suitable for n8n branching.

The response MUST include:

- Service status (e.g., `healthy` or `degraded`)
- Project or service name identifier
- Configured base path (resolved absolute or normalized path)
- Per-folder validation results
- Aggregate folder readiness indicator
- Version or service identifier when appropriate
- Non-secret `deployment_environment` with value `uat` or `prod` when `SILVERMAN_DEPLOYMENT_ENVIRONMENT` is configured for operator UI↔API pairing (US-094)

When `SILVERMAN_DEPLOYMENT_ENVIRONMENT` is unset, the health response MUST NOT invent a fake environment identity; pairing-capable separated-UI deploys MUST set the variable so the UI can validate agreement.

#### Scenario: Healthy editorial layout

- **WHEN** a client sends `GET /health` and all expected editorial folders exist
- **THEN** the response is JSON with `status` indicating healthy, `folders_ready` true, and per-folder details for each expected path

#### Scenario: Degraded editorial layout

- **WHEN** a client sends `GET /health` and one or more expected folders are missing
- **THEN** the response is JSON with `status` indicating degraded, `folders_ready` false, and per-folder details showing which paths failed

#### Scenario: Health does not expose secrets

- **WHEN** a client sends `GET /health`
- **THEN** the response MUST NOT include `SILVERMAN_BLOG_LINKEDIN_API_KEY` or any other secret value

#### Scenario: Health is read-only

- **WHEN** a client sends `GET /health`
- **THEN** the worker MUST NOT mutate editorial files, call OpenAI, perform content generation, or depend on n8n

#### Scenario: Health advertises deployment environment when configured

- **WHEN** `SILVERMAN_DEPLOYMENT_ENVIRONMENT` is set to `uat` or `prod` and a client sends `GET /health`
- **THEN** the JSON response includes `deployment_environment` with that normalized value and does not include secret values

### Requirement: Docker packaging

The repository SHALL include a Dockerfile that builds a runnable container image for the worker.

#### Scenario: Image build

- **WHEN** a operator builds the Docker image from the Dockerfile
- **THEN** the resulting image starts the worker HTTP service on the configured `PORT`

### Requirement: Docker Compose example

The repository SHALL include a docker-compose example file documenting local or server deployment with environment variables and a volume mount for editorial data at `/data/silverman-blog-linkedin`.

#### Scenario: Compose example documents server layout

- **WHEN** an operator reads the docker-compose example
- **THEN** it shows how to set `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`, `SILVERMAN_BLOG_LINKEDIN_API_KEY`, `PORT`, and mount host editorial data into the container

### Requirement: README documentation

The repository SHALL include a README describing worker purpose, local setup, environment variables, expected editorial folder layout, how to run tests, and how to call `GET /health`.

#### Scenario: New developer onboarding

- **WHEN** a developer follows the README to configure environment variables and start the worker locally
- **THEN** they can successfully invoke `GET /health` and interpret the JSON response

### Requirement: Foundation tests

The worker SHALL include automated tests covering configuration loading, editorial path validation, and the `GET /health` endpoint.

#### Scenario: Configuration tests

- **WHEN** tests run with various environment variable combinations
- **THEN** tests verify default base path, default port, required API key behavior, and path resolution

#### Scenario: Path validation tests

- **WHEN** tests run against a temporary directory with partial or complete editorial layout
- **THEN** tests verify correct ready/not-ready results and per-folder reporting

#### Scenario: Health endpoint tests

- **WHEN** tests invoke `GET /health` via the FastAPI test client
- **THEN** tests verify JSON structure, status values, folder reporting, and absence of secrets in the response
