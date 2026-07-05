## Why

The worker foundation (`GET /health`, configuration, editorial folder validation) is in place. n8n needs the next bounded HTTP endpoint to trigger a controlled scan of Markdown blog posts placed in `blog-posts/ready/` before any LinkedIn generation or file moves occur. This change delivers `POST /process-ready` as a read-only discovery and validation step: inspect candidates, record run metadata, and return structured JSON for n8n branching—without OpenAI, content generation, or mutating source files.

This is the second phase in the backlog (after foundation) and the first authenticated processing endpoint. It establishes the run-metadata pattern and candidate-validation rules that later changes (`POST /process-file`, OpenAI generation, file moves) will build on.

## Goals

- Define and implement `POST /process-ready` with API key authentication using `SILVERMAN_BLOG_LINKEDIN_API_KEY`.
- Scan `blog-posts/ready/` for Markdown candidates under the configured editorial base path.
- Validate basic candidate file properties (exists, regular file, `.md` extension, readable, non-empty).
- Attempt to create a run metadata JSON file under `metadata/runs/` when that directory exists and is writable; use a deterministic, traceable run identifier.
- Return structured JSON suitable for n8n branching: run id, status, `metadata_written`, `metadata_path`, candidate counts, valid and invalid file lists, and errors.
- Validate expected editorial folders before processing; skip candidate scanning when layout is not ready; return failed responses with `metadata_written: false` when `metadata/runs/` is unavailable or not writable.
- Keep `GET /health` behavior unchanged (unauthenticated, read-only).

## Non-Goals

- `POST /process-file` endpoint.
- OpenAI integration or LinkedIn draft generation.
- Moving files to `blog-posts/processed/` or `blog-posts/error/`.
- Publishing to LinkedIn or GitHub.
- n8n workflow JSON or server stack changes.
- Dairector content paths.
- Full blog post semantic parsing (front matter, title extraction, etc.).
- Scheduling or batch limits beyond listing what is in `ready/`.
- n8n Execute Command.

## What Changes

- Add `POST /process-ready` authenticated endpoint to the FastAPI worker.
- Add API key authentication dependency (Bearer token or equivalent header) using existing `SILVERMAN_BLOG_LINKEDIN_API_KEY`; reject unauthenticated or invalid requests with `401`.
- Add read-only scanning logic for `blog-posts/ready/` limited to `.md` files; report non-Markdown entries as ignored.
- Add per-candidate validation rules: file exists, is a regular file, has `.md` extension, is readable, is not empty.
- Add run metadata writer that persists JSON under `metadata/runs/` when that directory exists and is writable (only metadata write in this change—no source file moves).
- Add structured HTTP response contract including `metadata_written` and `metadata_path` (`null` when metadata is not written) for success, partial validation outcomes, folder-not-ready failures, and metadata-directory-unavailable failures.
- Add tests for authentication, scanning, validation, metadata creation, and response shape.
- Update README with `POST /process-ready` usage, authentication header, and example responses.

## Why a Dedicated HTTP Worker (Not n8n Execute Command)

n8n Execute Command runs arbitrary shell on the server host, which increases attack surface and mixes orchestration with file I/O. A dedicated HTTP worker exposes a bounded, testable API: n8n calls `POST /process-ready` via HTTP Request nodes, receives JSON for branching, and never needs filesystem access or shell execution on the host. Path validation, candidate rules, and metadata writes live in version-controlled Python code—not ad hoc scripts in workflows.

## Capabilities

### New Capabilities

- `ready-blog-post-processing`: Authenticated `POST /process-ready` endpoint that validates editorial layout, scans `blog-posts/ready/` for Markdown candidates when folders are ready, validates basic file properties, writes run metadata to `metadata/runs/` when writable, and returns structured JSON for n8n—read-only with respect to blog source files.

### Modified Capabilities

<!-- GET /health and foundation configuration remain unchanged at the spec level -->

## Impact

- **Repository**: New route, auth dependency, scanning/validation module, run metadata writer, and tests under `src/silverman_blog_linkedin/` and `tests/`.
- **APIs**: New `POST /process-ready` (authenticated); `GET /health` unchanged.
- **Editorial data**: Writes run metadata JSON to `metadata/runs/` when that directory exists and is writable; does not move or modify blog posts in `ready/`, `processed/`, or `error/`.
- **n8n**: Workflows can call the new endpoint once implemented; no workflow JSON in this change.
- **Security**: API key required for processing endpoint; secrets never appear in responses, logs, or metadata.
- **Dependencies**: No new external services (no OpenAI client in this change).
