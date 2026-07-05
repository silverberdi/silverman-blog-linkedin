# blog-post-file-processing

## Purpose

Authenticated `POST /process-file` endpoint for reading one Markdown blog post from `blog-posts/ready/` by `relative_path`, persisting run metadata under `metadata/runs/` (file summary only), and returning structured JSON including raw Markdown content for n8n branching—without OpenAI, content generation, or mutating source files.

## Requirements

### Requirement: Process-file request body

The worker SHALL accept a JSON request body on `POST /process-file` with a required `relative_path` string field.

The worker MUST reject requests with a missing body, missing `relative_path`, non-string `relative_path`, or empty `relative_path` with HTTP `422`.

Before validation, the worker SHALL normalize `relative_path` by stripping leading `./` and trailing slashes.

#### Scenario: Valid request body

- **WHEN** a client sends an authenticated `POST /process-file` with body `{ "relative_path": "blog-posts/ready/my-post.md" }`
- **THEN** the worker proceeds with folder validation and path validation

#### Scenario: Missing relative_path

- **WHEN** a client sends an authenticated `POST /process-file` with body `{}` or without `relative_path`
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Empty relative_path

- **WHEN** a client sends an authenticated `POST /process-file` with body `{ "relative_path": "" }`
- **THEN** the worker responds with HTTP `422` and a JSON validation error

#### Scenario: Body validation failure has no process-file contract

- **WHEN** a client sends an authenticated `POST /process-file` that fails FastAPI/Pydantic body validation
- **THEN** the worker responds with HTTP `422` and the process-file response/metadata contract does not apply

### Requirement: Pre-process editorial folder validation for process-file

Before reading a blog post file, the worker SHALL validate the expected editorial folder layout under the configured base path using the same rules as foundation folder validation.

If aggregate folder readiness is false, the worker MUST NOT read the requested file.

#### Scenario: All folders ready before read

- **WHEN** a client sends an authenticated `POST /process-file` with a valid request body and all expected editorial folders exist as directories
- **THEN** the worker validates and attempts to read the requested file

#### Scenario: Folders not ready with writable metadata directory

- **WHEN** a client sends an authenticated `POST /process-file`, one or more expected editorial folders are missing or not directories, and `metadata/runs/` exists and is writable
- **THEN** the worker does not read the file, writes run metadata documenting the failed folder validation, and returns JSON with `status` indicating failure, `folders_ready` false, `metadata_written` true, a relative `metadata_path`, the normalized `relative_path`, null `size_bytes`, null `content_sha256`, null `markdown_content`, and `errors` containing `editorial_folders_not_ready`

#### Scenario: Ready folder missing specifically

- **WHEN** `blog-posts/ready` does not exist or is not a directory
- **THEN** the worker does not attempt to read inside it and reports the run as failed due to editorial layout

### Requirement: Metadata directory readiness for process-file

Before writing run metadata or reading a file, the worker SHALL verify that `metadata/runs/` under the configured base path exists, is a directory, and is writable.

If `metadata/runs/` is missing, not a directory, or not writable, the worker MUST NOT read the requested file and MUST NOT attempt to write run metadata.

#### Scenario: metadata/runs missing or not a directory

- **WHEN** a client sends an authenticated `POST /process-file` and `metadata/runs/` does not exist or is not a directory
- **THEN** the worker returns JSON with `status` failed, `folders_ready` false, `metadata_written` false, `metadata_path` null, the normalized `relative_path`, null `size_bytes`, null `content_sha256`, null `markdown_content`, and `errors` containing `metadata_runs_not_ready`

#### Scenario: metadata/runs not writable

- **WHEN** a client sends an authenticated `POST /process-file` and `metadata/runs/` exists as a directory but is not writable
- **THEN** the worker returns JSON with `status` failed, `folders_ready` false, `metadata_written` false, `metadata_path` null, the normalized `relative_path`, null `size_bytes`, null `content_sha256`, null `markdown_content`, and `errors` containing `metadata_runs_not_writable`

### Requirement: Request path validation for process-file

The worker SHALL validate the request `relative_path` before reading file content.

The path MUST be relative (not absolute). The path MUST NOT contain path traversal segments (`..`). The path MUST start with `blog-posts/ready/` followed by exactly one filename segment (direct child of `blog-posts/ready/`). The filename MUST have a `.md` extension (case-insensitive). The resolved absolute path MUST remain inside `blog-posts/ready/` relative to the configured base path.

#### Scenario: Valid relative path under ready

- **WHEN** a client sends `relative_path` of `blog-posts/ready/my-post.md` and the file exists as a regular readable non-empty file under the configured base path
- **THEN** path validation succeeds and the worker proceeds to read the file

#### Scenario: Absolute path rejected

