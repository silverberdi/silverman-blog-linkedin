## ADDED Requirements

### Requirement: API key authentication for write-linkedin-draft

The worker SHALL require valid API key authentication for `POST /write-linkedin-draft` using the configured `SILVERMAN_BLOG_LINKEDIN_API_KEY`.

The client MUST send the key in the `Authorization` header as a Bearer token: `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>`.

#### Scenario: Valid API key for write-linkedin-draft

- **WHEN** a client sends `POST /write-linkedin-draft` with a correct Bearer token matching `SILVERMAN_BLOG_LINKEDIN_API_KEY`
- **THEN** the worker proceeds with request body validation and targeted directory readiness checks before any draft write

#### Scenario: Missing Authorization header

- **WHEN** a client sends `POST /write-linkedin-draft` without an `Authorization` header
- **THEN** the worker responds with HTTP `401` and a JSON body that does not expose secret values

#### Scenario: Invalid API key

- **WHEN** a client sends `POST /write-linkedin-draft` with an incorrect Bearer token
- **THEN** the worker responds with HTTP `401` and a JSON body that does not expose the expected key or configured secret

#### Scenario: Auth failure does not leak secrets

- **WHEN** authentication fails for `POST /write-linkedin-draft`
- **THEN** the response and logs MUST NOT include `SILVERMAN_BLOG_LINKEDIN_API_KEY` or the submitted token value

### Requirement: Write-linkedin-draft request body

The worker SHALL accept a JSON request body on `POST /write-linkedin-draft` with:

- required `source_relative_path` string field
- required `draft_content` string field
- optional `source_content_sha256` string field
- optional `title` string field
- optional `slug_hint` string field

The worker MUST reject requests with a missing body, missing required fields, non-string required fields, empty `source_relative_path` after normalization, `draft_content` that is empty or whitespace-only after stripping, or **any unexpected extra field** with HTTP `422`.

The request body MUST allow only these fields: `source_relative_path`, `draft_content`, `source_content_sha256`, `title`, `slug_hint`. The worker MUST reject extra fields (including `draft_relative_path`, `output_path`, `filename`, `target_path`, or any other unexpected field) via Pydantic `extra="forbid"` or equivalent.

Before validation, the worker SHALL normalize `source_relative_path` by stripping leading `./` and trailing slashes.

The worker MUST NOT accept any client-supplied output path field for determining where to write the draft file.

#### Scenario: Valid request body

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with body containing `source_relative_path` of `blog-posts/ready/my-post.md` and non-empty `draft_content`
- **THEN** the worker proceeds with directory readiness checks and source path shape validation

