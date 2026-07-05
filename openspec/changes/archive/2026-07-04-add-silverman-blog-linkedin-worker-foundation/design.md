## Context

The `silverman-blog-linkedin` repository currently contains project context, ADRs, and workflow documentation but no application code. n8n on the Linux server (`192.168.0.194`) will orchestrate content automation by calling a dedicated HTTP worker (ADR-0001). Development happens locally on Mac; deployment is a Docker container with the editorial tree mounted at `/data/silverman-blog-linkedin` (ADR-0003).

This change delivers the worker foundation only: service skeleton, configuration, editorial folder validation, and `GET /health`. Processing endpoints and OpenAI integration are deferred to later OpenSpec changes.

## Goals / Non-Goals

**Goals:**

- Provide a small, testable FastAPI HTTP service that n8n can call over HTTP Request nodes.
- Load configuration from environment variables with sensible local defaults.
- Validate the editorial folder layout under the configured base path and surface results in `/health`.
- Package the service for local development and container deployment (Dockerfile, docker-compose example, README).
- Include automated tests for configuration, path validation, and the health endpoint.

**Non-Goals:**

- `POST /process-ready`, `POST /process-file`, OpenAI calls, content generation, file moves, metadata writes.
- n8n workflow JSON, GitHub publish, LinkedIn publish, Dairector paths.
- Auto-creating missing editorial folders (validation reports missing paths; creation is a human or future-change concern unless explicitly added later).
- API key enforcement on `GET /health` in this change (key is loaded and reserved for future authenticated endpoints; health remains unauthenticated for ops/n8n liveness checks).

## Decisions

### 1. Python + FastAPI

**Decision:** Use Python 3.11+ with FastAPI and uvicorn.

**Rationale:** FastAPI provides async-capable HTTP handling, automatic OpenAPI docs, and straightforward JSON response models—well suited for n8n integration and local testing. Python aligns with common LLM tooling for future processing phases.

**Alternatives considered:**

- **Node.js (Express/Fastify):** Viable but no strong advantage for file-heavy processing planned in phase 2.
- **Go:** Strong for containers but higher upfront cost for a small foundation service.

### 2. Project layout

**Decision:** Minimal package layout under `src/silverman_blog_linkedin/` (or equivalent single top-level package):

```
src/silverman_blog_linkedin/
  __init__.py          # version / service identifier
  config.py            # env loading and defaults
  paths.py             # expected folder list and validation
  main.py              # FastAPI app factory and routes
tests/
  test_config.py
  test_paths.py
  test_health.py
Dockerfile
docker-compose.example.yml
README.md
pyproject.toml         # dependencies and test runner config
```

**Rationale:** Separates configuration, path validation, and HTTP layer for unit testing without standing up the full server for every case.

### 3. Environment variables

**Decision:** Three required configuration variables for foundation:

| Variable | Purpose | Default (local dev) |
|----------|---------|---------------------|
| `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` | Root editorial data directory | `./data/silverman-blog-linkedin` |
| `SILVERMAN_BLOG_LINKEDIN_API_KEY` | Shared secret for future authenticated endpoints | None (required at startup) |
| `PORT` | HTTP listen port | `8000` |

**Rationale:** Explicit names avoid collisions on the shared server. Base path defaults differ by deployment context: local `./data/silverman-blog-linkedin`, container `/data/silverman-blog-linkedin` (set in compose, not hard-coded as the only default).

**Behavior:**

- Resolve `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` to an absolute path after load.
- Fail fast at startup if `SILVERMAN_BLOG_LINKEDIN_API_KEY` is missing or empty.
- `PORT` used by uvicorn entrypoint and documented in README/compose.

### 4. Expected editorial folders

**Decision:** Validate the following paths relative to the configured base (all MUST exist as directories for "ready" status):

```
blog-posts/ready
blog-posts/processed
blog-posts/error
linkedin-posts/review
linkedin-posts/approved
linkedin-posts/published
metadata/runs
metadata/campaigns
metadata/backups
prompts
```

**Rationale:** Matches `docs/context/worker-architecture.md` and phase-1 flow. Validation is read-only: check existence and directory type; do not create, delete, or move files in this change.

**Health semantics:**

- Each folder reported individually (`exists`, `is_directory`, optional `readable`/`writable` checks as appropriate).
- Aggregate `folders_ready` boolean: true only when base path exists and all expected folders pass validation.
- Overall service `status`: `healthy` when folders are ready; `degraded` when the service is running but editorial layout is incomplete; avoid `503` for `/health` unless the process itself cannot respond (prefer `200` with structured degraded status so n8n can branch on JSON fields).

### 5. GET /health contract

**Decision:** Single unauthenticated endpoint returning JSON:

```json
{
  "status": "healthy",
  "service": "silverman-blog-linkedin-worker",
  "version": "0.1.0",
  "base_path": "/data/silverman-blog-linkedin",
  "folders_ready": true,
  "folders": {
    "blog-posts/ready": { "exists": true, "is_directory": true },
    "...": { "...": "..." }
  }
}
```

**Must NOT:** expose `SILVERMAN_BLOG_LINKEDIN_API_KEY` or other secrets; mutate files; call OpenAI; depend on n8n.

**Rationale:** Structured JSON supports n8n IF nodes on `status`, `folders_ready`, or per-folder fields. Version/service identifier aids ops and future deployment tracking.

### 6. Docker packaging

**Decision:**

- **Dockerfile:** Multi-stage or slim Python image; install dependencies from `pyproject.toml`; run uvicorn on `PORT`; default `SILVERMAN_BLOG_LINKEDIN_BASE_PATH=/data/silverman-blog-linkedin` in compose example (not necessarily Dockerfile ENV if compose sets it).
- **docker-compose.example.yml:** Service definition with port mapping, env vars, volume mount for editorial data (`host path → /data/silverman-blog-linkedin`), healthcheck calling `GET /health`.

**Rationale:** ADR-0003 requires container deployment on Linux server with mounted shared folder. Example compose documents server layout without modifying production stack in this change.

### 7. Security

**Decision:**

- Never include API key values in HTTP responses or error messages.
- Log API key presence at startup (e.g., "configured: yes") but never log the value.
- Path validation responses include configured base path and expected relative paths only—no broad directory listings.

**Future:** Authenticated endpoints in later changes may require `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>` or a dedicated header; not enforced on `/health`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Missing editorial folders on first deploy causes `degraded` health | README documents required folder layout; `/health` JSON lists which paths are missing |
| Local vs container base path confusion | Document defaults in README; compose example sets container path explicitly |
| Requiring API key at startup though unused on `/health` | Ensures production misconfiguration is caught early; document dummy value for local-only health testing if needed |
| Shared folder permissions on server | Path validation reports readability/writability where checked; ops fixes mount permissions outside worker |

## Migration Plan

1. Implement and test locally with `./data/silverman-blog-linkedin` mirror of editorial layout.
2. Build Docker image locally; run via `docker-compose.example.yml` with volume mount.
3. On server (future apply/deploy step): build/push image, run container with mount `/home/silverman/compartido_mac/silverman-blog-linkedin:/data/silverman-blog-linkedin`, configure env vars, verify `GET /health` from n8n network.
4. Rollback: stop container, revert to previous image tag; no data migration in this change.

## Open Questions

- None blocking foundation implementation. Optional follow-up: whether a later change should auto-create missing editorial folders or remain validate-only (current decision: validate-only).