- **WHEN** a client sends `relative_path` that is an absolute path (for example `/etc/passwd` or `/data/silverman-blog-linkedin/blog-posts/ready/post.md`)
- **THEN** path validation fails with error code `absolute_path`, the worker does not read the file, and the response and metadata include the normalized rejected `relative_path` with null `size_bytes`, null `content_sha256`, and null `markdown_content`

#### Scenario: Path traversal rejected

- **WHEN** a client sends `relative_path` containing `..` segments (for example `blog-posts/ready/../processed/secret.md`)
- **THEN** path validation fails with error code `path_traversal` and the worker does not read the file

#### Scenario: Path outside ready rejected

- **WHEN** a client sends `relative_path` that does not start with `blog-posts/ready/` (for example `blog-posts/processed/post.md`)
- **THEN** path validation fails with error code `path_outside_ready` and the worker does not read the file

#### Scenario: Non-markdown extension rejected

- **WHEN** a client sends `relative_path` ending in a non-`.md` extension (for example `blog-posts/ready/notes.txt`)
- **THEN** path validation fails with error code `extension_not_md` and the worker does not read the file

#### Scenario: Subdirectory path rejected

- **WHEN** a client sends `relative_path` with nested segments under ready (for example `blog-posts/ready/subdir/post.md`)
- **THEN** path validation fails with error code `path_not_direct_child` and the worker does not read the file

#### Scenario: Resolved path confinement

- **WHEN** the worker resolves the requested path
- **THEN** the resolved path MUST remain under `blog-posts/ready/` relative to the configured base path

### Requirement: Blog post file validation and reading

For a path passing request validation, the worker SHALL verify the target is a regular file, is readable, is not empty (size greater than zero bytes), and contains valid UTF-8 text.

The worker SHALL read file content as UTF-8 with strict decoding. The worker SHALL compute `content_sha256` as the lowercase hexadecimal SHA-256 digest of the raw file bytes.

#### Scenario: Successful read of valid Markdown file

- **WHEN** the target file exists, is a regular file, is readable, has size greater than zero, and contains valid UTF-8
- **THEN** the worker reads the content, computes `content_sha256`, and includes `markdown_content` in the HTTP response

#### Scenario: Missing file

- **WHEN** the validated relative path does not exist on disk
- **THEN** the worker reports error code `file_not_found`, returns the normalized `relative_path`, and sets `size_bytes`, `content_sha256`, and `markdown_content` to JSON `null`

#### Scenario: Target is directory

- **WHEN** the validated relative path points to a directory
- **THEN** the worker reports error code `is_directory`, returns the normalized `relative_path`, and sets `size_bytes`, `content_sha256`, and `markdown_content` to JSON `null`

#### Scenario: Empty file

- **WHEN** the target file exists but has zero bytes
- **THEN** the worker reports error code `file_empty`, returns the normalized `relative_path`, and sets `content_sha256` and `markdown_content` to JSON `null`

#### Scenario: Unreadable file

- **WHEN** the target file exists but cannot be read
- **THEN** the worker reports error code `not_readable`, returns the normalized `relative_path`, and sets `content_sha256` and `markdown_content` to JSON `null`

#### Scenario: Invalid UTF-8 content

- **WHEN** the target file bytes are not valid UTF-8
- **THEN** the worker reports error code `not_utf8`, returns the normalized `relative_path`, sets `markdown_content` to JSON `null`, and sets `content_sha256` to JSON `null` unless bytes were successfully read before decode failure

### Requirement: Process-file response and metadata field nullability

Once request body validation passes, the worker SHALL apply consistent nullability rules to file summary fields in both the HTTP response and run metadata (when written).

The normalized request `relative_path` MUST always be present in the HTTP response and in run metadata when written. It MUST NOT be JSON `null` after valid body validation.

`filename` MUST be JSON `null` when the final path component cannot be safely derived from the normalized path; otherwise it MUST contain the derived filename.

`size_bytes` MUST be JSON `null` unless the file is successfully stat/read enough to determine size.

`content_sha256` MUST be JSON `null` unless file bytes are successfully read.

`markdown_content` MUST appear only in the HTTP response. It MUST be JSON `null` unless UTF-8 decode succeeds on a valid non-empty file read. It MUST NOT appear in run metadata under any circumstance.

When run metadata is written for a failed run, the metadata file MUST include the same summary fields (`relative_path`, `filename`, `size_bytes`, `content_sha256`) with JSON `null` for values that were unavailable.

When `metadata/runs/` is unavailable, the worker MUST NOT write a metadata file and MUST return `metadata_written` false and `metadata_path` JSON `null`.

The response, metadata, and logs MUST NOT include `SILVERMAN_BLOG_LINKEDIN_API_KEY` or submitted token values.

