# silverman-blog-linkedin worker

Local HTTP worker for the **silverman-blog-linkedin** content automation system. n8n orchestrates workflows; this service performs bounded file processing and health checks over HTTP (see ADR-0001).

Phase 1 foundation: configuration, editorial folder validation, and `GET /health`. Processing endpoints (`POST /process-ready`, `POST /process-file`) are planned for later changes.

## Requirements

- Python 3.11+
- Editorial data directory with the expected folder layout (see below)

## Environment variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` | No | `./data/silverman-blog-linkedin` | Root path for editorial data |
| `SILVERMAN_BLOG_LINKEDIN_API_KEY` | **Yes** | None | Shared secret for future authenticated endpoints |
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

The example mounts `./data/silverman-blog-linkedin` read-only into `/data/silverman-blog-linkedin` inside the container.

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

## Project context

- Architecture and phasing: `docs/context/`
- ADRs: `docs/decisions/`
- OpenSpec changes: `openspec/changes/`
