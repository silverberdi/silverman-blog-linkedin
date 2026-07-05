# deepseek-linkedin-draft-generation

## Purpose

Authenticated `POST /generate-linkedin-draft` endpoint for generating one LinkedIn review draft from supplied blog Markdown using the DeepSeek chat completions API, persisting the draft under `linkedin-posts/review/` via existing draft writer behavior, writing run metadata under `metadata/runs/`, and returning structured JSON for n8n branching—without OpenAI, publishing, or mutating source blog files.

## Requirements

### Requirement: DeepSeek environment configuration

The worker SHALL support DeepSeek configuration through environment variables. DeepSeek configuration MUST NOT be required at worker startup. The worker MUST start successfully when `DEEPSEEK_API_KEY` is unset.

The following variables MUST be supported:

| Variable | Required at startup | Default |
|----------|---------------------|---------|
| `DEEPSEEK_API_KEY` | No | — |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | No | `deepseek-v4-flash` |
| `DEEPSEEK_TIMEOUT_SECONDS` | No | `60` |
| `DEEPSEEK_MAX_OUTPUT_TOKENS` | No | `1024` |

Model names MUST be treated as operational configuration. The worker MUST NOT hardcode legacy model names in application logic beyond safe defaults in configuration loading.

`DEEPSEEK_API_KEY` MUST be required only when handling `POST /generate-linkedin-draft`. It MUST NOT be required for `GET /health`, `POST /process-ready`, `POST /process-file`, or `POST /write-linkedin-draft`.

When loading DeepSeek settings at request time for `POST /generate-linkedin-draft`:

- `DEEPSEEK_TIMEOUT_SECONDS` MUST parse as a positive number (integer or float).
- `DEEPSEEK_MAX_OUTPUT_TOKENS` MUST parse as a positive integer.
- Invalid optional DeepSeek settings MUST cause the endpoint to return HTTP `200` with `status` failed, `errors` containing `deepseek_config_invalid`, no DeepSeek call, and no draft write. When `metadata/runs/` is writable, failed run metadata MUST be written.
- Invalid optional DeepSeek settings MUST NOT prevent worker startup.

For direct `httpx` usage, the chat completions URL MUST be constructed as `{normalized_base_url}/chat/completions` where `normalized_base_url` is `DEEPSEEK_BASE_URL` with any trailing slash removed. The worker MUST NOT append `/v1` automatically. If an operator sets `DEEPSEEK_BASE_URL` to a custom compatible gateway that already includes a path prefix, the worker MUST still append `/chat/completions` after trimming the trailing slash.

#### Scenario: Worker starts without DeepSeek API key

- **WHEN** the worker starts with valid foundation configuration and `DEEPSEEK_API_KEY` is unset
- **THEN** the HTTP server starts and accepts requests on configured endpoints other than requiring DeepSeek at startup

#### Scenario: Default DeepSeek base URL and model

- **WHEN** `DEEPSEEK_BASE_URL` and `DEEPSEEK_MODEL` are unset and `POST /generate-linkedin-draft` invokes DeepSeek
- **THEN** the worker uses base URL `https://api.deepseek.com`, requests `https://api.deepseek.com/chat/completions`, and model `deepseek-v4-flash`

#### Scenario: Trailing slash stripped from base URL

- **WHEN** `DEEPSEEK_BASE_URL` is `https://api.deepseek.com/` and `POST /generate-linkedin-draft` invokes DeepSeek
- **THEN** the worker requests `https://api.deepseek.com/chat/completions`

#### Scenario: Custom gateway base URL with path prefix

- **WHEN** `DEEPSEEK_BASE_URL` is `https://gateway.example.com/v1` and `POST /generate-linkedin-draft` invokes DeepSeek
- **THEN** the worker requests `https://gateway.example.com/v1/chat/completions` without inserting an additional `/v1` segment

#### Scenario: DeepSeek settings override via environment

