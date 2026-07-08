## 0. Dependency gate (before any implementation)

- [ ] 0.1 Confirm OpenSpec change `comfyui-blog-image-generation` is implemented, validated, and archived
- [ ] 0.2 Confirm live Flow A posts expose canonical `/assets/images/<public_slug>.png` on the public blog after publish

## 1. Configuration and types

- [ ] 1.1 Extend `linkedin_config.py` with preview settings (`SILVERMAN_LINKEDIN_PREVIEW_ENABLED`, `PREVIEW_REQUIRED`, `PREVIEW_STRATEGY`, `PREVIEW_OG_TIMEOUT_SECONDS`, `PREVIEW_IMAGE_MAX_BYTES`) with safe defaults
- [ ] 1.2 Add `LinkedInPreviewPlan` (or equivalent) dataclass with strategy, image URL/path, OG sufficiency, and image URN fields
- [ ] 1.3 Document new env vars in `deploy/server/silverman-worker.env.example`

## 2. Preview planning module

- [ ] 2.1 Create `linkedin_preview_flow.py` with `plan_linkedin_preview()` entry point
- [ ] 2.2 Implement `resolve_preview_image_url()` from campaign metadata and canonical image path conventions
- [ ] 2.3 Implement bounded OG metadata fetch and sufficiency check (`og:image`, `og:title`, `og:description`, canonical URL)
- [ ] 2.4 Implement strategy selection for `og_metadata`, `linkedin_explicit`, and `auto` modes
- [ ] 2.5 Implement fail-closed gating when `preview_required` is true (`linkedin_preview_required_blocked_publish`)

## 3. LinkedIn Images API client

- [ ] 3.1 Create `linkedin_image_client.py` with `LinkedInImageClientProtocol` and fake implementation for tests
- [ ] 3.2 Implement `upload_member_image()` (initialize → upload bytes → register) returning image URN
- [ ] 3.3 Enforce `PREVIEW_IMAGE_MAX_BYTES` and map failures to `linkedin_preview_image_upload_failed`
- [ ] 3.4 Verify Images API payload/headers against official LinkedIn documentation at apply time

## 4. LinkedIn post client extensions

- [ ] 4.1 Add `build_article_post_payload()` for OG/article link-style posts referencing `source_public_url`
- [ ] 4.2 Add `create_member_article_post()` (or extend existing helper) supporting optional `linkedin_image_urn` attachment
- [ ] 4.3 Verify Posts API article/link payload fields against official LinkedIn documentation at apply time

## 5. Publish-due integration

- [ ] 5.1 Integrate `plan_linkedin_preview()` into `publish_linkedin_due_variants()` before post creation when preview enabled
- [ ] 5.2 Preserve legacy text-only path when `SILVERMAN_LINKEDIN_PREVIEW_ENABLED=false`
- [ ] 5.3 Implement `linkedin_explicit` upload path and attach URN to post payload
- [ ] 5.4 Implement optional text-only fallback with warning when preview enabled but not required and preview fails
- [ ] 5.5 Extend per-variant HTTP response and campaign `linkedin_publication` metadata with preview fields
- [ ] 5.6 Ensure preview planning failures with `preview_required=true` do not mark variant `failed`

## 6. Tests

- [ ] 6.1 Add `tests/test_linkedin_preview.py` (or extend `tests/test_linkedin_publication.py`) with fake OG client and fake image client
- [ ] 6.2 Test preview disabled → unchanged text-only behavior
- [ ] 6.3 Test dry-run reports planned strategy and `preview_image_url`
- [ ] 6.4 Test `og_metadata` sufficient path and `auto` fallback to `linkedin_explicit`
- [ ] 6.5 Test `preview_required` blocks publish without LinkedIn API call on preview failure
- [ ] 6.6 Test successful explicit upload records `linkedin_image_urn` in metadata
- [ ] 6.7 Confirm no live LinkedIn API calls in default `pytest` runs

## 7. Operator documentation and smoke

- [ ] 7.1 Update `docs/deployment/linkedin-publication-prerequisites.md` with preview configuration, strategies, and dependency on archived `comfyui-blog-image-generation`
- [ ] 7.2 Extend `deploy/server/run-linkedin-publication-smoke.sh` dry-run output to report planned preview strategy when enabled
- [ ] 7.3 Update README LinkedIn publication section with preview flags and fail-closed semantics

## 8. Validation

- [ ] 8.1 Run `openspec validate linkedin-article-preview-image-support --strict` and fix any spec issues
- [ ] 8.2 Run full `pytest` and fix regressions
- [ ] 8.3 Manual dry-run on staging campaign: verify planned strategy, image URL, and no LinkedIn API calls
