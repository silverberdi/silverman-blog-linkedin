## Why

The `silverman-blog-linkedin` system needs a bounded HTTP worker that n8n can call safely instead of running arbitrary shell commands on the server (ADR-0001). Before any blog processing or content generation can begin, the worker must exist as a deployable service with configuration, editorial folder validation, and a health endpoint that n8n and operators can use for liveness and readiness checks.

This is the first OpenSpec change and the first implementation phase in the backlog. It establishes the service skeleton so later changes can add `POST /process-ready` and `POST /process-file` without re-deciding infrastructure fundamentals.

## Goals

- Define and implement the worker service foundation: Python + FastAPI, environment-based configuration, editorial base-path validation, and `GET /health`.
- Provide Dockerfile, docker-compose example, and README so the service can run locally on Mac and deploy as a container on the Linux server (ADR-0003).
- Return structured JSON from `/health` suitable for n8n branching, without exposing secrets or performing processing side effects.

## Non-Goals

- `POST /process-ready` or `POST /process-file` endpoints.
- OpenAI integration or LinkedIn content generation.
- Publishing to LinkedIn or GitHub.
- Actual n8n workflow integration.
- Dairector content paths or processing.
- Markdown blog post reading or file moves between `ready` / `processed` / `error`.
- n8n Execute Command.
- Modifying the production server stack beyond documented deployment artifacts.

## What Changes

- Add a new Python + FastAPI HTTP worker service skeleton in this repository.
- Add environment-variable configuration for `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`, `SILVERMAN_BLOG_LINKEDIN_API_KEY`, and `PORT`.
- Add validation logic for the expected editorial folder layout under the configured base path.
- Add `GET /health` returning structured JSON with service status, project name, configured base path, and per-folder readiness—without exposing API keys or mutating files.
- Add Dockerfile and docker-compose example for local and server deployment.
- Add README with setup, configuration, and health-check usage.
- Add tests for configuration loading, path validation, and the health endpoint.

## Why a Dedicated HTTP Worker (Not n8n Execute Command)

n8n Execute Command runs arbitrary shell on the server host, which increases attack surface, mixes orchestration with implementation, and makes behavior hard to test and version in git. A dedicated HTTP worker provides an explicit, bounded API surface (`GET /health` first, processing endpoints later), keeps secrets in environment configuration, and can be developed locally and deployed as a Docker container while n8n orchestrates via HTTP Request nodes only.

## Capabilities

### New Capabilities

- `worker-foundation`: HTTP worker service foundation—configuration via environment variables, editorial base-path and folder validation, `GET /health`, Docker packaging, and foundational tests.

### Modified Capabilities

<!-- No existing specs in openspec/specs/ yet -->

## Impact

- **Repository**: First application code (Python/FastAPI), tests, Dockerfile, docker-compose example, and README.
- **Dependencies**: Python runtime, FastAPI, uvicorn (or equivalent ASGI server), pytest (or equivalent test runner).
- **Deployment**: Container image built from Dockerfile; editorial data mounted at `/data/silverman-blog-linkedin` on server or `./data/silverman-blog-linkedin` locally.
- **n8n**: No workflow changes in this change; future n8n integration will call `GET /health` over HTTP Request nodes.
- **Editorial folders**: Worker validates existence/readiness of expected paths under the configured base; does not auto-create folders in this change unless design specifies otherwise.