- **WHEN** `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, `DEEPSEEK_TIMEOUT_SECONDS`, and `DEEPSEEK_MAX_OUTPUT_TOKENS` are set
- **THEN** `POST /generate-linkedin-draft` uses the configured values for the DeepSeek request

#### Scenario: DeepSeek API key not exposed

- **WHEN** the worker loads or uses DeepSeek configuration
- **THEN** `DEEPSEEK_API_KEY` MUST NOT appear in HTTP responses, run metadata, or info-level logs

#### Scenario: Invalid optional DeepSeek timeout

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with a valid body, `metadata/runs/` is writable, and `DEEPSEEK_TIMEOUT_SECONDS` is zero, negative, or non-numeric
- **THEN** the worker does not call DeepSeek, does not write a draft file, writes failed run metadata, and returns JSON with `status` failed, `provider` `"deepseek"`, `model` null, and `errors` containing `deepseek_config_invalid`

#### Scenario: Invalid optional DeepSeek max output tokens

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with a valid body, `metadata/runs/` is writable, and `DEEPSEEK_MAX_OUTPUT_TOKENS` is zero, negative, or non-integer
- **THEN** the worker does not call DeepSeek, does not write a draft file, writes failed run metadata, and returns JSON with `status` failed, `provider` `"deepseek"`, `model` null, and `errors` containing `deepseek_config_invalid`

#### Scenario: Worker starts with invalid optional DeepSeek settings

- **WHEN** the worker starts with valid foundation configuration and invalid optional DeepSeek settings such as `DEEPSEEK_TIMEOUT_SECONDS=abc`
- **THEN** the HTTP server starts successfully and `GET /health` remains functional

### Requirement: API key authentication for generate-linkedin-draft

The worker SHALL require valid API key authentication for `POST /generate-linkedin-draft` using the configured `SILVERMAN_BLOG_LINKEDIN_API_KEY`.

The client MUST send the key in the `Authorization` header as a Bearer token: `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>`.

#### Scenario: Valid API key for generate-linkedin-draft

- **WHEN** a client sends `POST /generate-linkedin-draft` with a correct Bearer token matching `SILVERMAN_BLOG_LINKEDIN_API_KEY`
- **THEN** the worker proceeds with request body validation and pre-generation checks

#### Scenario: Missing Authorization header

- **WHEN** a client sends `POST /generate-linkedin-draft` without an `Authorization` header
- **THEN** the worker responds with HTTP `401` and a JSON body that does not expose secret values

#### Scenario: Invalid API key

- **WHEN** a client sends `POST /generate-linkedin-draft` with an incorrect Bearer token
- **THEN** the worker responds with HTTP `401` and a JSON body that does not expose the expected key or configured secret

#### Scenario: Auth failure does not leak secrets

- **WHEN** authentication fails for `POST /generate-linkedin-draft`
- **THEN** the response and logs MUST NOT include `SILVERMAN_BLOG_LINKEDIN_API_KEY`, `DEEPSEEK_API_KEY`, or the submitted token value

### Requirement: Generate-linkedin-draft request body

The worker SHALL accept a JSON request body on `POST /generate-linkedin-draft` with:

- required `source_relative_path` string field
- required `markdown_content` string field
- optional `source_content_sha256` string field
- optional `title` string field
- optional `slug_hint` string field
- optional `tone` string field
- optional `audience` string field
- optional `variant` string field

The worker MUST reject requests with a missing body, missing required fields, non-string required fields, empty `source_relative_path` after normalization, `markdown_content` that is empty or whitespace-only after stripping, or **any unexpected extra field** with HTTP `422`.

The request body MUST allow only these fields: `source_relative_path`, `markdown_content`, `source_content_sha256`, `title`, `slug_hint`, `tone`, `audience`, `variant`. The worker MUST reject extra fields (including `draft_relative_path`, `output_path`, `filename`, `target_path`, `draft_content`, or any other unexpected field) via Pydantic `extra="forbid"` or equivalent.

Before validation, the worker SHALL normalize `source_relative_path` by stripping leading `./` and trailing slashes.

The worker MUST NOT accept any client-supplied output path field. The worker MUST NOT re-read the source blog post file from disk.

#### Scenario: Valid request body

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with body containing `source_relative_path` of `blog-posts/ready/my-post.md` and non-empty `markdown_content`
- **THEN** the worker proceeds with directory readiness checks and source path shape validation

#### Scenario: Missing source_relative_path

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with body missing `source_relative_path`
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Missing markdown_content

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with body missing `markdown_content`
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Empty markdown_content after strip

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with `markdown_content` of only whitespace
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Empty source_relative_path

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with `source_relative_path` of `""`
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Body validation failure has no generate-linkedin-draft contract

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` that fails FastAPI/Pydantic body validation
- **THEN** the worker responds with HTTP `422` and the generate-linkedin-draft response/metadata contract does not apply

