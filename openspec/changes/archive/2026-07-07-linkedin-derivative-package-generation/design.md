## Context

### Umbrella and sequencing

This is **child change 5** under the active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`. Completed siblings:

| Slice | Change | Delivers |
|-------|--------|----------|
| 1 | `editorial-canon-and-linkedin-distribution-strategy` | `content-strategy/silverman-editorial-system.md`, spec `editorial-canon` |
| 2 | `flow-a-lifecycle-and-duplicate-prevention` | `campaign_lifecycle.py`, spec `flow-a-lifecycle` |
| 3 | `ready-post-editorial-validation` | `ready_post_validation.py`, spec `ready-post-editorial-validation` |
| 4 | `worker-blog-publishing-endpoint` | `POST /publish-blog-post`, `blog_publish_flow.py`, spec `worker-blog-publishing-endpoint` |
| 5 | `linkedin-derivative-package-generation` (this change) | `POST /generate-linkedin-package`, `linkedin_package_flow.py` |

The umbrella lifecycle diagram places **GENERATE DERIVATIVE PACKAGE** after **CONFIRM URL**. Slice 4 records publish-confirmed `source_public_url` and transitions to `blog_published`; slice 5 generates the multi-variant package and transitions to `derivatives_generated`.

### Current state

| Component | LinkedIn package behavior today |
|-----------|--------------------------------|
| `POST /generate-linkedin-draft` | Generates one variant per call; writes to `linkedin-posts/review/` with timestamped filenames; writes run metadata to `metadata/runs/`; no campaign lifecycle integration |
| `linkedin_prompt.py` | Builds DeepSeek chat messages with variant/audience/tone hints and `source_public_url` CTA rules |
| `deepseek_client.py` | `generate_linkedin_draft_content()` calls DeepSeek API |
| `draft_writer.py` | Exclusive write under `linkedin-posts/review/` with collision retries |
| `campaign_lifecycle.py` | States through `derivatives_generated`; `build_derivative_idempotency_key()`; `CANONICAL_VARIANT_IDS` |
| `blog_publish_flow.py` | Leaves campaign in `blog_published` with `source_public_url` |
| `main.py` | No package generation route |

Gaps for Flow A package generation:

- No multi-variant coordinated package generation tied to `campaign_id`.
- No deterministic artifact paths per campaign/variant.
- No campaign lifecycle transitions for derivatives.
- No package-level idempotency in campaign metadata.
- Existing single-draft endpoint does not enforce `blog_published` or confirmed URL prerequisites.

### Policy references

- Umbrella: `flow-a-automatic-blog-linkedin-publishing-roadmap`
- Editorial canon: `openspec/specs/editorial-canon/spec.md`, `content-strategy/silverman-editorial-system.md`
- Lifecycle: `openspec/specs/flow-a-lifecycle/spec.md`, `campaign_lifecycle.py`
- Blog publish: `openspec/specs/worker-blog-publishing-endpoint/spec.md`, `blog_publish_flow.py`
- Single-draft generation: `openspec/specs/deepseek-linkedin-draft-generation/spec.md`, `linkedin_prompt.py`, `deepseek_client.py`, `draft_writer.py`

## Goals / Non-Goals

**Goals:**

- Implement `generate_linkedin_package(base_path, *, campaign_id=None, source_relative_path=None, variants=None, topic_theme=None, ...)` as the single service entry point for Flow A package generation.
- Add `POST /generate-linkedin-package` with API-key auth consistent with existing worker endpoints.
- Require campaign `flow_a`, state `blog_published`, non-null `source_public_url`, and matching source file/hash.
- Generate all four canonical variants by default unless request narrows list.
- Write one artifact per variant at `linkedin-posts/generated/<campaign_id>/<variant_id>.md`.
- Record package metadata in campaign JSON (`linkedin_package` object + `variants[]` entries with paths/hashes only).
- Transition `blog_published` → `derivatives_pending` → `derivatives_generated` on success.
- Support idempotent re-run when `derivatives_generated` and package idempotency key matches.
- Return `LinkedInPackageResult` dataclass with fields required for n8n branching.
- Add `tests/test_linkedin_package_generation.py` with mocked generation for determinism.

**Non-Goals:**

- LinkedIn distribution scheduling, `schedule_at`, or `publish_state` metadata.
- n8n workflow JSON changes.
- LinkedIn API publication.
- Flow B package generation.
- Physical source file moves.
- Git commit or git push.
- Archiving umbrella or this child.

## Decisions

### 1. Service module + thin HTTP route

**Decision:** Implement `linkedin_package_flow.py` with `generate_linkedin_package()` orchestrating campaign reads, eligibility checks, lifecycle transitions, per-variant generation, artifact writes, and metadata persistence; wire `POST /generate-linkedin-package` in `main.py` as a thin adapter.

**Rationale:** Matches slices 3–4 pattern (module-first, testable without HTTP). Keeps FastAPI layer free of package logic.

**Alternatives considered:** Extend `POST /generate-linkedin-draft` with a `package_mode` flag — rejected; mixes unrelated contracts and complicates existing tests.

### 2. Flow A generated path under `linkedin-posts/generated/`

**Decision:** Persist Flow A package artifacts at deterministic paths:

```
linkedin-posts/generated/<campaign_id>/<variant_id>.md
```

Do not use `linkedin-posts/review/` for Flow A packages. The review folder remains for the existing single-draft endpoint and manual/Flow B review workflows.

**Rationale:** Umbrella D5 reserves auto-approved paths for Flow A; deterministic campaign/variant paths simplify idempotency, scheduling child lookups, and operator inspection. Avoids implying human review is required for Flow A.

**Alternatives considered:** Reuse `linkedin-posts/review/` — rejected; conflicts with Flow A automatic policy and non-deterministic timestamp filenames.

### 3. Reuse generation stack; extract shared variant generation helper

**Decision:** Add an internal helper (for example `_generate_variant_draft()` in `linkedin_package_flow.py` or a small `linkedin_draft_generation.py` module) that:

1. Reads source Markdown from disk (campaign `source_relative_path`).
2. Resolves variant editorial hints (`audience`, `tone`) from a static map aligned with editorial canon.
3. Calls `linkedin_prompt.build_chat_messages()` with `source_public_url` from campaign metadata.
4. Calls injectable `generate_linkedin_draft_content()` (default: `deepseek_client.generate_linkedin_draft_content`).
5. Writes artifact via a new `write_generated_variant_file()` helper with exclusive create at the deterministic path.

Do not duplicate DeepSeek client behavior or prompt logic. Do not change `POST /generate-linkedin-draft` response contract.

**Rationale:** Single source of truth for prompts and provider calls. Injectable generator enables deterministic tests.

**Alternatives considered:** HTTP loop calling `POST /generate-linkedin-draft` internally — rejected; wrong output path, no campaign integration, extra HTTP overhead.

### 4. Package generation flow sequence

**Decision:** `generate_linkedin_package()` executes in this order:

1. **Resolve campaign** — from `campaign_id` or derive from `source_relative_path` via campaign metadata lookup.
2. **Eligibility** — reject: no campaign, `flow_b`, state before `blog_published`, regressive states beyond `derivatives_generated` that are not idempotent hits, missing `source_public_url`, missing source file, content hash mismatch, unexpected `source_public_url` change.
3. **Idempotent short-circuit** — if state is `derivatives_generated`, stored `linkedin_package.idempotency_key` matches expected package key, content hash matches, and all requested variant artifacts exist with matching hashes in metadata: return `status: completed` without regeneration or new state history.
4. **Orphan file guard** — if target artifact files exist on disk but campaign metadata does not prove matching package idempotency: fail with `linkedin_package_target_exists`.
5. **Variant resolution** — default to all `CANONICAL_VARIANT_IDS`; validate requested subset; fail on invalid variant with `linkedin_package_invalid_variant` or empty list with `linkedin_package_no_variants`.
6. **Transition** — `blog_published` → `derivatives_pending`.
7. **Generate variants** — sequential per variant; all requested variants MUST succeed. If any variant fails, the package result is `status: failed` with `linkedin_package_generation_failed`. Partial variant retry is out of scope for this slice.
8. **Persist** — update `variants[]` in campaign metadata, write `linkedin_package` object, transition `derivatives_pending` → `derivatives_generated`.

**Rationale:** Aligns with umbrella lifecycle and blog publish idempotency patterns. Fail-safe on orphan files prevents silent overwrite.

### 5. Package idempotency key

**Decision:** Define package-level idempotency key:

```
package:{campaign_id}:{source_content_sha256}:{variant_list}:{flow}
```

Where `{variant_list}` is a comma-separated sorted list of canonical variant IDs (for example `engineering-leadership,executive-recruiter,short-provocative,technical-architect`).

Store in campaign metadata as `linkedin_package.idempotency_key`. Per-variant derivative keys continue using `build_derivative_idempotency_key()` from `campaign_lifecycle.py`.

**Rationale:** Enables whole-package idempotent re-runs. Per-variant derivative keys support traceability; partial variant retry may be considered in a later child.

**Alternatives considered:** Package key from campaign_id only — rejected; variant list changes must produce different keys.

### 6. Campaign metadata shape extensions

**Decision:** Extend campaign JSON with:

```json
{
  "linkedin_package": {
    "package_id": "<campaign_id>-pkg",
    "idempotency_key": "package:...",
    "package_status": "generated",
    "generated_at": "<UTC ISO8601>",
    "source_public_url": "<confirmed URL>",
    "variant_ids": ["executive-recruiter", "..."]
  },
  "variants": [
    {
      "variant": "executive-recruiter",
      "audience": "recruiters and hiring managers",
      "tone": "executive",
      "idempotency_key": "derivative:...",
      "artifact_relative_path": "linkedin-posts/generated/<campaign_id>/executive-recruiter.md",
      "derivative_content_sha256": "<hex>",
      "source_public_url": "<confirmed URL>",
      "generated_at": "<UTC ISO8601>",
      "provider": "deepseek",
      "model": "deepseek-v4-flash"
    }
  ]
}
```

No `markdown_content`, `generated_draft_content`, or draft body in campaign metadata or HTTP responses. Artifact files MAY contain the full generated LinkedIn post body. Campaign metadata and HTTP responses MUST include paths, hashes, variant IDs, provider/model, and status fields only.

**Rationale:** Satisfies umbrella metadata traceability without body storage. Scheduling child reads `variants[]` for paths and hashes.

### 7. Variant editorial defaults

**Decision:** Static map from canonical variant ID to default `audience` and `tone` hints (aligned with `#linkedin-derivative-package` in editorial canon):

