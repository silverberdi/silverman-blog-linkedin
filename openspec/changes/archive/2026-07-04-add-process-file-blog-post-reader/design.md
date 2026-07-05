## Context

The worker foundation and `POST /process-ready` are implemented: FastAPI app, environment configuration, editorial folder validation (`paths.py`), API key authentication (`auth.py`), ready-folder scanning (`ready_scan.py`), run metadata persistence (`run_metadata.py`), and unauthenticated `GET /health`. n8n on the Linux server orchestrates content automation via HTTP Request nodes (ADR-0001).

This change adds the third endpoint: `POST /process-file`. Given a `relative_path` from a prior `POST /process-ready` scan, it validates the path, reads one Markdown blog post from `blog-posts/ready/`, writes run metadata, and returns structured JSON including raw Markdown content. It deliberately does **not** generate LinkedIn drafts, call OpenAI, or move source files—those belong to later changes.

Blog posts remain the canonical content source (ADR-0002). This endpoint is the single-file read gate before generation.

## Goals / Non-Goals

**Goals:**

- Expose `POST /process-file` with API key authentication (reuse existing `require_api_key` dependency).
- Accept JSON body `{ "relative_path": "blog-posts/ready/<filename>.md" }`.
- Reuse existing folder validation and metadata directory readiness checks before reading.
- Validate request-supplied paths with strict confinement to `blog-posts/ready/`; reject absolute paths, traversal, and invalid targets.
- Read Markdown as UTF-8; compute SHA-256 hash of file bytes.
- Write one run metadata JSON file per invocation under `metadata/runs/` when writable (file summary only—no raw content).
- Return structured JSON with run id, status, metadata fields, file summary, `markdown_content`, and errors—suitable for n8n IF nodes—with explicit nullability rules for file summary fields on failure.
- Keep `GET /health` and `POST /process-ready` unchanged.

**Non-Goals:**

- LinkedIn generation, OpenAI calls, campaign metadata, file moves to `processed/` or `error/`.
- n8n workflows, GitHub/LinkedIn publish, Dairector paths.
- Full Markdown/front-matter parsing, scheduling, batch processing.
- Modifying or deleting source blog post files.

## Decisions

### 1. New capability module layout

**Decision:** Add focused modules under `src/silverman_blog_linkedin/`:

```
src/silverman_blog_linkedin/
  file_reader.py         # request path validation + UTF-8 read + SHA-256
  run_metadata.py        # extend with process-file payload/response builders
  main.py                # add POST /process-file route (auth + orchestration)
tests/
  test_file_reader.py
  test_process_file.py
```

**Rationale:** Separates request-path validation and content reading from HTTP orchestration. Reuses `auth.py`, `paths.py`, and existing run metadata helpers. Keeps `main.py` as thin orchestration matching `POST /process-ready`.

**Alternatives considered:**

- **Extend `ready_scan.py`:** Scan logic is directory-listing scope; request-path validation is distinct.
- **Single `process_file.py`:** Acceptable but splits less cleanly between pure validation and HTTP concerns.

### 2. API key authentication

**Decision:** Reuse existing `require_api_key` dependency on `POST /process-file`. Same `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>` header and constant-time comparison. Update the `ready-blog-post-processing` spec delta to document auth applies to both processing endpoints.

**Rationale:** Auth dependency already exists and is endpoint-agnostic. No new env vars or header formats.

**Security:** Never include API key, submitted token, or file content in info-level logs. On auth failure, return `{ "detail": "Unauthorized" }` with HTTP `401`.

### 3. Request body contract

**Decision:** Require JSON body with single field:

```json
{ "relative_path": "blog-posts/ready/my-post.md" }
```

Use a Pydantic model for validation. FastAPI returns HTTP `422` for missing body, missing `relative_path`, wrong types, or empty string `relative_path`.

**422 boundary:** When body validation fails, FastAPI/Pydantic returns HTTP `422` with a standard validation error body. The process-file response/metadata contract does **not** apply—no `run_id`, no run metadata file, no normalized field set.