#### Scenario: Extra output path field rejected

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with body containing `draft_relative_path`, `output_path`, `filename`, `target_path`, or any other unexpected field
- **THEN** the worker responds with HTTP `422` and the generate-linkedin-draft response/metadata contract does not apply

#### Scenario: Any unexpected extra field rejected

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with any field not in the allowed set
- **THEN** the worker responds with HTTP `422` via Pydantic extra-field rejection and the generate-linkedin-draft response/metadata contract does not apply

### Requirement: Source content hash resolution for generate-linkedin-draft

After request body validation passes, the worker SHALL resolve `source_content_sha256` before any DeepSeek call or draft write.

If `source_content_sha256` is provided in the request, the worker MUST echo it unchanged in the HTTP response and run metadata.

If `source_content_sha256` is missing or null, the worker MUST compute it as the lowercase hexadecimal SHA-256 digest of the UTF-8 bytes of `markdown_content` exactly as received by the validated request model.

After valid body validation, the HTTP response and run metadata (when written) MUST include a non-null `source_content_sha256`.

Run metadata MUST NOT include `markdown_content`.

#### Scenario: Echo provided source_content_sha256

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid body and `source_content_sha256` of `abc123`
- **THEN** the HTTP response and written run metadata include `source_content_sha256` of `abc123` unchanged

#### Scenario: Compute source_content_sha256 when omitted

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid body omitting `source_content_sha256` and `markdown_content` of known UTF-8 text
- **THEN** the HTTP response and written run metadata include non-null `source_content_sha256` equal to the lowercase SHA-256 digest of the UTF-8 bytes of that `markdown_content`

#### Scenario: source_content_sha256 always non-null after valid body

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid body and any outcome after body validation
- **THEN** the HTTP response includes non-null `source_content_sha256`

### Requirement: Metadata directory readiness for generate-linkedin-draft

Before writing run metadata or calling DeepSeek, the worker SHALL verify that `metadata/runs/` under the configured base path exists, is a directory, and is writable.

If `metadata/runs/` is missing, not a directory, or not writable, the worker MUST NOT call DeepSeek and MUST NOT write a draft file and MUST NOT attempt to write run metadata.

#### Scenario: metadata/runs missing or not a directory

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with a valid body and `metadata/runs/` does not exist or is not a directory
- **THEN** the worker returns JSON with `status` failed, `metadata_written` false, `metadata_path` null, `draft_written` false, `draft_relative_path` null, non-null `source_content_sha256`, `provider` `"deepseek"`, `model` null, and `errors` containing `metadata_runs_not_ready`

#### Scenario: metadata/runs not writable

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with a valid body and `metadata/runs/` exists as a directory but is not writable
- **THEN** the worker returns JSON with `status` failed, `metadata_written` false, `metadata_path` null, `draft_written` false, `draft_relative_path` null, non-null `source_content_sha256`, `provider` `"deepseek"`, `model` null, and `errors` containing `metadata_runs_not_writable`

### Requirement: DeepSeek API key readiness for generate-linkedin-draft

Before calling DeepSeek or writing a draft file, the worker SHALL verify that `DEEPSEEK_API_KEY` is configured (non-empty) for the request.

If `DEEPSEEK_API_KEY` is missing or empty, the worker MUST NOT call DeepSeek and MUST NOT write a draft file. When `metadata/runs/` is writable, the worker SHALL write failed run metadata documenting the missing configuration.