#### Scenario: Normalized relative_path always present after valid body

- **WHEN** a client sends an authenticated `POST /process-file` with a valid request body and processing fails for any reason other than body validation
- **THEN** the HTTP response includes the normalized `relative_path` as a non-null string

#### Scenario: Filename null when not derivable

- **WHEN** the normalized `relative_path` has no safely derivable final path component
- **THEN** `filename` is JSON `null` in the response and in run metadata when written

#### Scenario: File summary nulls on folder-not-ready failure

- **WHEN** editorial folders are not ready and `metadata/runs/` is writable
- **THEN** the response and written metadata include the normalized `relative_path`, null `size_bytes`, null `content_sha256`, and null `markdown_content` in the response only

#### Scenario: File summary nulls on path validation failure

- **WHEN** path validation fails after editorial pre-checks pass
- **THEN** the response and written metadata include the normalized rejected `relative_path`, null `size_bytes`, null `content_sha256`, and null `markdown_content` in the response only

#### Scenario: Successful read populates all available fields

- **WHEN** a file is successfully read and UTF-8 decoded
- **THEN** the response includes non-null normalized `relative_path`, `filename`, `size_bytes`, `content_sha256`, and `markdown_content`, and written metadata includes non-null `relative_path`, `filename`, `size_bytes`, and `content_sha256` but not `markdown_content`

### Requirement: Process-file run metadata persistence

When `metadata/runs/` exists, is a directory, and is writable, each invocation of `POST /process-file` with a valid request body SHALL create a run metadata JSON file under `metadata/runs/`.

When `metadata/runs/` is missing, not a directory, or not writable, the worker MUST NOT attempt to write run metadata.

The run identifier MUST use the same deterministic traceable format as `POST /process-ready`.

Run metadata MUST include at minimum: run id, trigger source (`POST /process-file`), timestamps, run status, folder readiness, normalized `relative_path`, `filename`, `size_bytes`, `content_sha256`, and errors if any. Each of `filename`, `size_bytes`, and `content_sha256` MUST be JSON `null` when unavailable per the nullability requirement.

Run metadata MUST NOT include `markdown_content` or secret values.

#### Scenario: Successful read metadata written

- **WHEN** an authenticated `POST /process-file` completes reading a valid file with folders ready and `metadata/runs/` writable
- **THEN** a JSON file is written to `metadata/runs/` named after the run id and contains non-null normalized `relative_path`, `filename`, `size_bytes`, and `content_sha256` without `markdown_content`

#### Scenario: Failed path validation metadata written

- **WHEN** an authenticated `POST /process-file` fails path or file validation, folders are ready, and `metadata/runs/` is writable
- **THEN** a run metadata JSON file is written with the normalized rejected `relative_path`, null `size_bytes`, null `content_sha256`, error codes, and no `markdown_content`

#### Scenario: Failed folder validation metadata written

- **WHEN** an authenticated `POST /process-file` is invoked, editorial folders are not ready, and `metadata/runs/` exists and is writable
- **THEN** a run metadata JSON file is written with the normalized `relative_path`, null `size_bytes`, null `content_sha256`, folder readiness failure, and no `markdown_content`

#### Scenario: Metadata directory unavailable

- **WHEN** an authenticated `POST /process-file` is invoked and `metadata/runs/` is missing, not a directory, or not writable
- **THEN** no run metadata file is written and the response reports `metadata_written` false and `metadata_path` null

#### Scenario: Metadata excludes content and secrets

- **WHEN** run metadata is written for any `POST /process-file` invocation
- **THEN** the metadata file MUST NOT contain `markdown_content`, `SILVERMAN_BLOG_LINKEDIN_API_KEY`, or other secret values

### Requirement: Process-file HTTP response

The worker SHALL expose `POST /process-file` returning structured JSON suitable for n8n branching when the request is authenticated and body validation passes.

The response MUST include: `run_id`, `status`, `metadata_written`, `metadata_path`, `folders_ready`, `relative_path`, `filename`, `size_bytes`, `content_sha256`, `markdown_content`, and `errors`.

When run metadata is written, `metadata_path` MUST be the relative path `metadata/runs/{run_id}.json`. When run metadata is not written, `metadata_path` MUST be JSON `null`.

`relative_path` MUST be the normalized request value and MUST NOT be JSON `null` after valid body validation.

`filename`, `size_bytes`, `content_sha256`, and `markdown_content` MUST follow the nullability rules defined in the process-file response and metadata field nullability requirement.

On successful read, `status` MUST be `completed`, `markdown_content` MUST contain the UTF-8 file text, and `content_sha256` MUST be populated.

On validation or read failure (after pre-checks pass), `status` MUST be `failed`, `markdown_content` MUST be JSON `null`, and `errors` MUST contain applicable error codes.

