## 1. DeepSeek configuration and client

- [x] 1.1 Add `httpx` dependency to project packaging (`pyproject.toml` or requirements)
- [x] 1.2 Implement `deepseek_config.py` with lazy `load_deepseek_settings()`: `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` (default `https://api.deepseek.com`), `DEEPSEEK_MODEL` (default `deepseek-v4-flash`), `DEEPSEEK_TIMEOUT_SECONDS` (default `60`, must parse as positive number), `DEEPSEEK_MAX_OUTPUT_TOKENS` (default `1024`, must parse as positive integer); validate optional settings at endpoint time and return `deepseek_config_invalid` on parse failure; expose `is_configured` check for API key presence
- [x] 1.3 Ensure `load_settings()` for worker foundation remains unchanged—no DeepSeek vars required at startup; invalid optional DeepSeek settings must not prevent worker startup
- [x] 1.4 Implement `deepseek_client.py` with chat completions POST to `{normalized_base_url}/chat/completions` (strip trailing slash from `DEEPSEEK_BASE_URL` before append; do not append `/v1`), OpenAI-compatible request body, content extraction, and HTTP status → error code mapping (`deepseek_auth_failed`, `deepseek_insufficient_balance`, `deepseek_invalid_request`, `deepseek_rate_limited`, `deepseek_unavailable`, `deepseek_timeout`, `deepseek_empty_response`)
- [x] 1.5 Add `tests/test_deepseek_client.py` covering URL construction (default base, trailing slash strip, custom gateway path prefix), error mapping, empty content handling, successful content extraction, and no API key leakage in exceptions/results

## 2. LinkedIn prompt module

- [x] 2.1 Implement `linkedin_prompt.py` with system + user message builders using blog `markdown_content` and optional `title`, `tone`, `audience`, `variant` hints
- [x] 2.2 Ensure prompt instructs: output only LinkedIn draft text (no JSON/fences/explanations), no fabricated facts/metrics/names/URLs, no hashtags, senior architecture audience, English
- [x] 2.3 Add unit tests for prompt structure (messages present, markdown included, hints reflected when provided)

## 3. Run metadata extensions

- [x] 3.1 Add `TRIGGER_GENERATE_LINKEDIN_DRAFT = "POST /generate-linkedin-draft"` constant to `run_metadata.py`
- [x] 3.2 Implement `build_generate_linkedin_draft_metadata_payload()` with provider, model, summary fields, optional editorial hints; never include `markdown_content`, `generated_draft_content`, or prompt text
- [x] 3.3 Implement `build_generate_linkedin_draft_response()` with all required fields including `provider` always `"deepseek"` after valid body, `model` per nullability rules, non-null `source_content_sha256`, `generated_draft_content` (success only), and partial-failure case (`metadata_write_failed` with draft retained)
- [x] 3.4 Extend metadata tests for generate-linkedin-draft payload/response shapes and absence of secrets/content bodies

## 4. POST /generate-linkedin-draft endpoint

- [x] 4.1 Add Pydantic request model with `extra="forbid"`, required `source_relative_path` and `markdown_content` (strip-empty → 422), optional `source_content_sha256`, `title`, `slug_hint`, `tone`, `audience`, `variant`
- [x] 4.2 Wire authenticated `POST /generate-linkedin-draft` route using existing `require_api_key` dependency
- [x] 4.3 Orchestrate flow per design: validate body → resolve `source_content_sha256` (echo or compute, always non-null) → check metadata/runs → load DeepSeek settings (fail with `deepseek_config_invalid` if invalid) → check DeepSeek API key → check review dir → validate source path shape → call DeepSeek (only after pre-checks pass) → reuse `write_draft_file()` for persistence → write run metadata → return response with `provider: "deepseek"` always and `generated_draft_content` on success only
- [x] 4.4 Resolve `source_content_sha256`: echo request value unchanged when provided; otherwise compute lowercase SHA-256 of UTF-8 bytes of `markdown_content` exactly as received by the validated request model; always include non-null value in response and metadata after valid body
- [x] 4.5 Use `slug_hint` for filename; when absent and `variant` provided, use sanitized `variant` as filename slug segment
- [x] 4.6 Ensure endpoint does not re-read source blog file, does not move/modify blog posts, and does not call OpenAI
- [x] 4.7 Confirm `GET /health`, `POST /process-ready`, `POST /process-file`, and `POST /write-linkedin-draft` remain unchanged
- [x] 4.8 Add `tests/test_generate_linkedin_draft.py` covering auth, 422 on bad/extra fields, metadata/runs unavailable (`provider: "deepseek"`, `model: null`), invalid DeepSeek optional settings (`deepseek_config_invalid`), DeepSeek key missing (`provider: "deepseek"`, model from defaults), review dir unavailable, source path failures, mocked DeepSeek success (draft file + `generated_draft_content`), computed vs echoed `source_content_sha256`, DeepSeek error codes, draft collision, partial metadata failure, worker starts without DeepSeek key, and no secrets in responses

## 5. Documentation

- [x] 5.1 Update `README.md` with `POST /generate-linkedin-draft` description, DeepSeek environment variables, Bearer authentication, example success/failure JSON, n8n chain notes (`POST /process-file` → `POST /generate-linkedin-draft`)
- [x] 5.2 Update docker-compose example with optional DeepSeek env var comments

## 6. Validation

- [x] 6.1 Run full test suite (`pytest`) and ensure all tests pass
- [x] 6.2 Run `openspec validate add-deepseek-linkedin-draft-generation`
- [x] 6.3 Run `openspec validate --all`
- [ ] 6.4 Manual smoke test (optional): start worker with `DEEPSEEK_API_KEY`, call endpoint with sample payload after `POST /process-file` content, confirm draft under `linkedin-posts/review/` and metadata without content bodies