#### Scenario: DeepSeek API key missing

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with a valid body, `metadata/runs/` is writable, optional DeepSeek settings are valid, and `DEEPSEEK_API_KEY` is unset or empty
- **THEN** the worker does not call DeepSeek, does not write a draft file, writes failed run metadata, and returns JSON with `status` failed, `draft_written` false, `metadata_written` true, a relative `metadata_path`, non-null `source_content_sha256`, `provider` `"deepseek"`, non-null `model` reflecting configured or default DeepSeek model, and `errors` containing `deepseek_api_key_missing`

### Requirement: Review directory readiness for generate-linkedin-draft

Before calling DeepSeek or writing a draft file, the worker SHALL verify that `linkedin-posts/review/` under the configured base path exists, is a directory, and is writable.

If `linkedin-posts/review/` is missing, not a directory, or not writable, the worker MUST NOT call DeepSeek and MUST NOT write a draft file. When `metadata/runs/` is writable, the contract SHALL write failed run metadata documenting the review directory failure.

#### Scenario: linkedin-posts/review missing or not a directory

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with a valid body, `metadata/runs/` is writable, and `linkedin-posts/review/` does not exist or is not a directory
- **THEN** the worker does not call DeepSeek, does not write a draft file, writes failed run metadata, and returns JSON with `status` failed, `draft_written` false, `draft_relative_path` null, `metadata_written` true, a relative `metadata_path`, and `errors` containing `review_dir_not_ready`

#### Scenario: linkedin-posts/review not writable

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with a valid body, `metadata/runs/` is writable, and `linkedin-posts/review/` exists as a directory but is not writable
- **THEN** the worker does not call DeepSeek, does not write a draft file, writes failed run metadata, and returns JSON with `status` failed, `draft_written` false, `draft_relative_path` null, `metadata_written` true, a relative `metadata_path`, and `errors` containing `review_dir_not_writable`

### Requirement: Source path shape validation for generate-linkedin-draft

The worker SHALL validate the request `source_relative_path` shape before calling DeepSeek. The worker MUST NOT re-read or verify the source blog post file on disk.

The path MUST be relative (not absolute). The path MUST NOT contain path traversal segments (`..`). The path MUST start with `blog-posts/ready/` followed by exactly one filename segment (direct child of `blog-posts/ready/`). The filename MUST have a `.md` extension (case-insensitive). The resolved absolute path MUST remain inside `blog-posts/ready/` relative to the configured base path.

If source path shape validation fails, the worker MUST NOT call DeepSeek and MUST NOT write a draft file. When `metadata/runs/` is writable, the worker SHALL write failed run metadata.

#### Scenario: Valid source path shape

- **WHEN** a client sends `source_relative_path` of `blog-posts/ready/my-post.md` and directory pre-checks pass
- **THEN** source path shape validation succeeds and the worker proceeds to DeepSeek generation

#### Scenario: Absolute path rejected

- **WHEN** a client sends `source_relative_path` that is an absolute path
- **THEN** source path shape validation fails with error code `absolute_path`, the worker does not call DeepSeek, does not write a draft file, and when `metadata/runs/` is writable the response and metadata include the normalized rejected `source_relative_path` with `draft_written` false and `draft_relative_path` null

#### Scenario: Path traversal rejected

- **WHEN** a client sends `source_relative_path` containing `..` segments
- **THEN** source path shape validation fails with error code `path_traversal` and the worker does not call DeepSeek or write a draft file

#### Scenario: Path outside ready rejected

- **WHEN** a client sends `source_relative_path` that does not start with `blog-posts/ready/`
- **THEN** source path shape validation fails with error code `path_outside_ready` and the worker does not call DeepSeek or write a draft file

#### Scenario: Non-markdown extension rejected

- **WHEN** a client sends `source_relative_path` ending in a non-`.md` extension
- **THEN** source path shape validation fails with error code `extension_not_md` and the worker does not call DeepSeek or write a draft file

#### Scenario: Subdirectory path rejected

