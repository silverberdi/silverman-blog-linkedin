## Context

### Umbrella and sequencing

This is **child change 3** under the active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`. Completed siblings:

| Slice | Change | Delivers |
|-------|--------|----------|
| 1 | `editorial-canon-and-linkedin-distribution-strategy` | `content-strategy/silverman-editorial-system.md`, spec `editorial-canon` |
| 2 | `flow-a-lifecycle-and-duplicate-prevention` | `campaign_lifecycle.py`, spec `flow-a-lifecycle` |
| 3 | `ready-post-editorial-validation` (this change) | Validation gate before blog publish |

The umbrella lifecycle diagram places **VALIDATE** as step 1 after a user places files in `blog-posts/ready/`. Flow A treats validation pass as pre-approval; no human gate follows.

### Current state

| Component | Validation behavior today |
|-----------|---------------------------|
| `POST /process-ready` | Lists ready Markdown files; no editorial validation |
| `POST /process-file` | Reads file content; no structural/canon checks |
| `github_pages_publish.py` | CLI publish-time checks (slug, paths, frontmatter prep); not invoked for Flow A gate |
| `campaign_lifecycle.py` | Campaign metadata, `ready` → `validated` / `validation_failed` transitions |
| Editorial canon | Policy documented; not enforced at runtime |

The worker remains the filesystem and validation boundary (ADR-0001). This child implements a **pure module** callable from tests and future HTTP/n8n orchestration children.

### Policy references

- Umbrella: `flow-a-automatic-blog-linkedin-publishing-roadmap`
- Canonical spec: `openspec/specs/editorial-canon/spec.md`
- Canonical artifact: `content-strategy/silverman-editorial-system.md` (`#blog-post-rules`, `#anti-ai-writing-rules`, `#flow-a-vs-flow-b`)
- Lifecycle: `openspec/specs/flow-a-lifecycle/spec.md`, `campaign_lifecycle.py`
- Slug/URL: `openspec/specs/github-pages-blog-publishing/spec.md`, `github_pages_publish.py`

## Goals / Non-Goals

**Goals:**

- Implement `validate_ready_post(base_path, source_relative_path)` as the single entry point for Flow A ready-post validation.
- Enforce structural/publishing blockers: file location, `.md` extension, slug safety, PNG companion image, required frontmatter and values, empty body, H1/title alignment, TODO/secret markers, unsupported local images, non-Silverman publish instructions, embedded LinkedIn drafts.
- Apply anti-AI editorial heuristics as **warnings** for user-provided Flow A posts (non-blocking unless paired with structural violation).
- Create or update campaign metadata using lifecycle helpers; transition `ready` → `validated` on success or `ready` → `validation_failed` on blocking errors.
- Record warnings in campaign metadata `warnings[]` on success.
- Return `ReadyPostValidationResult` dataclass suitable for JSON serialization by future HTTP layer.
- Add comprehensive unit tests with fixture posts under `tests/fixtures/` or inline temp directories.

**Non-Goals:**

- `POST /validate-ready-post` HTTP endpoint (deferred; module-first).
- GitHub Pages publish, LinkedIn package generation, scheduling, n8n JSON, Flow B.
- Physical file moves to `blog-posts/error/` (metadata-only `source_file_status.location = error` via lifecycle transition).
- Runtime loading/parsing of `silverman-editorial-system.md` (rules encoded in module + spec).
- Archiving umbrella or this child.

## Decisions

### 1. Pure module, no HTTP in this child

**Decision:** Implement `ready_post_validation.py` as a library module with `validate_ready_post()`; no FastAPI route.

**Rationale:** Umbrella sequences validation logic before `worker-blog-publishing-endpoint`. A pure module keeps this child focused, testable without HTTP, and reusable from CLI tests and a future endpoint child.

**Alternatives considered:** Add `POST /validate-ready-post` now — rejected; couples validation to HTTP contract before module behavior is proven.

### 2. Reuse existing slug, date, and URL helpers

**Decision:** Import `derive_public_slug`, `validate_slug`, `public_url`, and frontmatter split logic from `github_pages_publish.py` (or extract shared helpers only if import coupling is awkward). Use `campaign_lifecycle.compute_source_content_sha256`, `build_initial_campaign_metadata`, `transition_state`, `write_campaign_metadata`, and `read_campaign_metadata`.

**Rationale:** Single source of truth for slug prefix stripping and public URL shape; avoids drift between validation and publish bridge.

**Alternatives considered:** Duplicate slug regex in validation module — rejected.

### 3. Blocking vs warning classification

**Decision:** Structural and policy violations are **errors** (block `ok: false`). Anti-AI heuristics from editorial canon (`#anti-ai-writing-rules`) are **warnings** for Flow A user blogs — recorded in result and metadata but do not alone fail validation.

**Rationale:** Matches umbrella Flow A policy and editorial canon §11: user-provided content is pre-approved after structural validation; style heuristics inform operator without blocking automation.

### 4. Campaign metadata on every validation attempt

**Decision:** When enough fields are known (at minimum `source_slug`, `public_slug`, `publication_date`), create campaign metadata in `ready` state if missing, then transition to `validated` or `validation_failed`. On early path failures (e.g. file not under `ready/`), skip metadata write when campaign ID cannot be derived; set `metadata_written: false` and appropriate `metadata_error_code`.

**Existing campaign handling (idempotency and guardrails):**

