## Why

`POST /process-ready` discovers and validates Markdown candidates in `blog-posts/ready/` but does not read file content. n8n workflows need a bounded next step: given a `relative_path` from a prior scan, read one specific blog post and return structured JSON (including raw Markdown) for downstream branching—without OpenAI, LinkedIn generation, or mutating source files. This change defines `POST /process-file` as that read-only single-file reader, completing the third endpoint in the phased worker sequence before n8n integration workflows.

## Goals

- Define and implement `POST /process-file` with API key authentication using `SILVERMAN_BLOG_LINKEDIN_API_KEY` (Bearer token, same as `POST /process-ready`).
- Accept a JSON request body with `relative_path` pointing to a file under `blog-posts/ready/`.
- Validate request body shape, editorial folder layout, and `metadata/runs/` readiness before reading.
- Validate the target path: relative only, confined to `blog-posts/ready/`, `.md` extension, regular readable non-empty file.
- Read Markdown content as UTF-8 and return a normalized blog post payload suitable for n8n branching, with explicit nullability rules for file summary fields on failure.
- Write run metadata under `metadata/runs/` when writable; exclude full Markdown content from metadata always; store file summary fields (`relative_path`, `filename`, `size_bytes`, `content_sha256`) with JSON `null` where values are unavailable.
- Keep `GET /health` and `POST /process-ready` behavior unchanged at the spec level.

## Non-Goals

- OpenAI integration or prompt selection.
- LinkedIn draft generation or writing to `linkedin-posts/review/`.
- Moving source files to `blog-posts/processed/` or `blog-posts/error/`.
- Modifying source blog post files.
- Campaign metadata, Dairector content, scheduling.
- n8n workflow JSON creation.
- GitHub or LinkedIn publishing.
- Full Markdown/front-matter semantic parsing.
- n8n Execute Command.

## What Changes

- Add `POST /process-file` authenticated endpoint to the FastAPI worker.
- Add request body validation for `{ "relative_path": "blog-posts/ready/<filename>.md" }`.
- Add path validation module logic: reject absolute paths, path traversal, paths outside `blog-posts/ready/`, non-`.md` files, missing files, directories, unreadable files, and empty files.
- Add blog post file reader that reads UTF-8 Markdown and computes `content_sha256`.
- Extend run metadata writer for `POST /process-file` runs (file summary only—no raw content in metadata; nulls for unavailable summary fields on failed runs).
- Define and return structured HTTP JSON with `run_id`, `status`, `metadata_written`, `metadata_path`, `relative_path`, `filename`, `size_bytes`, `content_sha256`, `markdown_content`, and `errors`, including consistent nullability: normalized `relative_path` always present after valid body; `filename`, `size_bytes`, `content_sha256`, and `markdown_content` null unless their respective preconditions are met.
- Add tests for authentication, request validation, path confinement, file reading, metadata creation, response shape, and null field behavior on folder failure, metadata/runs unavailable, invalid path, missing file, empty file, and invalid UTF-8.
- Update README with `POST /process-file` usage, request/response examples, and n8n integration notes.

## Why a Dedicated HTTP Worker (Not n8n Execute Command)

n8n Execute Command runs arbitrary shell on the server host, which increases attack surface and mixes orchestration with file I/O. A dedicated HTTP worker exposes a bounded, testable API: n8n calls `POST /process-file` via HTTP Request nodes with a `relative_path` from a prior `POST /process-ready` response, receives JSON including Markdown content for branching, and never needs direct filesystem access on the host. Path validation, content reading, and metadata writes live in version-controlled Python code—not ad hoc scripts in workflows.

## Capabilities

### New Capabilities

- `blog-post-file-processing`: Authenticated `POST /process-file` endpoint that validates editorial layout and request path, reads one Markdown blog post from `blog-posts/ready/`, writes run metadata to `metadata/runs/` when writable (file summary only), and returns structured JSON including raw Markdown content for n8n—read-only with respect to blog source files.

### Modified Capabilities

- `ready-blog-post-processing`: Extend API key authentication requirement to cover `POST /process-file` in addition to `POST /process-ready` (shared auth pattern for processing endpoints).

## Impact

- **Repository**: New route, file reader module, path validation for request-supplied paths, extended run metadata helpers, and tests under `src/silverman_blog_linkedin/` and `tests/`.
- **APIs**: New `POST /process-file` (authenticated); `GET /health` and `POST /process-ready` unchanged.
- **Editorial data**: Writes run metadata JSON to `metadata/runs/` when writable; does not move or modify blog posts in `ready/`, `processed/`, or `error/`.
- **n8n**: Workflows can call the new endpoint after `POST /process-ready` to read a specific file; no workflow JSON in this change.
- **Security**: API key required; path traversal prevention; secrets and submitted tokens never appear in responses, logs, or metadata.
- **Dependencies**: No new external services (no OpenAI client in this change).