- **WHEN** a client sends `source_relative_path` with nested segments under ready (for example `blog-posts/ready/subdir/post.md`)
- **THEN** source path shape validation fails with error code `path_not_direct_child` and the worker does not call DeepSeek or write a draft file

#### Scenario: Resolved path confinement

- **WHEN** the worker resolves the source path for shape validation
- **THEN** the resolved path MUST remain under `blog-posts/ready/` relative to the configured base path

### Requirement: DeepSeek LinkedIn draft generation

When pre-checks pass and `DEEPSEEK_API_KEY` is configured, the worker SHALL call the DeepSeek OpenAI-compatible chat completions API at `{normalized_base_url}/chat/completions` to generate one LinkedIn draft from the submitted `markdown_content`.

The request MUST use system and user messages. The prompt MUST instruct the model to output only LinkedIn draft content—no JSON, no markdown fences, no explanations or preamble.

The generated draft MUST be professional, human, aligned with a senior software architecture audience, and derived from the provided blog Markdown. The worker MUST NOT instruct or accept output that fabricates facts, metrics, names, companies, or URLs not present in the input. The worker MUST NOT include hashtags in generated output for this change.

Optional request fields `title`, `tone`, `audience`, and `variant` MAY influence the prompt as editorial hints only.

The worker MUST NOT store prompt text in run metadata or include it in HTTP responses.

#### Scenario: Successful DeepSeek generation

- **WHEN** DeepSeek returns non-empty message content after pre-checks pass
- **THEN** the worker uses the trimmed content as generated draft text for persistence

#### Scenario: DeepSeek auth failure

- **WHEN** DeepSeek responds with HTTP `401` or `403`
- **THEN** the worker does not write a draft file, writes failed run metadata when `metadata/runs/` is writable, and returns JSON with `status` failed, `draft_written` false, and `errors` containing `deepseek_auth_failed`

#### Scenario: DeepSeek insufficient balance

- **WHEN** DeepSeek responds with HTTP `402`
- **THEN** the worker does not write a draft file, writes failed run metadata when writable, and returns JSON with `status` failed and `errors` containing `deepseek_insufficient_balance`

#### Scenario: DeepSeek invalid request

- **WHEN** DeepSeek responds with HTTP `422`
- **THEN** the worker does not write a draft file, writes failed run metadata when writable, and returns JSON with `status` failed and `errors` containing `deepseek_invalid_request`

#### Scenario: DeepSeek rate limited

- **WHEN** DeepSeek responds with HTTP `429`
- **THEN** the worker does not write a draft file, writes failed run metadata when writable, and returns JSON with `status` failed and `errors` containing `deepseek_rate_limited`

#### Scenario: DeepSeek unavailable

- **WHEN** DeepSeek responds with HTTP `500` or `503`, or another non-mapped provider error
- **THEN** the worker does not write a draft file, writes failed run metadata when writable, and returns JSON with `status` failed and `errors` containing `deepseek_unavailable`

#### Scenario: DeepSeek timeout

- **WHEN** the DeepSeek request exceeds the configured timeout
- **THEN** the worker does not write a draft file, writes failed run metadata when writable, and returns JSON with `status` failed and `errors` containing `deepseek_timeout`

#### Scenario: DeepSeek empty response

- **WHEN** DeepSeek returns a response with empty or whitespace-only message content
- **THEN** the worker does not write a draft file, writes failed run metadata when writable, and returns JSON with `status` failed and `errors` containing `deepseek_empty_response`

#### Scenario: Generate does not call OpenAI

- **WHEN** a client sends `POST /generate-linkedin-draft` with any outcome
- **THEN** the worker MUST NOT call OpenAI, ChatGPT, or local LLM providers

### Requirement: Generated draft persistence via draft writer

When DeepSeek returns valid non-empty draft content, the worker SHALL persist the draft by reusing the same draft file writing behavior defined for linkedin-draft-review-writing: server-generated path under `linkedin-posts/review/`, exclusive creation with collision retries, no client output path, no overwrite, optional trailing newline normalization, and computation of `draft_content_sha256` and `size_bytes` from bytes written.

