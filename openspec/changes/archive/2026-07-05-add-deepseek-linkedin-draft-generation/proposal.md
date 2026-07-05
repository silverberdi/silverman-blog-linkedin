## Why

The worker can read blog posts (`POST /process-file`) and persist externally supplied LinkedIn drafts (`POST /write-linkedin-draft`), but n8n still has no bounded in-worker path to generate a draft from blog Markdown. This change adds `POST /generate-linkedin-draft` using the DeepSeek API (OpenAI-compatible chat completions) so n8n can call one authenticated endpoint to produce one review draft under `linkedin-posts/review/` with run metadata—without Execute Command, without OpenAI, and without auto-publishing.

## Goals

- Define and implement `POST /generate-linkedin-draft` with Bearer API key authentication (`SILVERMAN_BLOG_LINKEDIN_API_KEY`).
- Accept blog Markdown in the request body (`markdown_content`) plus `source_relative_path` for traceability; do not re-read the source blog file on disk.
- Call DeepSeek chat completions to generate one LinkedIn draft aligned with Silverio's architecture/software audience and editorial rules.
- Persist the generated draft by reusing existing draft writer and run metadata helpers (same safe write behavior as `POST /write-linkedin-draft`).
- Load DeepSeek configuration from environment variables; require `DEEPSEEK_API_KEY` only at request time for this endpoint—not at worker startup.
- Return structured JSON suitable for n8n branching, including `generated_draft_content` on success for workflow visibility.
- Write run metadata under `metadata/runs/` when writable; exclude markdown body, generated text, prompt text, and secrets from metadata.

## Non-Goals

- OpenAI, ChatGPT, or local LLM integration.
- Publishing to LinkedIn or GitHub.
- Moving blog posts to `processed/` or `error/`.
- Campaign management, scheduling, or n8n workflow JSON creation.
- Prompt library/versioning beyond a simple internal prompt module.
- Multi-variant generation (one draft per request only).
- Auto-approval or auto-publishing.
- Hashtags unless explicitly requested in a later change.
- Dairector content.

## What Changes

- Add `POST /generate-linkedin-draft` authenticated endpoint to the FastAPI worker.
- Add DeepSeek client module using OpenAI-compatible chat completions via direct `httpx` POST to `{normalized_base_url}/chat/completions` (default base URL `https://api.deepseek.com`; no automatic `/v1` path segment).
- Add optional DeepSeek environment variables (`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, `DEEPSEEK_TIMEOUT_SECONDS`, `DEEPSEEK_MAX_OUTPUT_TOKENS`); worker starts without DeepSeek configured; invalid optional DeepSeek settings fail only `/generate-linkedin-draft` with `deepseek_config_invalid`.
- Resolve `source_content_sha256` deterministically: echo when provided in request, otherwise compute SHA-256 of UTF-8 `markdown_content` bytes (always non-null in response/metadata after valid body).
- Return `provider: "deepseek"` on every `/generate-linkedin-draft` response after valid body validation; `model` reflects configured/default model when settings load successfully.
- Add strict request body validation: required `source_relative_path` and `markdown_content`; optional `source_content_sha256`, `title`, `slug_hint`, `tone`, `audience`, `variant`; reject extra fields with HTTP `422`.
- Reuse source path shape validation from draft writer; reuse `write_draft_file` for persistence after generation.
- Extend run metadata with trigger `POST /generate-linkedin-draft`, provider `deepseek`, and model name.
- Map DeepSeek HTTP failures to structured error codes (`deepseek_auth_failed`, `deepseek_rate_limited`, etc.).
- Include `generated_draft_content` in HTTP response on success only; never store it in metadata.
- Add tests for authentication, body validation, DeepSeek error mapping, draft persistence reuse, metadata, and failure modes.
- Update README with endpoint usage, DeepSeek env vars, and n8n integration notes.

## Why a Dedicated HTTP Worker (Not n8n Execute Command)

n8n Execute Command runs arbitrary shell on the server host, expanding attack surface and mixing orchestration with filesystem and API access. A dedicated HTTP worker exposes a bounded, testable API: n8n calls `POST /generate-linkedin-draft` via HTTP Request nodes after `POST /process-file`, supplies the blog Markdown payload, and never needs direct DeepSeek credentials or editorial write logic in workflow scripts. Path validation, LLM calls, draft persistence, and metadata writes live in version-controlled Python code.

## Capabilities

### New Capabilities

- `deepseek-linkedin-draft-generation`: Authenticated `POST /generate-linkedin-draft` endpoint that validates request body and source path shape, checks DeepSeek and editorial directory readiness, calls DeepSeek to generate one LinkedIn draft from supplied blog Markdown, persists the draft under `linkedin-posts/review/` via existing draft writer behavior, writes run metadata, and returns structured JSON for n8n—including `generated_draft_content` on success.

### Modified Capabilities

- `ready-blog-post-processing`: Extend API key authentication requirement to cover `POST /generate-linkedin-draft` alongside existing processing endpoints.

## Impact

- **Repository**: New DeepSeek client and prompt modules, extended config (lazy DeepSeek settings), route orchestration in `main.py`, extended `run_metadata.py` helpers, and tests under `src/silverman_blog_linkedin/` and `tests/`.
- **APIs**: New `POST /generate-linkedin-draft` (authenticated); existing endpoints unchanged.
- **Dependencies**: Add HTTP client dependency for DeepSeek API calls (e.g., `httpx`); no OpenAI SDK required.
- **Environment**: New optional DeepSeek variables; worker still starts without them; only `/generate-linkedin-draft` fails when `DEEPSEEK_API_KEY` is missing.
- **Editorial data**: Writes one draft to `linkedin-posts/review/` and run metadata to `metadata/runs/` on success; does not modify source blog files.
- **Security**: Worker API key required; DeepSeek API key never exposed in responses, metadata, or info-level logs; source path shape validation prevents traversal.
- **n8n**: Workflows can chain `POST /process-file` → `POST /generate-linkedin-draft` without external LLM nodes; no workflow JSON in this change.
