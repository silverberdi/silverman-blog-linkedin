## 1. Planning artifacts

- [x] 1.1 Review and approve `proposal.md` — umbrella reference (slice 3), goals, non-goals, capability scope
- [x] 1.2 Review and approve `design.md` — module shape, blocking vs warnings, metadata flow, reuse decisions
- [x] 1.3 Review and approve `specs/ready-post-editorial-validation/spec.md` — testable requirements and error codes
- [x] 1.4 Run `openspec validate ready-post-editorial-validation --strict` and fix any issues

## 2. Ready post validation module

- [x] 2.1 Create `src/silverman_blog_linkedin/ready_post_validation.py` with `ReadyPostValidationResult` dataclass and stable error/warning code constants
- [x] 2.2 Implement path and file checks (`ready_post_not_under_ready`, `ready_post_not_markdown`, `ready_post_missing`)
- [x] 2.3 Reuse slug helpers from `github_pages_publish.py` for `source_slug`, `public_slug`, and `invalid_public_slug`
- [x] 2.4 Implement image validation (`ready_post_image_missing`, `ready_post_image_invalid_extension`) with expected `blog-posts/ready/<source_slug>.png`
- [x] 2.5 Implement frontmatter parsing and required-field validation per spec (`title`, `audience`, `type`, `language`, `layout`, `date`, `categories`, `tags`, `description`, `image`)
- [x] 2.6 Implement publication date extraction (`YYYY-MM-DD`) and `source_public_url` derivation via publish bridge `public_url()`
- [x] 2.7 Implement blocking content checks (`ready_post_empty`, `content_missing_h1`, `content_title_mismatch`, `content_contains_todo`, `content_contains_secret_marker`, local image refs, non-Silverman publish targets, embedded LinkedIn drafts)
- [x] 2.8 Implement Flow A editorial warning heuristics (anti-AI openings, generic endings/transitions, weak CTA, influencer tone, style drift) as non-blocking `warnings[]`
- [x] 2.9 Integrate `campaign_lifecycle.py`: `compute_source_content_sha256`, `build_initial_campaign_metadata`, `transition_state` (`ready` → `validated` or `validation_failed`), `write_campaign_metadata`, `read_campaign_metadata`; handle idempotent re-validation (`validated` + same hash), `campaign_content_hash_changed`, and `campaign_invalid_existing_state`
- [x] 2.10 Implement `validate_ready_post(base_path, source_relative_path, *, site_url=...)` orchestrating the full pipeline and returning `ReadyPostValidationResult`

## 3. Tests

- [x] 3.1 Add `tests/test_ready_post_validation.py` with temp editorial base fixtures (`blog-posts/ready/`, `metadata/campaigns/`)
- [x] 3.2 Test canonical pass path: `01-why-i-did-not-start-with-the-database.md` + `.png` → `ok: true`, slugs, `source_public_url`, `state: validated`
- [x] 3.3 Test path/extension failures (`ready_post_not_under_ready`, `ready_post_not_markdown`, `ready_post_missing`)
- [x] 3.4 Test slug failures (`invalid_public_slug`)
- [x] 3.5 Test image failures (`ready_post_image_missing`, `ready_post_image_invalid_extension`)
- [x] 3.6 Test frontmatter failures (missing, invalid YAML, required field, date, image path)
- [x] 3.7 Test content blocking failures (empty body, missing H1, title mismatch, TODO, secret markers)
- [x] 3.8 Test anti-AI pattern produces warnings only (`ok: true` with non-empty `warnings`)
- [x] 3.9 Test campaign metadata create/update, state transitions, idempotent re-validation (same hash), `campaign_content_hash_changed`, and `campaign_invalid_existing_state`
- [x] 3.10 Test metadata write failure surfaces `metadata_written: false` and `metadata_error_code`
- [x] 3.11 Run full test suite (`pytest`) and confirm no regressions

## 4. Verification

- [x] 4.1 Confirm no HTTP endpoints, n8n workflow JSON, file moves, or GitHub publish behavior added
- [x] 4.2 Confirm umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` remains active (not archived)
- [x] 4.3 Run `openspec validate --all` and confirm all changes pass
