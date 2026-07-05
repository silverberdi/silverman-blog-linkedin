# ready-blog-post-processing

## Purpose

Authenticated `POST /process-ready` endpoint for scanning and validating Markdown blog post candidates in `blog-posts/ready/`, persisting run metadata under `metadata/runs/`, and returning structured JSON for n8n branching—without OpenAI, content generation, or mutating source files.

## Requirements

### Requirement: API key authentication for processing endpoints

The worker SHALL require valid API key authentication for processing endpoints (`POST /process-ready`, `POST /process-file`, `POST /write-linkedin-draft`, and `POST /generate-linkedin-draft`) using the configured `SILVERMAN_BLOG_LINKEDIN_API_KEY`.

The client MUST send the key in the `Authorization` header as a Bearer token: `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>`.

#### Scenario: Valid API key for process-ready

- **WHEN** a client sends `POST /process-ready` with a correct Bearer token matching `SILVERMAN_BLOG_LINKEDIN_API_KEY`
- **THEN** the worker proceeds with folder validation and metadata directory readiness checks before any candidate scanning

#### Scenario: Valid API key for process-file

- **WHEN** a client sends `POST /process-file` with a correct Bearer token matching `SILVERMAN_BLOG_LINKEDIN_API_KEY`
- **THEN** the worker proceeds with request body validation, folder validation, and metadata directory readiness checks before reading the requested file

#### Scenario: Valid API key for write-linkedin-draft

- **WHEN** a client sends `POST /write-linkedin-draft` with a correct Bearer token matching `SILVERMAN_BLOG_LINKEDIN_API_KEY`
- **THEN** the worker proceeds with request body validation and targeted directory readiness checks before writing a review draft

#### Scenario: Valid API key for generate-linkedin-draft

- **WHEN** a client sends `POST /generate-linkedin-draft` with a correct Bearer token matching `SILVERMAN_BLOG_LINKEDIN_API_KEY`
- **THEN** the worker proceeds with request body validation and pre-generation checks before calling DeepSeek or writing a draft

#### Scenario: Missing Authorization header

- **WHEN** a client sends `POST /process-ready`, `POST /process-file`, `POST /write-linkedin-draft`, or `POST /generate-linkedin-draft` without an `Authorization` header
- **THEN** the worker responds with HTTP `401` and a JSON body that does not expose secret values

#### Scenario: Invalid API key

- **WHEN** a client sends `POST /process-ready`, `POST /process-file`, `POST /write-linkedin-draft`, or `POST /generate-linkedin-draft` with an incorrect Bearer token
- **THEN** the worker responds with HTTP `401` and a JSON body that does not expose the expected key or configured secret

#### Scenario: Auth failure does not leak secrets

- **WHEN** authentication fails for `POST /process-ready`, `POST /process-file`, `POST /write-linkedin-draft`, or `POST /generate-linkedin-draft`
- **THEN** the response and logs MUST NOT include `SILVERMAN_BLOG_LINKEDIN_API_KEY` or the submitted token value

### Requirement: Pre-process editorial folder validation

Before scanning `blog-posts/ready/`, the worker SHALL validate the expected editorial folder layout under the configured base path using the same rules as foundation folder validation.

If aggregate folder readiness is false, the worker MUST NOT scan for Markdown candidates.

#### Scenario: All folders ready before scan

- **WHEN** a client sends an authenticated `POST /process-ready` and all expected editorial folders exist as directories
- **THEN** the worker scans `blog-posts/ready/` for candidates

#### Scenario: Folders not ready with writable metadata directory

- **WHEN** a client sends an authenticated `POST /process-ready`, one or more expected editorial folders are missing or not directories, and `metadata/runs/` exists and is writable
- **THEN** the worker does not scan candidates, writes run metadata documenting the failed folder validation, and returns JSON with `status` indicating failure, `folders_ready` false, `metadata_written` true, and a relative `metadata_path`

#### Scenario: Ready folder missing specifically

- **WHEN** `blog-posts/ready` does not exist or is not a directory
- **THEN** the worker does not attempt to list files inside it and reports the run as failed due to editorial layout

### Requirement: Metadata directory readiness

Before writing run metadata or scanning candidates, the worker SHALL verify that `metadata/runs/` under the configured base path exists, is a directory, and is writable.

If `metadata/runs/` is missing, not a directory, or not writable, the worker MUST NOT scan for Markdown candidates and MUST NOT attempt to write run metadata.

