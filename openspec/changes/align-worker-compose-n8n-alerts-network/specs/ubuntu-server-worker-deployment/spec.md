## MODIFIED Requirements

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