#### Scenario: Missing source_relative_path

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with body missing `source_relative_path`
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Missing draft_content

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with body missing `draft_content`
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Empty draft_content after strip

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with `draft_content` of only whitespace
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Empty source_relative_path

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with `source_relative_path` of `""`
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Body validation failure has no write-linkedin-draft contract

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` that fails FastAPI/Pydantic body validation
- **THEN** the worker responds with HTTP `422` and the write-linkedin-draft response/metadata contract does not apply

#### Scenario: Extra output path field rejected

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with body containing `draft_relative_path`, `output_path`, `filename`, `target_path`, or any other unexpected field
- **THEN** the worker responds with HTTP `422` and the write-linkedin-draft response/metadata contract does not apply

#### Scenario: Any unexpected extra field rejected

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with any field not in the allowed set (`source_relative_path`, `draft_content`, `source_content_sha256`, `title`, `slug_hint`)
- **THEN** the worker responds with HTTP `422` via Pydantic extra-field rejection and the write-linkedin-draft response/metadata contract does not apply

### Requirement: Metadata directory readiness for write-linkedin-draft

Before writing run metadata or a draft file, the worker SHALL verify that `metadata/runs/` under the configured base path exists, is a directory, and is writable.

If `metadata/runs/` is missing, not a directory, or not writable, the worker MUST NOT write a draft file and MUST NOT attempt to write run metadata.

#### Scenario: metadata/runs missing or not a directory

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with a valid body and `metadata/runs/` does not exist or is not a directory
- **THEN** the worker returns JSON with `status` failed, `metadata_written` false, `metadata_path` null, `draft_written` false, `draft_relative_path` null, and `errors` containing `metadata_runs_not_ready`

#### Scenario: metadata/runs not writable

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with a valid body and `metadata/runs/` exists as a directory but is not writable
- **THEN** the worker returns JSON with `status` failed, `metadata_written` false, `metadata_path` null, `draft_written` false, `draft_relative_path` null, and `errors` containing `metadata_runs_not_writable`

### Requirement: Review directory readiness for write-linkedin-draft

Before writing a draft file, the worker SHALL verify that `linkedin-posts/review/` under the configured base path exists, is a directory, and is writable.

If `linkedin-posts/review/` is missing, not a directory, or not writable, the worker MUST NOT write a draft file.

When `metadata/runs/` is writable, the worker SHALL write failed run metadata documenting the review directory failure.

#### Scenario: linkedin-posts/review missing or not a directory

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with a valid body, `metadata/runs/` is writable, and `linkedin-posts/review/` does not exist or is not a directory
- **THEN** the worker does not write a draft file, writes failed run metadata, and returns JSON with `status` failed, `draft_written` false, `draft_relative_path` null, `metadata_written` true, a relative `metadata_path`, and `errors` containing `review_dir_not_ready`

#### Scenario: linkedin-posts/review not writable

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with a valid body, `metadata/runs/` is writable, and `linkedin-posts/review/` exists as a directory but is not writable
- **THEN** the worker does not write a draft file, writes failed run metadata, and returns JSON with `status` failed, `draft_written` false, `draft_relative_path` null, `metadata_written` true, a relative `metadata_path`, and `errors` containing `review_dir_not_writable`

### Requirement: Source path shape validation for write-linkedin-draft

The worker SHALL validate the request `source_relative_path` shape before writing a draft file. The worker MUST NOT re-read or verify the source blog post file on disk.

The path MUST be relative (not absolute). The path MUST NOT contain path traversal segments (`..`). The path MUST start with `blog-posts/ready/` followed by exactly one filename segment (direct child of `blog-posts/ready/`). The filename MUST have a `.md` extension (case-insensitive). The resolved absolute path MUST remain inside `blog-posts/ready/` relative to the configured base path.

If source path shape validation fails, the worker MUST NOT write a draft file. When `metadata/runs/` is writable, the worker SHALL write failed run metadata.

#### Scenario: Valid source path shape

- **WHEN** a client sends `source_relative_path` of `blog-posts/ready/my-post.md` and directory pre-checks pass
- **THEN** source path shape validation succeeds and the worker proceeds to draft filename generation

#### Scenario: Absolute path rejected

- **WHEN** a client sends `source_relative_path` that is an absolute path
- **THEN** source path shape validation fails with error code `absolute_path`, the worker does not write a draft file, and when `metadata/runs/` is writable the response and metadata include the normalized rejected `source_relative_path` with `draft_written` false and `draft_relative_path` null

#### Scenario: Path traversal rejected

- **WHEN** a client sends `source_relative_path` containing `..` segments
- **THEN** source path shape validation fails with error code `path_traversal` and the worker does not write a draft file

#### Scenario: Path outside ready rejected

- **WHEN** a client sends `source_relative_path` that does not start with `blog-posts/ready/`
- **THEN** source path shape validation fails with error code `path_outside_ready` and the worker does not write a draft file

#### Scenario: Non-markdown extension rejected

- **WHEN** a client sends `source_relative_path` ending in a non-`.md` extension
- **THEN** source path shape validation fails with error code `extension_not_md` and the worker does not write a draft file

#### Scenario: Subdirectory path rejected

- **WHEN** a client sends `source_relative_path` with nested segments under ready (for example `blog-posts/ready/subdir/post.md`)
- **THEN** source path shape validation fails with error code `path_not_direct_child` and the worker does not write a draft file

#### Scenario: Resolved path confinement

- **WHEN** the worker resolves the source path for shape validation
- **THEN** the resolved path MUST remain under `blog-posts/ready/` relative to the configured base path

### Requirement: Draft filename generation

The worker SHALL generate the draft output filename server-side. The client MUST NOT supply the output path.

The generated relative path MUST be under `linkedin-posts/review/` and MUST use a `.md` extension.

The base filename pattern MUST be `{utc_timestamp}-{safe_source_stem}.md` where `utc_timestamp` is a UTC filesystem-safe timestamp and `safe_source_stem` is a sanitized stem derived from the source filename.

When `slug_hint` is provided in the request body, the worker MAY include a sanitized `slug_hint` segment in the filename (for example `{utc_timestamp}-{safe_source_stem}-{safe_slug_hint}.md`).

The worker MUST NEVER overwrite an existing draft file. Draft file creation MUST use exclusive creation (`open(..., "x")`, `os.O_CREAT | os.O_EXCL`, or equivalent no-overwrite strategy).

If the initially generated path collides with an existing file, the worker MUST append a short unique suffix derived from the run identifier and retry exclusive creation. If all allowed collision retries fail, the worker MUST NOT overwrite and MUST report error code `draft_path_collision`.

The resolved draft path MUST remain inside `linkedin-posts/review/` relative to the configured base path.

#### Scenario: Default filename from source stem

- **WHEN** a client sends a valid write request without `slug_hint` for source `blog-posts/ready/my-post.md`
- **THEN** the worker generates a draft path under `linkedin-posts/review/` with a filesystem-safe name containing the sanitized stem `my-post` and a UTC timestamp prefix

#### Scenario: Filename includes slug_hint when provided

- **WHEN** a client sends a valid write request with `slug_hint` of `executive`
- **THEN** the generated draft filename includes a sanitized `executive` segment distinguishing the variant

#### Scenario: Collision avoidance with exclusive creation

- **WHEN** the initially generated draft path already exists on disk
- **THEN** the worker retries with a run-identifier suffix using exclusive creation and does not overwrite the existing file

#### Scenario: All collision retries exhausted

- **WHEN** all allowed collision retry paths already exist on disk
- **THEN** the worker does not write a draft file, writes failed run metadata when `metadata/runs/` is writable, and returns JSON with `status` failed, `draft_written` false, `draft_relative_path` null, `metadata_written` true, and `errors` containing `draft_path_collision`

#### Scenario: Client cannot choose output path via body fields

- **WHEN** a client sends a request body field such as `draft_relative_path`, `output_path`, `filename`, or `target_path`
- **THEN** the worker responds with HTTP `422` at body validation and does not use any client-supplied output path

### Requirement: Draft file persistence

When directory and path validations pass, the worker SHALL write the provided `draft_content` as UTF-8 to the generated draft file under `linkedin-posts/review/` using exclusive creation so an existing file is never overwritten.

The worker SHOULD preserve the submitted `draft_content` exactly, except it MAY ensure a single trailing newline when content is non-empty and does not already end with a newline.

The worker MUST NOT add front matter or hidden metadata to the draft file body.

The worker SHALL compute `draft_content_sha256` as the lowercase hexadecimal SHA-256 digest of the UTF-8 bytes written and `size_bytes` as the byte length written.

#### Scenario: Successful draft write

- **WHEN** all pre-checks pass, `draft_content` is valid, and exclusive creation succeeds
- **THEN** a new Markdown file is created under `linkedin-posts/review/` containing the draft text, and the response includes non-null `draft_relative_path`, `draft_content_sha256`, and `size_bytes`

#### Scenario: Draft content preserved

- **WHEN** a draft file is written successfully
- **THEN** the file body matches the submitted `draft_content` except for optional single trailing newline normalization

#### Scenario: No front matter in draft file

- **WHEN** a draft file is written successfully
- **THEN** the file contains only the submitted draft body without YAML front matter added by the worker

#### Scenario: Existing draft file never overwritten

- **WHEN** the target draft path already exists at write time
- **THEN** the worker does not overwrite the existing file and follows collision retry or `draft_path_collision` failure behavior

### Requirement: Write-linkedin-draft run metadata persistence

When `metadata/runs/` exists, is a directory, and is writable, each invocation of `POST /write-linkedin-draft` with a valid request body SHALL create a run metadata JSON file under `metadata/runs/`.

When `metadata/runs/` is missing, not a directory, or not writable, the worker MUST NOT attempt to write run metadata.

The run identifier MUST use the same deterministic traceable format as other processing endpoints.

Run metadata MUST include at minimum: run id, trigger source (`POST /write-linkedin-draft`), timestamps, run status, normalized `source_relative_path`, `draft_relative_path` (or null), `source_content_sha256` (or null), `draft_content_sha256` (or null), `size_bytes` (or null), `draft_written`, optional `title` and `slug_hint` when provided, and errors if any.

Run metadata MUST NOT include full `draft_content`, `SILVERMAN_BLOG_LINKEDIN_API_KEY`, or submitted token values.

#### Scenario: Successful write metadata written

- **WHEN** an authenticated `POST /write-linkedin-draft` completes writing a draft with `metadata/runs/` writable
- **THEN** a JSON file is written to `metadata/runs/` named after the run id and contains draft paths, hashes, and size without full draft body text

#### Scenario: Failed review directory metadata written

- **WHEN** an authenticated `POST /write-linkedin-draft` fails because `linkedin-posts/review/` is not ready and `metadata/runs/` is writable
- **THEN** a run metadata JSON file is written documenting the failed run with `draft_written` false and null draft path fields

#### Scenario: Failed source path shape metadata written

- **WHEN** an authenticated `POST /write-linkedin-draft` fails source path shape validation and `metadata/runs/` is writable
- **THEN** a run metadata JSON file is written with the normalized rejected `source_relative_path`, `draft_written` false, and applicable error codes

#### Scenario: Metadata directory unavailable

- **WHEN** an authenticated `POST /write-linkedin-draft` is invoked and `metadata/runs/` is missing, not a directory, or not writable
- **THEN** no run metadata file is written and the response reports `metadata_written` false and `metadata_path` null

#### Scenario: Metadata excludes draft body and secrets

- **WHEN** run metadata is written for any `POST /write-linkedin-draft` invocation
- **THEN** the metadata file MUST NOT contain `draft_content`, API keys, or submitted auth tokens

#### Scenario: Metadata write failed after successful draft

- **WHEN** a draft file is successfully written but run metadata persistence fails afterward
- **THEN** no run metadata file is created, the draft file is not deleted or rolled back, and the response reports `status` failed, `draft_written` true, populated `draft_relative_path`, `draft_content_sha256`, and `size_bytes`, `metadata_written` false, `metadata_path` null, and `errors` containing `metadata_write_failed`

### Requirement: Write-linkedin-draft HTTP response

The worker SHALL expose `POST /write-linkedin-draft` returning structured JSON suitable for n8n branching when the request is authenticated and body validation passes.

The response MUST include: `run_id`, `status`, `metadata_written`, `metadata_path`, `draft_written`, `draft_relative_path`, `source_relative_path`, `source_content_sha256`, `draft_content_sha256`, `size_bytes`, and `errors`.

When run metadata is written, `metadata_path` MUST be the relative path `metadata/runs/{run_id}.json`. When run metadata is not written, `metadata_path` MUST be JSON `null`.

`source_relative_path` MUST be the normalized request value and MUST NOT be JSON `null` after valid body validation.

`source_content_sha256` MUST echo the request value when provided; otherwise JSON `null`.

`draft_relative_path`, `draft_content_sha256`, and `size_bytes` MUST be JSON `null` unless a draft file was successfully written.

On successful draft write and successful metadata write, `status` MUST be `completed`, `draft_written` MUST be true, `metadata_written` MUST be true, and `draft_relative_path` MUST be populated.

On validation or write failure before a draft is created (after pre-checks pass), `status` MUST be `failed`, `draft_written` MUST be false, and `errors` MUST contain applicable error codes.

On partial failure where the draft file was written but run metadata persistence failed, `status` MUST be `failed`, `draft_written` MUST be true, `draft_relative_path` MUST be populated, `draft_content_sha256` and `size_bytes` MUST be populated, `metadata_written` MUST be false, `metadata_path` MUST be null, and `errors` MUST contain `metadata_write_failed`. The worker MUST NOT delete or roll back the already-written draft file.

The endpoint MUST NOT call DeepSeek, OpenAI, ChatGPT, local LLMs, or any AI provider. It MUST NOT publish to LinkedIn or GitHub. It MUST NOT move or modify source blog post files.

#### Scenario: Completed draft write

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with valid body and all checks pass
- **THEN** the response is JSON with `status` completed, `draft_written` true, `metadata_written` true, a relative `metadata_path`, populated `draft_relative_path`, `draft_content_sha256`, and `size_bytes`, and HTTP `200`

#### Scenario: Failed source path shape with metadata written

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` with an invalid source path shape and `metadata/runs/` is writable
- **THEN** the response is JSON with `status` failed, `draft_written` false, `draft_relative_path` null, null `draft_content_sha256` and `size_bytes`, `metadata_written` true, normalized `source_relative_path`, and HTTP `200`

