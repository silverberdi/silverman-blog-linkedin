## 1. Source path shape validation and draft writing

- [x] 1.1 Implement `draft_writer.py` with constants for `linkedin-posts/review` relative path and reuse or share `normalize_relative_path` from `file_reader.py`
- [x] 1.2 Implement `validate_source_path_shape()` with shape-only validation: reject absolute paths, path traversal (`..`), paths not starting with `blog-posts/ready/`, non-direct-child paths, and non-`.md` extensions with explicit error codes (no file existence check)
- [x] 1.3 Implement `check_review_dir_ready()` mirroring `check_metadata_runs_ready()` pattern with `review_dir_not_ready` and `review_dir_not_writable` error codes
- [x] 1.4 Implement `sanitize_filename_segment()` for filesystem-safe stems from source filename and optional `slug_hint`
- [x] 1.5 Implement `generate_draft_relative_path()` using `{utc_timestamp}-{safe_source_stem}.md` pattern, optional `slug_hint` segment, run-id suffix collision candidates, and path confinement under `linkedin-posts/review/`
- [x] 1.6 Implement `write_draft_file()` using exclusive creation (`open(..., "x")` or `O_EXCL` equivalent): never overwrite; retry with run-id suffix on collision; return `draft_path_collision` when all retries fail; compute `draft_content_sha256` and `size_bytes` from bytes written
- [x] 1.7 Add `tests/test_draft_writer.py` covering source path shape validation, filename generation, sanitization, exclusive creation, collision retry, `draft_path_collision` failure, confinement, and draft content hashing

## 2. Run metadata extensions

- [x] 2.1 Add `TRIGGER_WRITE_LINKEDIN_DRAFT = "POST /write-linkedin-draft"` constant to `run_metadata.py`
- [x] 2.2 Implement `build_write_linkedin_draft_metadata_payload()` with summary fields (`source_relative_path`, `draft_relative_path`, `source_content_sha256`, `draft_content_sha256`, `size_bytes`, `draft_written`, optional `title`/`slug_hint`) using JSON null for unavailable values; never include `draft_content`
- [x] 2.3 Implement `build_write_linkedin_draft_response()` with all required HTTP response fields per spec nullability rules, including partial-failure case (`metadata_write_failed` with `draft_written` true)
- [x] 2.4 Extend metadata tests in `tests/test_run_metadata.py` for write-linkedin-draft payload shape on success, failure, and partial failure; absence of `draft_content`/secrets

## 3. POST /write-linkedin-draft endpoint

- [x] 3.1 Add Pydantic request model with `model_config = ConfigDict(extra="forbid")`, required `source_relative_path` and `draft_content` (strip-empty → 422), optional `source_content_sha256`, `title`, `slug_hint`; extra fields such as `draft_relative_path`, `output_path`, `filename`, `target_path` → HTTP 422
- [x] 3.2 Wire authenticated `POST /write-linkedin-draft` route in `main.py` using existing `require_api_key` dependency
- [x] 3.3 Orchestrate flow: validate body → normalize `source_relative_path` → check metadata/runs readiness → if unavailable return failed JSON without draft or metadata writes → check review dir readiness → validate source path shape → on failure write failed metadata when writable → write draft with exclusive creation → on `draft_path_collision` write failed metadata and return failed response → write run metadata → on metadata write failure return partial-failure response (`metadata_write_failed`, draft retained, not rolled back) → on success return completed response
- [x] 3.4 Return JSON with `run_id`, `status`, `metadata_written`, `metadata_path`, `draft_written`, `draft_relative_path`, `source_relative_path`, `source_content_sha256`, `draft_content_sha256`, `size_bytes`, and `errors` per spec
- [x] 3.5 Ensure endpoint does not move or modify blog source files and does not call any AI provider
- [x] 3.6 Confirm `GET /health`, `POST /process-ready`, and `POST /process-file` remain unchanged
- [x] 3.7 Add `tests/test_write_linkedin_draft.py` covering auth, 422 on bad body and extra fields (no endpoint contract), successful write, review dir unavailable with failed metadata, metadata/runs unavailable with no writes, source path shape failure, exclusive creation and collision retry, `draft_path_collision`, partial failure (`metadata_write_failed` with draft retained), optional fields echo, and no-secrets-in-response

## 4. Documentation

- [x] 4.1 Update `README.md` with `POST /write-linkedin-draft` description, allowed request body fields (no output path fields), Bearer authentication, example success/failure/partial-failure response JSON, and n8n integration notes (persist draft after external or future LLM step; pass `source_relative_path` and optional `source_content_sha256` from `POST /process-file`)

## 5. Validation

- [x] 5.1 Run full test suite (`pytest`) and ensure all tests pass
- [x] 5.2 Run `openspec validate add-linkedin-draft-review-writer`
- [x] 5.3 Manual smoke test: start worker locally, call `POST /write-linkedin-draft` with valid Bearer token and sample draft payload, confirm draft file under `linkedin-posts/review/`, metadata file without full draft body, and JSON response shape; verify extra body field returns 422