#### Scenario: metadata/runs missing or not a directory

- **WHEN** a client sends an authenticated `POST /process-ready` and `metadata/runs/` does not exist or is not a directory
- **THEN** the worker returns JSON with `status` failed, `folders_ready` false, `metadata_written` false, `metadata_path` null, and `errors` containing `metadata_runs_not_ready`

#### Scenario: metadata/runs not writable

- **WHEN** a client sends an authenticated `POST /process-ready` and `metadata/runs/` exists as a directory but is not writable
- **THEN** the worker returns JSON with `status` failed, `folders_ready` false, `metadata_written` false, `metadata_path` null, and `errors` containing `metadata_runs_not_writable`

### Requirement: Ready folder candidate discovery

The worker SHALL list candidate entries only from `blog-posts/ready/` under the configured base path.

Discovery MUST be non-recursive (direct children only). The worker MUST NOT accept arbitrary filesystem paths from the HTTP request body.

#### Scenario: Markdown files discovered

- **WHEN** `blog-posts/ready/` contains regular files with a `.md` extension
- **THEN** those files are considered Markdown candidates for validation

#### Scenario: Non-Markdown files ignored

- **WHEN** `blog-posts/ready/` contains regular files without a `.md` extension
- **THEN** those files are reported in `ignored_files` and are not validated as Markdown candidates

#### Scenario: Subdirectories ignored

- **WHEN** `blog-posts/ready/` contains subdirectories
- **THEN** those entries are reported in `ignored_files` and are not scanned recursively

#### Scenario: Path confinement

- **WHEN** the worker resolves a candidate path
- **THEN** the resolved path MUST remain under `blog-posts/ready/` relative to the configured base path

### Requirement: Markdown candidate validation

For each Markdown candidate in `blog-posts/ready/`, the worker SHALL validate:

- the file exists
- the file is a regular file (not a directory)
- the file extension is `.md` (case-insensitive)
- the file is readable
- the file is not empty (size greater than zero bytes)

Candidates passing all checks MUST appear in `valid_files`. Candidates failing one or more checks MUST appear in `invalid_files` with explicit error codes.

#### Scenario: Valid Markdown candidate

- **WHEN** a `.md` file in `blog-posts/ready/` exists, is a regular file, is readable, and has size greater than zero
- **THEN** the file is listed in `valid_files`

#### Scenario: Empty Markdown file

- **WHEN** a `.md` file in `blog-posts/ready/` exists but has zero bytes
- **THEN** the file is listed in `invalid_files` with an error indicating it is empty

#### Scenario: Unreadable Markdown file

- **WHEN** a `.md` file in `blog-posts/ready/` exists but cannot be read
- **THEN** the file is listed in `invalid_files` with an error indicating it is not readable

### Requirement: Run metadata persistence

When `metadata/runs/` exists, is a directory, and is writable, each invocation of `POST /process-ready` SHALL create a run metadata JSON file under `metadata/runs/`.

When `metadata/runs/` is missing, not a directory, or not writable, the worker MUST NOT attempt to write run metadata.

The run identifier MUST be deterministic in format and traceable (for example, UTC timestamp-based with a uniqueness suffix).

Run metadata MUST include at minimum: run id, trigger source, timestamps, run status, folder readiness, candidate counts, valid/invalid/ignored file summaries, and errors if any.

Run metadata MUST NOT include secret values.

#### Scenario: Successful scan metadata written

- **WHEN** an authenticated `POST /process-ready` completes scanning with folders ready and `metadata/runs/` writable
- **THEN** a JSON file is written to `metadata/runs/` named after the run id and contains counts and file lists from the scan

#### Scenario: Failed folder validation metadata written

- **WHEN** an authenticated `POST /process-ready` is invoked, editorial folders are not ready, and `metadata/runs/` exists and is writable
- **THEN** a run metadata JSON file is written documenting the failed run and the folder readiness outcome

#### Scenario: Metadata directory unavailable

- **WHEN** an authenticated `POST /process-ready` is invoked and `metadata/runs/` is missing, not a directory, or not writable
- **THEN** no run metadata file is written and the response reports `metadata_written` false and `metadata_path` null

#### Scenario: Metadata excludes secrets

- **WHEN** run metadata is written for any `POST /process-ready` invocation
- **THEN** the metadata file MUST NOT contain `SILVERMAN_BLOG_LINKEDIN_API_KEY` or other secret values

