## Context

### Umbrella and sequencing

This is **child change 4** under the active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`. Completed siblings:

| Slice | Change | Delivers |
|-------|--------|----------|
| 1 | `editorial-canon-and-linkedin-distribution-strategy` | `content-strategy/silverman-editorial-system.md`, spec `editorial-canon` |
| 2 | `flow-a-lifecycle-and-duplicate-prevention` | `campaign_lifecycle.py`, spec `flow-a-lifecycle` |
| 3 | `ready-post-editorial-validation` | `ready_post_validation.py`, spec `ready-post-editorial-validation` |
| 4 | `worker-blog-publishing-endpoint` (this change) | `POST /publish-blog-post`, `blog_publish_flow.py` |

The umbrella lifecycle diagram places **PUBLISH** after **VALIDATE**. Slice 3 delivers `validate_ready_post()` as a pure module; slice 4 is the first HTTP operation that performs publish side effects while preserving ADR-0001 (n8n calls worker over HTTP only).

### Current state

| Component | Blog publish behavior today |
|-----------|----------------------------|
| `github_pages_publish.py` | CLI bridge with dry-run default, `run_publish(apply=True)` writes `_posts/` and `assets/images/`; no git operations |
| `ready_post_validation.py` | `validate_ready_post()` gates ready posts; transitions `ready` → `validated` / `validation_failed` |
| `campaign_lifecycle.py` | Campaign metadata, blog idempotency key, states through `blog_published` |
| `main.py` | Existing authenticated endpoints; no blog publish route |
| n8n | No Flow A orchestration workflow yet (slice 7) |

The worker remains the filesystem and publish boundary. This child adds a **service module** plus **HTTP endpoint** callable from n8n and tests.

### Policy references

- Umbrella: `flow-a-automatic-blog-linkedin-publishing-roadmap`
- Validation: `openspec/specs/ready-post-editorial-validation/spec.md`, `ready_post_validation.py`
- Lifecycle: `openspec/specs/flow-a-lifecycle/spec.md`, `campaign_lifecycle.py`
- Publishing bridge: `openspec/specs/github-pages-blog-publishing/spec.md`, `github_pages_publish.py`
- Editorial canon: `openspec/specs/editorial-canon/spec.md`, `content-strategy/silverman-editorial-system.md`

## Goals / Non-Goals

**Goals:**

- Implement `publish_blog_post(base_path, source_relative_path, *, site_url=..., public_slug_override=..., github_pages_repo_path=...)` as the single service entry point for Flow A blog publishing.
- Add `POST /publish-blog-post` with API-key auth consistent with existing worker endpoints.
- Run safe preflight inspection, then `validate_ready_post()` for non-published campaigns; abort publish on validation failure with structured errors.
- Short-circuit idempotent `already_published` re-runs before validation when campaign metadata proves a prior successful publish.
- Transition campaign metadata: `validated` → `blog_publish_pending` → `blog_published` on success; record `blog_publish` object updates.
- Invoke `github_pages_publish.run_publish(..., apply=True)` for file writes to the configured public repo checkout.
- Enforce idempotency via `build_blog_publish_idempotency_key()` and bridge `check_no_overwrite()`.
- Return `BlogPublishResult` dataclass with fields required for n8n branching.
- Add `tests/test_blog_publish_flow.py` and HTTP endpoint tests using temp directories.

**Non-Goals:**

- LinkedIn derivative package generation, scheduling, or LinkedIn API publishing.
- n8n workflow JSON changes.
- Physical source file moves between editorial folders.
- Git commit or git push of the public GitHub Pages repository.
- Flow B automatic publish paths.
- Archiving umbrella or this child.

## Decisions

### 1. Service module + thin HTTP route

**Decision:** Implement `blog_publish_flow.py` with `publish_blog_post()` orchestrating validation, lifecycle, and bridge; wire `POST /publish-blog-post` in `main.py` as a thin adapter that loads settings, calls the service, and serializes the result.

**Rationale:** Matches slice 3 pattern (module-first, testable without HTTP) while delivering the HTTP contract n8n requires. Keeps FastAPI layer free of publish logic.

**Alternatives considered:** Put all logic in `main.py` — rejected; harder to test and couples HTTP to business rules.

### 2. Publish flow sequence: preflight, idempotent short-circuit, then validation

**Decision:** `publish_blog_post()` executes in this order:

1. **Preflight path/source inspection** — sufficient to derive `source_slug`, `public_slug`, `publication_date` (when possible), `source_content_sha256`, `campaign_id`, and the expected blog idempotency key via `build_blog_publish_idempotency_key()`. No campaign state transitions or public repo writes in this step.
2. **Idempotent `already_published` short-circuit** — if campaign metadata exists and `state` is `blog_published`, and `flow` is `flow_a`, and stored `source_content_sha256` matches the current source hash, and stored `blog_publish.idempotency_key` matches the expected key, and stored `source_public_url` exists: return `status: completed` with `blog_publish.status: already_published` **without** calling `validate_ready_post()` and **without** writing files.
3. **Validation gate** — for all other non-published campaigns, call `validate_ready_post()` before any publish side effect. Slice 3 rejects existing campaigns beyond `validated` (including `blog_published`) with `campaign_invalid_existing_state`; the short-circuit in step 2 avoids that path for legitimate idempotent re-runs.
4. **Validation failure** — if `validation.ok` is false, return `status: failed` with `blog_publish_validation_failed`; do not transition to `blog_publish_pending` or write public repo files.
5. **Publish progression** — when validation succeeds and campaign state is `validated`: transition `validated` → `blog_publish_pending`, invoke bridge apply, then transition `blog_publish_pending` → `blog_published`.

**Rationale:** Umbrella requires validation before first publish side effects. Child 3 `validate_ready_post()` accepts `ready` and `validated` states but rejects `blog_published` and later states; idempotent re-runs must bypass validation when metadata proves the same publish already completed.

**Alternatives considered:** Always call `validate_ready_post()` first — rejected; breaks idempotent `already_published` re-runs against `blog_published` campaigns.

### 3. Reuse GitHub Pages bridge; no duplicated publish logic

**Decision:** After lifecycle pre-checks and `blog_publish_pending` transition, call `github_pages_publish.run_publish(source_slug, apply=True, publication_date=..., public_slug_override=..., environ=...)` using `SILVERMAN_GITHUB_PAGES_REPO_PATH` from config/env. Use `plan.public_url` as `source_public_url`. Do not duplicate `build_plan`, `apply_plan`, or frontmatter logic.

**Implementation note (during `/opsx-apply`):** Inspect `src/silverman_blog_linkedin/github_pages_publish.py` and use the actual existing function signatures (`build_plan`, `apply_plan`, `run_publish`). Do not invent bridge APIs. If the existing bridge surface is CLI-oriented or awkward for service use, add a thin internal wrapper around those functions without duplicating publish logic. Do not rewrite the bridge unless strictly necessary.

**Rationale:** Single source of truth for Jekyll filename, image copy, and URL shape. Bridge already enforces non-overwrite.

**Alternatives considered:** Inline file copy in `blog_publish_flow.py` — rejected; drift risk vs CLI bridge.

### 4. Campaign state machine integration

**Decision:** Publish flow state handling:

| Step | Campaign state | Action |
|------|----------------|--------|
| Preflight idempotent hit | `blog_published` + `flow_a` + matching idempotency key + same content hash + stored `source_public_url` | Return `status: completed`, `blog_publish.status: already_published` without calling `validate_ready_post()` or writing files |
| Preflight invalid | `validation_failed`, `error`, or states beyond `blog_published` that would regress lifecycle (`derivatives_pending`, `derivatives_generated`, `distribution_scheduled`, `distribution_complete`, `flow_a_complete`) | Fail with `blog_publish_invalid_campaign_state` |
| Preflight | `ready` | Do not reject upfront; proceed to `validate_ready_post()` (validation may transition `ready` → `validated`) |
| Preflight | Content hash differs from stored campaign hash | Fail with `blog_publish_content_hash_changed` |
| Preflight | `flow_b` campaign | Fail with `blog_publish_flow_b_not_allowed` |
| After validation pass | `validated` | Transition to `blog_publish_pending` |
| After bridge apply | `blog_publish_pending` | Update `blog_publish`, set `source_public_url`, transition to `blog_published` |
| Bridge failure | `blog_publish_pending` | Transition to `error` or remain pending with `blog_publish.status: failed` and `error_code` |

`blog_published` is **not** an invalid state when it satisfies the idempotent `already_published` checks above.

Use `transition_state(..., actor="worker")` from `campaign_lifecycle.py`. Persist via `write_campaign_metadata`.

**Rationale:** Aligns with lifecycle spec adjacent transitions and umbrella Flow A sequencing. Keeps validation before first publish side effects while allowing idempotent re-runs after successful publish.

### 5. Idempotency and duplicate prevention

**Decision:**

- Compute expected key via `build_blog_publish_idempotency_key(source_slug, public_slug, publication_date, source_content_sha256)`.
- If campaign is `blog_published`, `flow` is `flow_a`, stored `blog_publish.idempotency_key` matches, content hash matches, and stored `source_public_url` exists, return completed / `already_published` without calling `validate_ready_post()` or `apply_plan`.
- If public repo targets exist (`check_no_overwrite` would fail) but campaign metadata does not prove same idempotency key, fail with `blog_publish_target_exists` — do not overwrite.
- Bridge `check_no_overwrite` remains the filesystem guard; service layer adds metadata-aware idempotency before apply.

**Rationale:** Matches lifecycle spec blog publish idempotency requirement and bridge non-overwrite policy.

### 6. HTTP request and response contract

**Decision:**

Request body (`PublishBlogPostRequest`):

| Field | Required | Notes |
|-------|----------|-------|
| `source_relative_path` | yes | Normalized like existing endpoints; must resolve under `blog-posts/ready/` |
| `site_url` | no | Default `https://silverman.pro` |
| `public_slug` | no | Passed to bridge only when safe override supported |

