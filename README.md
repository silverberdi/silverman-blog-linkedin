# silverman-blog-linkedin worker

Local HTTP worker for the **silverman-blog-linkedin** content automation system. n8n orchestrates workflows; this service performs bounded file processing and health checks over HTTP (see ADR-0001).

Current capabilities: configuration, editorial folder validation, `GET /health`, authenticated `POST /process-ready` (read-only scan of Markdown candidates in `blog-posts/ready/`), authenticated `POST /process-file` (read one Markdown blog post by `relative_path`), authenticated `POST /write-linkedin-draft` (persist one LinkedIn review draft from client-supplied content), and authenticated `POST /generate-linkedin-draft` (generate one LinkedIn review draft from blog Markdown via DeepSeek).

## Requirements

- Python 3.11+
- Editorial data directory with the expected folder layout (see below)

## Environment variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` | No | `./data/silverman-blog-linkedin` | Root path for editorial data |
| `SILVERMAN_BLOG_LINKEDIN_API_KEY` | **Yes** | None | Shared secret for authenticated endpoints (`POST /process-ready`, `POST /process-file`, `POST /write-linkedin-draft`, `POST /generate-linkedin-draft`) |
| `PORT` | No | `8000` | HTTP listen port |

The worker **fails fast at startup** if `SILVERMAN_BLOG_LINKEDIN_API_KEY` is missing or empty. The API key is never included in HTTP responses or error messages.

### DeepSeek (optional — required only for `POST /generate-linkedin-draft`)

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DEEPSEEK_API_KEY` | For generate only | — | DeepSeek API key for chat completions |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com` | DeepSeek-compatible API base URL (trailing slash stripped; `/chat/completions` appended; no automatic `/v1`) |
| `DEEPSEEK_MODEL` | No | `deepseek-v4-flash` | Model name for generation |
| `DEEPSEEK_TIMEOUT_SECONDS` | No | `60` | Request timeout (positive number) |
| `DEEPSEEK_MAX_OUTPUT_TOKENS` | No | `1024` | Max output tokens (positive integer) |

The worker starts without `DEEPSEEK_API_KEY`. Other endpoints work normally. Invalid optional DeepSeek settings do not block startup; they cause `POST /generate-linkedin-draft` to return `deepseek_config_invalid`. The DeepSeek API key is never included in HTTP responses, run metadata, or info-level logs.

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

### Local development

Build and run with the example compose file (set `SILVERMAN_BLOG_LINKEDIN_API_KEY` in your environment first):

```bash
export SILVERMAN_BLOG_LINKEDIN_API_KEY="your-key"
docker compose -f docker-compose.example.yml up --build
```

The example mounts `./data/silverman-blog-linkedin` into `/data/silverman-blog-linkedin` inside the container. Write access to `metadata/runs/` and `linkedin-posts/review/` is required for processing endpoints (the example mount is read-write).

Quick check (host-side JSON formatting):

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

### Ubuntu server deployment

For the isolated worker deployment on Ubuntu server `192.168.0.194` (host port `8010`, separate from `local-ai-stack`), see [docs/deployment/ubuntu-server-worker-deployment.md](docs/deployment/ubuntu-server-worker-deployment.md).

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

## POST /write-linkedin-draft

Authenticated endpoint that persists one LinkedIn review draft Markdown file under `linkedin-posts/review/` from client-supplied `draft_content`, writes run metadata to `metadata/runs/` when writable (summary fields only—no full draft body), and returns structured JSON for n8n branching. Does not call AI providers, publish to LinkedIn or GitHub, or move or modify source blog files.

**Authentication:** `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>`

**Request body (allowed fields only):**

```json
{
  "source_relative_path": "blog-posts/ready/my-post.md",
  "draft_content": "LinkedIn draft text here.",
  "source_content_sha256": "abc123...",
  "title": "Optional human title",
  "slug_hint": "executive"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `source_relative_path` | Yes | Non-empty after normalization; shape validated under `blog-posts/ready/` (file is not re-read) |
| `draft_content` | Yes | Non-empty after strip; written as UTF-8 (optional single trailing newline) |
| `source_content_sha256` | No | Echoed in response/metadata when provided |
| `title` | No | Stored in metadata only |
| `slug_hint` | No | Optional variant label; affects generated filename |

The worker rejects extra fields (`draft_relative_path`, `output_path`, `filename`, `target_path`, or any other unexpected field) with HTTP `422`. The client cannot choose the output path; the server generates filenames under `linkedin-posts/review/`.

Missing body, missing required fields, empty `draft_content` after strip, or empty `source_relative_path` returns HTTP `422` (the write-linkedin-draft response contract does not apply).

**Example (successful write):**

```bash
curl -s -X POST http://localhost:8000/write-linkedin-draft \
  -H "Authorization: Bearer your-local-dev-key" \
  -H "Content-Type: application/json" \
  -d '{"source_relative_path":"blog-posts/ready/my-post.md","draft_content":"LinkedIn draft text.","slug_hint":"executive"}' | python3 -m json.tool
