## ADDED Requirements

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

### Requirement: Deploy docs describe dual-service topology without claiming US-094

Operator deploy documentation for the Ubuntu worker SHALL briefly describe the dual-service topology (worker API on `8010`, operator UI on the chosen UI port), state that browsers use the UI while n8n continues to call the worker HTTP API only, and MUST NOT claim US-094 UAT/prod pairing is complete.

#### Scenario: Deploy guide mentions both services

- **WHEN** an operator reads the updated ubuntu-server worker deployment guide after US-093
- **THEN** the guide identifies how to reach the separated operator UI and the worker API as distinct LAN endpoints and reiterates ADR-0001 (n8n → worker HTTP only)