#### Scenario: Failed review directory with metadata written

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft`, `metadata/runs/` is writable, and `linkedin-posts/review/` is not ready
- **THEN** the response is JSON with `status` failed, `draft_written` false, `metadata_written` true, a relative `metadata_path`, and `errors` containing `review_dir_not_ready` or `review_dir_not_writable`, and HTTP `200`

#### Scenario: Metadata directory unavailable

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft` and `metadata/runs/` is missing, not a directory, or not writable
- **THEN** the response is JSON with `status` failed, `metadata_written` false, `metadata_path` null, `draft_written` false, `draft_relative_path` null, normalized `source_relative_path`, null hash and size fields as applicable, and HTTP `200`

#### Scenario: Draft path collision with metadata written

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft`, all allowed exclusive-creation collision retries fail, and `metadata/runs/` is writable
- **THEN** the response is JSON with `status` failed, `draft_written` false, `draft_relative_path` null, `metadata_written` true, a relative `metadata_path`, and `errors` containing `draft_path_collision`, and HTTP `200`

#### Scenario: Partial failure draft written metadata not written

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft`, the draft file is successfully created, and run metadata writing fails afterward
- **THEN** the response is JSON with `status` failed, `draft_written` true, populated `draft_relative_path`, `draft_content_sha256`, and `size_bytes`, `metadata_written` false, `metadata_path` null, `errors` containing `metadata_write_failed`, and HTTP `200`, and the draft file remains on disk unchanged

