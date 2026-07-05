# ADR-0003: Develop Locally on Mac, Deploy as Docker Container on Linux Server

## Status

Accepted

## Context

The project owner develops with Cursor and OpenSpec on a Mac. n8n and production editorial files live on a Linux server (`192.168.0.194`). Editorial data is shared via `/home/silverman/compartido_mac/silverman-blog-linkedin` (Mac: `Compartido_Mac`).

The worker must support local development (fast iteration, debugging) and server deployment (stable service for n8n to call).

## Decision

- **Develop locally on Mac** — application code, OpenSpec changes, and tests run in the local repository.
- **Deploy as a Docker container on the Linux server** — production worker runs in Docker with the editorial tree mounted at `/data/silverman-blog-linkedin`.
- **Do not develop directly on the server** — the server receives deployed artifacts, not day-to-day editing.

## Rationale

| Concern | Local Mac dev | Server-only dev |
|---------|---------------|-----------------|
| Cursor / OpenSpec | Native workflow | Awkward or unavailable |
| Iteration speed | Fast | Slower, remote |
| Risk to n8n host | Isolated | Higher |
| Parity | Docker reproduces server mount layout | N/A |

Environment variables configure paths so the same codebase uses a local data root during development and `/data/silverman-blog-linkedin` in the container.

## Consequences

### Positive

- Git remains source of truth for worker code
- Docker image provides repeatable deployment
- Shared folder allows placing blog posts from Mac while worker on server processes them

### Negative

- Must maintain Docker build/publish steps (future OpenSpec change)
- Local integration testing may require pointing at shared folder or a local mirror

### Neutral

- n8n stays on server; worker URL in workflows must reflect where the container listens
- Dockerfile and compose are not created during phase 0 bootstrap

## Related Documents

- `docs/context/deployment-context.md`
- `docs/context/worker-architecture.md`
