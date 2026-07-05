## Context

The worker foundation is implemented: FastAPI app, environment configuration (`SILVERMAN_BLOG_LINKEDIN_BASE_PATH`, `SILVERMAN_BLOG_LINKEDIN_API_KEY`, `PORT`), read-only editorial folder validation (`paths.py`), and unauthenticated `GET /health`. n8n on the Linux server will orchestrate content automation via HTTP Request nodes (ADR-0001).

This change adds the first authenticated processing endpoint: `POST /process-ready`. It performs a read-only scan of `blog-posts/ready/` for Markdown candidates, validates basic file properties, writes run metadata to `metadata/runs/`, and returns structured JSON. It deliberately does **not** generate LinkedIn drafts, call OpenAI, or move source files—those belong to later changes.

Blog posts remain the canonical content source (ADR-0002). This endpoint is the discovery and validation gate before generation.

## Goals / Non-Goals

**Goals:**

- Expose `POST /process-ready` with API key authentication.
- Reuse existing folder validation before scanning; fail safely when editorial layout is not ready.
- List and validate `.md` candidates in `blog-posts/ready/` only; never accept arbitrary paths from the request body.
- Write one run metadata JSON file per invocation under `metadata/runs/` when that directory exists and is writable.
- Return structured JSON with run id, status, `metadata_written`, `metadata_path`, counts, valid/invalid/ignored file lists, and errors—suitable for n8n IF nodes.
- Keep `GET /health` unchanged (unauthenticated, read-only).

**Non-Goals:**

- LinkedIn generation, OpenAI calls, campaign metadata, file moves to `processed/` or `error/`.
- `POST /process-file`, n8n workflows, GitHub/LinkedIn publish, Dairector paths.
- Full Markdown/front-matter parsing, scheduling, batch size limits.
- Request body parameters for paths or filters (empty body or no body is sufficient).

## Decisions

### 1. New capability module layout

**Decision:** Add focused modules under `src/silverman_blog_linkedin/`:

```
src/silverman_blog_linkedin/
  auth.py              # API key verification dependency
  ready_scan.py        # list + validate candidates in blog-posts/ready/
  run_metadata.py      # run id generation and metadata/runs/ writer
  main.py              # add POST /process-ready route (auth + orchestration)
tests/
  test_auth.py
  test_ready_scan.py
  test_run_metadata.py
  test_process_ready.py
```

**Rationale:** Separates authentication, scanning logic, and metadata persistence for unit testing without full HTTP stack. Keeps `main.py` as thin orchestration.

**Alternatives considered:**

- **Single `process_ready.py`:** Fewer files but mixes auth, scan, and metadata concerns.
- **Extend `paths.py` only:** Path validation is editorial-layout scope; candidate scanning is distinct behavior.

### 2. API key authentication

**Decision:** Require `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>` on `POST /process-ready`. Compare using constant-time equality (`secrets.compare_digest`). Return `401 Unauthorized` with a generic JSON body when the header is missing, malformed, or incorrect.

**Rationale:** Standard pattern for n8n HTTP Request nodes (Header Auth or manual Authorization header). Reuses existing env var loaded at startup. Does not affect unauthenticated `GET /health`.

**Alternatives considered:**

- **`X-API-Key` header:** Works but less conventional; Bearer is widely documented.
- **Query parameter:** Leaks in logs and proxy history—rejected.

**Security:**

- Never include API key in responses, error messages, run metadata, or info-level logs.
- On auth failure, respond with `{ "detail": "Unauthorized" }` or equivalent—no hint about expected key format beyond 401.

### 3. Pre-scan folder validation and metadata directory readiness

**Decision:** Before listing candidates, call existing `validate_folders(base_path)` and separately check whether `metadata/runs/` exists, is a directory, and is writable.

**Folder readiness (`folders_ready`):** Aggregate result from foundation folder validation across all ten expected editorial paths.

**Metadata directory readiness (`metadata_runs_ready`):** `metadata/runs/` exists, is a directory, and the worker can write a file there (check via `os.access(path, W_OK)` or equivalent).

**Orchestration order:**

1. Authenticate request.
2. Generate run id.
3. Validate all editorial folders → set `folders_ready`.
4. Check `metadata/runs/` writability → set `metadata_runs_ready`.
5. Branch:
   - If `metadata_runs_ready` is false → do **not** scan candidates; return HTTP **200** with `status: "failed"`, `folders_ready: false`, `metadata_written: false`, `metadata_path: null`, and `errors` containing `metadata_runs_not_ready` (missing/not a directory) or `metadata_runs_not_writable` (exists but not writable).
   - If `folders_ready` is false but `metadata_runs_ready` is true → do **not** scan candidates; write failed run metadata documenting folder readiness failure; return HTTP **200** with `status: "failed"`, `folders_ready: false`, `metadata_written: true`, `metadata_path: "metadata/runs/{run_id}.json"`, and `errors` containing `editorial_folders_not_ready`.
   - If both ready → scan candidates, write completed run metadata, return success response.

