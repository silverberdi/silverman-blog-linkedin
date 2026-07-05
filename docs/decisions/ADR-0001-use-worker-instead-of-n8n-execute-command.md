# ADR-0001: Use Worker Service Instead of n8n Execute Command

## Status

Accepted

## Context

The `silverman-blog-linkedin` system runs n8n on a Linux server for workflow orchestration. Processing requires reading Markdown blog posts from shared folders, generating LinkedIn drafts via an LLM, writing metadata, and moving files between editorial directories.

n8n can invoke arbitrary shell commands through the Execute Command node. That would allow scripts to perform file I/O and call external APIs directly from workflows.

## Decision

Use a dedicated **HTTP worker service** (this repository) for file processing and content generation. n8n will call the worker via HTTP Request nodes only. **Do not enable n8n Execute Command** for this system.

## Rationale

| Factor | Execute Command | HTTP worker |
|--------|-----------------|-------------|
| Operational risk | High — arbitrary shell on server | Lower — bounded API surface |
| Testability | Hard to unit test from workflows | Worker testable locally and in CI |
| Versioning | Scripts scattered in n8n or filesystem | Code and specs in git repository |
| Security | Broad host access | Explicit endpoints and env config |
| Separation of concerns | Orchestration and execution mixed | n8n orchestrates; worker executes |

## Consequences

### Positive

- Clear contract between n8n and processing logic (HTTP + JSON)
- Worker can be developed on Mac and deployed as Docker on server
- Easier to audit what processing steps exist (OpenAPI/endpoints vs shell snippets)

### Negative

- Additional service to deploy and monitor
- Network path required between n8n and worker (same host/Docker network)

### Neutral

- n8n workflows remain the place for scheduling, branching, and notifications
- Future endpoints (`/health`, `/process-ready`, `/process-file`) must be implemented through OpenSpec changes

## Related Documents

- `docs/context/n8n-integration-context.md`
- `docs/context/worker-architecture.md`
- ADR-0003 (local dev, container deploy)
