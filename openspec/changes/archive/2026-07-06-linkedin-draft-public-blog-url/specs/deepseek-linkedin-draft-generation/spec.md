## MODIFIED Requirements

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
- optional `source_public_url` string field
- optional `topic_theme` string field

The worker MUST reject requests with a missing body, missing required fields, non-string required fields, empty `source_relative_path` after normalization, `markdown_content` that is empty or whitespace-only after stripping, invalid `source_public_url` when provided, or **any unexpected extra field** with HTTP `422`.

The request body MUST allow only these fields: `source_relative_path`, `markdown_content`, `source_content_sha256`, `title`, `slug_hint`, `tone`, `audience`, `variant`, `source_public_url`, `topic_theme`. The worker MUST reject extra fields (including `draft_relative_path`, `output_path`, `filename`, `target_path`, `draft_content`, `cta_style`, or any other unexpected field) via Pydantic `extra="forbid"` or equivalent.

When `source_public_url` is provided, it MUST be a non-empty string after stripping that parses as a URL with scheme `http` or `https` and a non-empty host (`netloc`). Schemes other than `http` or `https` MUST be rejected with HTTP `422`.

When `topic_theme` is provided, it MUST be a non-empty string after stripping. Whitespace-only `topic_theme` MUST be rejected with HTTP `422`.

Before validation, the worker SHALL normalize `source_relative_path` by stripping leading `./` and trailing slashes.

The worker MUST NOT accept any client-supplied output path field. The worker MUST NOT re-read the source blog post file from disk.

#### Scenario: Valid request body

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with body containing `source_relative_path` of `blog-posts/ready/my-post.md` and non-empty `markdown_content`
- **THEN** the worker proceeds with directory readiness checks and source path shape validation

#### Scenario: Valid request body with source_public_url

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid required fields and `source_public_url` of `https://silverman.pro/2026/07/06/my-post/`
- **THEN** the worker accepts the body and proceeds with directory readiness checks and source path shape validation

#### Scenario: Valid request body with topic_theme

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid required fields and `topic_theme` of `architecture`
- **THEN** the worker accepts the body and proceeds with directory readiness checks and source path shape validation

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

#### Scenario: Invalid source_public_url scheme

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with `source_public_url` of `javascript:alert(1)` or `file:///etc/passwd`
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Invalid source_public_url not a URL

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with `source_public_url` of `not-a-url`
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Empty source_public_url after strip

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with `source_public_url` of only whitespace
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Empty topic_theme after strip

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with `topic_theme` of only whitespace
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

#### Scenario: Backward compatible request without public URL fields

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid required fields and omits `source_public_url` and `topic_theme`
- **THEN** the worker accepts the body and behaves as before this change for prompt, metadata, and response shape regarding public URL fields

### Requirement: DeepSeek LinkedIn draft generation

When pre-checks pass and `DEEPSEEK_API_KEY` is configured, the worker SHALL call the DeepSeek OpenAI-compatible chat completions API at `{normalized_base_url}/chat/completions` to generate one LinkedIn draft from the submitted `markdown_content`.

The request MUST use system and user messages. The prompt MUST instruct the model to output only LinkedIn draft content—no JSON, no markdown fences, no explanations or preamble.

The generated draft MUST be professional, human, aligned with a senior software architecture audience, and derived from the provided blog Markdown. The worker MUST NOT instruct or accept output that fabricates facts, metrics, names, companies, or URLs not present in the input. The worker MUST NOT include hashtags in generated output for this change.

Optional request fields `title`, `tone`, `audience`, and `variant` MAY influence the prompt as editorial hints only.

When `source_public_url` is provided in the request, the user prompt MUST include the exact URL value and MUST instruct the model to:

- include that URL exactly once in the generated draft
- place it near the end as a natural call to action
- vary CTA wording naturally (for example "Read the full story here: {url}", "I wrote the full article here: {url}")
- when `topic_theme` is also provided, MAY use phrasing such as "Read the full {topic_theme} story here: {url}"
- not sound spammy
- not repeat the URL
- not invent, modify, or substitute a different URL
- not include hashtags

When `source_public_url` is omitted, the prompt MUST NOT include public blog URL or CTA URL instructions.

When `topic_theme` is provided without `source_public_url`, the prompt MAY include `topic_theme` as an editorial hint only and MUST NOT include public blog URL CTA instructions.

The worker MUST NOT store prompt text in run metadata or include it in HTTP responses.

#### Scenario: Successful DeepSeek generation

- **WHEN** DeepSeek returns non-empty message content after pre-checks pass
- **THEN** the worker uses the trimmed content as generated draft text for persistence

#### Scenario: Prompt includes public URL when provided

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid body and `source_public_url` of `https://silverman.pro/2026/07/06/my-post/` and pre-checks pass before DeepSeek is called
- **THEN** the DeepSeek user prompt includes that exact URL and instructions to use it once as a natural end CTA

#### Scenario: Prompt excludes public URL when omitted

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid body omitting `source_public_url` and pre-checks pass before DeepSeek is called
- **THEN** the DeepSeek user prompt does not include public blog URL or CTA URL instructions

#### Scenario: Prompt includes topic_theme when provided

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid body and `topic_theme` of `architecture` and pre-checks pass before DeepSeek is called
- **THEN** the DeepSeek user prompt includes the topic theme as an editorial or CTA hint as applicable

#### Scenario: Prompt allows varied CTA wording

- **WHEN** the worker builds the DeepSeek user prompt with `source_public_url` provided
- **THEN** the prompt instructs varied natural CTA wording and does not mandate one fixed phrase for every generation

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

### Requirement: Generate-linkedin-draft run metadata persistence