Response (`BlogPublishResult` / JSON):

| Field | Notes |
|-------|-------|
| `status` | `completed` or `failed` |
| `campaign_id`, `state`, `source_slug`, `public_slug`, `publication_date` | From campaign/validation |
| `source_relative_path`, `image_relative_path` | Editorial paths |
| `source_public_url` | From publish plan on success or stored on idempotent hit |
| `errors`, `warnings` | Stable codes |
| `validation` | Embedded validation summary (`ok`, key fields) |
| `blog_publish` | `{ idempotency_key, status, source_public_url, published_at, public_repo_path?, error_code? }` |
| `metadata_written`, `metadata_error_code` | Campaign write outcome |

`status: completed` covers both fresh publish and `already_published` idempotent outcomes; distinguish via `blog_publish.status`.

**Rationale:** n8n needs stable top-level `status` for branching plus detailed nested objects for logging.

### 7. Authentication and configuration

**Decision:** Protect `POST /publish-blog-post` with `Depends(require_api_key)` like `/process-file` and `/generate-linkedin-draft`. Load `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` and `SILVERMAN_GITHUB_PAGES_REPO_PATH` from existing `config.py` / `github_pages_publish.load_config`. Fail with `blog_publish_public_repo_not_configured` when public repo path is missing or layout invalid.

