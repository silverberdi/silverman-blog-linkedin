# silverman-blog-linkedin worker

Local HTTP worker for the **silverman-blog-linkedin** content automation system. n8n orchestrates workflows; this service performs bounded file processing and health checks over HTTP (see ADR-0001).

Current capabilities: configuration, editorial folder validation, `GET /health`, authenticated `POST /process-ready` (read-only scan of Markdown candidates in `blog-posts/ready/`), and authenticated `POST /process-file` (read one Markdown blog post by `relative_path`).

## Requirements

- Python 3.11+
- Editorial data directory with the expected folder layout (see below)

## Environment variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` | No | `./data/silverman-blog-linkedin` | Root path for editorial data |
| `SILVERMAN_BLOG_LINKEDIN_API_KEY` | **Yes** | None | Shared secret for authenticated endpoints (`POST /process-ready`, `POST /process-file`) |
| `PORT` | No | `8000` | HTTP listen port |

The worker **fails fast at startup** if `SILVERMAN_BLOG_LINKEDIN_API_KEY` is missing or empty. The API key is never included in HTTP responses or error messages.

### Local vs container base path

- **Local development (Mac):** default `./data/silverman-blog-linkedin` relative to the working directory.
- **Docker / Linux server:** set `SILVERMAN_BLOG_LINKEDIN_BASE_PATH=/data/silverman-blog-linkedin` and mount host editorial data at that path (see `docker-compose.example.yml`).

## Expected editorial folder layout

All paths are relative to the configured base path:

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

Create this layout under your base path before expecting `healthy` status from `/health`.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

export SILVERMAN_BLOG_LINKEDIN_API_KEY="your-local-dev-key"

# Optional: create sample editorial tree for a healthy health check
mkdir -p data/silverman-blog-linkedin/{blog-posts/{ready,processed,error},linkedin-posts/{review,approved,published},metadata/{runs,campaigns,backups},prompts}

python -m silverman_blog_linkedin.main
```

Or with uvicorn directly:

```bash
uvicorn silverman_blog_linkedin.main:create_app --host 0.0.0.0 --port 8000 --factory
```

## Tests

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

## Docker

Build and run with the example compose file (set `SILVERMAN_BLOG_LINKEDIN_API_KEY` in your environment first):

```bash
export SILVERMAN_BLOG_LINKEDIN_API_KEY="your-key"
docker compose -f docker-compose.example.yml up --build
```

The example mounts `./data/silverman-blog-linkedin` into `/data/silverman-blog-linkedin` inside the container. Write access to `metadata/runs/` is required for `POST /process-ready` and `POST /process-file` (the example mount is read-write).

Quick check (host-side JSON formatting):

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

## GET /health

Unauthenticated liveness/readiness endpoint. Returns `200` with structured JSON for n8n branching. Does not mutate files, call OpenAI, or depend on n8n.

**Example (healthy):**

```json
{
  "status": "healthy",
  "service": "silverman-blog-linkedin-worker",
  "version": "0.1.0",
  "base_path": "/Users/you/project/data/silverman-blog-linkedin",
  "folders_ready": true,
  "folders": {
    "blog-posts/ready": { "exists": true, "is_directory": true },
    "blog-posts/processed": { "exists": true, "is_directory": true },
    "blog-posts/error": { "exists": true, "is_directory": true },
    "linkedin-posts/review": { "exists": true, "is_directory": true },
    "linkedin-posts/approved": { "exists": true, "is_directory": true },
    "linkedin-posts/published": { "exists": true, "is_directory": true },
    "metadata/runs": { "exists": true, "is_directory": true },
    "metadata/campaigns": { "exists": true, "is_directory": true },
    "metadata/backups": { "exists": true, "is_directory": true },
    "prompts": { "exists": true, "is_directory": true }
  }
}
```

When one or more folders are missing, `status` is `degraded` and `folders_ready` is `false`. Per-folder entries show `exists` and `is_directory` for each expected path.

Quick check:

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

## POST /process-ready

Authenticated endpoint that scans `blog-posts/ready/` for Markdown candidates, validates basic file properties, writes run metadata to `metadata/runs/` when writable, and returns structured JSON for n8n branching. Does not generate LinkedIn drafts, call OpenAI, or move source files.

**Authentication:** `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>`

**Request:** empty body (no required JSON). The worker does not accept arbitrary paths from the request.

**Example (successful scan):**

```bash
curl -s -X POST http://localhost:8000/process-ready \
  -H "Authorization: Bearer your-local-dev-key" | python3 -m json.tool