The worker MUST NOT duplicate draft filename generation or exclusive-write logic outside the shared draft writer module.

#### Scenario: Draft persisted under review

- **WHEN** DeepSeek generation succeeds and draft writing succeeds
- **THEN** a new Markdown file is created under `linkedin-posts/review/` containing the generated draft text

#### Scenario: Draft path collision

- **WHEN** all allowed exclusive-creation collision retries fail
- **THEN** the worker does not overwrite an existing file, writes failed run metadata when `metadata/runs/` is writable, and returns JSON with `status` failed, `draft_written` false, `draft_relative_path` null, and `errors` containing `draft_path_collision`

#### Scenario: No front matter in draft file

- **WHEN** a generated draft file is written successfully
- **THEN** the file contains only the generated draft body without YAML front matter added by the worker

### Requirement: Generate-linkedin-draft run metadata persistence

When `metadata/runs/` exists, is a directory, and is writable, each invocation of `POST /generate-linkedin-draft` with a valid request body SHALL create a run metadata JSON file under `metadata/runs/`.

When `metadata/runs/` is missing, not a directory, or not writable, the worker MUST NOT attempt to write run metadata.

The run identifier MUST use the same deterministic traceable format as other processing endpoints.

Run metadata MUST include at minimum: run id, trigger source (`POST /generate-linkedin-draft`), timestamps, run status, base path, provider (`deepseek`), model, normalized `source_relative_path`, non-null `source_content_sha256`, `draft_relative_path` (or null), `draft_content_sha256` (or null), `size_bytes` (or null), `draft_written`, optional `title`, `slug_hint`, `tone`, `audience`, and `variant` when provided, and errors if any.

Run metadata MUST NOT include `markdown_content`, `generated_draft_content`, prompt text, `SILVERMAN_BLOG_LINKEDIN_API_KEY`, `DEEPSEEK_API_KEY`, or submitted auth token values.

When `source_content_sha256` is provided in the request, run metadata MUST echo it unchanged. When not provided, run metadata MUST include the computed lowercase hexadecimal SHA-256 digest of the UTF-8 bytes of `markdown_content` exactly as received by the validated request model.

#### Scenario: Successful generation metadata written

- **WHEN** an authenticated `POST /generate-linkedin-draft` completes writing a draft with `metadata/runs/` writable
- **THEN** a JSON file is written to `metadata/runs/` named after the run id and contains provider, model, draft paths, hashes, and size without markdown or generated draft body text

#### Scenario: Failed DeepSeek metadata written

- **WHEN** an authenticated `POST /generate-linkedin-draft` fails due to DeepSeek error and `metadata/runs/` is writable
- **THEN** a run metadata JSON file is written documenting the failed run with `draft_written` false and null draft path fields

#### Scenario: Metadata directory unavailable

- **WHEN** an authenticated `POST /generate-linkedin-draft` is invoked and `metadata/runs/` is missing, not a directory, or not writable
- **THEN** no run metadata file is written and the response reports `metadata_written` false and `metadata_path` null

#### Scenario: Metadata excludes content and secrets

- **WHEN** run metadata is written for any `POST /generate-linkedin-draft` invocation
- **THEN** the metadata file MUST NOT contain `markdown_content`, `generated_draft_content`, prompt text, API keys, or submitted auth tokens

#### Scenario: Metadata write failed after successful draft

- **WHEN** a draft file is successfully written but run metadata persistence fails afterward
- **THEN** no run metadata file is created, the draft file is not deleted or rolled back, and the response reports `status` failed, `draft_written` true, populated `draft_relative_path`, `draft_content_sha256`, and `size_bytes`, `metadata_written` false, `metadata_path` null, and `errors` containing `metadata_write_failed`

### Requirement: Generate-linkedin-draft HTTP response

The worker SHALL expose `POST /generate-linkedin-draft` returning structured JSON suitable for n8n branching when the request is authenticated and body validation passes.