| variant_id | audience hint | tone hint |
|------------|---------------|-----------|
| `executive-recruiter` | recruiters and hiring managers for senior architecture roles | executive, hireable judgment |
| `technical-architect` | software architects and senior developers | technical depth, design trade-offs |
| `engineering-leadership` | engineering managers and technical leaders | leadership, delivery implications |
| `short-provocative` | senior ICs and architecture practitioners | concise, pattern-interrupt |

Request `topic_theme` applies to all variants in the package when provided.

**Rationale:** Operationalizes editorial canon without loading/parsing the full artifact at runtime in this slice (consistent with lifecycle child posture).

### 8. Source public URL in every variant

**Decision:** Every generated variant MUST include the campaign's publish-confirmed `source_public_url` exactly once in the artifact body. Prompt assembly MUST pass `source_public_url` to `build_chat_messages()` for all package variants.

Runtime MUST validate URL occurrence count before writing the artifact or before finalizing variant metadata. If generated content contains the URL zero times or more than once, treat that variant as generation failure with `linkedin_package_generation_failed` and fail the whole package.

Tests MUST use a mocked generator that returns the URL exactly once per variant.

**Rationale:** Umbrella CTA rules and traceability; scheduling child depends on live link in artifacts.

### 9. HTTP request/response contract

