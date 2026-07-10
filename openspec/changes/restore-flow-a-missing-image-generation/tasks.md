## 1. Pre-generation validation

- [x] 1.1 Add `validate_ready_post_pre_generation()` in `ready_post_validation.py` allowing missing/empty generatable `image` and generatable missing PNG when generation enabled
- [x] 1.2 Keep non-empty non-canonical `image` blocking in pre-generation
- [x] 1.3 Add `source_prefix` / active-folder derivation helper shared by pre-generation, full validation, and image generation
- [x] 1.4 Update full `validate_ready_post()` to require canonical non-empty `image` and companion PNG from active folder after remediation
- [x] 1.5 Add unit tests: absent `image` field; empty `image`; non-canonical non-empty `image` blocking; generation-disabled strict full validation; queued path

## 2. Staged editorial image remediation

- [x] 2.1 Extract `ensure_editorial_blog_image()` (or equivalent internal phase) — detect, generate/adopt/backfill locally, patch frontmatter, no public repo write
- [x] 2.2 Refactor `blog_image_generation.py` missing-image detection to derive companion path from `source_relative_path` (remove hardcoded `READY_RELATIVE_PREFIX` for detect/write)
- [x] 2.3 Ensure ComfyUI output writes beside active Markdown (`blog-posts/queued/<slug>.png` when source is queued)
- [x] 2.4 Implement active-folder sibling backfill from readable public asset without ComfyUI
- [x] 2.5 Preserve legacy direct-ready behavior: generate and patch missing frontmatter `image`
- [x] 2.6 Extend `test_blog_image_generation.py` with absent/empty `image`, queued-source generation, public backfill, skip-with-existing-queued-PNG, ready-path regression

## 3. Staged public asset handoff

- [x] 3.1 Extract `handoff_public_blog_image()` (or equivalent) callable only after full validation
- [x] 3.2 Keep `ensure_blog_image()` as compatibility facade for non-publish callers; `publish_blog_post` uses staged ordering internally
- [x] 3.3 Add test proving full-validation failure performs no public asset write (inject public repo I/O spy/fake)
- [x] 3.4 Add test: handoff failure after full validation blocks publish and preserves editorial PNG

## 4. Publish flow staged orchestration

- [x] 4.1 Update `blog_publish_flow.py` to call pre-generation → editorial remediation → authorized hash reconciliation → full validation → handoff → publish
- [x] 4.2 Implement authorized hash reconciliation: `intake_source_content_sha256`, active `source_content_sha256`, idempotency key recompute; block on metadata-write failure
- [x] 4.3 Ensure ComfyUI/handoff failures return specific error codes and never mask as `ready_post_image_missing`
- [x] 4.4 Update `test_blog_publish_flow.py` for staged ordering, hash reconciliation, queued Markdown-only path, and direct ready regression

## 5. GitHub Pages source resolution

- [x] 5.1 Refactor `github_pages_publish.resolve_source_paths` to accept `source_relative_path` and resolve ready/queued/processed pairs with confinement
- [x] 5.2 Wire `blog_publish_flow` to pass active `source_relative_path` into publish planning
- [x] 5.3 Add tests for queued and processed resolution; preserve CLI ready-only behavior

## 6. Connector ordering and claim-release matrix

- [x] 6.1 Remove blocking `validate_ready_post()` call before `publish_blog_post` in `editorial_calendar_flow_a_execute._execute_flow_a_item`
- [x] 6.2 Implement image failure claim-release matrix: ComfyUI transient → release once/retryable; handoff failure → release once/repair_required; deterministic validation error move owns closure (no redundant release)
- [x] 6.3 Map `publish_blog_post` validation/generation/handoff failures to post-acceptance policies per delta specs
- [x] 6.4 Remove or narrow `validate_ready_post` patches in connector tests that mask Markdown-only path behavior
- [x] 6.5 Add integration tests asserting persisted state and exact `release_flow_a_execution` call count per failure class

## 7. Campaign metadata and lifecycle

