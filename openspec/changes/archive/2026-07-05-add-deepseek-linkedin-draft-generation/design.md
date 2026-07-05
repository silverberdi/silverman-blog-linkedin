## Context

The worker foundation, `POST /process-ready`, `POST /process-file`, and `POST /write-linkedin-draft` are implemented: FastAPI app, environment configuration, editorial folder validation, API key authentication, blog post reading, draft writing (`draft_writer.py`), and run metadata persistence (`run_metadata.py`). n8n orchestrates via HTTP Request nodes (ADR-0001).

This change adds `POST /generate-linkedin-draft`: the first in-worker LLM integration. n8n chains `POST /process-file` (returns `markdown_content`) → `POST /generate-linkedin-draft` (generates and persists one LinkedIn draft). DeepSeek exposes an OpenAI-compatible chat completions API; the worker calls `{normalized_base_url}/chat/completions` via direct `httpx` (default base URL `https://api.deepseek.com`, no automatic `/v1` segment). The worker must start without DeepSeek configured; only this endpoint requires `DEEPSEEK_API_KEY` flexibly at request time.

Blog posts remain canonical (ADR-0002). Generated drafts land in `linkedin-posts/review/` for human review—no auto-publishing.

## Goals / Non-Goals

**Goals:**

- Expose `POST /generate-linkedin-draft` with Bearer API key authentication.
- Accept `markdown_content` and `source_relative_path` in JSON body; optional editorial hints (`title`, `slug_hint`, `tone`, `audience`, `variant`, `source_content_sha256`).
- Call DeepSeek chat completions to produce one LinkedIn draft from supplied Markdown (no disk re-read of source blog file).
- Reuse `write_draft_file()` and existing run metadata patterns from `POST /write-linkedin-draft`.
- Load DeepSeek settings lazily per request; worker starts without `DEEPSEEK_API_KEY`.
- Return structured JSON with `generated_draft_content` on success; map DeepSeek failures to stable error codes.
- Write run metadata with provider/model; exclude markdown, generated text, prompts, and secrets.

**Non-Goals:**

- OpenAI, ChatGPT, local LLM, multi-variant generation, publishing, blog file moves, n8n workflows, prompt library versioning, hashtags, Dairector.

## Decisions

### 1. Module layout

**Decision:** Add focused modules:

```
src/silverman_blog_linkedin/
  deepseek_config.py     # lazy DeepSeek settings from env (not startup-required)
  deepseek_client.py     # chat completions HTTP client + error mapping
  linkedin_prompt.py     # system/user prompt builders (internal, not prompts/ dir yet)
  run_metadata.py        # extend with generate-linkedin-draft builders + trigger constant
  main.py                # POST /generate-linkedin-draft route orchestration
tests/
  test_deepseek_client.py
  test_generate_linkedin_draft.py
```

Reuse without duplication: `validate_source_path_shape`, `check_review_dir_ready`, `write_draft_file`, `check_metadata_runs_ready`, `generate_run_id`, `write_run_metadata`, `require_api_key`, `normalize_relative_path`.

**Rationale:** Separates LLM transport from HTTP orchestration. Keeps prompt text versionable in code for phase 1 without a full prompt library change.

### 2. Reuse draft writer instead of duplicating write orchestration

**Decision:** After DeepSeek returns non-empty draft text, call `write_draft_file()` directly with the generated content. Do **not** duplicate filename generation, exclusive creation, collision retry, or hash computation logic. Do **not** internally HTTP-call `POST /write-linkedin-draft`.

Extract a shared orchestration helper only if `main.py` duplication becomes excessive; prefer calling `write_draft_file()` plus metadata builders inline mirroring `write-linkedin-draft` flow.

**Rationale:** Single source of truth for review draft persistence. Consistent collision and confinement behavior.

**Alternatives considered:**

- **Duplicate write logic in generate route:** Rejected—drift risk.
- **Internal HTTP to write-linkedin-draft:** Rejected—unnecessary overhead and auth coupling.