```

```json
{
  "run_id": "run-20260705T150045Z-a1b2",
  "status": "completed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260705T150045Z-a1b2.json",
  "draft_written": true,
  "draft_relative_path": "linkedin-posts/review/20260705T150045Z-my-post-executive.md",
  "source_relative_path": "blog-posts/ready/my-post.md",
  "source_content_sha256": null,
  "draft_content_sha256": "def456...",
  "size_bytes": 21,
  "errors": []
}
```

**Example (review directory unavailable):**

```json
{
  "run_id": "run-20260705T150045Z-a1b2",
  "status": "failed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260705T150045Z-a1b2.json",
  "draft_written": false,
  "draft_relative_path": null,
  "source_relative_path": "blog-posts/ready/my-post.md",
  "source_content_sha256": null,
  "draft_content_sha256": null,
  "size_bytes": null,
  "errors": ["review_dir_not_ready"]
}
```

**Example (partial failure—draft written, metadata write failed):**

```json
{
  "run_id": "run-20260705T150045Z-a1b2",
  "status": "failed",
  "metadata_written": false,
  "metadata_path": null,
  "draft_written": true,
  "draft_relative_path": "linkedin-posts/review/20260705T150045Z-my-post-executive.md",
  "source_relative_path": "blog-posts/ready/my-post.md",
  "source_content_sha256": "abc123...",
  "draft_content_sha256": "def456...",
  "size_bytes": 512,
  "errors": ["metadata_write_failed"]
}
```

When `metadata/runs/` is missing or not writable, the response has `status: "failed"`, `metadata_written: false`, `metadata_path: null`, `draft_written: false`, and an error such as `metadata_runs_not_ready` or `metadata_runs_not_writable`—no draft or metadata files are created.

Run metadata never includes `draft_content`. The HTTP response never includes API keys or submitted tokens.

**n8n integration:** after an external or future LLM step produces draft text, use an HTTP Request node with method `POST`, URL `{worker_base_url}/write-linkedin-draft`, header `Authorization: Bearer {{api_key}}`, and JSON body containing `source_relative_path` (from `POST /process-file`) and `draft_content`. Optionally pass `source_content_sha256` from the process-file response for traceability. Branch on `status`, `draft_written`, `metadata_written`, and `errors`.

## POST /generate-linkedin-draft

Authenticated endpoint that generates one LinkedIn review draft from supplied blog Markdown using the DeepSeek chat completions API, persists the draft under `linkedin-posts/review/`, writes run metadata to `metadata/runs/` when writable (summary fields only—no markdown body or generated text), and returns structured JSON for n8n branching. Does not publish to LinkedIn or GitHub, or move or modify source blog files.

**Authentication:** `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>`

**DeepSeek:** requires `DEEPSEEK_API_KEY` at request time (worker starts without it). Configure optional `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, `DEEPSEEK_TIMEOUT_SECONDS`, and `DEEPSEEK_MAX_OUTPUT_TOKENS` as needed.

**Request body (allowed fields only):**

```json
{
  "source_relative_path": "blog-posts/ready/my-post.md",
  "markdown_content": "# Title\n\nBlog body from POST /process-file.",
  "source_content_sha256": "abc123...",
  "title": "Optional human title",
  "slug_hint": "executive",
  "tone": "professional",
  "audience": "senior architects",
  "variant": "technical-leadership",
  "source_public_url": "https://silverman.pro/2026/07/06/my-post/",
  "topic_theme": "architecture"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `source_relative_path` | Yes | Non-empty after normalization; shape validated under `blog-posts/ready/` (file is not re-read) |
| `markdown_content` | Yes | Non-empty after strip; typically from `POST /process-file` response |
| `source_content_sha256` | No | Echoed unchanged when provided; otherwise computed as lowercase SHA-256 of UTF-8 `markdown_content` |
| `title` | No | Prompt hint and metadata |
| `slug_hint` | No | Filename segment; when absent, `variant` may be used as slug segment |
| `tone` | No | Prompt hint and metadata |
| `audience` | No | Prompt hint and metadata |
| `variant` | No | Prompt hint and metadata |
| `source_public_url` | No | Public blog article URL (`http` or `https` only); when provided, the generated draft includes it once as a natural end CTA |
| `topic_theme` | No | Editorial hint; with `source_public_url`, may influence CTA wording (e.g. "Read the full {topic_theme} story here") |

The worker rejects extra fields (including `cta_style`) with HTTP `422`. The client cannot choose the output path.

**Example (successful generation):**

```bash
curl -s -X POST http://localhost:8000/generate-linkedin-draft \
  -H "Authorization: Bearer your-local-dev-key" \
  -H "Content-Type: application/json" \
  -d '{"source_relative_path":"blog-posts/ready/my-post.md","markdown_content":"# Architecture\n\nSenior insight.","slug_hint":"executive"}' | python3 -m json.tool