**Decision:**

**Request** (`POST /generate-linkedin-package`):

- Exactly one of `campaign_id` or `source_relative_path` (required).
- Optional `variants` (array of canonical variant IDs).
- Optional `topic_theme`.
- Optional `site_url` only if needed for validation; prefer campaign `source_public_url`.
- `extra="forbid"` on Pydantic model.

**Response** (`LinkedInPackageResult`):

- `status`: `completed` | `failed`
- `campaign_id`, `state`, `package_id`
- `source_relative_path`, `source_public_url`, `source_content_sha256`
- `variants`: array of per-variant summaries (paths, hashes, variant_id — not full bodies)
- `package`: package metadata object
- `errors`, `warnings`
- `metadata_written`, `metadata_error_code`

The response MUST NOT include `generated_draft_content`, `markdown_content`, or variant body text.

Auth: `Depends(require_api_key)` consistent with `POST /publish-blog-post` and `POST /generate-linkedin-draft`.

**Rationale:** n8n branches on `status`; mirrors blog publish response patterns.

### 10. State machine integration

**Decision:**

| Step | Campaign state | Action |
|------|----------------|--------|
| Eligibility fail | any | Return `status: failed` with stable error code; no state change |
| Idempotent hit | `derivatives_generated` + matching package key | Return `completed`; no regeneration |
| Start generation | `blog_published` | Transition → `derivatives_pending` |
| Success | `derivatives_pending` | Transition → `derivatives_generated` |
| Generation failure | `derivatives_pending` | Remain or transition to `error` with `linkedin_package_generation_failed` |
| Regressive attempt | `distribution_scheduled`, `distribution_complete`, `flow_a_complete` | Fail `linkedin_package_invalid_campaign_state` |