**Chosen behavior:** Return HTTP **200** with structured JSON for all operational outcomes (consistent with `/health` degraded semantics and n8n branching on JSON fields). Do not attempt to scan `blog-posts/ready/` when `folders_ready` is false.

**Rationale:** n8n workflows branch reliably on JSON `status`, `metadata_written`, and `folders_ready`. Separating metadata-directory failure from general folder failure avoids the inconsistent contract where metadata must be written but `metadata/runs/` itself is unavailable.

### 4. Candidate discovery scope

**Decision:** Scan only `base_path / "blog-posts/ready"`. Use `Path.iterdir()` (non-recursive). Consider only direct children of `ready/`.

| Entry type | Handling |
|------------|----------|
| Regular file with `.md` suffix (case-insensitive) | Validate as candidate |
| Regular file without `.md` suffix | Report in `ignored_files` with reason `non_markdown` |
| Subdirectory | Report in `ignored_files` with reason `subdirectory` |
| Symlink to file | Follow for validation if within `ready/`; reject if resolves outside `ready/` |
| Hidden files (e.g. `.DS_Store`) | Non-`.md` → `ignored_files` |

**Rationale:** Phase 1 expects flat placement in `ready/`. Non-recursive scan avoids accidental deep traversal and path surprises.

**Path traversal prevention:**

- Resolve candidate paths with `Path.resolve()` and verify `resolved.is_relative_to(ready_dir.resolve())` (Python 3.11+).
- Never construct paths from request input.
- Only use filenames discovered from directory listing; reject resolved paths outside `blog-posts/ready/`.

### 5. Candidate validation rules

**Decision:** For each `.md` candidate, apply checks in order:

1. **exists** — path still exists after resolve
2. **is_regular_file** — `path.is_file()` and not a directory
3. **extension_md** — suffix `.md` (case-insensitive)
4. **readable** — attempt `path.read_bytes()` or `open()` read; catch `OSError`
5. **not_empty** — file size > 0 bytes after read attempt

Valid candidates appear in `valid_files` as objects: `{ "filename": "post.md", "relative_path": "blog-posts/ready/post.md", "size_bytes": N }`.

Invalid candidates appear in `invalid_files`: `{ "filename": "...", "relative_path": "...", "errors": ["not_empty", ...] }`.

**Rationale:** Minimal, testable rules aligned with user requirements. No Markdown parsing.

### 6. Run identifier and metadata file

**Decision:** Generate run id as UTC timestamp + short suffix for uniqueness:

```
run-20260704T223045Z-a1b2
```

Format: `run-{YYYYMMDD}T{HHMMSS}Z-{4-char-hex}` where hex is from `secrets.token_hex(2)`.

Metadata filename: `metadata/runs/{run_id}.json`.

**Metadata schema (minimum fields):**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "trigger": "POST /process-ready",
  "started_at": "2026-07-04T22:30:45Z",
  "completed_at": "2026-07-04T22:30:45Z",
  "status": "completed",
  "base_path": "/data/silverman-blog-linkedin",
  "folders_ready": true,
  "candidate_count": 2,
  "valid_count": 1,
  "invalid_count": 1,
  "ignored_count": 0,
  "valid_files": [...],
  "invalid_files": [...],
  "ignored_files": [...],
  "errors": []
}
```

**Rationale:** Timestamp-based ids are human-sortable and traceable in logs and n8n. Single JSON file per run supports future audit and retry workflows.

**Write behavior:** Creating run metadata is the **only** editorial mutation in this change. Metadata writes are attempted only when `metadata/runs/` exists, is a directory, and is writable.

| Condition | Metadata write | `metadata_written` | `metadata_path` |
|-----------|----------------|------------------|-----------------|
| `metadata/runs/` missing or not a directory | Skipped | `false` | `null` |
| `metadata/runs/` exists but not writable | Skipped | `false` | `null` |
| Folders not ready, metadata dir writable | Failed-run metadata written | `true` | `metadata/runs/{run_id}.json` |
| Scan completed, metadata dir writable | Completed-run metadata written | `true` | `metadata/runs/{run_id}.json` |
| Scan completed, metadata write fails (disk/permissions) | Attempted but failed | `false` | `null` |

`metadata_path` is always a **relative** path from the editorial base (e.g., `metadata/runs/run-20260704T223045Z-a1b2.json`). When metadata is not written, `metadata_path` is JSON `null` (not omitted).

### 7. POST /process-ready HTTP response contract

**Decision:** `POST /process-ready` accepts empty body (no required JSON). Response always JSON.

**Required fields (every response):**

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Generated run identifier |
| `status` | string | `completed` or `failed` |
| `metadata_written` | boolean | Whether run metadata was persisted |
| `metadata_path` | string \| null | Relative path `metadata/runs/{run_id}.json` when written; `null` when not |
| `folders_ready` | boolean | Aggregate editorial folder validation result |
| `candidate_count` | integer | Total Markdown candidates considered |
| `valid_count` | integer | Valid candidates |
| `invalid_count` | integer | Invalid candidates |
| `ignored_count` | integer | Ignored non-candidates |
| `valid_files` | array | Valid candidate details |
| `invalid_files` | array | Invalid candidate details |
| `ignored_files` | array | Ignored entry details |
| `errors` | array | Error code strings |

**Success scan (folders ready, metadata written):**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "status": "completed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260704T223045Z-a1b2.json",
  "folders_ready": true,
  "candidate_count": 2,
  "valid_count": 1,
  "invalid_count": 1,
  "ignored_count": 0,
  "valid_files": [...],
  "invalid_files": [...],
  "ignored_files": [...],
  "errors": []
}
```

