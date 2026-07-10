## 1. Public asset copy helper

- [x] 1.1 Add `BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED` constant and a thin `copy_public_blog_image` (or equivalent) helper in `github_pages_publish.py` that validates repo layout, resolves `assets/images/<public_slug>.png`, copies atomically with mode `0644`, and refuses overwrite when target exists
- [x] 1.2 Add unit tests for the helper: successful copy, refuse overwrite when target exists, missing `assets/images/` layout failure

## 2. Detection and handoff orchestration

- [x] 2.1 Extend `_detection_outcome` (or equivalent) in `blog_image_generation.py` to evaluate public repo `assets/images/<public_slug>.png` in addition to editorial ready sibling PNG
- [x] 2.2 Implement public asset reuse path: skip ComfyUI, ensure canonical front matter, optionally backfill ready sibling from public asset when missing (never overwrite existing ready sibling); record non-blocking warning when backfill fails but publish can proceed using public asset
- [x] 2.3 Implement ready sibling adoption path: copy to public assets when public target missing, patch front matter when needed, skip ComfyUI
- [x] 2.4 After ComfyUI generation, hand off editorial PNG to public assets; return `blog_image_public_asset_handoff_failed` on copy failure
- [x] 2.5 Extend `BlogImageGenerationResult` and metadata summary with `public_asset_handoff_status`, `public_asset_source`, `public_repo_image_relative_path`, `ready_sibling_backfill_status`, and optional `warnings[]`
- [x] 2.6 Accept `github_pages_repo_path` on `ensure_blog_image()` (default from `SILVERMAN_GITHUB_PAGES_REPO_PATH`); extend dry-run to report planned handoff without writes

## 3. Publish flow integration

- [x] 3.1 Pass `github_pages_repo_path` from `publish_blog_post()` into `ensure_blog_image()`
- [x] 3.2 Ensure publish failure surfaces `blog_image_public_asset_handoff_failed` distinctly in `errors[]` and `blog_image_generation` summary
- [x] 3.3 Verify bridge apply still succeeds when public image already handed off (non-overwrite safe)

## 4. Automated tests

- [x] 4.1 Test: public asset exists, ready sibling missing, backfill succeeds → no ComfyUI call, publish image step succeeds
- [x] 4.2 Test: public asset exists, ready sibling missing, backfill fails but publish can proceed → no ComfyUI, non-blocking warning, no `blog_image_public_asset_handoff_failed`
- [x] 4.3 Test: ready sibling exists, public asset missing → adopt/copy succeeds, no ComfyUI
- [x] 4.4 Test: ready sibling exists, public asset missing, handoff fails → `blog_image_public_asset_handoff_failed`, no ComfyUI
- [x] 4.5 Test: ComfyUI fake generates image → public handoff succeeds
- [x] 4.6 Test: retry after local sibling PNG exists → no duplicate ComfyUI call, public asset adopted
- [x] 4.7 Test: retry after public asset already exists → no duplicate ComfyUI call
- [x] 4.8 Test: post `02-deferring-is-not-avoiding-it-can-be-architecture` regression scenario (canonical front matter, sibling PNG, missing public asset)
- [x] 4.9 Extend `tests/test_blog_publish_flow.py` for handoff failure, backfill warning, and success paths through `publish_blog_post`
- [x] 4.10 Ensure tests use non-root temp directories and do not assume root-owned files

## 5. Operator documentation

- [x] 5.1 Update `docs/workflows/blog-publishing-bridge.md` (or adjacent ops doc) with automatic public asset handoff, public asset authority for Jekyll, optional ready sibling backfill, canonical Jekyll image path, no manual copy requirement, and retry reuse behavior
- [x] 5.2 Document handoff failure troubleshooting (`blog_image_public_asset_handoff_failed`, public repo path permissions)

## 6. Validation

- [x] 6.1 Run `pytest` for new and affected tests
- [x] 6.2 Run `openspec validate blog-image-public-asset-handoff --strict`
- [x] 6.3 Run `openspec validate --all --strict`