**Normalization:** Strip leading `./` and trailing slashes from `relative_path` before validation. Reject paths containing `..` segments (after normalization). Reject absolute paths (leading `/` or Windows drive prefixes). Once body validation passes, the normalized value is the canonical `relative_path` echoed in all subsequent response and metadata documents.

**Rationale:** n8n passes `relative_path` values from `POST /process-ready` `valid_files` entries. Strict body validation prevents ambiguous requests.

### 4. Request path validation rules

**Decision:** After normalization, validate in order:

1. **relative_path_required** — non-empty after normalization (422 at body validation layer)
2. **absolute_path** — must not be absolute
3. **path_traversal** — must not contain `..` components
4. **path_prefix** — must start with `blog-posts/ready/` (exact prefix; no bare `blog-posts/ready` without trailing filename)
5. **extension_md** — final component must have `.md` suffix (case-insensitive)
6. **path_confinement** — resolve `(base_path / relative_path).resolve()` and verify `resolved.is_relative_to(ready_dir.resolve())`
7. **file_exists** — resolved path exists
8. **is_regular_file** — not a directory
9. **readable** — attempt read; catch `OSError`
10. **not_empty** — size > 0 bytes

Valid paths are direct children of `blog-posts/ready/` only (no subdirectories), matching `POST /process-ready` non-recursive discovery scope. A path like `blog-posts/ready/subdir/post.md` fails `path_prefix` / confinement if subdirectories are not allowed—or fails because subdirs are ignored in process-ready. **Decision:** Reject any path whose relative form contains more path segments than `blog-posts/ready/<filename>` (exactly one filename segment under ready). Error code: `path_not_direct_child`.

**Rationale:** Aligns with flat `ready/` layout from process-ready. Prevents traversal via symlinks or `..`.

### 5. Content reading and hashing

**Decision:** Read file bytes with `Path.read_bytes()`. Decode as UTF-8 with `errors="strict"`; on `UnicodeDecodeError`, treat as unreadable (`not_utf8` error). Compute `content_sha256` as lowercase hex digest of raw bytes (before decode).

**Rationale:** Blog posts are UTF-8 Markdown. Strict decode catches binary/corrupt files early. Hash of bytes supports deduplication and audit without storing content in metadata.

### 6. Response and metadata field nullability

**Decision:** Once request body validation passes, HTTP response and run metadata (when written) share the same file summary fields with identical nullability rules. `markdown_content` appears in the HTTP response only—never in metadata.

| Field | Always present | Null when |
|-------|----------------|-----------|
| `relative_path` | Yes (after valid body) | Never null after body validation; always the normalized request value |
| `filename` | Key always present | Null when final path component cannot be safely derived from the normalized path (e.g. bare `blog-posts/ready` with no filename segment) |
| `size_bytes` | Key always present | Null unless file is successfully stat/read enough to determine size |
| `content_sha256` | Key always present | Null unless file bytes are successfully read |
| `markdown_content` | Response only | Null unless UTF-8 decode succeeds on a valid non-empty file read; never in metadata |

**Examples by failure mode:**

| Failure | `relative_path` | `filename` | `size_bytes` | `content_sha256` | `markdown_content` |
|---------|-----------------|------------|--------------|------------------|-------------------|
| Folders not ready | normalized | derived or null | null | null | null (response) |
| Path validation failed | normalized rejected path | derived or null | null | null | null (response) |
| File not found / is directory | normalized | derived or null | null | null | null (response) |
| File empty | normalized | derived or null | 0 or null* | null | null (response) |
| File unreadable / not UTF-8 | normalized | derived or null | null or size if stat succeeded | null | null (response) |
| Successful read | normalized | populated | populated | populated | populated (response only) |

\*For empty files, `size_bytes` MAY be `0` when stat succeeds before read rejection, or `null` if size was not determined—implementation MUST NOT populate `content_sha256` or `markdown_content`.

**Metadata on failed runs:** When `metadata/runs/` is writable and metadata is written, the JSON file includes the same summary fields with nulls where unavailable. `markdown_content` is never written to metadata.

**Metadata/runs unavailable:** `metadata_written: false`, `metadata_path: null`; no metadata file. Response still includes normalized `relative_path` and null file summary fields as applicable.