```

```json
{
  "run_id": "run-20260705T160045Z-a1b2",
  "status": "completed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260705T160045Z-a1b2.json",
  "draft_written": true,
  "draft_relative_path": "linkedin-posts/review/20260705T160045Z-my-post-executive.md",
  "source_relative_path": "blog-posts/ready/my-post.md",
  "source_content_sha256": "a1b2c3...",
  "draft_content_sha256": "def456...",
  "size_bytes": 128,
  "provider": "deepseek",
  "model": "deepseek-v4-flash",
  "generated_draft_content": "LinkedIn draft text for human review.",
  "source_public_url": "https://silverman.pro/2026/07/06/my-post/",
  "topic_theme": "architecture",
  "errors": []
}
```

**Example (DeepSeek API key missing):**

```json
{
  "run_id": "run-20260705T160045Z-a1b2",
  "status": "failed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260705T160045Z-a1b2.json",
  "draft_written": false,
  "draft_relative_path": null,
  "source_relative_path": "blog-posts/ready/my-post.md",
  "source_content_sha256": "a1b2c3...",
  "draft_content_sha256": null,
  "size_bytes": null,
  "provider": "deepseek",
  "model": "deepseek-v4-flash",
  "errors": ["deepseek_api_key_missing"]
}
```

**Example (DeepSeek failure):**

```json
{
  "run_id": "run-20260705T160045Z-a1b2",
  "status": "failed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260705T160045Z-a1b2.json",
  "draft_written": false,
  "draft_relative_path": null,
  "source_relative_path": "blog-posts/ready/my-post.md",
  "source_content_sha256": "a1b2c3...",
  "provider": "deepseek",
  "model": "deepseek-v4-flash",
  "errors": ["deepseek_rate_limited"]
}
```

When `metadata/runs/` is missing or not writable, the response has `provider: "deepseek"`, `model: null`, `metadata_written: false`, and no draft or metadata files are created. Run metadata never includes `markdown_content`, `generated_draft_content`, prompt text, or API keys.

**n8n integration:** chain `POST /process-file` → (optional GitHub Pages publish) → `POST /generate-linkedin-draft`. Pass `relative_path` as `source_relative_path` and `markdown_content` from the process-file response. After the blog is published to https://silverman.pro, pass the public article URL as `source_public_url` so the generated LinkedIn draft includes a natural call to action pointing readers to the full article. Optionally pass `content_sha256` as `source_content_sha256` and `topic_theme` for CTA wording. Branch on `status`, `draft_written`, `generated_draft_content`, and `errors`.

## n8n workflow: draft generation orchestration

Importable workflow JSON: `n8n/workflows/silverman-blog-linkedin-draft-generation.json`

This workflow orchestrates the worker over HTTP only (see [ADR-0001](docs/decisions/ADR-0001-use-worker-instead-of-n8n-execute-command.md)). n8n does **not** read or write editorial files, call DeepSeek directly, publish to LinkedIn/GitHub, or move blog posts out of `blog-posts/ready/`. The worker remains the filesystem and LLM boundary.

### Import

1. In n8n, open **Workflows** → **Import from File**.
2. Select `n8n/workflows/silverman-blog-linkedin-draft-generation.json`.
3. Open the imported workflow **Silverman Blog LinkedIn Draft Generation**.

### Configure before first run

Edit the **Set Configuration** node (first node after Manual Trigger):

| Field | Placeholder | Purpose |
|-------|-------------|---------|
| `worker_base_url` | `http://localhost:8000` | Worker root URL (no trailing slash). Use your Docker service hostname on the server, e.g. `http://silverman-blog-linkedin-worker:8000`. |
| `worker_api_key` | `CHANGE_ME_WORKER_API_KEY` | Must match `SILVERMAN_BLOG_LINKEDIN_API_KEY` on the worker. |
| `tone` | `executive` | Editorial hint passed to `POST /generate-linkedin-draft`. |
| `audience` | `recruiters and engineering leaders` | Editorial hint for generation. |
| `variant` | `executive-recruiter` | Editorial hint for draft filename/slug segment. |
| `site_base_url` | `https://silverman.pro` | Canonical site root for per-post URL derivation (trailing slash stripped in workflow). |
| `topic_theme` | _(empty)_ | Optional editorial hint for CTA wording when a derived `source_public_url` is included (e.g. `domain-first architecture`). |

