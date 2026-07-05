# Worker Architecture

## System Pattern

```
┌─────────┐     HTTP      ┌──────────────────┐     file I/O     ┌─────────────────┐
│   n8n   │ ────────────► │  HTTP worker     │ ───────────────► │  Editorial dirs │
│ (orch.) │               │  (this repo)     │                  │  blog, linkedin │
└─────────┘               └──────────────────┘                  │  metadata       │
                                                                  └─────────────────┘
```

- **n8n** orchestrates: scheduling, triggers, HTTP calls, future workflow branching.
- **Worker** owns: folder validation, reading Markdown blog posts, content generation, writing LinkedIn drafts, metadata persistence, and moving source files to `processed/` or `error/`.

The worker should be small, explicit, and operationally safe. It does not replace n8n; it executes the bounded processing steps n8n requests.

## Expected Endpoints

| Method | Path | Purpose | Phase |
|--------|------|---------|-------|
| GET | `/health` | Liveness/readiness for n8n and ops checks | Foundation |
| POST | `/process-ready` | Process all Markdown files in `blog-posts/ready/` | Process-ready |
| POST | `/process-file` | Process a single named file in `blog-posts/ready/` | Process-file |

Endpoint implementation follows approved OpenSpec changes; do not add endpoints outside that workflow.

## Environment Variables

The worker should be configurable through environment variables (exact names to be defined in the foundation change). Expected categories:

| Category | Examples |
|----------|----------|
| Base paths | Root data directory (container: `/data/silverman-blog-linkedin`) |
| OpenAI / LLM | API key, model, timeout |
| Processing | Batch limits, retry behavior |
| Logging | Log level, structured output |

The worker must **not** expose secrets in HTTP responses or logs at info level.

## Folder Contracts

Expected editorial layout under the configured root:

```
blog-posts/
  ready/        ← input: Markdown blog posts (manual placement)
  processed/    ← success: moved after successful processing
  error/        ← failure: moved when processing fails

linkedin-posts/
  review/       ← output: generated drafts awaiting human review
  approved/     ← human-approved drafts
  published/    ← published drafts (future tracking)

metadata/
  runs/         ← per-run processing metadata
  campaigns/    ← campaign-level metadata
  backups/      ← reserved for future use

prompts/        ← prompt templates for content generation
```

## Path Validation

Before processing, the worker must:

1. Verify the configured root path exists and is readable/writable as required.
2. Verify expected subdirectories exist (or create them only if an OpenSpec change explicitly allows auto-creation).
3. Reject or fail safely when paths are misconfigured rather than writing to unexpected locations.

Path validation failures should return clear HTTP error responses without leaking internal secrets or full filesystem maps.

## Error Handling Expectations

| Scenario | Expected behavior |
|----------|-------------------|
| Single file parse/generation failure | Move file to `blog-posts/error/`, record error in run metadata, continue batch if applicable |
| Missing folders | Fail fast with descriptive HTTP response; do not partial-write |
| LLM/API failure | Retry policy as defined in spec; on exhaustion, move source to `error/` |
| Invalid request body | 4xx with validation message |

Responses should be structured JSON suitable for n8n branching (success flag, counts, file names, error summaries).

## Metadata Expectations

Each processing run should write metadata to `metadata/runs/` including at minimum:

- Run identifier and timestamp
- Trigger source (e.g., `/process-ready`, `/process-file`)
- Input files processed
- Output files generated
- Success/failure per file
- Error messages where applicable

Campaign metadata in `metadata/campaigns/` links blog posts, generated LinkedIn variants, and optional campaign labels for future analytics and publishing workflows.
