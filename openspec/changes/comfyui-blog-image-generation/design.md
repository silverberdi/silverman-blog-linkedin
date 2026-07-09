## Context

### Current state

Flow A blog publish (`blog_publish_flow.py` → `publish_blog_post()`) runs preflight inspection, optional idempotent `already_published` short-circuit, then `validate_ready_post()` before any GitHub Pages bridge write. Ready-post validation (`ready_post_validation.py`) **blocks** when:

- companion PNG `blog-posts/ready/<source_slug>.png` is missing (`ready_post_image_missing`), or
- front matter `image` does not equal `/assets/images/<public_slug>.png` (`frontmatter_invalid_image`).

Authors sometimes submit Markdown without `image` and without a PNG. The public Jekyll theme at [silverman.pro](https://silverman.pro) reuses the same front matter `image` for hero, list cards, tag cards, and sidebar thumbnails with CSS `aspect-ratio: 1.3333333333` and `object-fit: cover` — canonical generated size **1200×900** (4:3). Legacy **1024×768** remains compatible when supplied manually.

ComfyUI runs as an operator-managed service — locally on Mac, on the LAN, or on a hosted platform such as Comfy Cloud (`https://cloud.comfy.org`). The Comfy Cloud API is compatible with the local ComfyUI REST API; hosted deployments may require an API path prefix (for example `/api`) and an API key via Bearer auth and/or `extra_data` on `/prompt` (Partner Nodes). The worker calls ComfyUI over its REST API per ADR-0001; n8n does not invoke ComfyUI directly in this change.

### Policy references

- Publish flow: `openspec/specs/worker-blog-publishing-endpoint/spec.md`, `blog_publish_flow.py`
- Validation: `openspec/specs/ready-post-editorial-validation/spec.md`, `ready_post_validation.py`
- Publishing bridge: `openspec/specs/github-pages-blog-publishing/spec.md`, `github_pages_publish.py`
- Flow A umbrella: `openspec/specs/flow-a-automatic-publishing/spec.md`

## Goals / Non-Goals

**Goals:**

- Detect missing canonical image prerequisites on a ready post before validation (missing/empty `image`, or canonical `image` with missing companion PNG).
- MUST NOT auto-generate when `image` points to a non-canonical path.
- When ComfyUI generation is enabled, synthesize an editorial visual prompt from post metadata and body, call ComfyUI, write PNG + update front matter, record metadata.
- Integrate as a **pre-validation** step inside `publish_blog_post()` (no new HTTP endpoint required for slice 1).
- Default **disabled**; dry-run plans generation without side effects.
- Injectable ComfyUI client for tests; no live ComfyUI in CI/normal test runs.
- Fail publish with stable codes when generation is required but fails.

**Non-Goals:**

- n8n workflow activation, cron, real `--real-publish`, direct edits to `silverberdi.github.io`.
- LinkedIn image upload or article preview images.
- Changing validation rules in `ready_post_validation.py` (generation must satisfy existing rules before validation runs).
- LLM-based prompt generation in v1 (deterministic template assembly from front matter + excerpt is sufficient; optional future enhancement).

## Decisions

### 1. Pre-validation hook inside `publish_blog_post()`

**Decision:** Add `ensure_blog_image(...)` (or equivalent) invoked after preflight/idempotent short-circuit and **before** `validate_ready_post()` when:

1. canonical image prerequisites are missing — front matter omits `image` or `image` is empty/whitespace-only, OR front matter `image` equals `/assets/images/<public_slug>.png` but companion PNG `blog-posts/ready/<source_slug>.png` is missing — AND
2. `SILVERMAN_COMFYUI_IMAGE_ENABLED` is true.

When front matter `image` points to any non-canonical path, generation MUST NOT run; the post MUST remain unchanged and existing validation or operator remediation MUST handle the mismatch.

If generation is disabled and canonical image prerequisites are missing, skip generation and let validation fail with existing codes (backward compatible).

**Rationale:** Validation remains the single editorial gate; generation is a remediation step, not a bypass. Matches existing slice 4 sequencing pattern.

**Alternatives considered:** New `POST /generate-blog-image` endpoint — deferred; publish flow is the primary n8n entry today and keeps orchestration in one call.

### 2. Module split: prompt + generation orchestration + ComfyUI client

**Decision:**

| Module | Responsibility |
|--------|----------------|
| `blog_image_prompt.py` | Build deterministic positive/negative prompt strings from title, description, tags, categories, body excerpt; enforce editorial style rules (no readable text, no logos, centered subject, safe margins for cover crop). |
| `comfyui_client.py` | Load workflow JSON template, inject width/height/prompt/seed, POST to ComfyUI `/prompt`, poll history, download output bytes via `/view`. Protocol behind `ComfyUIClientProtocol` for fakes. |
| `blog_image_generation.py` | `ensure_blog_image(base_path, source_relative_path, *, config, client, dry_run)` — detection, orchestration, PNG write, front matter patch, metadata object. |

**Rationale:** Testability and separation mirror `deepseek_client.py` / `linkedin_package_flow.py` patterns.

### 3. Asset paths and front matter update

**Decision:**

- Write PNG to `blog-posts/ready/<source_slug>.png` (same path validation already expects).
- Set front matter `image: /assets/images/<public_slug>.png` (public path used by Jekyll theme and bridge).
- Patch front matter in-place on the source Markdown using existing `_split_frontmatter` helpers from `github_pages_publish.py` where possible; do not duplicate YAML parsing.

**Rationale:** Aligns with ready-post validation and GitHub Pages bridge without new folder conventions.

### 4. ComfyUI workflow and configuration

**Decision:** Store a default workflow JSON under `prompts/comfyui/blog-image-workflow.json` (or similar). Configure via env:

| Variable | Purpose | Default |
|----------|---------|---------|
| `SILVERMAN_COMFYUI_IMAGE_ENABLED` | Master enable | `false` |
| `SILVERMAN_COMFYUI_BASE_URL` | ComfyUI origin (local/LAN or hosted, e.g. `https://cloud.comfy.org`) | unset (required when enabled) |
| `SILVERMAN_COMFYUI_API_PREFIX` | Optional API path prefix (hosted example `/api`) | empty |
| `SILVERMAN_COMFYUI_API_KEY` | ComfyUI/Comfy Cloud API key | unset |
| `SILVERMAN_COMFYUI_AUTH_HEADER_NAME` | HTTP header for Bearer API key | `Authorization` |
| `SILVERMAN_COMFYUI_EXTRA_DATA_API_KEY_FIELD` | `extra_data` field for API key on `/prompt` (Partner Nodes) | unset |
| `SILVERMAN_COMFYUI_WORKFLOW_PATH` | Workflow JSON path | repo default workflow file |
| `SILVERMAN_COMFYUI_TIMEOUT_SECONDS` | HTTP/poll timeout | `120` |
| `SILVERMAN_COMFYUI_IMAGE_WIDTH` | Output width | `1200` |
| `SILVERMAN_COMFYUI_IMAGE_HEIGHT` | Output height | `900` |
| `SILVERMAN_COMFYUI_DRY_RUN` | Plan only, no HTTP/files | `false` |

Publish request-level dry-run (if bridge supports) OR generation dry-run via env/parameter on `publish_blog_post` kwargs for tests.

**Rationale:** Safe defaults; operator opts in explicitly. Dimensions match blog template 4:3 preference.

**Alternatives considered:** Hard-code workflow in Python — rejected; operators need to swap models/nodes without code changes.

### 5. ComfyUI REST API interaction (minimal v1)

**Decision:** Use ComfyUI REST API (local/LAN or hosted such as Comfy Cloud):

1. `POST {base_url}{api_prefix}/prompt` with workflow graph + client id; optionally include API key in `extra_data` when configured.
2. Poll `GET {base_url}{api_prefix}/history/{prompt_id}` until completed or timeout.
3. Download first PNG output via `GET {base_url}{api_prefix}/view?filename=...&type=output`.

When `SILVERMAN_COMFYUI_API_KEY` is set, send `{SILVERMAN_COMFYUI_AUTH_HEADER_NAME}: Bearer <api-key>`. Never log, return, or store the API key in metadata or HTTP responses.

When `SILVERMAN_COMFYUI_API_PREFIX` is empty, URLs match local ComfyUI defaults (`/prompt`, `/history`, `/view`).

Wrap in retry-safe polling with configurable timeout. Surface ComfyUI errors as `blog_image_generation_comfyui_failed` without leaking stack traces or secrets in HTTP JSON.

**Rationale:** Standard ComfyUI API; compatible with Comfy Cloud; no custom nodes required in worker.

### 6. Metadata recording

**Decision:** Extend campaign metadata (when campaign exists) with `blog_image_generation`:

```json
{
  "status": "generated|skipped|failed|dry_run",
  "source_relative_path": "...",
  "image_relative_path": "blog-posts/ready/<source_slug>.png",
  "public_image_path": "/assets/images/<public_slug>.png",
  "width": 1200,
  "height": 900,
  "prompt_hash": "<sha256 of prompt>",
  "generated_at": "<utc iso>",
  "error_code": null
}
```

Also append a run record under `metadata/runs/` when generation executes (reuse `run_metadata.py` patterns). Do not store full prompt text in campaign JSON (hash only).

**Rationale:** Auditability for n8n branching; keeps metadata small.

### 7. Publish flow failure semantics

**Decision:** When canonical image prerequisites are missing and generation is enabled:

- Success → recompute `source_content_sha256` if Markdown changed (front matter patch), then continue to validation.
- Failure → return `status: failed` with `blog_image_generation_failed` (or specific sub-codes), do **not** call `validate_ready_post()`, do **not** write public repo files.

When front matter `image` points to a non-canonical path, generation MUST NOT run; validation or operator remediation MUST handle the mismatch.

When `image` and PNG already satisfy validation expectations → `blog_image_generation.status: skipped`.

**Rationale:** User requirement: must not publish if generation failed.

### 8. Image composition rules (prompt template)

**Decision:** Encode editorial constraints in prompt builder and negative prompt:

- Professional technical editorial illustration/photo style; software architecture, AI, engineering leadership, systems design themes.
- 4:3 composition, main subject centered, generous margins (safe for `object-fit: cover` crop).
- Negative: text, typography, logos, watermarks, UI screenshots with readable text, cluttered edges.

**Rationale:** Matches blog brand and CSS crop behavior.

### 9. Testing strategy

**Decision:** `FakeComfyUIClient` returns fixed PNG bytes; tests cover:

- missing `image` + enabled → generates, updates front matter, validation passes
- canonical `image` with missing companion PNG + enabled → generates PNG only, validation passes
- existing valid `image` + PNG → skipped
- non-canonical `image` path → skipped, post unchanged, validation fails
- ComfyUI error → publish failed, no public writes
- dry-run → no file writes, metadata `dry_run`
- metadata fields persisted

No network in default pytest run.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| ComfyUI unavailable on server | Disabled by default; publish fails fast with clear error when enabled but unreachable |
| Front matter patch corrupts YAML | Use existing front matter utilities; add round-trip tests |
| Content hash changes after front matter update | Recompute hash in publish preflight after generation before validation/idempotency checks |
| Generated images poor quality | Prompt template + operator workflow tuning; v1 does not auto-regenerate |
| Long generation times block HTTP request | Configurable timeout; n8n can retry; document expected latency |
| ComfyUI API drift | Client isolated in `comfyui_client.py`; workflow JSON versioned in repo |

## Migration Plan

1. Deploy worker with new code; leave `SILVERMAN_COMFYUI_IMAGE_ENABLED=false` (no behavior change).
2. Operator validates ComfyUI workflow locally with dry-run publish tests.
3. Enable on dev/staging with `SILVERMAN_COMFYUI_IMAGE_ENABLED=true` and base URL pointing to ComfyUI instance.
4. Rollback: set enable flag false — publish reverts to requiring manual PNG + `image`.

No public blog repo migration required.

## Open Questions

- Whether to add optional `POST /generate-blog-image` for manual operator use in a follow-up (out of scope for v1).
- Whether prompt assembly should later call DeepSeek for richer visual briefs (out of scope for v1).
- Exact ComfyUI workflow model/checkpoint choice — operator-owned via workflow JSON, not fixed in spec.
