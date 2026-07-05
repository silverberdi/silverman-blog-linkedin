## 1. API key authentication

- [x] 1.1 Implement `auth.py` with FastAPI dependency that reads `Authorization: Bearer <token>` and validates against `Settings.api_key` using constant-time comparison
- [x] 1.2 Return HTTP `401` with generic JSON body on missing, malformed, or incorrect tokens; never log or echo secret values
- [x] 1.3 Add `tests/test_auth.py` covering valid token, missing header, invalid token, and no-secrets-in-response

## 2. Ready folder scanning and candidate validation

- [x] 2.1 Implement `ready_scan.py` with constant for `blog-posts/ready` relative path
- [x] 2.2 Implement non-recursive directory listing; classify entries as Markdown candidates, ignored non-Markdown files, or ignored subdirectories
- [x] 2.3 Resolve candidate paths and verify they remain under `blog-posts/ready/` (path traversal prevention)
- [x] 2.4 Implement validation checks: exists, regular file, `.md` extension, readable, not empty; return structured valid/invalid/ignored lists with error codes
- [x] 2.5 Add `tests/test_ready_scan.py` using temporary directories with valid `.md`, empty `.md`, non-`.md` files, and subdirectories

## 3. Run metadata

- [x] 3.1 Implement `run_metadata.py` with run id generator (`run-{UTC timestamp}Z-{hex suffix}`)
- [x] 3.2 Implement metadata directory readiness check (`metadata/runs/` exists, is directory, writable) separate from aggregate folder validation
- [x] 3.3 Implement metadata writer that persists JSON to `metadata/runs/{run_id}.json` only when metadata directory is writable; skip write when missing or not writable
- [x] 3.4 Ensure metadata never includes API key or request token values
- [x] 3.5 Add `tests/test_run_metadata.py` verifying file creation when writable, skipped write when unavailable, schema fields, and absence of secrets

## 4. POST /process-ready endpoint

- [x] 4.1 Wire authenticated `POST /process-ready` route in `main.py` using auth dependency
- [x] 4.2 Orchestrate flow: check metadata directory readiness → validate folders → if metadata dir unavailable, return failed JSON with `metadata_written: false` and `metadata_path: null` without scanning → if folders not ready but metadata dir writable, write failed run metadata and return failure JSON without scanning → else scan and validate candidates → write completed run metadata → return response
- [x] 4.3 Return JSON with `run_id`, `status`, `metadata_written`, `metadata_path` (relative path when written, `null` when not), `folders_ready`, counts, `valid_files`, `invalid_files`, `ignored_files`, and `errors`
- [x] 4.4 Ensure endpoint does not move or modify blog source files; only writes run metadata under `metadata/runs/` when writable
- [x] 4.5 Confirm `GET /health` remains unauthenticated and unchanged
- [x] 4.6 Add `tests/test_process_ready.py` covering auth, successful scan, empty ready folder, mixed valid/invalid files, folder-not-ready with metadata written, metadata/runs missing or not writable with `metadata_written: false`, and no-secrets-in-response

## 5. Documentation and deployment notes

- [x] 5.1 Update `README.md` with `POST /process-ready` description, Bearer authentication header, example request/response JSON, and n8n integration notes
- [x] 5.2 Document that `metadata/runs/` requires write access in Docker volume mount (update `docker-compose.example.yml` if currently read-only)

## 6. Validation

- [x] 6.1 Run full test suite (`pytest`) and ensure all tests pass
- [x] 6.2 Run `openspec validate add-process-ready-blog-posts`
- [x] 6.3 Manual smoke test: start worker locally, call `POST /process-ready` with valid Bearer token against sample editorial tree, confirm JSON structure and metadata file on disk