The endpoint MUST NOT call OpenAI, generate LinkedIn content, or move blog post files between editorial folders.

#### Scenario: Completed read with content

- **WHEN** a client sends an authenticated `POST /process-file` with a valid path to a readable non-empty Markdown file and folders are ready
- **THEN** the response is JSON with `status` completed, `metadata_written` true, a relative `metadata_path`, populated `markdown_content` and `content_sha256`, and HTTP `200`

#### Scenario: Failed file validation with metadata written

- **WHEN** a client sends an authenticated `POST /process-file` with a path to an empty `.md` file and folders are ready
- **THEN** the response is JSON with `status` failed, normalized `relative_path`, null `content_sha256`, null `markdown_content`, `errors` containing `file_empty`, `metadata_written` true, and HTTP `200`

#### Scenario: Folders not ready with metadata written

- **WHEN** a client sends an authenticated `POST /process-file`, editorial folders are not ready, and `metadata/runs/` is writable
- **THEN** the response is JSON with `status` failed, `folders_ready` false, `metadata_written` true, a relative `metadata_path`, normalized `relative_path`, null `size_bytes`, null `content_sha256`, null `markdown_content`, and `errors` containing `editorial_folders_not_ready`

#### Scenario: Metadata directory unavailable

- **WHEN** a client sends an authenticated `POST /process-file` and `metadata/runs/` is missing, not a directory, or not writable
- **THEN** the response is JSON with `status` failed, `metadata_written` false, `metadata_path` null, normalized `relative_path`, null `size_bytes`, null `content_sha256`, null `markdown_content`, and `errors` containing `metadata_runs_not_ready` or `metadata_runs_not_writable`

#### Scenario: Process-file is read-only for source files

- **WHEN** a client sends an authenticated `POST /process-file`
- **THEN** the worker MUST NOT move, delete, or modify files under `blog-posts/ready/`, `blog-posts/processed/`, or `blog-posts/error/`

#### Scenario: Process-file does not expose secrets

- **WHEN** a client sends `POST /process-file` with any outcome
- **THEN** the JSON response MUST NOT include `SILVERMAN_BLOG_LINKEDIN_API_KEY` or other secret values

#### Scenario: Health and process-ready unchanged

- **WHEN** a client sends `GET /health` or `POST /process-ready`
- **THEN** the worker responds as defined by the worker-foundation and ready-blog-post-processing specs without requiring changes to those endpoints

### Requirement: Process-file tests

The worker SHALL include automated tests covering API key authentication, request body validation, path validation, file reading, run metadata creation, and the `POST /process-file` HTTP response shape.

#### Scenario: Authentication tests

- **WHEN** tests invoke `POST /process-file` with missing, invalid, and valid Bearer tokens
- **THEN** tests verify `401` for unauthorized requests and successful processing for valid tokens

#### Scenario: Path validation tests

- **WHEN** tests invoke `POST /process-file` with absolute paths, traversal paths, paths outside ready, non-`.md` paths, and valid paths
- **THEN** tests verify appropriate error codes, normalized `relative_path` in response, null `content_sha256` and null `markdown_content` on failure, and populated fields only on success

#### Scenario: File read tests

- **WHEN** tests run against a temporary editorial layout with valid, empty, unreadable, and invalid UTF-8 Markdown files
- **THEN** tests verify correct content and hash on success, null `markdown_content` and null `content_sha256` on failure, and appropriate error codes

#### Scenario: Metadata tests

- **WHEN** tests invoke `POST /process-file` successfully with a writable `metadata/runs/` directory
- **THEN** tests verify a run metadata JSON file is created with non-null file summary fields on success, no `markdown_content`, and no secrets

#### Scenario: Failed run metadata null field tests

- **WHEN** tests invoke `POST /process-file` for folder-not-ready, path validation failure, missing file, empty file, or invalid UTF-8 outcomes with writable `metadata/runs/`
- **THEN** tests verify written metadata includes normalized `relative_path`, null `size_bytes` and null `content_sha256` where unavailable, no `markdown_content`, and matching error codes

#### Scenario: Metadata directory unavailable tests

- **WHEN** tests invoke `POST /process-file` with `metadata/runs/` missing, not a directory, or not writable
- **THEN** tests verify `metadata_written` false, `metadata_path` null, no metadata file created, no file read, normalized `relative_path` in response, null file summary fields, and appropriate error codes

#### Scenario: Folder-not-ready with writable metadata tests

- **WHEN** tests invoke `POST /process-file` against a layout with missing editorial folders but a writable `metadata/runs/` directory
- **THEN** tests verify failed status, no file read, failed run metadata written with null unavailable summary fields and no `markdown_content`, `metadata_written` true, normalized `relative_path` in response, and structured error reporting