**Rationale:** Requiring non-null `filename`, `size_bytes`, or `content_sha256` on failed runs would force fabricated values. Normalized `relative_path` preserves traceability for n8n even when pre-checks or validation fail before a successful read.

### 7. Run metadata: exclude full content

**Decision:** Run metadata JSON for `POST /process-file` includes file summary only (never `markdown_content`):

**Successful read metadata:**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "trigger": "POST /process-file",
  "started_at": "2026-07-04T22:30:45Z",
  "completed_at": "2026-07-04T22:30:45Z",
  "status": "completed",
  "base_path": "/data/silverman-blog-linkedin",
  "folders_ready": true,
  "relative_path": "blog-posts/ready/my-post.md",
  "filename": "my-post.md",
  "size_bytes": 1234,
  "content_sha256": "abc123...",
  "errors": []
}
```

**Failed path validation metadata:**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "trigger": "POST /process-file",
  "started_at": "2026-07-04T22:30:45Z",
  "completed_at": "2026-07-04T22:30:45Z",
  "status": "failed",
  "base_path": "/data/silverman-blog-linkedin",
  "folders_ready": true,
  "relative_path": "blog-posts/processed/post.md",
  "filename": "post.md",
  "size_bytes": null,
  "content_sha256": null,
  "errors": ["path_outside_ready"]
}
```

**Failed folder validation metadata:**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "trigger": "POST /process-file",
  "started_at": "2026-07-04T22:30:45Z",
  "completed_at": "2026-07-04T22:30:45Z",
  "status": "failed",
  "base_path": "/data/silverman-blog-linkedin",
  "folders_ready": false,
  "relative_path": "blog-posts/ready/my-post.md",
  "filename": "my-post.md",
  "size_bytes": null,
  "content_sha256": null,
  "errors": ["editorial_folders_not_ready"]
}
```

**Alternatives considered:**

- **Store full content in metadata:** Rejected—duplicates canonical source.
- **Omit null keys on failure:** Rejected—n8n branching requires predictable field presence.

### 8. Orchestration order

**Decision:** Match `POST /process-ready` pre-check pattern:

1. Authenticate request.
2. Validate request body (422 on shape errors—no process-file contract applies).
3. Normalize `relative_path`; generate run id; record `started_at`.
4. Check `metadata/runs/` writability.
5. Validate all editorial folders → `folders_ready`.
6. Branch:
   - Metadata dir unavailable → no file read, no metadata write; return HTTP `200` with normalized `relative_path`, null file summary fields (`filename` derived or null, `size_bytes`/`content_sha256`/`markdown_content` null), `metadata_written: false`, `metadata_path: null`, `errors: ["metadata_runs_not_ready"|"metadata_runs_not_writable"]`.
   - Folders not ready, metadata dir writable → no file read; write failed run metadata with normalized `relative_path` and null unavailable summary fields; return HTTP `200`, `status: "failed"`, `folders_ready: false`, `metadata_written: true`, `errors: ["editorial_folders_not_ready"]`.
   - Both ready → validate path and read file → write run metadata → return response.

**Rationale:** Consistent operational semantics with process-ready. Normalized `relative_path` is always echoed after valid body for traceability.

### 9. POST /process-file HTTP response contract

**Decision:** Response always JSON when the process-file contract applies (authenticated request with valid body). Required fields on every such response:

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Generated run identifier |
| `status` | string | `completed` or `failed` |
| `metadata_written` | boolean | Whether run metadata was persisted |
| `metadata_path` | string \| null | Relative `metadata/runs/{run_id}.json` when written; `null` when not |
| `folders_ready` | boolean | Aggregate editorial folder validation |
| `relative_path` | string | Normalized request path (always present after valid body) |
| `filename` | string \| null | Final path component when safely derivable; otherwise `null` |
| `size_bytes` | integer \| null | File size when stat/read determines it; otherwise `null` |
| `content_sha256` | string \| null | SHA-256 hex when bytes successfully read; otherwise `null` |
| `markdown_content` | string \| null | UTF-8 content when read and decode succeed; otherwise `null` |
| `errors` | array | Error code strings |

**Successful read:**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "status": "completed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260704T223045Z-a1b2.json",
  "folders_ready": true,
  "relative_path": "blog-posts/ready/my-post.md",
  "filename": "my-post.md",
  "size_bytes": 42,
  "content_sha256": "a1b2c3...",
  "markdown_content": "# Title\n\nBody text.",
  "errors": []
}
```