#### Scenario: Write-linkedin-draft does not modify source blog files

- **WHEN** a client sends an authenticated `POST /write-linkedin-draft`
- **THEN** the worker MUST NOT move, delete, or modify files under `blog-posts/ready/`, `blog-posts/processed/`, or `blog-posts/error/`

#### Scenario: Write-linkedin-draft does not call AI providers

- **WHEN** a client sends `POST /write-linkedin-draft` with any outcome
- **THEN** the worker MUST NOT call DeepSeek, OpenAI, ChatGPT, local LLMs, or any external AI content generation API

#### Scenario: Write-linkedin-draft does not expose secrets

- **WHEN** a client sends `POST /write-linkedin-draft` with any outcome
- **THEN** the JSON response MUST NOT include `SILVERMAN_BLOG_LINKEDIN_API_KEY` or other secret values

#### Scenario: Existing endpoints unchanged

- **WHEN** a client sends `GET /health`, `POST /process-ready`, or `POST /process-file`
- **THEN** the worker responds as defined by the worker-foundation, ready-blog-post-processing, and blog-post-file-processing specs without requiring changes to those endpoints

### Requirement: Write-linkedin-draft tests

The worker SHALL include automated tests covering API key authentication, request body validation, source path shape validation, review directory readiness, draft file writing, filename collision handling, run metadata creation, and the `POST /write-linkedin-draft` HTTP response shape.