The exported JSON contains **no real secrets**. Replace placeholders after import.

**Per-post public URL:** The workflow derives `source_public_url` for each processed item in **Compute Source Public URL**—do not set a manual article URL in **Set Configuration**. Derivation uses:

1. **Public slug:** basename of `relative_path`, remove `.md`, strip a leading numeric ordering prefix (e.g. `01-why-i-did-not-start-with-the-database.md` → `why-i-did-not-start-with-the-database`).
2. **Date:** YAML frontmatter `date:` from `markdown_content` (date portion `YYYY-MM-DD`, e.g. from `2026-07-06 00:00:00 -0500`).
3. **URL format:** `{site_base_url}/{YYYY}/{MM}/{DD}/{public-slug}/`

**Canonical example:** `blog-posts/ready/01-why-i-did-not-start-with-the-database.md` with frontmatter `date: 2026-07-06` → `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/`

If slug or date validation fails, the item gets `source_public_url_error` (`missing_relative_path`, `missing_frontmatter_date`, or `invalid_public_slug`) and **Generate LinkedIn Draft** proceeds without `source_public_url` in the request body.

**Expected vs publish-confirmed URL:** The derived URL follows the same convention as the [blog publishing bridge](#blog-publishing-bridge-github-pages) but is an *expected* URL—not confirmed live until you publish separately. This workflow does **not** publish to GitHub Pages or LinkedIn.

**Re-import after merge:** When this repository updates the workflow JSON, re-import the file in n8n. The export remains `"active": false`; activate only when you intentionally schedule or automate (not part of this workflow).

Authenticated HTTP Request nodes use `Authorization: Bearer {{ $('Set Configuration').first().json.worker_api_key }}` via expressions—not hardcoded tokens.

Ensure the worker has `DEEPSEEK_API_KEY` set when using generation (see DeepSeek env vars above).

### Node flow

```
Manual Trigger
  → Set Configuration
  → Health Check (GET /health)
  → IF Health Ready (status healthy + folders_ready)
  → Process Ready (POST /process-ready)
  → IF Process Ready Failed → error output → stop
  → IF Has Valid Candidates (valid_count > 0)
      → else: clean stop (no candidates)
  → Split Out Valid Files
  → Process File (POST /process-file)
  → IF Process File OK
      → Compute Source Public URL (derive source_public_url from site_base_url, frontmatter date, filename slug)
      → Generate LinkedIn Draft (POST /generate-linkedin-draft)
      → IF Generate Completed
          → success: draft_relative_path, metadata_path, source_relative_path, source_public_url, topic_theme (when echoed)
          → failure: errors, metadata_path, source_relative_path
      → else: process-file errors on item
```

### Expected outcomes

- **Success:** draft file under `linkedin-posts/review/` (written by worker); workflow output includes `draft_relative_path`, `metadata_path`, and when derived and echoed by the worker, `source_public_url` and `topic_theme`.
- **No candidates:** workflow stops cleanly when `valid_count` is 0.
- **Failures:** health not ready, process-ready failed, process-file failed, or generate failed branches expose `errors` and `metadata_path` when the worker returns them.
- **Source posts:** remain in `blog-posts/ready/` (this workflow does not move them).

### Run manually

1. Place at least one valid `.md` file in `blog-posts/ready/` on the worker base path.
2. Start the worker with `SILVERMAN_BLOG_LINKEDIN_API_KEY` and `DEEPSEEK_API_KEY` configured.
3. Execute the workflow from the n8n editor (Manual Trigger).
4. Review generated drafts under `linkedin-posts/review/` on the editorial data mount.

For per-endpoint HTTP Request examples, see sections above (`GET /health`, `POST /process-ready`, `POST /process-file`, `POST /generate-linkedin-draft`).

## Blog publishing bridge (GitHub Pages)

Operator CLI to prepare one ready editorial post pair (`<source-slug>.md` + `<source-slug>.png`) for the public Jekyll site at [silverman.pro](https://silverman.pro). Source slugs may include numeric ordering prefixes (`01-`, `02-`); the helper derives a public slug for URLs and published filenames. Dry-run by default; writes require `--apply`. No HTTP endpoint, no automatic git push.

See [docs/workflows/blog-publishing-bridge.md](docs/workflows/blog-publishing-bridge.md) for paths, environment variables, and manual commit/push steps.

## Project context

- Architecture and phasing: `docs/context/`
- ADRs: `docs/decisions/`
- OpenSpec changes: `openspec/changes/`
