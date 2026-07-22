## MODIFIED Requirements

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