```

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "status": "completed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260704T223045Z-a1b2.json",
  "folders_ready": true,
  "candidate_count": 1,
  "valid_count": 1,
  "invalid_count": 0,
  "ignored_count": 0,
  "valid_files": [
    {
      "filename": "my-post.md",
      "relative_path": "blog-posts/ready/my-post.md",
      "size_bytes": 42
    }
  ],
  "invalid_files": [],
  "ignored_files": [],
  "errors": []
}
```

When `metadata/runs/` is missing or not writable, the response has `status: "failed"`, `metadata_written: false`, `metadata_path: null`, and an error code such as `metadata_runs_not_ready` or `metadata_runs_not_writable`. When other editorial folders are missing but `metadata/runs/` is writable, the worker writes failed run metadata and returns `errors: ["editorial_folders_not_ready"]`.

**n8n integration:** use an HTTP Request node with method `POST`, URL `{worker_base_url}/process-ready`, and header `Authorization: Bearer {{api_key}}`. Branch on `status`, `metadata_written`, `valid_count`, and `errors`. Pass each `relative_path` from `valid_files` to `POST /process-file` for single-file reads.

## POST /process-file

Authenticated endpoint that reads one Markdown blog post from `blog-posts/ready/` by `relative_path`, writes run metadata to `metadata/runs/` when writable (file summary only—no raw content), and returns structured JSON including `markdown_content` for n8n branching. Does not generate LinkedIn drafts, call OpenAI, or move source files.

**Authentication:** `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>`

**Request body:**

```json
{ "relative_path": "blog-posts/ready/my-post.md" }
```

Missing body, missing `relative_path`, non-string `relative_path`, or empty `relative_path` returns HTTP `422` (FastAPI validation; the process-file response contract does not apply).

**Example (successful read):**

```bash
curl -s -X POST http://localhost:8000/process-file \
  -H "Authorization: Bearer your-local-dev-key" \
  -H "Content-Type: application/json" \
  -d '{"relative_path":"blog-posts/ready/my-post.md"}' | python3 -m json.tool
```

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "status": "completed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260704T223045Z-a1b2.json",
  "folders_ready": true,
  "relative_path": "blog-posts/ready/my-post.md",
  "filename": "my-post.md",
  "size_bytes": 42,
  "content_sha256": "a1b2c3...",
  "markdown_content": "# Title\n\nBody text.",
  "errors": []
}
```

**Example (path validation failure):**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "status": "failed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260704T223045Z-a1b2.json",
  "folders_ready": true,
  "relative_path": "blog-posts/processed/post.md",
  "filename": "post.md",
  "size_bytes": null,
  "content_sha256": null,
  "markdown_content": null,
  "errors": ["path_outside_ready"]
}
```

When `metadata/runs/` is missing or not writable, the response has `status: "failed"`, `metadata_written: false`, `metadata_path: null`, null file summary fields, and an error code such as `metadata_runs_not_ready` or `metadata_runs_not_writable`. When editorial folders are missing but `metadata/runs/` is writable, the worker writes failed run metadata and returns null `size_bytes`, `content_sha256`, and `markdown_content` with `errors: ["editorial_folders_not_ready"]`.

Run metadata never includes `markdown_content`. The HTTP response includes `markdown_content` only on successful UTF-8 reads.

**n8n integration:** after `POST /process-ready`, use an HTTP Request node with method `POST`, URL `{worker_base_url}/process-file`, header `Authorization: Bearer {{api_key}}`, and JSON body `{ "relative_path": "{{ $json.valid_files[0].relative_path }}" }`. Branch on `status`, `markdown_content`, and `errors`.

## Project context

- Architecture and phasing: `docs/context/`
- ADRs: `docs/decisions/`
- OpenSpec changes: `openspec/changes/`