The response MUST include: `run_id`, `status`, `metadata_written`, `metadata_path`, `draft_written`, `draft_relative_path`, `source_relative_path`, `source_content_sha256`, `draft_content_sha256`, `size_bytes`, `model`, `provider`, and `errors`.

When run metadata is written, `metadata_path` MUST be the relative path `metadata/runs/{run_id}.json`. When run metadata is not written, `metadata_path` MUST be JSON `null`.

`source_relative_path` MUST be the normalized request value and MUST NOT be JSON `null` after valid body validation.

`source_content_sha256` MUST be non-null after valid body validation. When provided in the request it MUST be echoed unchanged; when omitted it MUST be the computed lowercase SHA-256 of UTF-8 `markdown_content` bytes exactly as received by the validated request model.

`provider` MUST be `"deepseek"` for every HTTP response after valid body validation, including pre-check failures where DeepSeek is not called.

`model` MUST be the configured or default DeepSeek model name when DeepSeek settings are loaded successfully at request time. `model` MAY be JSON `null` only when the endpoint fails before DeepSeek settings are loaded (for example `metadata/runs` unavailable) or when optional DeepSeek settings are invalid (`deepseek_config_invalid`) preventing model resolution.

`draft_relative_path`, `draft_content_sha256`, and `size_bytes` MUST be JSON `null` unless a draft file was successfully written.

On successful draft write and successful metadata write, `status` MUST be `completed`, `draft_written` MUST be true, `metadata_written` MUST be true, `draft_relative_path` MUST be populated, and `generated_draft_content` MUST contain the generated LinkedIn draft text.

On failure outcomes after valid body validation, `status` MUST be `failed`, `generated_draft_content` MUST be JSON `null` or absent, and `errors` MUST contain applicable error codes.

On partial failure where the draft file was written but run metadata persistence failed, `status` MUST be `failed`, `draft_written` MUST be true, populated draft path and hash fields, `metadata_written` MUST be false, `metadata_path` MUST be null, `generated_draft_content` MUST be JSON `null` or absent, and `errors` MUST contain `metadata_write_failed`. The worker MUST NOT delete or roll back the already-written draft file.

The endpoint MUST NOT move or modify source blog post files. It MUST NOT publish to LinkedIn or GitHub.

#### Scenario: Completed generation with draft and metadata

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid body and all checks and DeepSeek generation pass
- **THEN** the response is JSON with `status` completed, `draft_written` true, `metadata_written` true, a relative `metadata_path`, populated draft fields, `provider` `"deepseek"`, non-null `model`, non-null `generated_draft_content`, and HTTP `200`

#### Scenario: Failed source path shape with metadata written

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with an invalid source path shape and `metadata/runs/` is writable
- **THEN** the response is JSON with `status` failed, `draft_written` false, null draft fields, `generated_draft_content` null or absent, `metadata_written` true, normalized `source_relative_path`, non-null `source_content_sha256`, `provider` `"deepseek"`, non-null `model`, and HTTP `200`

#### Scenario: DeepSeek API key missing response

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid body, optional DeepSeek settings are valid, and `DEEPSEEK_API_KEY` is unset
- **THEN** the response is JSON with `status` failed, `draft_written` false, non-null `source_content_sha256`, `provider` `"deepseek"`, non-null `model` reflecting configured or default DeepSeek model, `errors` containing `deepseek_api_key_missing`, and HTTP `200`

#### Scenario: Metadata directory unavailable

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` and `metadata/runs/` is missing, not a directory, or not writable
- **THEN** the response is JSON with `status` failed, `metadata_written` false, `metadata_path` null, `draft_written` false, `draft_relative_path` null, normalized `source_relative_path`, non-null `source_content_sha256`, null `draft_content_sha256` and `size_bytes`, `provider` `"deepseek"`, `model` null, and HTTP `200`

#### Scenario: Partial failure draft written metadata not written

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft`, the draft file is successfully created, and run metadata writing fails afterward
- **THEN** the response is JSON with `status` failed, `draft_written` true, populated draft path and hashes, `metadata_written` false, `metadata_path` null, `generated_draft_content` null or absent, `errors` containing `metadata_write_failed`, and HTTP `200`, and the draft file remains on disk unchanged

