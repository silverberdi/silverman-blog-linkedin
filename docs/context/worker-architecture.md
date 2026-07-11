# Worker Architecture

Canonical status: [CURRENT-STATE.md](../CURRENT-STATE.md). Terminology: [GLOSSARY.md](../GLOSSARY.md). Specs: `openspec/specs/`.

## System Pattern

```
┌─────────┐     HTTP      ┌──────────────────┐     file I/O     ┌─────────────────┐
│   n8n   │ ────────────► │  HTTP worker     │ ───────────────► │  Editorial dirs │
│ (orch.) │               │  (this repo)     │                  │  + /public-blog │
└─────────┘               └──────────────────┘                  │  metadata       │
                                                                  └─────────────────┘
```

- **n8n** orchestrates: scheduling, triggers, HTTP calls, workflow branching.
- **Worker** owns: folder validation, Flow A pipeline, draft generation, metadata, lifecycle moves, public checkout handoff.

The worker does not replace n8n; it executes bounded processing steps n8n requests over HTTP only (ADR-0001).

## Endpoints (current)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness/readiness |
| POST | `/process-ready` | Scan `blog-posts/ready/` (read-only inventory) |
| POST | `/process-file` | Read one ready Markdown file |
| POST | `/write-linkedin-draft` | Persist client-supplied draft |
| POST | `/generate-linkedin-draft` | DeepSeek single-variant generation |
| POST | `/publish-blog-post` | Flow A blog handoff to public checkout |
| POST | `/generate-linkedin-package` | Flow A multi-variant package |
| POST | `/schedule-linkedin-distribution` | Flow A stagger scheduling |
| POST | `/queue-linkedin-publication` | Authorize variant for publish window |
| POST | `/publish-linkedin-due-variants` | Guarded LinkedIn API publish |
| POST | `/cancel-linkedin-publication` | Cancel queued variant |
| POST | `/editorial-calendar/plan-due` | Calendar planning |
| GET | `/editorial-calendar/status` | Calendar status |
| POST | `/editorial-calendar/execute-flow-a-due` | Flow A calendar connector |
| GET | `/linkedin/oauth/*` | OAuth helper endpoints |

New endpoints require an approved OpenSpec change. Full contracts: `openspec/specs/`.

## Flow A scope

Queue acceptance (`ready` → `queued`), publish, package, schedule, lifecycle (`flow_a_complete`), reconciliation, and idempotency. See [flow-a-target-flow.md](../workflows/flow-a-target-flow.md).

## Environment Variables

| Category | Examples |
|----------|----------|
| Base paths | `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`, `SILVERMAN_GITHUB_PAGES_REPO_PATH` |
| Auth | `SILVERMAN_BLOG_LINKEDIN_API_KEY` |
| LLM | `DEEPSEEK_*` (not OpenAI) |
| ComfyUI | `SILVERMAN_COMFYUI_*` |
| LinkedIn publication | `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, token/URN |
| Flow A stale detection | `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` |
| Build | `BUILD_REVISION` at image build time |

The worker must **not** expose secrets in HTTP responses or info-level logs.

## Folder Contracts

```
blog-posts/{ready,queued,processed,error}/
linkedin-posts/{review,approved,published,generated}/
metadata/{runs,campaigns,backups}/
prompts/
editorial-calendar/
```

## Path Validation

Verify configured root and expected subdirectories before processing. Fail safely with structured JSON errors — no secret leakage.

## Error Handling

| Scenario | Expected behavior |
|----------|-------------------|
| Single file failure (Flow B path) | Metadata + structured errors; Flow A uses `error/` + campaign state |
| Missing folders | Degraded `/health` or failed run with clear codes |
| LLM/API failure | Structured error codes; no secret in response |
| Invalid request | HTTP 422 with validation detail |

## Metadata

`metadata/runs/` per HTTP call; `metadata/campaigns/` is traceability authority for Flow A lifecycle.
