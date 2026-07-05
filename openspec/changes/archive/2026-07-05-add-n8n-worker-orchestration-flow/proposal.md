## Why

The worker now exposes the full HTTP chain needed to turn ready blog Markdown into LinkedIn review drafts (`GET /health`, `POST /process-ready`, `POST /process-file`, `POST /generate-linkedin-draft`), but n8n still has no importable workflow that wires those endpoints together. Operators must hand-craft HTTP Request nodes for every run. This change delivers the first version-controlled, importable n8n workflow that orchestrates draft generation end-to-end while keeping the worker as the sole filesystem and LLM boundary (ADR-0001).

## Goals

- Deliver an importable n8n workflow JSON at `n8n/workflows/silverman-blog-linkedin-draft-generation.json`.
- Orchestrate worker endpoints only via HTTP Request nodes: health check → scan ready posts → read each candidate → generate LinkedIn draft via worker (DeepSeek inside worker).
- Stop cleanly when no valid candidates exist; branch on `completed` vs `failed` generation outcomes.
- Leave generated drafts under `linkedin-posts/review/` for human review; do not move source blog files.
- Make worker base URL and API key configurable without hardcoding secrets in the workflow export.
- Document import and configuration steps in the repository README.

## Non-Goals

- n8n Execute Command, SSH, or any direct filesystem access from n8n.
- Direct DeepSeek, OpenAI, ChatGPT, or local LLM calls from n8n.
- Publishing to LinkedIn or GitHub.
- Moving blog posts to `processed/` or `error/`.
- Campaign management, scheduling/cron triggers, or notifications.
- Multi-variant generation in one workflow run (one draft per valid candidate per invocation).
- Auto-approval or auto-publishing of drafts.
- Changes to existing worker endpoint behavior or new worker routes.
- Dairector content.

## What Changes

- Add OpenSpec capability `n8n-worker-orchestration-flow` defining requirements for the first importable orchestration workflow.
- Add `n8n/workflows/silverman-blog-linkedin-draft-generation.json` with Manual Trigger, HTTP Request nodes for worker calls, iteration over `valid_files`, IF branching on generate status, and no embedded secrets.
- Use workflow-level variables or credential-friendly expressions for `worker_base_url` and Bearer authorization.
- Pass `source_relative_path`, `markdown_content`, `source_content_sha256`, optional `title`, and static editorial hints (`tone`, `audience`, `variant`) to `POST /generate-linkedin-draft`.
- Expose `draft_relative_path` and `metadata_path` on success; expose `errors` and `metadata_path` when available on failure.
- Update README with workflow import, configuration, and expected run behavior.
- Add lightweight validation (JSON structure / required node checks) if useful—no over-engineering.

## Why a Dedicated HTTP Worker (Not n8n Execute Command)

n8n Execute Command runs arbitrary shell on the server host, mixing orchestration with filesystem and API access. This workflow keeps n8n as a thin HTTP orchestrator: every read, write, path validation, and DeepSeek call stays inside the version-controlled worker. n8n never touches editorial folders or provider credentials for generation.

## Capabilities

### New Capabilities

- `n8n-worker-orchestration-flow`: Importable n8n workflow that orchestrates `GET /health` → `POST /process-ready` → per-candidate `POST /process-file` → `POST /generate-linkedin-draft` via HTTP Request nodes only, with configurable worker URL/auth, clean empty-candidate exit, and status branching—without publishing, file moves, or direct LLM calls from n8n.

### Modified Capabilities

- _(none — worker endpoint requirements are unchanged; this change adds orchestration artifacts only)_

## Impact

- **Repository**: New `n8n/workflows/` directory and workflow JSON; README section for n8n import/configuration; optional lightweight validation script or test.
- **Worker APIs**: No code changes; workflow consumes existing endpoints.
- **n8n**: Operators import one workflow; configure base URL and API key credential/variable after import.
- **Editorial data**: Reads from `blog-posts/ready/` via worker; writes drafts to `linkedin-posts/review/` via worker; source blog files remain in place.
- **Security**: Workflow JSON must not contain real API keys; Bearer auth uses placeholders or n8n credentials.
- **Operations**: Same worker deployment model (local Mac dev, Docker on Linux server); workflow base URL switches per environment.