#### Scenario: Generate does not modify source blog files

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft`
- **THEN** the worker MUST NOT move, delete, or modify files under `blog-posts/ready/`, `blog-posts/processed/`, or `blog-posts/error/`

#### Scenario: Generate does not expose secrets

- **WHEN** a client sends `POST /generate-linkedin-draft` with any outcome
- **THEN** the JSON response MUST NOT include `SILVERMAN_BLOG_LINKEDIN_API_KEY`, `DEEPSEEK_API_KEY`, or other secret values

#### Scenario: Existing endpoints unchanged

- **WHEN** a client sends `GET /health`, `POST /process-ready`, `POST /process-file`, or `POST /write-linkedin-draft`
- **THEN** the worker responds as defined by the worker-foundation, ready-blog-post-processing, blog-post-file-processing, and linkedin-draft-review-writing specs without requiring changes to those endpoints

### Requirement: Generate-linkedin-draft tests

The worker SHALL include automated tests covering API key authentication, request body validation, DeepSeek configuration readiness, source path shape validation, review directory readiness, DeepSeek client error mapping, draft persistence reuse, run metadata creation, HTTP response shape including `generated_draft_content` on success only, and failure modes.

#### Scenario: Authentication tests

- **WHEN** tests invoke `POST /generate-linkedin-draft` with missing, invalid, and valid Bearer tokens
- **THEN** tests verify `401` for unauthorized requests and successful processing for valid tokens

#### Scenario: Body validation tests

- **WHEN** tests invoke `POST /generate-linkedin-draft` with missing fields, empty `markdown_content`, invalid types, and unexpected extra fields
- **THEN** tests verify HTTP `422` and that the generate-linkedin-draft response contract does not apply

#### Scenario: DeepSeek API key missing tests

- **WHEN** tests invoke `POST /generate-linkedin-draft` without `DEEPSEEK_API_KEY` configured but with otherwise valid optional DeepSeek settings
- **THEN** tests verify no DeepSeek call, no draft file, failed metadata when writable, `deepseek_api_key_missing` error, `provider` `"deepseek"`, and non-null `model` from defaults

#### Scenario: Invalid DeepSeek optional settings tests

- **WHEN** tests invoke `POST /generate-linkedin-draft` with invalid `DEEPSEEK_TIMEOUT_SECONDS` or `DEEPSEEK_MAX_OUTPUT_TOKENS`
- **THEN** tests verify no DeepSeek call, no draft file, failed metadata when writable, `deepseek_config_invalid` error, `provider` `"deepseek"`, and `model` null

#### Scenario: source_content_sha256 resolution tests

- **WHEN** tests invoke `POST /generate-linkedin-draft` with and without `source_content_sha256` in the request body
- **THEN** tests verify echoed value when provided and computed SHA-256 of UTF-8 `markdown_content` when omitted, always non-null in response and metadata after valid body

#### Scenario: DeepSeek error mapping tests

- **WHEN** tests simulate DeepSeek HTTP responses for auth failure, rate limit, timeout, and empty content
- **THEN** tests verify appropriate error codes, no draft write, and failed metadata when writable

#### Scenario: Successful generation tests

- **WHEN** tests invoke `POST /generate-linkedin-draft` with mocked DeepSeek returning draft text
- **THEN** tests verify draft file under `linkedin-posts/review/`, metadata without full content, response includes `generated_draft_content`, and `provider` is `deepseek`

#### Scenario: Metadata write failure after draft tests

- **WHEN** tests simulate successful draft write followed by metadata persistence failure
- **THEN** tests verify `status` failed, `draft_written` true, `metadata_written` false, `metadata_write_failed` error, draft file retained, and no `generated_draft_content` in response

#### Scenario: Worker starts without DeepSeek key tests

- **WHEN** tests start the worker without `DEEPSEEK_API_KEY`
- **THEN** tests verify `GET /health` and other endpoints remain functional
