## 1. Request path validation and file reading

- [x] 1.1 Implement `file_reader.py` with constants for `blog-posts/ready` relative path and path normalization (strip `./`, trailing slashes)
- [x] 1.2 Implement validation: reject absolute paths, path traversal (`..`), paths not starting with `blog-posts/ready/`, non-direct-child paths, and non-`.md` extensions with explicit error codes
- [x] 1.3 Resolve candidate paths and verify they remain under `blog-posts/ready/` (path confinement via `is_relative_to`)
- [x] 1.4 Implement file property checks: exists, regular file, readable, not empty, valid UTF-8; compute `content_sha256` as lowercase hex SHA-256 of raw bytes only when bytes are successfully read
- [x] 1.5 Return structured read result dataclass with normalized `relative_path`, `filename` (derived or null), `size_bytes` (or null), `content_sha256` (or null), `markdown_content` (or null), and errors list
- [x] 1.6 Add `tests/test_file_reader.py` covering valid reads, absolute paths, traversal, outside-ready paths, subdirectories, empty files, missing files, directories, invalid UTF-8, and null field behavior when values are unavailable

## 2. Run metadata extensions

- [x] 2.1 Add `TRIGGER_PROCESS_FILE = "POST /process-file"` constant to `run_metadata.py`
- [x] 2.2 Implement `build_process_file_metadata_payload()` with file summary fields (`relative_path`, `filename`, `size_bytes`, `content_sha256`) using JSON null for unavailable values; never include `markdown_content`
- [x] 2.3 Implement `build_process_file_response()` with all required HTTP response fields, always including normalized non-null `relative_path` after valid body, and null file summary/content fields when unavailable
- [x] 2.4 Extend metadata tests in `tests/test_run_metadata.py` for process-file payload shape on success and failure, null unavailable summary fields on failed runs, and absence of `markdown_content`/secrets

## 3. POST /process-file endpoint

- [x] 3.1 Add Pydantic request model with required non-empty `relative_path` string field (422 on failure; no process-file contract applies)
- [x] 3.2 Wire authenticated `POST /process-file` route in `main.py` using existing `require_api_key` dependency
- [x] 3.3 Orchestrate flow: validate body → normalize `relative_path` → check metadata directory readiness → validate folders → if metadata dir unavailable, return failed JSON with normalized `relative_path` and null summary fields without reading or writing metadata → if folders not ready but metadata dir writable, write failed run metadata with null unavailable summary fields and return failure JSON without reading → else validate path and read file → write run metadata → return response
- [x] 3.4 Return JSON with `run_id`, `status`, `metadata_written`, `metadata_path`, `folders_ready`, normalized `relative_path`, `filename`, `size_bytes`, `content_sha256`, `markdown_content`, and `errors` per nullability rules
- [x] 3.5 Ensure endpoint does not move or modify blog source files; only writes run metadata under `metadata/runs/` when writable
- [x] 3.6 Confirm `GET /health` and `POST /process-ready` remain unchanged
- [x] 3.7 Add `tests/test_process_file.py` covering auth, 422 on bad body (no process-file contract), successful read with populated fields, folder-not-ready with null summary fields in response and metadata, metadata/runs unavailable with null summary fields and no metadata file, path validation failure with normalized rejected path, missing file, empty file, invalid UTF-8, and no-secrets-in-response

## 4. Documentation

- [x] 4.1 Update `README.md` with `POST /process-file` description, request body, Bearer authentication, example success/failure response JSON showing null field behavior, and n8n integration notes (pass `relative_path` from process-ready `valid_files`)

## 5. Validation

- [x] 5.1 Run full test suite (`pytest`) and ensure all tests pass
- [x] 5.2 Run `openspec validate add-process-file-blog-post-reader`
- [x] 5.3 Manual smoke test: start worker locally, call `POST /process-file` with valid Bearer token and `relative_path` for a sample `.md` file, confirm JSON structure, populated fields on success, null fields on intentional failure, `markdown_content` in response only, and metadata file on disk without content