#### Scenario: Authentication tests

- **WHEN** tests invoke `POST /write-linkedin-draft` with missing, invalid, and valid Bearer tokens
- **THEN** tests verify `401` for unauthorized requests and successful processing for valid tokens

#### Scenario: Body validation tests

- **WHEN** tests invoke `POST /write-linkedin-draft` with missing fields, empty `draft_content`, invalid types, and unexpected extra fields (including `draft_relative_path`, `output_path`, `filename`, `target_path`)
- **THEN** tests verify HTTP `422` and that the write-linkedin-draft response contract does not apply

#### Scenario: Source path shape tests

- **WHEN** tests invoke `POST /write-linkedin-draft` with absolute paths, traversal paths, paths outside ready, non-`.md` paths, subdirectory paths, and valid paths
- **THEN** tests verify appropriate error codes, no draft file written on failure, and populated `draft_relative_path` only on success

#### Scenario: Draft write and collision tests

- **WHEN** tests run against a temporary editorial layout with writable `linkedin-posts/review/` and invoke the endpoint with inputs that collide on the initial generated filename
- **THEN** tests verify exclusive creation (no overwrite of existing files), successful retry with suffix when possible, `draft_path_collision` failure when all retries exhausted, and `draft_content_sha256` matches written bytes on success

#### Scenario: Metadata tests

- **WHEN** tests invoke `POST /write-linkedin-draft` successfully with a writable `metadata/runs/` directory
- **THEN** tests verify a run metadata JSON file is created with expected fields, no full `draft_content`, and no secrets

#### Scenario: Metadata write failure after draft tests

- **WHEN** tests simulate successful draft write followed by metadata persistence failure
- **THEN** tests verify `status` failed, `draft_written` true, populated draft path and hashes, `metadata_written` false, `metadata_path` null, `errors` containing `metadata_write_failed`, and the draft file remains on disk

#### Scenario: Review directory unavailable tests

- **WHEN** tests invoke `POST /write-linkedin-draft` with `linkedin-posts/review/` missing or not writable but writable `metadata/runs/`
- **THEN** tests verify `draft_written` false, failed run metadata written, `metadata_written` true, and appropriate error codes

#### Scenario: Metadata directory unavailable tests

- **WHEN** tests invoke `POST /write-linkedin-draft` with `metadata/runs/` missing, not a directory, or not writable
- **THEN** tests verify `metadata_written` false, `metadata_path` null, no metadata file created, no draft file created, and appropriate error codes