### Requirement: Process-ready HTTP response

The worker SHALL expose `POST /process-ready` returning structured JSON suitable for n8n branching.

The response MUST include: `run_id`, `status`, `metadata_written`, `metadata_path`, `folders_ready`, `candidate_count`, `valid_count`, `invalid_count`, `ignored_count`, `valid_files`, `invalid_files`, `ignored_files`, and `errors`.

When run metadata is written, `metadata_path` MUST be the relative path `metadata/runs/{run_id}.json`. When run metadata is not written, `metadata_path` MUST be JSON `null`.

The endpoint MUST NOT call OpenAI, generate LinkedIn content, or move blog post files between editorial folders.

#### Scenario: Completed scan with mixed results

- **WHEN** a client sends an authenticated `POST /process-ready` and folders are ready with both valid and invalid Markdown candidates
- **THEN** the response is JSON with `status` indicating completion, `metadata_written` true, a relative `metadata_path`, accurate counts, populated `valid_files` and `invalid_files`, and HTTP `200`

#### Scenario: Completed scan with no candidates

- **WHEN** a client sends an authenticated `POST /process-ready` and `blog-posts/ready/` contains no Markdown candidates
- **THEN** the response is JSON with zero counts, empty file lists, `status` indicating completion, `metadata_written` true, a relative `metadata_path`, and HTTP `200`

#### Scenario: Folders not ready with metadata written

- **WHEN** a client sends an authenticated `POST /process-ready`, editorial folders are not ready, and `metadata/runs/` is writable
- **THEN** the response is JSON with `status` failed, `folders_ready` false, `metadata_written` true, a relative `metadata_path`, zero candidate counts, and `errors` containing `editorial_folders_not_ready`

#### Scenario: Metadata directory unavailable

- **WHEN** a client sends an authenticated `POST /process-ready` and `metadata/runs/` is missing, not a directory, or not writable
- **THEN** the response is JSON with `status` failed, `folders_ready` false, `metadata_written` false, `metadata_path` null, zero candidate counts, and `errors` containing `metadata_runs_not_ready` or `metadata_runs_not_writable`

#### Scenario: Process-ready is read-only for source files

- **WHEN** a client sends an authenticated `POST /process-ready`
- **THEN** the worker MUST NOT move, delete, or modify files under `blog-posts/ready/`, `blog-posts/processed/`, or `blog-posts/error/`

#### Scenario: Process-ready does not expose secrets

- **WHEN** a client sends `POST /process-ready` with any outcome
- **THEN** the JSON response MUST NOT include `SILVERMAN_BLOG_LINKEDIN_API_KEY` or other secret values

#### Scenario: Health endpoint unchanged

- **WHEN** a client sends `GET /health`
- **THEN** the worker responds as defined by the worker-foundation spec without requiring authentication

### Requirement: Process-ready tests

The worker SHALL include automated tests covering API key authentication, ready-folder scanning, candidate validation, run metadata creation, and the `POST /process-ready` HTTP response shape.

#### Scenario: Authentication tests

- **WHEN** tests invoke `POST /process-ready` with missing, invalid, and valid Bearer tokens
- **THEN** tests verify `401` for unauthorized requests and successful processing for valid tokens

#### Scenario: Scan and validation tests

- **WHEN** tests run against a temporary editorial layout with valid, invalid, ignored, and non-Markdown files in `blog-posts/ready/`
- **THEN** tests verify correct classification into `valid_files`, `invalid_files`, and `ignored_files`

#### Scenario: Metadata tests

- **WHEN** tests invoke `POST /process-ready` successfully with a writable `metadata/runs/` directory
- **THEN** tests verify a run metadata JSON file is created under `metadata/runs/` with expected fields and no secrets

#### Scenario: Metadata directory unavailable tests

- **WHEN** tests invoke `POST /process-ready` with `metadata/runs/` missing, not a directory, or not writable
- **THEN** tests verify `metadata_written` false, `metadata_path` null, no metadata file created, no candidate scan, and appropriate error codes

#### Scenario: Folder-not-ready with writable metadata tests

- **WHEN** tests invoke `POST /process-ready` against a layout with missing editorial folders but a writable `metadata/runs/` directory
- **THEN** tests verify failed status, no candidate scan, failed run metadata written, `metadata_written` true, and structured error reporting