- [x] 7.1 Add `intake_source_content_sha256` persistence at queue acceptance when not already present
- [x] 7.2 Persist authorized active hash update after frontmatter patch on same campaign
- [x] 7.3 Ensure `complete_flow_a_source_lifecycle` discovers and moves `blog-posts/queued/<slug>.png` with Markdown
- [x] 7.4 Update metadata (`queued_image_relative_path`, `processed_image_relative_path`) when generated PNG present
- [x] 7.5 Extend lifecycle tests for generated queued companion move and partial-move recovery

## 8. Mandatory integration test matrix (retain 17 + explicit additions)

Use real `validate_ready_post_pre_generation` and `validate_ready_post`; fake only ComfyUI client and public repo I/O boundaries.

- [x] 8.1 Add integration test module (for example `test_flow_a_markdown_only_image_generation.py`) without autouse-stubbing validation entry points
- [x] 8.2 Test 1: Markdown-only source in `ready/` is queue-accepted
- [x] 8.3 Test 2: No initial PNG exists
- [x] 8.4 Test 3: Connector does not fail with `ready_post_image_missing` before generation
- [x] 8.5 Test 4: Fake ComfyUI client called exactly once
- [x] 8.6 Test 5: Generated PNG written to `blog-posts/queued/<source_slug>.png`
- [x] 8.7 Test 6: Generated PNG copied to configured public assets directory only after full validation
- [x] 8.8 Test 7: Campaign metadata records generation and handoff evidence
- [x] 8.9 Test 8: Full validation runs successfully after editorial remediation
- [x] 8.10 Test 9: Blog publication proceeds
- [x] 8.11 Test 10: Package and scheduling proceed
- [x] 8.12 Test 11: Lifecycle completion moves queued Markdown and generated PNG to `processed/`
- [x] 8.13 Test 12: No Markdown or generated PNG remains in `ready/` or `queued/`
- [x] 8.14 Test 13: ComfyUI failure blocks publication with specific generation error (not `ready_post_image_missing`)
- [x] 8.15 Test 14: Existing queued PNG skips ComfyUI
- [x] 8.16 Test 15: Existing ready direct-publish behavior remains valid
- [x] 8.17 Test 16: Public handoff failure blocks publication and preserves generated image
- [x] 8.18 Test 17: Full regression suite passes (`pytest` or project test command)
- [x] 8.19 Test 18: Queued Markdown with absent `image` field remediated through publish path
- [x] 8.20 Test 19: Queued Markdown with empty `image` remediated through publish path
- [x] 8.21 Test 20: Non-canonical non-empty `image` remains blocking in pre-generation
- [x] 8.22 Test 21: Generation disabled does not bypass full validation
- [x] 8.23 Test 22: Full-validation failure produces no public asset write
- [x] 8.24 Test 23: Authorized frontmatter patch updates campaign hash and idempotency key safely; same `campaign_id` retained
- [x] 8.25 Test 24: Unrelated Markdown body mutation rejected (`campaign_content_hash_changed` or equivalent)
- [x] 8.26 Test 25: ComfyUI transient failure ends queued/idle/retryable; `release_flow_a_execution` called exactly once
- [x] 8.27 Test 26: Handoff failure ends queued/idle/repair_required; `release_flow_a_execution` called exactly once
- [x] 8.28 Test 27: Deterministic validation error move does not cause redundant release
- [x] 8.29 Test 28: Public asset reuse backfills queued sibling and passes full validation without ComfyUI
- [x] 8.30 Test 29: Public asset reuse with failed queued-sibling backfill does not publish
- [x] 8.31 Test 30: Hash metadata persistence failure blocks handoff and publish

## 9. Validation and review

- [x] 9.1 Run `openspec validate restore-flow-a-missing-image-generation --strict`
- [x] 9.2 Run `openspec validate --all --strict`
- [x] 9.3 Confirm proposal, design, specs, and tasks are consistent with canonical specs and no archived change was modified
