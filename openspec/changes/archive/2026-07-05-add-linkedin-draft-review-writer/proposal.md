## Why

`POST /process-file` reads a blog post and returns Markdown for n8n branching, but no worker endpoint yet persists LinkedIn draft content into the editorial pipeline. n8n (or an external LLM step) needs a bounded, authenticated way to write one review draft under `linkedin-posts/review/` with run metadata—without calling AI providers, moving source blog files, or publishing anywhere. This change defines `POST /write-linkedin-draft` as that persistence gate, intentionally before DeepSeek/OpenAI generation so the write path is stable and testable first.

## Goals

- Define and implement `POST /write-linkedin-draft` with API key authentication using `SILVERMAN_BLOG_LINKEDIN_API_KEY` (Bearer token, same pattern as other processing endpoints).
- Accept a JSON body with `source_relative_path`, non-empty `draft_content`, and optional `source_content_sha256`, `title`, or slug hint.
- Validate request body shape and `source_relative_path` confinement to `blog-posts/ready/` (shape only—do not re-read the source blog file).
- Validate `linkedin-posts/review/` and `metadata/runs/` readiness before writing.
- Write one draft Markdown file under `linkedin-posts/review/` with a safe deterministic filename using exclusive (no-overwrite) creation; reject extra request body fields (for example `draft_relative_path`, `output_path`, `filename`, `target_path`) with HTTP `422`.
- Write run metadata under `metadata/runs/` when writable; exclude full `draft_content` and secrets from metadata.
- Return structured JSON suitable for n8n branching (`run_id`, `status`, draft/metadata paths, hashes, errors).
- Keep `GET /health`, `POST /process-ready`, and `POST /process-file` behavior unchanged at the spec level.

## Non-Goals

- DeepSeek, OpenAI, ChatGPT, local LLM, or any AI provider integration.
- LinkedIn content generation or prompt selection.
- Publishing to LinkedIn or GitHub.
- Moving or modifying source blog files under `blog-posts/`.
- Re-reading source blog post content (unless strongly justified—out of scope).
- Campaign metadata, Dairector content, scheduling.
- n8n workflow JSON creation.
- n8n Execute Command.

## What Changes

- Add `POST /write-linkedin-draft` authenticated endpoint to the FastAPI worker.
- Add strict request body validation for `source_relative_path`, `draft_content`, and optional fields; reject extra fields via Pydantic `extra="forbid"` (HTTP `422`, endpoint contract does not apply).
- Add source path shape validation (relative, `blog-posts/ready/` direct child, `.md` extension, no traversal)—without verifying file existence on disk.
- Add `linkedin-posts/review/` directory readiness check (exists, directory, writable).
- Add draft file writer: persist `draft_content` as UTF-8 under `linkedin-posts/review/` using `{timestamp}-{source_stem}.md` with exclusive creation and collision retries (never overwrite existing drafts).
- Define partial-failure behavior when draft write succeeds but run metadata write fails (`metadata_write_failed`; draft file is retained, not rolled back).
- Extend run metadata writer for write-linkedin-draft runs (paths, hashes, sizes—no full draft body).
- Define structured HTTP JSON response with `run_id`, `status`, `metadata_written`, `metadata_path`, `draft_written`, `draft_relative_path`, `source_relative_path`, `source_content_sha256`, `draft_content_sha256`, `size_bytes`, and `errors`.
- Add tests for authentication, body validation (including extra-field rejection), path validation, exclusive draft writing, collision handling, metadata partial-failure, and failure modes.
- Update README with `POST /write-linkedin-draft` usage and n8n integration notes.

## Why a Dedicated HTTP Worker (Not n8n Execute Command)

n8n Execute Command runs arbitrary shell on the server host, which increases attack surface and mixes orchestration with filesystem writes. A dedicated HTTP worker exposes a bounded, testable API: n8n calls `POST /write-linkedin-draft` via HTTP Request nodes after an external or future LLM step, supplies already-generated draft text, and never needs direct write access to editorial folders on the host. Path validation, filename generation, and metadata writes live in version-controlled Python code—not ad hoc scripts in workflows.

## Capabilities

### New Capabilities

- `linkedin-draft-review-writing`: Authenticated `POST /write-linkedin-draft` endpoint that validates request body and source path shape, checks `linkedin-posts/review/` and `metadata/runs/` readiness, writes one LinkedIn review draft file from client-supplied content, persists run metadata, and returns structured JSON for n8n—without AI calls, publishing, or mutating source blog files.

### Modified Capabilities

- `ready-blog-post-processing`: Extend API key authentication requirement to cover `POST /write-linkedin-draft` in addition to `POST /process-ready` and `POST /process-file` (shared auth pattern for processing endpoints).

## Impact

- **Repository**: New route, draft writer module, source path validation reuse/extension, extended run metadata helpers, and tests under `src/silverman_blog_linkedin/` and `tests/`.
- **APIs**: New `POST /write-linkedin-draft` (authenticated); existing endpoints unchanged.
- **Editorial data**: Writes draft Markdown to `linkedin-posts/review/` and run metadata JSON to `metadata/runs/` when writable; does not move or modify blog posts in `ready/`, `processed/`, or `error/`.
- **n8n**: Workflows can call the new endpoint after content generation (external or future in-worker) to persist a review draft; no workflow JSON in this change.
- **Security**: API key required; source path shape validation and server-side filename generation prevent traversal and arbitrary writes; secrets and submitted tokens never appear in responses, logs, or metadata.
- **Dependencies**: No new external services (no AI clients in this change).