**Path validation failure:**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "status": "failed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260704T223045Z-a1b2.json",
  "folders_ready": true,
  "relative_path": "blog-posts/processed/post.md",
  "filename": "post.md",
  "size_bytes": null,
  "content_sha256": null,
  "markdown_content": null,
  "errors": ["path_outside_ready"]
}
```

**Invalid target file (file property failure after path validation):**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "status": "failed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260704T223045Z-a1b2.json",
  "folders_ready": true,
  "relative_path": "blog-posts/ready/empty.md",
  "filename": "empty.md",
  "size_bytes": null,
  "content_sha256": null,
  "markdown_content": null,
  "errors": ["file_empty"]
}
```

**Folders not ready (metadata writable):**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "status": "failed",
  "metadata_written": true,
  "metadata_path": "metadata/runs/run-20260704T223045Z-a1b2.json",
  "folders_ready": false,
  "relative_path": "blog-posts/ready/my-post.md",
  "filename": "my-post.md",
  "size_bytes": null,
  "content_sha256": null,
  "markdown_content": null,
  "errors": ["editorial_folders_not_ready"]
}
```

**Metadata/runs unavailable:**

```json
{
  "run_id": "run-20260704T223045Z-a1b2",
  "status": "failed",
  "metadata_written": false,
  "metadata_path": null,
  "folders_ready": false,
  "relative_path": "blog-posts/ready/my-post.md",
  "filename": "my-post.md",
  "size_bytes": null,
  "content_sha256": null,
  "markdown_content": null,
  "errors": ["metadata_runs_not_ready"]
}
```

**HTTP status codes:**

| Condition | HTTP |
|-----------|------|
| Authenticated, valid body, endpoint handled request | 200 |
| Missing/invalid auth | 401 |
| Invalid JSON body / missing `relative_path` / empty `relative_path` | 422 (FastAPI validation; process-file contract does not apply) |
| Unexpected server error | 500 |

**Rationale:** n8n receives Markdown in response for immediate downstream use (future OpenAI step). Predictable field presence with JSON `null` for unavailable values keeps branching reliable without fabricated data.

### 10. Read-only source file guarantee

**Decision:** Do not move, delete, rename, or modify files under `blog-posts/ready/`, `processed/`, or `error/`. The only write is run metadata under `metadata/runs/`.

**Rationale:** User scope explicitly requires read-only source handling. File moves belong to a later change after generation.

### 11. Docker and deployment

**Decision:** No new dependencies. Existing compose mount must allow write to `metadata/runs/` (already documented for process-ready). No Dockerfile changes expected.

### 12. Logging

**Decision:** Log at INFO: run id, status, relative_path, size_bytes. Log content SHA-256 at DEBUG. Never log `markdown_content`, API key, or submitted token.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Large Markdown files inflate HTTP response | Accept for phase 1; n8n and worker on same network; future change can add size limits |
| Symlink escape attempts | Resolve path and verify confinement under `blog-posts/ready/` |
| UTF-8 decode failures | Report `not_utf8` error; do not silently replace characters |
| Concurrent reads of same file | Acceptable—read-only; each run gets unique id |
| n8n passes path from stale process-ready scan | File may be missing; return `file_not_found` with failed status |
| Metadata duplication without content | Hash + relative_path sufficient for traceability; content stays canonical in `ready/` |

## Migration Plan

1. Implement `file_reader.py`, extend `run_metadata.py`, add route in `main.py`.
2. Run pytest; manual curl with Bearer token and sample `relative_path`.
3. Update README with request/response examples.
4. On server deploy: no new env vars; same API key and volume mount as process-ready.
5. Rollback: revert to previous image; run metadata files are additive.

## Open Questions

- None blocking. Optional follow-up: maximum file size limit for HTTP response (out of scope here).