When `metadata/runs/` exists, is a directory, and is writable, each invocation of `POST /generate-linkedin-draft` with a valid request body SHALL create a run metadata JSON file under `metadata/runs/`.

When `metadata/runs/` is missing, not a directory, or not writable, the worker MUST NOT attempt to write run metadata.

The run identifier MUST use the same deterministic traceable format as other processing endpoints.

Run metadata MUST include at minimum: run id, trigger source (`POST /generate-linkedin-draft`), timestamps, run status, base path, provider (`deepseek`), model, normalized `source_relative_path`, non-null `source_content_sha256`, `draft_relative_path` (or null), `draft_content_sha256` (or null), `size_bytes` (or null), `draft_written`, optional `title`, `slug_hint`, `tone`, `audience`, and `variant` when provided, optional `source_public_url` and `topic_theme` when provided in the request, and errors if any.

Run metadata MUST NOT include `markdown_content`, `generated_draft_content`, prompt text, `SILVERMAN_BLOG_LINKEDIN_API_KEY`, `DEEPSEEK_API_KEY`, or submitted auth token values.

When `source_content_sha256` is provided in the request, run metadata MUST echo it unchanged. When not provided, run metadata MUST include the computed lowercase hexadecimal SHA-256 digest of the UTF-8 bytes of `markdown_content` exactly as received by the validated request model.

#### Scenario: Successful generation metadata written

- **WHEN** an authenticated `POST /generate-linkedin-draft` completes writing a draft with `metadata/runs/` writable
- **THEN** a JSON file is written to `metadata/runs/` named after the run id and contains provider, model, draft paths, hashes, and size without markdown or generated draft body text

#### Scenario: Metadata includes source_public_url when provided

- **WHEN** an authenticated `POST /generate-linkedin-draft` with valid body includes `source_public_url` and run metadata is written
- **THEN** the metadata file includes `source_public_url` with the same value as the request

#### Scenario: Metadata includes topic_theme when provided

- **WHEN** an authenticated `POST /generate-linkedin-draft` with valid body includes `topic_theme` and run metadata is written
- **THEN** the metadata file includes `topic_theme` with the same value as the request

#### Scenario: Metadata omits public URL fields when not provided

- **WHEN** an authenticated `POST /generate-linkedin-draft` with valid body omits `source_public_url` and `topic_theme` and run metadata is written
- **THEN** the metadata file does not include `source_public_url` or `topic_theme` keys

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

When `source_public_url` was provided in the request, the response MUST include `source_public_url` with the same value. When not provided, the response MUST NOT include a `source_public_url` key.

When `topic_theme` was provided in the request, the response MUST include `topic_theme` with the same value. When not provided, the response MUST NOT include a `topic_theme` key.

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

#### Scenario: Response echoes source_public_url when provided

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid body including `source_public_url` and any outcome after valid body validation
- **THEN** the response JSON includes `source_public_url` with the same value as the request

#### Scenario: Response omits source_public_url when not provided

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid body omitting `source_public_url` and any outcome after valid body validation
- **THEN** the response JSON does not include a `source_public_url` key

#### Scenario: Response echoes topic_theme when provided

- **WHEN** a client sends an authenticated `POST /generate-linkedin-draft` with valid body including `topic_theme` and any outcome after valid body validation
- **THEN** the response JSON includes `topic_theme` with the same value as the request

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

The worker SHALL include automated tests covering API key authentication, request body validation, DeepSeek configuration readiness, source path shape validation, review directory readiness, DeepSeek client error mapping, draft persistence reuse, run metadata creation, HTTP response shape including `generated_draft_content` on success only, public blog URL and topic theme handling, and failure modes.

#### Scenario: Authentication tests

- **WHEN** tests invoke `POST /generate-linkedin-draft` with missing, invalid, and valid Bearer tokens
- **THEN** tests verify `401` for unauthorized requests and successful processing for valid tokens

#### Scenario: Body validation tests

- **WHEN** tests invoke `POST /generate-linkedin-draft` with missing fields, empty `markdown_content`, invalid types, invalid `source_public_url`, and unexpected extra fields
- **THEN** tests verify HTTP `422` and that the generate-linkedin-draft response contract does not apply

#### Scenario: Valid source_public_url accepted

- **WHEN** tests invoke `POST /generate-linkedin-draft` with a valid `https` `source_public_url` and otherwise valid body
- **THEN** tests verify the request is accepted past body validation

#### Scenario: Invalid source_public_url rejected

- **WHEN** tests invoke `POST /generate-linkedin-draft` with invalid `source_public_url` values such as `not-a-url` or disallowed schemes
- **THEN** tests verify HTTP `422`

#### Scenario: Extra fields still rejected

- **WHEN** tests invoke `POST /generate-linkedin-draft` with unexpected extra fields including `cta_style`
- **THEN** tests verify HTTP `422`

#### Scenario: Prompt public URL tests

- **WHEN** tests build chat messages with and without `source_public_url`
- **THEN** tests verify the URL appears in the user prompt when provided, is absent when omitted, and the prompt instructs single-use natural CTA with varied wording

#### Scenario: Prompt topic_theme tests

- **WHEN** tests build chat messages with `topic_theme` provided
- **THEN** tests verify `topic_theme` appears in the user prompt when provided

#### Scenario: Metadata public URL fields tests

- **WHEN** tests invoke `POST /generate-linkedin-draft` with `source_public_url` and/or `topic_theme` and metadata is written
- **THEN** tests verify metadata includes provided fields and excludes `markdown_content` and `generated_draft_content`

#### Scenario: Backward compatibility tests

- **WHEN** tests invoke `POST /generate-linkedin-draft` without `source_public_url` or `topic_theme` using existing valid fixtures
- **THEN** tests verify generation still succeeds and response/metadata omit the new keys

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
