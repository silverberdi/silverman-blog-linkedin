## 1. Planning artifacts

- [x] 1.1 Review and approve `proposal.md` — umbrella reference (slice 4), goals, non-goals, capability scope
- [x] 1.2 Review and approve `design.md` — service module shape, validation-first flow, lifecycle transitions, bridge reuse, idempotency
- [x] 1.3 Review and approve `specs/worker-blog-publishing-endpoint/spec.md` — testable requirements and error codes
- [x] 1.4 Run `openspec validate worker-blog-publishing-endpoint --strict` and fix any issues

## 2. Blog publish flow module

- [x] 2.1 Create `src/silverman_blog_linkedin/blog_publish_flow.py` with `BlogPublishResult` dataclass and stable error code constants
- [x] 2.2 Implement `publish_blog_post(base_path, source_relative_path, *, site_url, public_slug_override, github_pages_repo_path, environ)` orchestration entry point
- [x] 2.3 Implement preflight path/source inspection to derive `source_slug`, `public_slug`, `publication_date`, `source_content_sha256`, `campaign_id`, and expected blog idempotency key
- [x] 2.4 Implement idempotent `already_published` short-circuit before `validate_ready_post()` when campaign is `blog_published` with `flow_a`, matching idempotency key, matching content hash, and stored `source_public_url`
- [x] 2.5 For non-published campaigns, call `validate_ready_post()` before publish side effects; on failure return `status: failed` with `blog_publish_validation_failed` and embedded `validation` summary
- [x] 2.6 Implement campaign eligibility checks: Flow B rejection (`blog_publish_flow_b_not_allowed`), invalid states (`validation_failed`, `error`, regressive states beyond `blog_published`), content hash mismatch (`blog_publish_content_hash_changed`); handle `ready` via validation, not upfront rejection
- [x] 2.7 Implement `validated` → `blog_publish_pending` transition via `campaign_lifecycle.transition_state`
- [x] 2.8 Inspect `github_pages_publish.py` actual signatures during apply; invoke bridge via `run_publish` (or thin wrapper) with `apply=True` and configured `SILVERMAN_GITHUB_PAGES_REPO_PATH`; map `plan.public_url` to `source_public_url`
- [x] 2.9 Handle `blog_publish_target_exists` when bridge targets exist without matching metadata idempotency proof
- [x] 2.10 On success transition `blog_publish_pending` → `blog_published`; update `blog_publish` object (`idempotency_key`, `status`, `source_public_url`, `published_at`, `public_repo_path`)
- [x] 2.11 On bridge or unexpected failure set `blog_publish.status: failed` with appropriate `error_code`; handle `blog_publish_public_repo_not_configured`
- [x] 2.12 Persist campaign metadata via `write_campaign_metadata`; preserve metadata body exclusion (no Markdown or draft bodies)

## 3. HTTP endpoint

- [x] 3.1 Add `PublishBlogPostRequest` Pydantic model (`source_relative_path`, optional `site_url`, optional `public_slug`)
- [x] 3.2 Add `POST /publish-blog-post` route in `main.py` with `Depends(require_api_key)`
- [x] 3.3 Wire route to `publish_blog_post()` using settings from `load_settings()` and env for public repo path
- [x] 3.4 Serialize `BlogPublishResult` to JSON response with all required fields (`status`, campaign fields, `validation`, `blog_publish`, `metadata_written`, `metadata_error_code`)

## 4. Tests

- [x] 4.1 Add `tests/test_blog_publish_flow.py` with temp editorial base and fake public repo checkout fixtures
- [x] 4.2 Test validation failure prevents publish (`blog_publish_validation_failed`; no public repo writes)
- [x] 4.3 Test successful publish transitions campaign to `blog_published` and writes `_posts/` + `assets/images/` files
- [x] 4.4 Test response includes `source_public_url` matching bridge URL
- [x] 4.5 Test idempotent re-run returns `status: completed` with `blog_publish.status: already_published` without calling `validate_ready_post()` and without duplicate writes
- [x] 4.5a Test `ready` campaign is validated then published (no upfront `blog_publish_invalid_campaign_state`)
- [x] 4.6 Test target exists without matching metadata fails with `blog_publish_target_exists`
- [x] 4.7 Test invalid campaign state fails with `blog_publish_invalid_campaign_state`
- [x] 4.8 Test changed content hash fails with `blog_publish_content_hash_changed`
- [x] 4.9 Test campaign metadata does not store full Markdown body
- [x] 4.10 Add HTTP endpoint tests: auth required, successful publish response shape, unauthorized rejected
- [x] 4.11 Confirm no n8n workflow JSON changed and no LinkedIn draft/package generated
- [x] 4.12 Run full test suite (`pytest`) and confirm no regressions

## 5. Verification

- [x] 5.1 Confirm no source file moves, git commit/push, or LinkedIn derivative generation added
- [x] 5.2 Confirm umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` remains active (not archived)
- [x] 5.3 Run `openspec validate --all` and confirm all changes pass