### 3. DeepSeek configuration (lazy, not startup-required)

**Decision:** Add `DeepSeekSettings` loaded via `load_deepseek_settings(environ)` called at request time for `/generate-linkedin-draft` only.

| Variable | Required | Default |
|----------|----------|---------|
| `DEEPSEEK_API_KEY` | Yes for generate endpoint only | — |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | No | `deepseek-v4-flash` |
| `DEEPSEEK_TIMEOUT_SECONDS` | No | `60` |
| `DEEPSEEK_MAX_OUTPUT_TOKENS` | No | `1024` |

`load_settings()` for worker foundation unchanged—no DeepSeek vars at startup.

**Validation rules (endpoint-time only):**

- `DEEPSEEK_TIMEOUT_SECONDS` MUST parse as a positive number (integer or float).
- `DEEPSEEK_MAX_OUTPUT_TOKENS` MUST parse as a positive integer.
- Invalid optional DeepSeek settings MUST cause `/generate-linkedin-draft` to return HTTP `200` with `status: failed`, `errors: ["deepseek_config_invalid"]`, no DeepSeek call, no draft write, and failed metadata when `metadata/runs/` is writable. Invalid optional settings MUST NOT prevent worker startup.

Missing `DEEPSEEK_API_KEY` (when other settings are valid) → HTTP `200`, `status: failed`, `errors: ["deepseek_api_key_missing"]`, no DeepSeek call, no draft write; write failed metadata if `metadata/runs/` writable. Response still includes `provider: "deepseek"` and `model` from configured/default settings.

Model names are operational configuration—never hardcode legacy model names in application logic beyond config defaults.

**Rationale:** Worker remains usable for health/scan/read/write without LLM credentials. Matches container ops where DeepSeek key is added when generation is enabled.

### 4. HTTP client for DeepSeek

**Decision:** Use `httpx` for POST to `{normalized_base_url}/chat/completions` with OpenAI-compatible JSON body.

**URL construction (direct httpx, no SDK):**

- Default `DEEPSEEK_BASE_URL`: `https://api.deepseek.com`
- Chat completions path segment: `/chat/completions`
- Final URL: strip trailing slash from `DEEPSEEK_BASE_URL`, then append `/chat/completions`
- Example default: `https://api.deepseek.com/chat/completions`
- Do **not** append `/v1` automatically.
- If an operator sets `DEEPSEEK_BASE_URL` to a custom compatible gateway that already includes a path prefix (for example `https://gateway.example.com/v1`), still append `/chat/completions` after trimming the trailing slash (result: `https://gateway.example.com/v1/chat/completions`).
- No URL autodetection or path rewriting beyond trailing-slash normalization.

```json
{
  "model": "<DEEPSEEK_MODEL>",
  "messages": [
    {"role": "system", "content": "<system prompt>"},
    {"role": "user", "content": "<user prompt with blog markdown>"}
  ],
  "max_tokens": <DEEPSEEK_MAX_OUTPUT_TOKENS>,
  "temperature": 0.7
}
```

Authorization: `Bearer {DEEPSEEK_API_KEY}`. Parse `choices[0].message.content`; strip surrounding whitespace; reject empty after strip as `deepseek_empty_response`.

Map HTTP status to error codes:

| DeepSeek HTTP | Error code |
|---------------|------------|
| 401, 403 | `deepseek_auth_failed` |
| 402 | `deepseek_insufficient_balance` |
| 422 | `deepseek_invalid_request` |
| 429 | `deepseek_rate_limited` |
| 500, 503 | `deepseek_unavailable` |
| Timeout | `deepseek_timeout` |
| Empty content | `deepseek_empty_response` |
| Other / network | `deepseek_unavailable` |

Never include DeepSeek API key or raw provider error bodies containing secrets in HTTP responses or metadata.

**Alternatives considered:**

- **OpenAI Python SDK:** Rejected—adds dependency for a single provider; httpx is sufficient for OpenAI-compatible API.