**No candidates:**

- Same shape with counts zero, `status: "completed"`, `metadata_written: true`, and relative `metadata_path`.

**Folders not ready (metadata/runs/ writable):**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "status": "failed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260704T223045Z-a1b2.json",
  "folders_ready": false,
  "candidate_count": 0,
  "valid_count": 0,
  "invalid_count": 0,
  "ignored_count": 0,
  "valid_files": [],
  "invalid_files": [],
  "ignored_files": [],
  "errors": ["editorial_folders_not_ready"]
}
```

**metadata/runs/ missing, not a directory, or not writable:**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "status": "failed",
  "metadata_written": false,
  "metadata_path": null,
  "folders_ready": false,
  "candidate_count": 0,
  "valid_count": 0,
  "invalid_count": 0,
  "ignored_count": 0,
  "valid_files": [],
  "invalid_files": [],
  "ignored_files": [],
  "errors": ["metadata_runs_not_ready"]
}
```

Use `metadata_runs_not_writable` when the directory exists but is not writable; use `metadata_runs_not_ready` when it is missing or not a directory.

**Status values:** `completed` (scan finished, folders were ready), `failed` (folders not ready, metadata directory unavailable, or unrecoverable error).

**HTTP status codes:**

| Condition | HTTP |
|-----------|------|
| Authenticated, endpoint handled request | 200 |
| Missing/invalid auth | 401 |
| Unexpected server error | 500 |

**Rationale:** n8n branches on `valid_count`, `status`, `metadata_written`, and file lists. Relative `metadata_path` avoids leaking full host filesystem beyond configured `base_path` already exposed in `/health`. JSON `null` for `metadata_path` when not written keeps the field always present for predictable n8n parsing.

### 8. Read-only source file guarantee

**Decision:** Do not move, delete, rename, or modify files under `blog-posts/ready/`, `processed/`, or `error/`. The only write is run metadata under `metadata/runs/`.

**Rationale:** User scope explicitly defaults to read-only scanning. File moves belong to a later change after generation is implemented.

### 9. Docker and deployment

**Decision:** No Dockerfile changes required unless new dependencies are added (none expected). Existing compose mount must allow **write** to `metadata/runs/` (foundation compose example may mount read-only—update README/compose example to note write access needed for this endpoint).

**Rationale:** ADR-0003 container deployment unchanged; only metadata subdirectory needs write permission.

### 10. Logging

**Decision:** Log at INFO: run id, counts, status. Log filenames of valid/invalid at DEBUG only. Never log file contents or API key.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| `metadata/runs/` missing or not writable | Return `metadata_written: false`, `metadata_path: null`, and `metadata_runs_not_ready` or `metadata_runs_not_writable`; skip candidate scan |
| Read-only Docker mount blocks metadata writes | Document write requirement for `metadata/runs/` in README; compose example uses read-write mount or documents override |
| Large number of files in `ready/` | Accept for phase 1; no batch limit in this change; future change can add pagination/limits |
| Concurrent n8n triggers create duplicate run files | Acceptable—each run gets unique id; deduplication is orchestration concern |
| Empty vs invalid `.md` files | Report as `invalid_files` with `not_empty` error; n8n can branch on `invalid_count` |
| Symlink escape attempts | Resolve and verify path stays under `blog-posts/ready/` |

## Migration Plan

1. Implement auth, scan, metadata modules and route locally against temp editorial tree.
2. Run pytest; manual curl with Bearer token against local worker.
3. Update README with authentication and response examples.
4. On server deploy: ensure volume mount allows writes to `metadata/runs/`; verify n8n HTTP Request node sends Authorization header.
5. Rollback: revert to previous image; run metadata files are additive and harmless.

## Open Questions

- None blocking. Optional follow-up: whether a later change should auto-move invalid empty `.md` files to `error/` (out of scope here).