`derivatives_generated` re-run with matching idempotency is allowed (completed, no duplicate history).

Use `transition_state(..., actor="worker")` from `campaign_lifecycle.py`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| DeepSeek latency/cost for 4 variants | Sequential generation; idempotent skip on re-run; mock in tests |
| Partial generation leaves campaign in `derivatives_pending` | All requested variants must succeed; any failure fails whole package with `linkedin_package_generation_failed`; campaign may remain in `derivatives_pending` until a full successful re-run |
| Orphan files without metadata | `linkedin_package_target_exists` fail-safe; no overwrite |
| Drift between single-draft and package prompts | Shared `build_chat_messages()` |
| `linkedin-posts/generated/` folder missing | Worker MAY create `linkedin-posts/generated/` and campaign subfolder when editorial base path is valid; MUST fail with `linkedin_package_generated_dir_not_ready` if path exists but is not a directory; MUST fail with `linkedin_package_generated_dir_not_writable` if not writable; check before DeepSeek calls |
| Existing `POST /generate-linkedin-draft` regression | No changes to its contract; shared helpers only via careful extraction |

## Migration Plan

1. Apply this child change: add module, endpoint, tests.
2. Worker MAY create `linkedin-posts/generated/` and per-campaign subfolders when editorial base path is valid; pre-check directory readiness before DeepSeek calls.
3. n8n orchestration (slice 7) will call `POST /generate-linkedin-package` after `POST /publish-blog-post` succeeds.
4. Scheduling slice (6) reads package artifacts and `variants[]` metadata.
5. Rollback: endpoint remains optional; existing single-draft workflow unaffected.

## Resolved Decisions

### 1. Partial variant failure

**Decision:** This slice requires all requested variants to succeed. If any variant fails, the package result is `status: failed` with `linkedin_package_generation_failed`. Partial variant retry may be considered in a later child but is not implemented here.

### 2. Editorial canon runtime loading

**Decision:** This slice uses a static variant editorial map (`DEFAULT_VARIANT_EDITORIAL_MAP`) aligned with the canonical editorial canon. Do not parse `content-strategy/silverman-editorial-system.md` at runtime in this slice.

### 3. `linkedin-posts/generated/` behavior

**Decision:** The worker MAY create `linkedin-posts/generated/` and the per-campaign subfolder when the editorial base path is otherwise valid. The worker MUST still fail with `linkedin_package_generated_dir_not_ready` if the path exists but is not a directory, and `linkedin_package_generated_dir_not_writable` if it cannot write there. This check MUST run before calling DeepSeek or writing variant files.

## Implementation Note (apply)

During `/opsx-apply`, inspect the real signatures and existing contracts of:

- `src/silverman_blog_linkedin/campaign_lifecycle.py`
- `src/silverman_blog_linkedin/linkedin_prompt.py`
- `src/silverman_blog_linkedin/deepseek_client.py`
- `src/silverman_blog_linkedin/draft_writer.py`
- `src/silverman_blog_linkedin/main.py`
- `src/silverman_blog_linkedin/run_metadata.py`

Use the actual signatures. Do not invent APIs.

Especially verify:

- `CANONICAL_VARIANT_IDS`
- `build_derivative_idempotency_key`
- `transition_state`
- `write_campaign_metadata`
- `build_chat_messages`
- `generate_linkedin_draft_content`

If an existing helper is too single-draft-specific, add a thin package-specific wrapper/helper without changing the existing `POST /generate-linkedin-draft` contract.