| Existing state | Condition | Behavior |
|----------------|-----------|----------|
| `ready` | Validation runs | Transition to `validated` or `validation_failed` per outcome |
| `validated` | Same `source_content_sha256` as stored | **Idempotent success:** return `ok: true` without appending duplicate state history entries |
| `validated` | Different `source_content_sha256` | **Blocking error** `campaign_content_hash_changed`; do not overwrite metadata; reset/revalidation deferred to a later child |
| Beyond `validated` (e.g. `blog_published`, `derivatives_generated`) | Any re-validation attempt | **Blocking error** `campaign_invalid_existing_state`; do not silently overwrite or regress lifecycle |

Future `worker-blog-publishing-endpoint` depends on idempotent re-validation when a campaign is already `validated` with unchanged content hash.

**Rationale:** Aligns with lifecycle child metadata-first posture; future publish child reads existing campaign by ID and must safely re-run validation without corrupting progressed campaigns.

### 5. Validation pipeline order

**Decision:** Run checks in fail-fast order:

1. Path and file existence (location, extension, readable file)
2. Source slug derivation and public slug validation
3. Image presence and extension (see Image validation below)
4. Frontmatter parse and required fields
5. Publication date extraction (`YYYY-MM-DD`)
6. Campaign metadata bootstrap and existing-state checks (if derivable)
7. Content body checks (blocking)
8. Anti-AI heuristics (warnings)
9. Derive `source_public_url` when date + public slug valid
10. Persist metadata and state transition

**Rationale:** Avoids writing partial campaign metadata when fundamental path/slug checks fail; still records metadata when frontmatter date enables campaign ID.

### 5a. Image validation

**Decision:** The expected companion image path is exactly `blog-posts/ready/<source_slug>.png` (same basename as the Markdown file, `.png` extension).

| Condition | Error code |
|-----------|------------|
| Expected `.png` exists | Pass — set `image_relative_path` |
| Expected `.png` missing, but a same-basename file with a non-`.png` extension exists (e.g. `.jpg`, `.webp`) | `ready_post_image_invalid_extension` |
| No file with the same basename exists at all (no `.png` and no other extension) | `ready_post_image_missing` |

**Rationale:** Distinguishes operator mistakes (wrong format) from missing assets (no image file). Publishing bridge expects PNG.

### 6. Error code registry

**Decision:** Centralize stable string error codes in the module (e.g. `READY_POST_ERROR_CODES` frozenset or constants) matching spec. Warnings use separate codes prefixed `warning_` or listed in a `WARNING_CODES` set. Metadata guardrail codes include `campaign_content_hash_changed` and `campaign_invalid_existing_state`.

**Rationale:** n8n and future endpoints branch on stable codes; tests assert exact values.

### 7. Title/H1 matching heuristic

**Decision:** Normalize frontmatter `title` and first Markdown H1 (`# `) by lowercasing, stripping punctuation, and collapsing whitespace; require substantial overlap (e.g. one normalized string contained in the other or token-set ratio above threshold). Exact match not required for minor punctuation differences.

**Rationale:** Authors may use slightly different punctuation in H1 vs frontmatter; blocking on exact string is brittle.

### 8. Configuration

**Decision:** Accept `base_path: Path` and optional `site_url: str` (default `https://silverman.pro` from publish module) for URL derivation. No new environment variables required in this child.

**Rationale:** Matches existing `config.py` / publish patterns; HTTP child can inject env later.

## Module shape

```
ready_post_validation.py
├── ReadyPostValidationResult (dataclass)
├── validate_ready_post(base_path, source_relative_path, *, site_url=...) -> ReadyPostValidationResult
├── _validate_path_and_file(...)
├── _validate_slugs(...)
├── _validate_image(...)
├── _validate_frontmatter(...)
├── _validate_content_blocking(...)
├── _collect_editorial_warnings(...)
└── _persist_campaign_metadata(...)
```

`ReadyPostValidationResult` fields (minimum):

| Field | Type | Notes |
|-------|------|-------|
| `ok` | bool | True only when no blocking errors |
| `campaign_id` | str \| None | When derivable |
| `state` | str \| None | `validated` or `validation_failed` after metadata write |
| `source_slug` | str \| None | |
| `public_slug` | str \| None | |
| `publication_date` | str \| None | `YYYY-MM-DD` |
| `source_relative_path` | str | Input path normalized |
| `image_relative_path` | str \| None | Expected PNG path |
| `source_content_sha256` | str \| None | From lifecycle helper |
| `source_public_url` | str \| None | When derivable |
| `errors` | list[str] | Stable error codes |
| `warnings` | list[str] | Warning codes |
| `metadata_written` | bool | |
| `metadata_error_code` | str \| None | When write skipped or failed |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Anti-AI heuristics produce false positives on legitimate writing | Warnings only for Flow A; do not block automation |
| Heuristic title/H1 match too loose or too strict | Tunable normalization; tests with canonical example post |
| Duplicated frontmatter parsing between publish and validation | Reuse `_split_frontmatter` from publish module |
| Campaign metadata written before content checks fail | Single transactional flow: build in memory, transition once at end |
| Import coupling to `github_pages_publish` pulls CLI concerns | Import only pure functions; consider small `slug_utils.py` extraction only if circular imports appear |

## Migration Plan

Not applicable for runtime deployment in this child (module + tests only). When a future HTTP endpoint is added, wire `validate_ready_post` behind `POST /validate-ready-post` without changing result shape.

## Open Questions

- Whether to extract shared `slug_utils.py` from `github_pages_publish.py` during implementation — decide during `/opsx-apply` if import graph is clean.
- Exact token overlap threshold for title/H1 match — implement with conservative default and adjust via tests.
