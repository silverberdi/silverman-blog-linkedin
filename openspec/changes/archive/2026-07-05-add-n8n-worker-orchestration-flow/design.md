## Context

Worker endpoints are implemented and archived: `GET /health`, `POST /process-ready`, `POST /process-file`, `POST /write-linkedin-draft`, and `POST /generate-linkedin-draft` (DeepSeek inside worker). README already documents per-endpoint n8n HTTP Request patterns. No importable workflow JSON exists yet.

n8n runs on the Linux server; the worker runs locally (Mac dev) or in Docker on the server (`SILVERMAN_BLOG_LINKEDIN_BASE_PATH=/data/silverman-blog-linkedin`). ADR-0001 requires HTTP Request nodes only. Blog posts stay canonical in `blog-posts/ready/`; LinkedIn drafts land in `linkedin-posts/review/` for human review (ADR-0002).

This design covers the first orchestration workflow only—manual trigger, no scheduling, no publish, no blog file moves.

## Goals / Non-Goals

**Goals:**

- Single importable workflow: `n8n/workflows/silverman-blog-linkedin-draft-generation.json`.
- End-to-end path: health → scan → per-candidate read → generate draft → branch on status.
- Configurable `worker_base_url` and Bearer auth without secrets in git.
- README import/configuration guide.
- Lightweight JSON validation in repo tests or script.

**Non-Goals:**

- Cron/webhook triggers, notifications, campaign metadata.
- Moving posts to `processed/` / `error/`.
- Calling `POST /write-linkedin-draft` (generate endpoint persists on success).
- Multi-variant loops (three tones per post)—static hints per run only.
- n8n credential auto-provisioning on import (document manual setup).

## Decisions

### 1. Workflow variables for URL and API key

**Decision:** Define n8n workflow variables (or a single Set node at start) for:

| Variable | Example placeholder | Purpose |
|----------|---------------------|---------|
| `worker_base_url` | `http://localhost:8000` | Prefix for all HTTP Request URLs |
| `worker_api_key` | `REPLACE_AFTER_IMPORT` | Bearer token value |

All HTTP Request nodes use expressions such as `{{$vars.worker_base_url}}/health` and header `Authorization: Bearer {{$vars.worker_api_key}}`.

**Rationale:** One place to change per environment; matches `docs/context/n8n-integration-context.md` guidance. Exported JSON uses obvious placeholders, not real keys.

**Alternatives considered:**

- **Hardcode URLs per node:** Rejected—error-prone across dev/prod.
- **n8n Header Auth credential only:** Valid; README will document creating a credential and replacing the expression. Variables remain the default export pattern for simplicity on first import.

### 2. Node graph (high level)

```
Manual Trigger
  → HTTP GET /health
  → IF healthy (optional: check status field)
  → HTTP POST /process-ready
  → IF valid_count > 0  (else → No Op / stop)
  → Split valid_files (Split In Batches or Item Lists)
    → HTTP POST /process-file  { relative_path }
    → IF process-file status completed
      → HTTP POST /generate-linkedin-draft  { mapped body }
      → IF generate status completed
          → success branch (Set: draft_relative_path, metadata_path)
        else
          → failure branch (Set: errors, metadata_path)
    else
      → process-file failure branch
```

**Rationale:** Mirrors README integration notes and user-requested flow. Standard n8n patterns; no custom code nodes required.

### 3. Mapping generate-linkedin-draft body

**Decision:** Build JSON body in HTTP Request node using expressions from current item context:

| Field | Source |
|-------|--------|
| `source_relative_path` | `$json.relative_path` from process-file (or candidate) |
| `markdown_content` | `$json.markdown_content` from process-file |
| `source_content_sha256` | `$json.content_sha256` from process-file |
| `title` | Optional: omitted in v1, or derived via simple expression from first line of `markdown_content` if added later |
| `tone` | Static string in node body, e.g. `"executive"` |
| `audience` | Static string, e.g. `"recruiters and engineering leaders"` |
| `variant` | Static string, e.g. `"executive-recruiter"` |

Document chosen static hints in README so operators can edit the HTTP Request body without changing worker code.

**Rationale:** Worker accepts optional `title`; deriving title from Markdown in n8n adds fragility. Static editorial hints satisfy “variant as static editorial hints” without over-building expression logic in v1.

### 4. Empty-candidate and early-failure handling

**Decision:**

- After `process-ready`: IF `valid_count === 0` (or `valid_files` empty) → connect to No Operation / end—no error throw.
- After `process-ready` with `status === "failed"`: stop with error output (Set node or stop branch).
- After `process-file` failure: log errors on item, skip generate for that item, continue loop.
- After `generate-linkedin-draft` failure: failure branch exposes `errors` array and `metadata_path`.

**Rationale:** Aligns with worker JSON contracts and user requirement for clean stop vs failure visibility.

### 5. Iteration mechanism

**Decision:** Use **Split In Batches** (batch size 1) or **Loop Over Items** on `valid_files` array from `process-ready` response. Ensure the node referencing `valid_files` uses the correct n8n path (e.g. `$('Process Ready').item.json.valid_files` or split from parent).

**Rationale:** n8n version differences exist; export targets commonly available loop nodes. README notes where to adjust if import shows disconnected references.

### 6. Validation approach

**Decision:** Add `tests/test_n8n_workflow.py` (or `scripts/validate_n8n_workflow.py` invoked from pytest) that:

- Asserts file exists at `n8n/workflows/silverman-blog-linkedin-draft-generation.json`
- Parses JSON
- Checks presence of node types: `n8n-nodes-base.manualTrigger`, `n8n-nodes-base.httpRequest`, `n8n-nodes-base.if`
- Asserts no literal patterns resembling API keys (e.g. grep for `sk-`, long Bearer literals)
- Optionally asserts URL expressions reference `worker_base_url`

**Rationale:** Catches accidental corruption without n8n in CI.

### 7. No worker code changes

**Decision:** This change is workflow + docs + validation only. Worker behavior is frozen to current specs.

**Rationale:** User scope and OpenSpec phasing—orchestration follows completed worker capabilities.

## Risks / Trade-offs

- **[n8n version / node type drift]** → Document minimum n8n version if known; keep node set minimal (Manual Trigger, HTTP Request, IF, Split/Loop, Set).
- **[Expression path errors after import]** → README troubleshooting section; descriptive node names (`Health Check`, `Process Ready`, etc.).
- **[Large markdown in workflow execution data]** → Acceptable for phase 1; worker already returns content in HTTP JSON. Future: worker-side batch endpoint if payloads become problematic.
- **[Placeholder API key left unchanged]** → README warns; health/process-ready will return 401 until configured.

## Migration Plan

1. Merge change with workflow JSON and README.
2. On n8n server: Import workflow JSON.
3. Set workflow variables `worker_base_url` (e.g. `http://silverman-blog-linkedin-worker:8000` on Docker network) and `worker_api_key`.
4. Ensure worker has `DEEPSEEK_API_KEY` configured for generate endpoint.
5. Place a test `.md` file in `blog-posts/ready/` on worker base path.
6. Manual execute; confirm draft under `linkedin-posts/review/` and source file still in `ready/`.

Rollback: deactivate or delete imported workflow in n8n; no worker deployment change required.

## Open Questions

- Minimum n8n version supported by the exported JSON (confirm during implementation export from dev n8n instance).
- Whether to add optional `title` derivation expression in v1 or defer to README-only static omission.