### 5. Prompt design

**Decision:** Internal module `linkedin_prompt.py` builds system + user messages.

**System prompt intent:**

- Output **only** LinkedIn post text—no JSON, no markdown fences, no explanations or preamble.
- Professional, human, senior architecture/software audience tone (English).
- Derive content only from provided blog Markdown; do not fabricate facts, metrics, names, companies, or URLs absent from input.
- No hashtags (phase 1).
- Suitable for human review, not auto-publishing.

**User prompt:** Include blog `markdown_content`; optionally incorporate `title`, `tone`, `audience`, `variant` when provided as editorial hints (not as facts to invent).

Prompt text MUST NOT be stored in run metadata or returned in HTTP response.

**Rationale:** Simple internal prompt for phase 1; `prompts/` directory versioning deferred per scope.

### 6. Request body contract

**Decision:** Pydantic model with `extra="forbid"`.

| Field | Required | Notes |
|-------|----------|-------|
| `source_relative_path` | Yes | Normalized; shape validation only |
| `markdown_content` | Yes | Non-empty after `.strip()` |
| `source_content_sha256` | No | Echoed unchanged when provided; else computed as lowercase SHA-256 of UTF-8 bytes of `markdown_content` exactly as received by the validated request model |
| `title` | No | Prompt hint + metadata |
| `slug_hint` | No | Filename segment + metadata |
| `tone` | No | Prompt hint + metadata |
| `audience` | No | Prompt hint + metadata |
| `variant` | No | Prompt hint + metadata; if `slug_hint` absent, may be used as filename slug segment |

HTTP `422` for invalid body; endpoint contract does not apply.

Do not accept output path fields. Do not re-read source blog file from disk.

### 7. Editorial folder validation scope

**Decision:** Targeted checks only (same as write-linkedin-draft):

1. `metadata/runs/` — exists, directory, writable (first).
2. `linkedin-posts/review/` — exists, directory, writable (before draft write).

No full aggregate `validate_folders()` gate. No `folders_ready` in response.

### 8. Orchestration order

**Decision:**

1. Authenticate (`401` on failure).
2. Validate body (`422` on failure—endpoint contract does not apply).
3. Resolve `source_content_sha256`: echo request value when provided; otherwise compute lowercase SHA-256 of UTF-8 bytes of `markdown_content` exactly as received by the validated model (always non-null for subsequent response/metadata).
4. Normalize `source_relative_path`; generate `run_id`; record `started_at`.
5. Check `metadata/runs/` readiness → if unavailable: no DeepSeek load/call, no draft, no metadata write; return failed with `provider: "deepseek"`, `model: null`.
6. Load DeepSeek settings → if optional settings invalid: no DeepSeek call, no draft; write failed metadata if writable; return failed with `provider: "deepseek"`, `model: null`, `errors: ["deepseek_config_invalid"]`.
7. Check `DEEPSEEK_API_KEY` → if missing: no DeepSeek call, no draft; write failed metadata if writable; return failed with `provider: "deepseek"`, `model` from loaded settings (default/configured), `errors: ["deepseek_api_key_missing"]`.
8. Check `linkedin-posts/review/` readiness → if unavailable: no DeepSeek call, no draft; write failed metadata if writable; response includes `provider: "deepseek"` and resolved `model`.
9. Validate `source_relative_path` shape → if failure: no DeepSeek call, no draft; write failed metadata if writable; response includes `provider: "deepseek"` and resolved `model`.
10. Call DeepSeek → map failures; on empty content: no draft; write failed metadata; response includes `provider: "deepseek"` and resolved `model`.
11. Call `write_draft_file()` with generated text → handle `draft_path_collision`.
12. Write run metadata → handle `metadata_write_failed` partial failure (draft retained).
13. Return response; include `generated_draft_content` only on `status: completed`.

DeepSeek is not called when pre-checks fail (steps 5–9). After valid body validation, every response includes `provider: "deepseek"`.