**Rationale:** Consistent security posture; reuses established env patterns.

### 8. Error code registry

**Decision:** Centralize stable publish error codes in `blog_publish_flow.py`:

- `blog_publish_validation_failed`
- `blog_publish_invalid_campaign_state`
- `blog_publish_content_hash_changed`
- `blog_publish_target_exists`
- `blog_publish_failed`
- `blog_publish_metadata_write_failed`
- `blog_publish_public_repo_not_configured`
- `blog_publish_source_not_ready`
- `blog_publish_flow_b_not_allowed`

**Rationale:** n8n and tests branch on exact strings; spec documents the set.

### 9. Metadata body exclusion preserved

**Decision:** Campaign metadata updates store paths, hashes, URLs, timestamps, and error codes only. Never persist full Markdown body or draft content. Use `write_campaign_metadata` sanitization from lifecycle module.

**Rationale:** Lifecycle spec metadata body exclusion applies to all Flow A writes.

### 10. Tests use temp directories

**Decision:** Unit and HTTP tests create temp editorial trees and fake public repo checkouts with `_posts/` and `assets/images/`. Use `apply=True` only in tests; assert file contents and idempotent re-run behavior.

**Rationale:** No dependency on operator paths or network; matches existing test patterns.

## Module shape

```
blog_publish_flow.py
├── BlogPublishResult (dataclass)
├── publish_blog_post(base_path, source_relative_path, *, site_url, public_slug_override, github_pages_repo_path, environ) -> BlogPublishResult
├── _preflight_inspect(...)  → source_slug, public_slug, publication_date, source_content_sha256, campaign_id, expected idempotency key
├── _check_idempotent_already_published(...)  → short-circuit before validate_ready_post()
├── _check_campaign_eligible_for_publish(...)  → invalid states, flow_b, content hash
├── _transition_and_publish(...)
└── BLOG_PUBLISH_ERROR_CODES (constants)

main.py
├── PublishBlogPostRequest (Pydantic)
└── POST /publish-blog-post → publish_blog_post(...)
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Validation + publish race if source file changes mid-request | Re-validate at start; compare content hash before apply; fail with `blog_publish_content_hash_changed` |
| Public repo target exists from manual operator publish without campaign metadata | Fail with `blog_publish_target_exists`; operator resolves manually |
| `SILVERMAN_GITHUB_PAGES_REPO_PATH` misconfigured on server | Validate repo layout before apply; stable error code |
| Partial failure after file write but before metadata save | Write metadata in `blog_publish_pending` before apply where possible; on apply success transition immediately; document manual recovery in tests |
| Endpoint exposes filesystem writes remotely | API-key auth; path validation; no arbitrary absolute paths in request |

## Migration Plan

1. Implement `blog_publish_flow.py` and unit tests locally with temp dirs.
2. Add `POST /publish-blog-post` route and HTTP tests.
3. Deploy updated worker container to Ubuntu server with `SILVERMAN_GITHUB_PAGES_REPO_PATH` set to local `silverberdi.github.io` clone.
4. Manual smoke test via `curl` with API key before n8n orchestration (slice 7).
5. Rollback: disable route usage in n8n (not yet wired); revert container image; uncommitted public repo files remain operator responsibility.

## Open Questions

- Whether to transition to `error` state vs leave `blog_publish_pending` with failed `blog_publish.status` on bridge failure — implement per spec scenario; prefer `error` when transition is valid from `blog_publish_pending`.
- Exact shape of `public_repo_path` in response (relative to repo root vs absolute) — store relative paths in metadata when safe.
- Whether HTTP layer should accept optional `publication_date` override — defer unless bridge already supports via frontmatter-derived date from validation result.
