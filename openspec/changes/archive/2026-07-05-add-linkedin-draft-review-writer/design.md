## Context

The worker foundation, `POST /process-ready`, and `POST /process-file` are implemented: FastAPI app, environment configuration, editorial folder validation (`paths.py`), API key authentication (`auth.py`), ready-folder scanning (`ready_scan.py`), blog post file reading (`file_reader.py`), and run metadata persistence (`run_metadata.py`). n8n on the Linux server orchestrates content automation via HTTP Request nodes (ADR-0001).

This change adds the fourth endpoint: `POST /write-linkedin-draft`. After n8n (or an external LLM step) has blog Markdown from `POST /process-file` and generated LinkedIn draft text, it calls this endpoint to persist one review draft under `linkedin-posts/review/` with run metadata. The endpoint deliberately does **not** call DeepSeek, OpenAI, or any AI provider; does **not** re-read the source blog file; does **not** move source files; and does **not** publish anywhere.

Blog posts remain the canonical content source (ADR-0002). The draft file in `linkedin-posts/review/` is the canonical review artifact for this step; run metadata records traceability without duplicating full draft body text.

## Goals / Non-Goals

**Goals:**

- Expose `POST /write-linkedin-draft` with API key authentication (reuse existing `require_api_key` dependency).
- Accept JSON body with `source_relative_path`, `draft_content`, and optional `source_content_sha256`, `title`, `slug_hint`.
- Validate `metadata/runs/` and `linkedin-posts/review/` writability before any file write.
- Validate `source_relative_path` shape (same confinement rules as `POST /process-file`) without reading the source blog file on disk.
- Write one draft Markdown file under `linkedin-posts/review/` using server-generated filenames only.
- Write run metadata under `metadata/runs/` when writable (summary fields only—no full `draft_content`).
- Return structured JSON with `run_id`, `status`, draft/metadata flags and paths, hashes, `size_bytes`, and `errors`.
- Keep `GET /health`, `POST /process-ready`, and `POST /process-file` unchanged.

**Non-Goals:**

- AI/LLM integration (DeepSeek, OpenAI, ChatGPT, local models).
- LinkedIn or GitHub publishing.
- Moving or modifying source blog files.
- Re-reading source blog post content for existence or validation.
- Campaign metadata, n8n workflows, Dairector paths, scheduling.
- Front matter injection into draft files (keep draft body exactly as submitted).

## Decisions

### 1. Module layout

**Decision:** Add focused modules under `src/silverman_blog_linkedin/`:

```
src/silverman_blog_linkedin/
  draft_writer.py        # source path shape validation, filename generation, UTF-8 draft write
  run_metadata.py        # extend with write-linkedin-draft payload/response builders
  main.py                # add POST /write-linkedin-draft route (auth + orchestration)
tests/
  test_draft_writer.py
  test_write_linkedin_draft.py
```

Reuse `normalize_relative_path` and path-shape validation patterns from `file_reader.py` (extract shared helpers or import where practical). Reuse `check_metadata_runs_ready`, `generate_run_id`, and `write_run_metadata`.

**Rationale:** Mirrors the `file_reader.py` / `process-file` split. Keeps HTTP orchestration thin in `main.py`.

**Alternatives considered:**

- **Single `linkedin_draft.py`:** Acceptable but mixes pure validation/filename logic with HTTP concerns.
- **Extend `file_reader.py`:** Reader is read-only; draft writing is a distinct responsibility.

### 2. API key authentication

**Decision:** Reuse existing `require_api_key` on `POST /write-linkedin-draft`. Same `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>` header. Update the `ready-blog-post-processing` spec delta to document auth applies to `POST /write-linkedin-draft` alongside `POST /process-ready` and `POST /process-file`.

**Security:** Never include API key or submitted token in responses, metadata, or info-level logs. Auth failure returns HTTP `401`.

### 3. Request body contract

**Decision:** Require JSON body:

```json
{
  "source_relative_path": "blog-posts/ready/my-post.md",
  "draft_content": "LinkedIn draft text here.",
  "source_content_sha256": "abc123...",
  "title": "Optional human title",
  "slug_hint": "executive"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `source_relative_path` | Yes | Non-empty string after normalization |
| `draft_content` | Yes | Non-empty string after `.strip()` |
| `source_content_sha256` | No | Echoed in response/metadata when provided; not validated against disk |
| `title` | No | Stored in metadata only when provided |
| `slug_hint` | No | Optional variant label; affects filename when provided (see §6) |

Use a Pydantic model configured with `model_config = ConfigDict(extra="forbid")` (or equivalent) so **any unexpected field** in the request body causes HTTP `422`. Allowed fields only: `source_relative_path`, `draft_content`, `source_content_sha256`, `title`, `slug_hint`.

HTTP `422` for: missing body, wrong types, **extra fields** (including `draft_relative_path`, `output_path`, `filename`, `target_path`, or any other client-supplied output path), empty `source_relative_path` after normalization, or `draft_content` empty/whitespace-only after strip.

**422 boundary:** When body validation fails, FastAPI/Pydantic returns HTTP `422`. The write-linkedin-draft response/metadata contract does **not** apply—no `run_id`, no metadata file, no draft write.

**Normalization:** Strip leading `./` and trailing slashes from `source_relative_path` before shape validation (reuse `normalize_relative_path`).

**Rationale:** Structural and empty-content rejections belong at the HTTP validation layer, consistent with `POST /process-file` empty `relative_path` → `422`. Rejecting extra fields at validation time is deterministic—no silent ignore of client-supplied output paths. Once body validation passes, all outcomes use HTTP `200` with `status` `completed` or `failed`.

### 4. Editorial folder validation scope

**Decision:** **Targeted write-path validation only**—do not require full aggregate editorial folder readiness before writing a draft.

This endpoint checks:

1. `metadata/runs/` — exists, is directory, writable (required before any metadata write; checked first).
2. `linkedin-posts/review/` — exists, is directory, writable (required before draft write).

It does **not** gate on `blog-posts/processed`, `prompts`, or other folders. The HTTP response for this endpoint does **not** include `folders_ready` (unlike process-ready/process-file).

**Rationale:** Persisting an externally generated draft only needs the review output folder and metadata directory. Requiring every editorial folder (including `blog-posts/ready` existence) would block draft persistence when unrelated layout gaps exist. n8n can still call `GET /health` for full layout status. This matches the user's "at minimum" guidance and keeps the write path independent of source-file processing state.

**Alternatives considered:**

- **Full `validate_folders()` gate:** Rejected—overly strict for a write-only endpoint that does not touch blog-post folders.
- **No folder checks:** Rejected—must verify review and metadata targets before writing.

### 5. Source path shape validation (no file read)

**Decision:** After body validation, validate `source_relative_path` shape using the same rules as `POST /process-file` path validation, but **stop before** `file_exists` / read checks:

1. **absolute_path** — must not be absolute
2. **path_traversal** — must not contain `..`
3. **path_prefix** — must start with `blog-posts/ready/`
4. **extension_md** — final component `.md` (case-insensitive)
5. **path_not_direct_child** — exactly `blog-posts/ready/<filename>` (one segment under ready)
6. **path_confinement** — resolved path under `blog-posts/ready/` relative to base (defense in depth; no disk read)

Do **not** verify the source file exists, is readable, or is non-empty. Traceability is via the submitted path string (and optional `source_content_sha256` from a prior `POST /process-file` response).

**Rationale:** n8n may write drafts while the source remains in `ready/` or after partial pipeline steps; shape validation prevents traversal and arbitrary paths without coupling to current file state.

### 6. Draft filename generation

**Decision:** Server generates all output paths. The client MUST NOT supply `draft_relative_path` or any output path.

**Base pattern:**

```
linkedin-posts/review/{utc_timestamp}-{safe_source_stem}.md
```

- `utc_timestamp`: `YYYYMMDDTHHMMSSZ` (UTC, no colons—filesystem-safe)
- `safe_source_stem`: stem of source filename (`my-post` from `my-post.md`), sanitized to `[a-zA-Z0-9_-]+` (collapse invalid chars to `-`, trim edges, fallback `draft` if empty)

**With optional `slug_hint`:**

```
linkedin-posts/review/{utc_timestamp}-{safe_source_stem}-{safe_slug_hint}.md
```

`sanitize(slug_hint)` with same rules when provided.

**Collision avoidance and no-overwrite creation:** The worker MUST **never overwrite** an existing draft file. Draft creation MUST use exclusive creation (`open(..., "x")`, `os.O_CREAT | os.O_EXCL`, or equivalent) so concurrent requests cannot race between existence check and write.

1. Attempt exclusive write at the base generated path.
2. On `FileExistsError` / `EEXIST`, append `-{run_id_suffix}` (last 4 hex chars of run id) and retry exclusive write once.
3. On second collision, append full run id segment and retry exclusive write once.
4. If all allowed collision retries fail, do **not** overwrite; return HTTP `200` with `status: failed`, `draft_written: false`, `draft_relative_path: null`, `metadata_written: true` (when `metadata/runs/` writable), and `errors: ["draft_path_collision"]`.

**Confinement:** Resolve `(base_path / draft_relative_path).resolve()` and verify `is_relative_to(review_dir.resolve())`.

**Rationale:** Deterministic-ish names aid human review (`my-post` visible in filename). Timestamp ordering supports multiple runs. `slug_hint` supports multiple variants per source. Exclusive creation plus run-id suffix retries prevents overwrite under concurrency without client-chosen paths.

**Alternatives considered:**

- **UUID-only filenames:** Rejected—harder for reviewers to correlate with source posts.
- **Client-supplied filename:** Rejected—security and path injection risk.

### 7. Draft file content

**Decision:** Write `draft_content` as UTF-8 bytes of the string **as submitted** (after body validation passed). Optionally ensure a single trailing newline if the content is non-empty and does not already end with `\n`—the only permitted transformation.

Do **not** add YAML front matter, HTML comments, or hidden metadata to the draft file. Optional `title` and `slug_hint` appear in run metadata only.

**Rationale:** Reviewers edit the draft file directly; what n8n sends is what they see. Metadata carries traceability fields.

### 8. Content hashing and size

**Decision:** Compute `draft_content_sha256` as lowercase hex SHA-256 of the UTF-8 bytes actually written (after optional trailing-newline normalization). `size_bytes` is the byte length written.

`source_content_sha256` is taken from the request when provided and echoed in response/metadata unchanged; the worker does not recompute or verify it against disk.

### 9. Run metadata (exclude full draft body)

**Decision:** Run metadata JSON includes summary fields only—never `draft_content`:

**Successful write metadata (example):**

```json
{
  "run_id": "run-20260705T150045Z-a1b2",
  "trigger": "POST /write-linkedin-draft",
  "started_at": "2026-07-05T15:00:45Z",
  "completed_at": "2026-07-05T15:00:45Z",
  "status": "completed",
  "base_path": "/data/silverman-blog-linkedin",
  "source_relative_path": "blog-posts/ready/my-post.md",
  "draft_relative_path": "linkedin-posts/review/20260705T150045Z-my-post-executive.md",
  "source_content_sha256": "abc123...",
  "draft_content_sha256": "def456...",
  "size_bytes": 512,
  "title": "Optional title",
  "slug_hint": "executive",
  "draft_written": true,
  "errors": []
}
```

Omit `title` / `slug_hint` keys when not provided. On failure before draft write, `draft_relative_path` is `null`, `draft_written` is `false`, `draft_content_sha256` and `size_bytes` are `null`.

**Partial failure — draft written, metadata write failed:** If the draft file is successfully created but `write_run_metadata()` fails afterward, the worker MUST NOT delete or roll back the draft file. This is a partial failure: the review artifact exists but the run was not audited. Return HTTP `200` with `status: failed`, `draft_written: true`, populated `draft_relative_path`, `draft_content_sha256`, and `size_bytes`, `metadata_written: false`, `metadata_path: null`, and `errors: ["metadata_write_failed"]`. No metadata JSON file is created for this run id.

**Rationale:** Draft file is canonical for review content; metadata supports audit and n8n branching without duplication. Retaining the draft on metadata failure avoids losing reviewer-visible work; n8n can branch on `metadata_write_failed` while the draft remains in `linkedin-posts/review/`.

### 10. Orchestration order

**Decision:**

1. Authenticate request (`401` on failure).
2. Validate request body (`422` on failure—no endpoint contract).
3. Normalize `source_relative_path`; generate `run_id`; record `started_at`.
4. Check `metadata/runs/` writability.
5. Branch:
   - **Metadata dir unavailable** → no draft write, no metadata write; HTTP `200`, `status: failed`, `metadata_written: false`, `draft_written: false`, null paths, `errors: [metadata_runs_not_ready|metadata_runs_not_writable]`.
6. Check `linkedin-posts/review/` writability.
7. Validate `source_relative_path` shape (no file read).
8. Branch on review dir or source path failure:
   - **Review dir unavailable** → no draft write; write failed run metadata; HTTP `200`, `status: failed`, `draft_written: false`, `draft_relative_path: null`, applicable errors.
   - **Source path shape failure** → no draft write; write failed run metadata; HTTP `200`, `status: failed`, `errors` with path error codes.
9. Generate draft filename; write draft file UTF-8 using exclusive creation (no overwrite); on `draft_path_collision` after retries, write failed run metadata and return failed response without draft.
10. Write run metadata.
11. Branch on metadata write outcome:
    - **Metadata write succeeds** → HTTP `200`, `status: completed`, `draft_written: true`, `metadata_written: true`, populated paths and hashes.
    - **Metadata write fails after successful draft** → HTTP `200`, `status: failed`, `draft_written: true`, populated `draft_relative_path` / hashes / `size_bytes`, `metadata_written: false`, `metadata_path: null`, `errors: ["metadata_write_failed"]`; draft file is **not** deleted or rolled back.

**Rationale:** Metadata dir checked first (matches process-ready/process-file). Failed business outcomes still HTTP `200` for n8n IF-node consistency. Partial failure preserves the review artifact when audit metadata cannot be written.

### 11. HTTP response contract

**Decision:** Response JSON when the endpoint contract applies (authenticated, valid body):

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Generated run identifier |
| `status` | string | `completed` or `failed` |
| `metadata_written` | boolean | Whether run metadata was persisted |
| `metadata_path` | string \| null | `metadata/runs/{run_id}.json` when written |
| `draft_written` | boolean | Whether draft file was created |
| `draft_relative_path` | string \| null | Relative path under review when written |
| `source_relative_path` | string | Normalized source path (always present after valid body) |
| `source_content_sha256` | string \| null | From request when provided; else `null` |
| `draft_content_sha256` | string \| null | Hash of written bytes when draft written; else `null` |
| `size_bytes` | integer \| null | Written byte length when draft written; else `null` |
| `errors` | array | Error code strings |

**HTTP status codes:**

| Condition | HTTP |
|-----------|------|
| Authenticated, valid body, endpoint handled request | 200 |
| Missing/invalid auth | 401 |
| Invalid JSON body / missing required fields / empty `draft_content` after strip / **extra unexpected body fields** | 422 |
| Unexpected server error | 500 |

**Partial failure example (draft written, metadata write failed):**

```json
{
  "run_id": "run-20260705T150045Z-a1b2",
  "status": "failed",
  "metadata_written": false,
  "metadata_path": null,
  "draft_written": true,
  "draft_relative_path": "linkedin-posts/review/20260705T150045Z-my-post-executive.md",
  "source_relative_path": "blog-posts/ready/my-post.md",
  "source_content_sha256": "abc123...",
  "draft_content_sha256": "def456...",
  "size_bytes": 512,
  "errors": ["metadata_write_failed"]
}
```

### 12. Source and draft immutability guarantees

**Decision:** Do not move, delete, rename, or modify files under `blog-posts/`. The only writes are: one new file under `linkedin-posts/review/` (on success) and run metadata under `metadata/runs/`.

### 13. Docker and deployment

**Decision:** No new dependencies or environment variables. Existing compose mount must allow write to `linkedin-posts/review/` and `metadata/runs/`. No Dockerfile changes expected.

### 14. Logging

**Decision:** Log at INFO: `run_id`, `status`, `source_relative_path`, `draft_relative_path` (when written), `size_bytes`. Log content hashes at DEBUG. Never log `draft_content`, API key, or submitted token.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Draft written for non-existent source path | Acceptable—shape-only validation; optional `source_content_sha256` links to prior read; human review catches mismatches |
| Filename collision under concurrent requests | Exclusive file creation (`O_EXCL` / `open(..., "x")`); run-id suffix retries; `draft_path_collision` if all retries fail—never overwrite |
| Metadata write fails after draft created | Return `metadata_write_failed`; retain draft file (partial failure—artifact exists, run not audited) |
| Large draft bodies in HTTP request | Accept for phase 1; same network as n8n; future change can add size limits |
| Symlink escape via review dir | Resolve path and verify confinement under `linkedin-posts/review/` |
| Partial write on disk failure | Use atomic write pattern (write temp + rename) where practical |
| No `folders_ready` in response | n8n uses `GET /health` for full layout; this endpoint reports targeted errors |

## Migration Plan

1. Implement `draft_writer.py`, extend `run_metadata.py`, add route in `main.py`.
2. Run pytest; manual curl with Bearer token and sample draft payload.
3. Update README with request/response examples.
4. On server deploy: no new env vars; same API key and volume mount; ensure `linkedin-posts/review/` is writable in container.
5. Rollback: revert to previous image; draft and metadata files are additive.

## Open Questions

- None blocking. Optional follow-up: maximum `draft_content` size limit (out of scope here).