### 9. HTTP response contract

**Decision:** When endpoint contract applies (auth + valid body):

| Field | Notes |
|-------|-------|
| `run_id` | Generated |
| `status` | `completed` or `failed` |
| `metadata_written` | boolean |
| `metadata_path` | relative or null |
| `draft_written` | boolean |
| `draft_relative_path` | string or null |
| `source_relative_path` | normalized, always present |
| `source_content_sha256` | non-null string (echoed or computed in step 3) |
| `draft_content_sha256` | string or null |
| `size_bytes` | integer or null |
| `provider` | MUST be `"deepseek"` for every response after valid body validation |
| `model` | configured/default DeepSeek model when settings load successfully; JSON `null` only when settings were not loaded (for example `metadata/runs` unavailable before load, or `deepseek_config_invalid`) |
| `generated_draft_content` | present only on success (`status: completed`); null/absent on failure |
| `errors` | array of error codes |

**Examples after valid body:**

- `metadata/runs` unavailable: `provider: "deepseek"`, `model: null`, non-null `source_content_sha256`
- `DEEPSEEK_API_KEY` missing: `provider: "deepseek"`, `model: "deepseek-v4-flash"` (or configured), `errors: ["deepseek_api_key_missing"]`
- `deepseek_config_invalid`: `provider: "deepseek"`, `model: null`

HTTP codes: `401` auth failure; `422` body validation; `200` for all business outcomes after valid body.

### 10. Run metadata

**Decision:** Trigger `POST /generate-linkedin-draft`. Include: `run_id`, `trigger`, `started_at`, `completed_at`, `status`, `base_path`, `provider` (`deepseek`), `model`, `source_relative_path`, non-null `source_content_sha256`, `draft_relative_path`, `draft_content_sha256`, `size_bytes`, `draft_written`, optional `title`/`slug_hint`/`tone`/`audience`/`variant`, `errors`.

Exclude: `markdown_content`, `generated_draft_content`, prompt text, worker API key, DeepSeek API key, auth token.

Partial failure: draft written, metadata failed → same as write-linkedin-draft (`metadata_write_failed`, draft retained).

### 11. Security

**Decision:**

- Reuse `require_api_key` for worker auth.
- DeepSeek key only in outbound Authorization header; never in responses, metadata, or INFO logs.
- Source path shape validation prevents traversal.
- Server-generated draft paths only via `write_draft_file()`.

### 12. Docker and deployment

**Decision:** Add `httpx` to project dependencies. Document new env vars in README and docker-compose example comments. No Dockerfile structural changes expected. Mount and API key patterns unchanged.

### 13. Logging

**Decision:** INFO: `run_id`, `status`, `source_relative_path`, `draft_relative_path`, `model`, `provider`. DEBUG: content hashes. Never log `markdown_content`, `generated_draft_content`, prompts, API keys, or tokens.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| LLM fabricates facts | Strict prompt rules; human review in `linkedin-posts/review/` |
| DeepSeek outage blocks pipeline | Structured error codes; n8n can branch/retry; write-linkedin-draft still available |
| Large `markdown_content` in request | Accept for phase 1; same as process-file returning content to n8n |
| Metadata write fails after draft | Partial failure pattern; draft retained |
| Model name changes at DeepSeek | Configurable `DEEPSEEK_MODEL`; default in config only |
| Concurrent requests collide on filename | Reuse exclusive creation + collision retries from draft_writer |

## Migration Plan

1. Implement modules, route, tests.
2. Run pytest; manual curl with mock/stub DeepSeek in tests; optional manual test with real key locally.
3. Update README and docker-compose env documentation.
4. Deploy: add `DEEPSEEK_API_KEY` to container env when enabling generation; worker starts without it.
5. Rollback: revert image; drafts and metadata are additive.

## Open Questions

- None blocking. Future: max `markdown_content` size limit, multi-variant generation, external prompt files under `prompts/`.
